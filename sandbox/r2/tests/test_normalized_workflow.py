import difflib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from r2.cli import main
from r2.evaluation.normalized import evaluate
from r2.report import search_units, validate_report
from test_session_integration import Response


def diff(path, *models):
    lines = "".join(f"    self.env[{name!r}]\n" for name in models)
    before = f"def evidence(self):\n{lines}    return 'old'\n"
    after = before.replace("'old'", "'new'")
    return "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        fromfile=f"a/{path}", tofile=f"b/{path}"))


class NormalizedWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.module = self.root / "partner.py"
        self.module.write_text("class Original:\n    _name = 'original.seed'\n", encoding="utf-8")
        primary = "https://github.com/odoo/odoo/compare/16.0...17.0"
        future = "https://github.com/odoo/odoo/compare/17.0...18.0"
        duplicate = "https://github.com/odoo/odoo/compare/base16...target17"
        blocked = "https://www.odoo.com/documentation/17.0/excluded.html"
        records = {
            "primary": (primary, "github_diff"),
            "future": (future, "github_diff"),
            "duplicate": (duplicate, "github_diff"),
            "blocked": (blocked, "official_documentation"),
        }
        primary_diff = diff("addons/primary.py", "original.seed", "link.model")
        primary_diff += "".join(diff(f"addons/neighbor_{i}.py", "link.model") for i in range(11))
        self.responses = {
            primary: primary_diff,
            future: diff("addons/future.py", "original.seed"),
            duplicate: diff("addons/primary.py", "original.seed", "link.model"),
        }
        self.plan = self.save("plan.json", [
            dict(id=name, kind=kind, files={"change.diff" if kind == "github_diff" else "guide.txt": url})
            for name, (url, kind) in records.items()])
        self.catalog = self.save("catalog.json", dict(allowed_urls=list(self.responses),
            excluded_urls=[blocked], oca_repositories=["OCA/example"], oca_addons=["excluded_addon"]))
        self.bindings = self.save("bindings.json", dict(sources={
            "primary": dict(from_version="16.0", to_version="17.0"),
            "duplicate": dict(from_version="16.0", to_version="17.0"),
            "future": dict(from_version="17.0", to_version="18.0"),
        }))
        self.output = self.root / "run"
        self.db = self.output / "collection.sqlite"

    def save(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def run_workflow(self):
        with patch("r2.adquisition.http.request.build_opener") as opener, redirect_stdout(io.StringIO()) as stdout:
            def transport(req, **kwargs):
                source = req.full_url.replace("https://api.github.com/repos/", "https://github.com/")
                return Response(self.responses[source].encode())

            opener.return_value.open.side_effect = transport
            main(["run", str(self.module), "--module-name", "original", "--plan", str(self.plan),
                  "--catalog", str(self.catalog), "--bindings", str(self.bindings), "--output-dir",
                  str(self.output), "--from", "16.0", "--to", "17.0", "--format", "json"])
        return json.loads(stdout.getvalue())

    def test_run_reports_scoped_distinct_hunks_with_provenance_before_display_limit(self):
        report = self.run_workflow()
        self.assertEqual(report, json.loads((self.output / "report.json").read_text(encoding="utf-8")))
        self.assertTrue((self.output / "crossing.json").is_file())
        self.assertTrue((self.output / "relations.json").is_file())
        summary = report["summary"]
        self.assertEqual(summary["eligible_units"], 13)
        self.assertEqual(summary["changes_found"], 12)
        self.assertEqual(summary["changes_shown"], 10)
        self.assertEqual(summary["new_findings_by_depth"], {"0": 1, "1": 11})
        self.assertTrue(any("excluded" in warning for warning in report["warnings"]))
        self.assertTrue(all(row["source"]["to_version"] == "17.0" for row in report["results"]))
        self.assertTrue(all(row["module_evidence"] for row in report["results"]))
        report["results"][1]["relations"] = []
        with self.assertRaisesRegex(ValueError, "path"):
            validate_report(report)

    def test_evaluation_compares_the_same_units_and_keeps_missing_judgments_undefined(self):
        graph = self.run_workflow()
        options = dict(module_name="original", limit=10, maximum_hops=3, layer="all")
        bm25, crossing, relations = search_units(self.db, self.module, "16.0", "17.0", engine="bm25", **options)
        self.assertIsNone(crossing)
        self.assertIsNone(relations)
        self.assertEqual(graph["query"], bm25["query"])
        self.assertEqual(graph["summary"]["eligible_units"], bm25["summary"]["eligible_units"])
        self.assertEqual(bm25["summary"]["changes_found"], 1)
        direct = graph["results"][0]["change_id"]
        specification = dict(reviewer="Synthetic fixture", collection_revision=graph["collection_revision"],
            references={"reference": dict(migration_id="fixture", from_version="16.0", to_version="17.0",
                        available_unit_ids=[direct])},
            queries=[dict(id="query", module=self.module.name, from_version="16.0", to_version="17.0",
                          input_revision=graph["query"]["input_revision"], reference_ids=["reference"],
                          judgments={direct: dict(relevant=True, reference_ids=["reference"])}, **options)])
        result = evaluate(self.db, specification, self.root, repeats=2)
        self.assertEqual(result["C1"], 100)
        self.assertIsNone(result["queries"][0]["engines"]["graph"]["P1"])
        self.assertEqual(result["queries"][0]["engines"]["bm25"]["C2"], 100)
        self.assertEqual(len(result["queries"][0]["engines"]["bm25"]["T1_seconds"]), 2)
        empty, _, _ = search_units(self.db, self.module, "16.0", "17.0", layer="xml")
        self.assertEqual(empty["results"], [])
        with self.assertRaisesRegex(ValueError, "Destination"):
            search_units(self.db, self.module, "17.0", "16.0")

    def test_legacy_build_is_not_a_cli_entry_point(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["build-legacy"])
