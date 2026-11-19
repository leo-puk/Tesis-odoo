"""Exercise the normalized CLI on local OCA/Odoo snapshots with simulated HTTP."""
import argparse
import ast
import difflib
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from r2.cli import main as cli
from r2.records import connect, load
from r2.report import validate_report

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
            units = load(con, "information_units")
            assert all(source["kind"] == "github_diff" for source in load(con, "sources"))
        targets = {}
        for layer, phrase in (("python", "states is no longer supported"),
                              ("xml", "attributes are no longer used")):
            matches = [unit["id"] for unit in units
                       if unit["kind"] == "diff_hunk" and phrase in unit["data"]["added"]]
            assert len(matches) == 1, (phrase, matches)
            targets[layer] = matches[0]
        scope = ["--db", str(raw_db), "--format", "json"]
        query = ["query", str(module), "--module-name", "sale_advance_payment",
                 "--from", "16.0", "--to", "17.0", *scope]
        outputs = {engine: command(query + ["--engine", engine]) for engine in ("graph", "bm25")}
        for engine, result in outputs.items():
            assert validate_report(result)
            save(f"query-{engine}.json", result)
        graph, bm25 = outputs["graph"], outputs["bm25"]
        assert graph["collection_revision"] == bm25["collection_revision"]
        assert graph["query"] == bm25["query"]
        assert graph["summary"]["eligible_units"] == bm25["summary"]["eligible_units"]
        xml = command(query + ["--layer", "xml"])
        assert any(row["source"]["unit_id"] == targets["xml"] and row["source_layers"] == ["python"]
                   for row in xml["results"])
        checks.update(expected_hunks_in_collection=True, shared_corpus_and_query=True,
                      graph_and_bm25_conformant=True, no_oca_solution_indexed=True,
                      xml_change_located_in_python_evidence=True)
        control = output / "unrelated_module.py"
        control.write_text("class Unrelated:\n    _name = 'functional.unrelated'\n", encoding="utf-8")
        negative = command(["query", str(control), "--from", "16.0", "--to", "17.0", *scope])
        wrong_jump = command(["query", str(module), "--from", "17.0", "--to", "18.0", *scope])
        assert negative["summary"]["changes_found"] == wrong_jump["summary"]["changes_found"] == 0
        checks.update(unrelated_module_has_no_findings=True, wrong_jump_has_no_findings=True)
        accepted = [row["id"] for row in inventory if row["status"] == "accepted"]
        command(["delete-units", capture["session_id"], *accepted, "--output", str(output)])
        assert command(query) == graph
        checks["retrieval_survives_temporary_unit_deletion"] = True
    assert hashes(module) == module_before
    assert hashes(project / "r2/adquisition") == final_before
    checks.update(oca_input_unchanged=True, final_adquisition_unchanged=True)
    report = dict(passed=True, scope="Functional engineering test with local snapshots and simulated HTTP",
                  module="sale_advance_payment", module_version=manifest["version"], jump="16.0->17.0",
                  module_path=str(module), module_repository=manifest["website"], module_hashes=module_before,
                  snapshot_provenance=json.loads((project / "examples/manifest.json").read_text(encoding="utf-8")),
                  core_files=provenance, candidate_hunks=graph["summary"]["eligible_units"],
                  collection_revision=built["collection_revision"], expected_targets=targets,
                  query_summaries={engine: result["summary"] for engine, result in outputs.items()},
                  targets_shown={engine: sorted(set(targets.values()) &
                                                {row["source"]["unit_id"] for row in result["results"]})
                                 for engine, result in outputs.items()},
                  checks=checks, http_calls=calls, final_acquisition_hashes=final_before, output=str(output))
    save("report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps(dict(passed=result["passed"], module=result["module"], candidate_hunks=result["candidate_hunks"],
                          candidates_found=result["query_summaries"]["graph"]["changes_found"], output=result["output"])))


if __name__ == "__main__":
    main()
