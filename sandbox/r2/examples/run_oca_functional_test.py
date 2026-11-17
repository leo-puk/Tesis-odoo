"""Mock HTTP and reviewer inputs around real local OCA/Odoo source snapshots."""
import argparse
import ast
import difflib
import hashlib
import io
import json
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from r2.cli import main as cli
from r2.collection import connect, load
from r2.query import validate_output

COMPARE = "https://github.com/odoo/odoo/compare/16.0...17.0"
API_COMPARE = "https://api.github.com/repos/odoo/odoo/compare/16.0...17.0"
EXCLUDED_PR = "https://github.com/OCA/sale-workflow/pull/1"
CORE_PATHS = ("odoo/fields.py", "odoo/addons/base/models/ir_ui_view.py")


def hashes(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def run(output):
    project = Path(__file__).resolve().parents[1]
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a new output directory")
    output.mkdir(parents=True)
    module = project / "examples/original_module"
    module_before = hashes(module)
    final_before = hashes(project / "r2/adquisition")
    manifest_tree = ast.parse((module / "__manifest__.py").read_text(encoding="utf-8"))
    manifest = ast.literal_eval(next(n.value for n in manifest_tree.body if isinstance(n, ast.Expr)))
    if manifest["version"] != "16.0.1.0.0":
        raise ValueError("Expected the unchanged OCA 16.0.1.0.0 fixture")
    diff, provenance = [], []
    for name in CORE_PATHS:
        before = project / "examples/core16" / name
        after = project / "examples/core17" / name
        diff.append(f"diff --git a/{name} b/{name}\n")
        diff.extend(difflib.unified_diff(before.read_text(encoding="utf-8").splitlines(True),
                                        after.read_text(encoding="utf-8").splitlines(True),
                                        fromfile="a/"+name, tofile="b/"+name))
        provenance.append(dict(path=name, before_sha256=hashlib.sha256(before.read_bytes()).hexdigest(),
                               after_sha256=hashlib.sha256(after.read_bytes()).hexdigest()))
    diff_bytes = "".join(diff).encode()
    (output / "mock-response.diff").write_bytes(diff_bytes)

    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def command(args):
        with redirect_stdout(io.StringIO()) as captured:
            cli(args)
        return json.loads(captured.getvalue())

    save("plan.json", [dict(id="core", kind="github_diff", files={"core.diff": COMPARE}),
                       dict(id="excluded-oca-solution", kind="github_pr", files={"solution.json": EXCLUDED_PR})])
    # The PR URL below is an exclusion sentinel. It is never fetched or claimed
    # to be a real migration solution; the OCA module is only the query input.
    save("catalog.json", dict(allowed_urls=[COMPARE, EXCLUDED_PR], excluded_urls=[],
                              oca_repositories=["OCA/sale-workflow"], oca_addons=["sale_advance_payment"]))
    save("bindings.json", dict(sources={"core": dict(from_version="16.0", to_version="17.0",
        from_revision="local-core16-snapshot", to_revision="local-core17-snapshot")}))
    calls = []

    class Response:
        status = 200
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return diff_bytes

    def transport(req, **kwargs):
        calls.append(req.full_url)
        if req.full_url != API_COMPARE:
            raise AssertionError("Only the mocked official comparison may be requested")
        return Response()

    with patch("r2.adquisition.http.request.build_opener") as opener:
        opener.return_value.open.side_effect = transport
        capture = command(["capture-plan", str(output / "plan.json"), "--catalog", str(output / "catalog.json"), "--output", str(output)])
    inventory = json.loads(Path(capture["inventory"]).read_text(encoding="utf-8"))
    assert calls == [API_COMPARE]
    assert [r["status"] for r in inventory] == ["accepted", "excluded"]
    checks = dict(official_capture_accepted=True, oca_solution_excluded_before_network=True)
    with patch("r2.adquisition.http.request.build_opener", side_effect=AssertionError("unexpected network")):
        raw_db = output / "candidates.sqlite"
        built = command(["build", capture["inventory"], "--bindings", str(output / "bindings.json"), "--db", str(raw_db)])
        with connect(raw_db) as con:
            candidates = load(con, "changes")
            assert all(s["kind"] == "github_diff" for s in load(con, "sources"))
        query_args = ["query", str(module), "--module-name", "sale_advance_payment", "--from", "16.0", "--to", "17.0", "--format", "json"]
        candidate_output = command(query_args + ["--db", str(raw_db)])
        save("query-candidates.json", candidate_output)
        specifications = [
            ("states is no longer supported", "property:states", "python",
             "Odoo 17 warns that the states field property is no longer supported"),
            ("attributes are no longer used", "xml-attribute:attrs", "xml",
             "Odoo 17 rejects attrs/states attributes in view validation"),
        ]
        annotations, targets = [], []
        for phrase, element, layer, title in specifications:
            matches = [c for c in candidates if phrase in c["added"]]
            assert len(matches) == 1, (phrase, len(matches))
            change = matches[0]
            assert element in change["elements"], (phrase, change["elements"])
            eid = "ev-" + change["id"][4:]
            annotations.append(dict(change_id=change["id"], status="verified", title=title, layer=layer,
                reviewer="Mocked developer-review fixture; not an independent academic judgment",
                rationale="Expected review input anchored to the explicit destination code in the captured diff.",
                reviewed_at=datetime.now(timezone.utc).isoformat(), category="syntax",
                required_elements=[element], affected_elements=[element],
                destination_validity=dict(status="checked", from_version="16.0", to_version="17.0",
                    explanation="This functional fixture cites the actual warning/rejection in local Odoo 17 code; other hunk edits are not validated.", evidence_ids=[eid])))
            targets.append(dict(id=change["id"], element=element, title=title, core_file=change["file_path"],
                                destination_start=change["after_start"], destination_end=change["after_end"]))
        save("mock-review.json", annotations)
        reviewed_db = output / "reviewed.sqlite"
        command(["build", capture["inventory"], "--bindings", str(output / "bindings.json"),
                 "--annotations", str(output / "mock-review.json"), "--db", str(reviewed_db)])
        outputs = {}
        for engine in ("graph", "bm25"):
            result = command(query_args + ["--db", str(reviewed_db), "--status", "verified", "--engine", engine])
            save(f"query-{engine}.json", result)
            assert validate_output(result)["conformant"]
            assert {r["id"] for r in result["results"]} == {t["id"] for t in targets}
            assert result["summary"]["changes_found"] == 2
            assert all(r["source_citations"][0]["unit_id"] for r in result["results"])
            outputs[engine] = result["summary"]
        checks.update(both_expected_findings_retrieved=True, graph_and_bm25_conformant=True,
                      no_oca_solution_indexed=True, versions_and_provenance_preserved=True)
        control = output / "unrelated_module"
        control.mkdir()
        (control / "models.py").write_text("from odoo import fields, models\nclass Unrelated(models.Model):\n    _name = 'functional.unrelated'\n    name = fields.Char()\n", encoding="utf-8")
        negative = command(["query", str(control), "--db", str(reviewed_db), "--from", "16.0", "--to", "17.0", "--status", "verified", "--format", "json"])
        save("query-negative-control.json", negative)
        assert negative["summary"]["changes_found"] == 0
        wrong_jump = command(["query", str(module), "--module-name", "sale_advance_payment", "--db", str(reviewed_db), "--from", "17.0", "--to", "18.0", "--status", "verified", "--format", "json"])
        save("query-wrong-jump.json", wrong_jump)
        assert wrong_jump["summary"]["changes_found"] == 0
        checks.update(unrelated_module_has_no_verified_findings=True, wrong_jump_has_no_findings=True)
        accepted = [r["id"] for r in inventory if r["status"] == "accepted"]
        command(["delete-units", capture["session_id"], *accepted, "--output", str(output)])
        after_delete = command(query_args + ["--db", str(reviewed_db), "--status", "verified"])
        assert after_delete["summary"]["changes_found"] == 2
        checks["retrieval_survives_temporary_unit_deletion"] = True
    assert hashes(module) == module_before
    assert hashes(project / "r2/adquisition") == final_before
    checks.update(oca_input_unchanged=True, final_adquisition_unchanged=True)
    report = dict(passed=True, scope="functional engineering test; not a migration or academic evaluation",
                  module="sale_advance_payment", module_version=manifest["version"], jump="16.0->17.0",
                  module_path=str(module), module_repository=manifest["website"], module_hashes=module_before,
                  input_code="real unchanged local OCA snapshot", http="mocked; no live downloads",
                  review="injected mocked developer-review annotations, not automatic verification",
                  diff="computed from two real local Odoo snapshots, not a live GitHub compare response",
                  snapshot_provenance=json.loads((project / "examples/manifest.json").read_text(encoding="utf-8")),
                  core_files=provenance, candidate_hunks=built["change_count"],
                  raw_graph_summary=candidate_output["summary"], expected_targets=targets,
                  reviewed_query_summaries=outputs, checks=checks, http_calls=calls,
                  final_adquisition_hashes=final_before, output=str(output))
    save("report.json", report)
    summary = ["# Prueba funcional con módulo OCA real", "", "Resultado: aprobada.", "",
        f"Entrada: sale_advance_payment {manifest['version']}; salto consultado 16→17.", "",
        "HTTP y revisión se simularon. El código OCA y los dos snapshots del núcleo son copias reales locales sin modificar.", "",
        f"La colección produjo {built['change_count']} hunks candidatos; no son incompatibilidades confirmadas.", "",
        "Las dos anotaciones de revisión simuladas permiten comprobar que grafo y BM25 recuperan exactamente los cambios esperados:", ""]
    summary.extend("- " + target["title"] for target in targets)
    summary.extend(["", "El control sin esas condiciones y el salto 17→18 devolvieron cero hallazgos revisados. La consulta siguió funcionando después de borrar los temporales.", "",
        "El módulo OCA se usó solo como entrada; la unidad de solución OCA de control se excluyó antes de la red. No se ejecutó Odoo ni se migró o modificó el módulo. No se prueba equivalencia funcional ni cobertura de todas las incompatibilidades.", "",
        "La revisión es una entrada mock del test, no una capacidad de verificación automática ni un juicio independiente. Este módulo ya estaba reservado como caso de desarrollo y continúa excluido de evaluación final.", "",
        "report.json conserva comprobaciones, hashes y procedencia; query-graph.json y query-bm25.json contienen los resultados. mock-response.diff conserva la respuesta simulada.", ""])
    (output / "REPORT.md").write_text("\n".join(summary), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps(dict(passed=result["passed"], module=result["module"], candidate_hunks=result["candidate_hunks"],
                          verified_findings=result["reviewed_query_summaries"]["graph"]["changes_found"], output=result["output"])))


if __name__ == "__main__":
    main()
