import hashlib
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from r2.adquisition import capture_plan
from r2.cli import main, parser
from r2.collection import build_session, connect, load
from r2.conversion.diff import parse_diff
from r2.ingestion import read_session
from r2.query import retrieve, validate_output
from test_r2 import CORE_OLD, CORE_NEW, OLD, review_event
import difflib

DOC = "https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html"
DIFF = "https://github.com/odoo/odoo/compare/16.0...17.0"
MANIFEST = "https://raw.githubusercontent.com/odoo/odoo/17.0/addons/sale/__manifest__.py"
PR = "https://github.com/odoo/odoo/pull/123"


class Response:
    status = 200
    headers = {"Content-Type": "text/plain"}

    def __init__(self, raw): self.raw = raw
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return self.raw


class SessionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "collection.sqlite"
        self.module = self.root / "module"
        self.module.mkdir()
        (self.module / "model.py").write_text(OLD, encoding="utf-8")
        self.diff = "".join(difflib.unified_diff(CORE_OLD.splitlines(True), CORE_NEW.splitlines(True),
                                                fromfile="a/odoo/fields.py", tofile="b/odoo/fields.py"))
        self.catalog = self.root / "catalog.json"
        self.catalog.write_text(json.dumps(dict(allowed_urls=[DOC, DIFF, MANIFEST, PR], excluded_urls=[],
            oca_repositories=["OCA/example"], oca_addons=["excluded_addon"])), encoding="utf-8")
        self.plan = self.root / "plan.json"
        self.plan.write_text(json.dumps([
            dict(id="core", kind="github_diff", files={"change.diff": DIFF}),
            dict(id="guide", kind="official_documentation", files={"guide.txt": DOC}),
            dict(id="manifest", kind="official_manifest", files={"manifest.py": MANIFEST}),
        ]), encoding="utf-8")
        self.bindings = self.root / "bindings.json"
        self.config = dict(sources={
            "core": dict(from_version="16.0", to_version="17.0", from_revision="16.0", to_revision="17.0", context_units=["guide"]),
            "guide": dict(from_version="16.0", to_version="17.0"),
            "manifest": dict(from_version="16.0", to_version="17.0", module="sale"),
        })
        self.bindings.write_text(json.dumps(self.config), encoding="utf-8")

    def transport(self, req, **kwargs):
        if req.full_url == DOC:
            return Response(b"The states option changed. Explanatory context is not another diff.")
        if req.full_url == MANIFEST:
            return Response(b"{'name': 'Sale', 'depends': ['base']}\n")
        return Response(self.diff.encode())

    def capture(self):
        result = capture_plan(self.plan, self.root, catalog_path=self.catalog, transport=self.transport)
        self.inventory = Path(result["inventory"])
        self.result = result
        return result

    def test_normalization_pipeline_preserves_records_and_exclusions(self):
        from r2.conversion import convert_units
        from r2.normalization import normalize_session

        self.capture()
        rows = json.loads(self.inventory.read_text(encoding="utf-8"))
        rows.append(dict(id="f" * 32, status="excluded"))
        self.inventory.write_text(json.dumps(rows), encoding="utf-8")
        units, excluded = read_session(self.inventory, self.bindings)
        expected = {**convert_units(units), "excluded": excluded}
        with patch("r2.adquisition.http.request.build_opener", side_effect=AssertionError("unexpected network")):
            actual = normalize_session(self.inventory, self.bindings)
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual["units"]), 3)
        self.assertEqual(sum(u['kind']=='diff_hunk' for u in actual['units'].values()), 1)
        self.assertNotIn('relations',actual)
        self.assertEqual(len(actual["artifacts"]), 3)
        self.assertEqual(actual["excluded"], [dict(id="f" * 32, reason="excluded")])

    def test_normalization_pipeline_rejects_invalid_binding(self):
        from r2.normalization import normalize_session

        self.capture()
        self.config["sources"]["core"]["from_version"] = "18.0"
        self.bindings.write_text(json.dumps(self.config), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "destination must follow origin"):
            normalize_session(self.inventory, self.bindings)

    def test_cli_capture_build_query_export_delete_and_offline_retrieval(self):
        with patch("r2.adquisition.http.request.build_opener") as opener:
            opener.return_value.open.side_effect = self.transport
            with redirect_stdout(io.StringIO()) as stdout:
                main(["capture-plan", str(self.plan), "--catalog", str(self.catalog), "--output", str(self.root)])
            self.result = json.loads(stdout.getvalue())
            self.inventory = Path(self.result["inventory"])
        with patch("r2.adquisition.http.request.build_opener", side_effect=AssertionError("unexpected network")):
            with redirect_stdout(io.StringIO()):
                main(["build", str(self.inventory), "--bindings", str(self.bindings), "--db", str(self.db)])
            with connect(self.db) as con:
                sources = load(con, "sources")
                changes = load(con, "changes")
                self.assertEqual(len(changes), 1)
                self.assertEqual(changes[0]["classification"], "observed_diff_hunk")
                self.assertEqual(len(load(con, "documents")), 2)
                self.assertEqual(len(load(con, "artifacts")), 3)
                self.assertTrue(any(e["path"] == "__manifest__.py" for e in load(con, "elements")))
            output = retrieve(self.db, self.module, "16.0", "17.0")
            self.assertTrue(validate_output(output)["conformant"])
            self.assertEqual(output["summary"]["changes_found"], 1)
            self.assertEqual(retrieve(self.db, self.module, "16.0", "17.0", engine="bm25")["summary"]["changes_found"], 1)
            self.assertEqual(len(output["results"][0]["context_documents"]), 1)
            self.assertTrue(output["results"][0]["source_citations"][0]["unit_id"])
            with redirect_stdout(io.StringIO()) as stdout:
                main(["export", "--db", str(self.db)])
            self.assertEqual(len(json.loads(stdout.getvalue())["artifacts"]), 3)
            unit_ids = [s["unit_id"] for s in sources]
            with redirect_stdout(io.StringIO()):
                main(["delete-units", self.result["session_id"], *unit_ids, "--output", str(self.root)])
            self.assertTrue(all(u["status"] == "deleted" for u in json.loads(self.inventory.read_text())))
            self.assertEqual(retrieve(self.db, self.module, "16.0", "17.0")["summary"]["changes_found"], 1)

    def test_reviewed_native_collection_is_evaluable_and_reproducible(self):
        self.capture()
        first = build_session(self.inventory, self.bindings, self.db)
        second = build_session(self.inventory, self.bindings, self.root / "same.sqlite")
        self.assertEqual(first["collection_revision"], second["collection_revision"])
        with connect(self.db) as con:
            change = load(con, "changes")[0]
        annotations = self.root / "review.json"
        annotations.write_text(json.dumps([review_event(change)]))
        reviewed = self.root / "reviewed.sqlite"
        build_session(self.inventory, self.bindings, reviewed, annotations)
        output = retrieve(reviewed, self.module, "16.0", "17.0", status="verified")
        self.assertTrue(output["results"])
        self.assertTrue(validate_output(output)["conformant"])
        from r2.evaluate import evaluate
        spec = dict(reviewer="synthetic fixture", references=[], cache_state="fixture", queries=[dict(
            id="q", module="module", module_id="module", status="verified", limit=10, depth=3,
            from_version="16.0", to_version="17.0", reference_ids=[], judgments={output["results"][0]["id"]:
                dict(relevant=True, applicable=True, justification="Synthetic engineering fixture", reference_ids=[])}
        )])
        report = evaluate(reviewed, spec, self.root, development=True)
        self.assertTrue(report["development_only"])
        self.assertEqual(len(report["queries"]), 2)

    def test_missing_version_binding_preserves_unknown_interval(self):
        self.capture()
        del self.config["sources"]["core"]["from_version"]
        self.bindings.write_text(json.dumps(self.config))
        build_session(self.inventory, self.bindings, self.db)
        with connect(self.db) as con:
            unit = next(u for u in load(con,'information_units') if u['kind']=='diff_hunk')
            self.assertIsNone(unit['version_from'])
            self.assertEqual(load(con,'changes'),[])

    def test_pr_json_preserves_comments_but_only_diff_creates_changes(self):
        self.plan.write_text(json.dumps([dict(id="core", kind="github_pr", files={"pr.json": PR})]))
        self.config["sources"]["core"]["context_units"] = []
        self.bindings.write_text(json.dumps(self.config))
        def transport(req, **kwargs):
            if req.get_header("Accept") == "application/vnd.github.diff":
                return Response(self.diff.encode())
            if "?" not in req.full_url:
                value = dict(merged_at="2026-01-01", changed_files=1, commits=1, body="A contextual solution")
            elif "/files?" in req.full_url:
                value = [dict(filename="odoo/fields.py")]
            elif "/commits?" in req.full_url:
                value = [dict(sha="fixture")]
            else:
                value = [dict(body="Another explanatory comment")]
            return Response(json.dumps(value).encode())
        result = capture_plan(self.plan, self.root, catalog_path=self.catalog, transport=transport)
        build_session(result["inventory"], self.bindings, self.db)
        with connect(self.db) as con:
            self.assertEqual(len(load(con, "changes")), 1)
            stored = json.loads(load(con, "artifacts")[0]["text"])
            self.assertEqual(stored["pull"]["body"], "A contextual solution")
            self.assertEqual(stored["comments"][0]["body"], "Another explanatory comment")

    def test_context_only_session_has_no_changes(self):
        self.plan.write_text(json.dumps([dict(id="guide", kind="official_documentation", files={"guide.txt": DOC})]))
        self.capture()
        result = build_session(self.inventory, self.bindings, self.db)
        self.assertEqual(result["change_count"], 0)
        self.assertEqual(result["document_count"], 1)

    def test_nonaccepted_units_are_not_opened(self):
        self.capture()
        rows = json.loads(self.inventory.read_text())
        rows[0].update(status="incomplete", files=["missing/file.diff"])
        self.inventory.write_text(json.dumps(rows))
        build_session(self.inventory, self.bindings, self.db)
        with connect(self.db) as con:
            self.assertEqual(load(con, "changes"), [])

    def test_unit_path_escape_is_rejected(self):
        self.capture()
        rows = json.loads(self.inventory.read_text())
        rows[0]["files"] = ["../outside.diff"]
        self.inventory.write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, "escapes"):
            read_session(self.inventory, self.bindings)

    def test_no_full_source_reconstruction_for_incomplete_python_hunk(self):
        self.diff = "--- a/x.py\n+++ b/x.py\n@@ -40 +40 @@\n-    return old()\n+    return new()\n"
        self.capture()
        result = build_session(self.inventory, self.bindings, self.db)
        with connect(self.db) as con:
            change = load(con, "changes")[0]
            self.assertEqual(change["before_start"], 40)
            self.assertEqual(change["evidence_scope"], "partial_source_hunk")
            self.assertEqual(change["elements"], [])
        self.assertTrue(result["warnings"])

    def test_truncated_diff_cannot_create_candidates(self):
        self.diff = "--- a/x.py\n+++ b/x.py\n@@ -1,2 +1,2 @@\n-old\n+new\n"
        self.capture()
        report = build_session(self.inventory, self.bindings, self.db)
        self.assertEqual(report['normalization_issue_count'],1)
        self.assertIn('Truncated',report['normalization_issues'][0]['detail'])
        with connect(self.db) as con:
            self.assertEqual(load(con,'changes'),[])
            self.assertTrue(load(con,'artifacts'))

    def test_original_delivery_is_preserved_after_authorized_active_changes(self):
        root = Path(__file__).resolve().parents[1]
        baseline = json.loads((root / "audit/adquisition-final-baseline.json").read_text())
        reference = root / "reference/adquisition-final/adquisition"
        actual = {p.relative_to(reference).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in reference.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        self.assertEqual(actual, baseline)

    def test_removed_switch_is_rejected_by_cli(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser().parse_args(["query", "module", "--db", "x", "--from", "16.0", "--to", "17.0", "--include-oca-migrations"])


class DiffParserTests(unittest.TestCase):
    def test_multiple_files_added_deleted_and_no_newline_marker(self):
        text = "--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n+x = 1\n\\ No newline at end of file\n--- a/old.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-y = 1\n"
        hunks, _ = parse_diff(text)
        self.assertEqual(len(hunks), 2)
        self.assertIsNone(hunks[0]["old_path"])
        self.assertIsNone(hunks[1]["new_path"])

    def test_extra_lines_and_path_traversal_rejected(self):
        for text in ("--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n+extra\n",
                     "--- a/../x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\n"):
            with self.assertRaises(ValueError):
                parse_diff(text)
