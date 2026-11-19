"""Exercise the public R2 CLI with controlled upstream HTTP responses."""
from contextlib import redirect_stderr, redirect_stdout
from difflib import unified_diff
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from r2.cli import main
from test_session_integration import Response


class CajaNegraR2(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.module = self.root / "partner"
        self.module.mkdir()
        self.code = self.module / "models.py"
        self.code.write_text("class Custom:\n    _inherit = 'original.seed'\n", encoding="utf-8")
        (self.module / "__manifest__.py").write_text("{'name': 'Partner', 'depends': ['sale']}\n",
                                                     encoding="utf-8")
        self.scope = [str(self.module), "--from", "16.0", "--to", "17.0"]
        self.catalog = self.root / "policy.json"
        self.catalog.write_text(json.dumps(dict(allowed_urls=[], excluded_urls=[],
                                                oca_repositories=["OCA/example"],
                                                oca_addons=["reserved_addon"])), encoding="utf-8")
        self.calls = []

    def cli(self, args):
        with redirect_stdout(io.StringIO()) as stdout:
            main([str(arg) for arg in args])
        return json.loads(stdout.getvalue())

    def transport(self, req, **kwargs):
        self.calls.append(req.full_url)
        if req.full_url.endswith("/compare/16.0...17.0"):
            changes = []
            for filename, models in [("direct.py", ("original.seed", "link.model")),
                                     ("indirect.py", ("link.model",))]:
                lines = ["def method(self):\n", *(f"    self.env[{name!r}]\n" for name in models)]
                changes.extend(unified_diff([*lines, "    return 1\n"], [*lines, "    return 2\n"],
                                            fromfile=f"a/addons/sale/{filename}",
                                            tofile=f"b/addons/sale/{filename}"))
            return Response("".join(changes).encode())
        if req.full_url.endswith("/addons/sale/__manifest__.py"):
            return Response(b"{'name': 'Sale'}\n")
        raise HTTPError(req.full_url, 404, "Fixture has no resource", {}, None)

    def test_r21_auto_plan_through_traceable_report_and_r22_query(self):
        output = self.root / "run"
        original = self.code.read_bytes()
        with patch("r2.adquisition.http.request.build_opener") as opener:
            opener.return_value.open.side_effect = self.transport
            result = self.cli(["run", *self.scope, "--catalog", self.catalog, "--output-dir", output,
                               "--format", "json"])
        self.assertEqual(original, self.code.read_bytes())
        self.assertTrue((output / "planning" / "plan.json").is_file())
        self.assertGreater(len(self.calls), 1)
        self.assertEqual(result["summary"]["new_findings_by_depth"], {"0": 1, "1": 1})
        self.assertEqual(result["summary"]["changes_found"], 2)
        self.assertTrue(any("failed" in item for item in result["warnings"]))
        self.assertTrue(result["results"][1]["relations"])
        self.assertEqual(self.cli(["validate-output", output / "report.json"]), {"conformant": True})
        database = output / "collection.sqlite"
        direct = self.cli(["query", *self.scope, "--db", database, "--depth", "0", "--format", "json"])
        wrong_scope = self.cli(["query", *self.scope, "--db", database, "--layer", "xml", "--format", "json"])
        baseline = self.cli(["query", *self.scope, "--db", database, "--engine", "bm25", "--format", "json"])
        self.assertEqual(direct["summary"]["changes_found"], 1)
        self.assertEqual(wrong_scope["results"], [])
        self.assertEqual(baseline["summary"]["eligible_units"], result["summary"]["eligible_units"])
        self.assertEqual(baseline["collection_revision"], result["collection_revision"])

    def test_r22_plan_is_offline_and_writes_reusable_acquisition_inputs(self):
        output = self.root / "planning"
        with patch("r2.adquisition.http.request.build_opener", side_effect=AssertionError("Unexpected HTTP")):
            result = self.cli(["plan", *self.scope, "--catalog", self.catalog, "--output-dir", output])
        self.assertGreater(result["planned_url_count"], 1)
        self.assertTrue(result["warnings"])
        self.assertTrue(all(Path(result[name]).is_file() for name in ("plan", "catalog", "bindings", "planning")))
        with patch("r2.adquisition.http.request.build_opener") as opener:
            opener.return_value.open.side_effect = self.transport
            capture = self.cli(["capture-plan", result["plan"], "--catalog", result["catalog"],
                                "--output", self.root / "capture"])
        self.assertGreater(capture["included"], 0)
        self.assertGreater(capture["counts"]["failed"], 0)

    def test_r21_reports_no_eligible_changes_when_only_manifests_are_admitted(self):
        output = self.root / "manifest-only"

        def manifests_only(req, **kwargs):
            if req.full_url.endswith("/compare/16.0...17.0"):
                raise HTTPError(req.full_url, 404, "Fixture has no diff", {}, None)
            return self.transport(req, **kwargs)

        with patch("r2.adquisition.http.request.build_opener") as opener:
            opener.return_value.open.side_effect = manifests_only
            result = self.cli(["run", *self.scope, "--catalog", self.catalog, "--output-dir", output,
                               "--format", "json"])
        self.assertEqual(result["summary"]["eligible_units"], 0)
        self.assertEqual(result["results"], [])
        self.assertIn("Planning: No version-bound change blocks were eligible for this query.", result["warnings"])

    def test_r22_rejects_reversed_versions_without_output(self):
        output = self.root / "invalid"
        with redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit) as exc:
            main(["plan", str(self.module), "--from", "17.0", "--to", "16.0",
                  "--catalog", str(self.catalog), "--output-dir", str(output)])
        self.assertEqual(exc.exception.code, 2)
        self.assertIn("Destination version must follow origin", stderr.getvalue())
        self.assertFalse(output.exists())
