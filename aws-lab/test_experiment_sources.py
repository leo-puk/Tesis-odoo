"""Check acquisition merging and full-artifact retrieval against a local R2 fixture."""
import importlib.util
import json
import csv
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

import experimentos as batch
from experiment_sources import SourceBaseline, acquire_oca, supplement
from mig_review import suggest_links


@unittest.skipUnless(importlib.util.find_spec("r2"), "Requires the R2 test environment")
class SourceExperimentTests(unittest.TestCase):
    def setUp(self):
        self.fixture_path = str(batch.ROOT / "sandbox/r2/tests")
        sys.path.insert(0, self.fixture_path)
        self.addCleanup(lambda: sys.path.remove(self.fixture_path))
        import test_normalized_workflow as fixtures
        self.fixture = fixtures.NormalizedWorkflowTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.run_workflow()
        self.addon = self.fixture.root / "original"
        self.addon.mkdir()
        (self.addon / "models.py").write_bytes(self.fixture.module.read_bytes())

    def test_baseline_ranks_complete_sources_and_keeps_separate_judgments(self):
        baseline = SourceBaseline(self.fixture.db, self.fixture.root / "source-index.sqlite", "16.0", "17.0")
        report = baseline.search(self.addon, "original")
        self.assertEqual(report["summary"]["eligible_sources"], 2)
        self.assertTrue(all(row["source_id"].startswith("src-") for row in report["results"]))
        result = batch.measure_module(self.fixture.db, self.addon, dict(version_from="16.0", version_to="17.0"),
                                      self.fixture.root / "comparison", 2, baseline)
        self.assertIn("bm25_sources", result["engines"])
        timing = batch.read(self.fixture.root / "comparison/timing.json")
        self.assertEqual(len(timing), 6)
        self.assertTrue(any("relations_seconds" in row["stages"] for row in timing))
        self.assertTrue(any("bm25_sources_search_seconds" in row["stages"] for row in timing))
        self.assertTrue((self.fixture.root / "comparison/source-judgments.csv").exists())
        folder = self.fixture.root / "comparison"
        references = self.fixture.root / "references"
        references.mkdir()
        (references / "abc.diff").write_text(
            "--- a/original/models.py\n+++ b/original/models.py\n@@ -1 +1 @@\n"
            "-model = 'old.seed'\n+model = 'original.seed'\n", encoding="utf-8")
        links = suggest_links(self.fixture.db, folder, references, [{"sha": "abc"}], "16.0", "17.0")
        hunk = links["hunks"][0]
        self.assertEqual(links["status"], "pending_review")
        self.assertTrue(hunk["available_unit_candidates"])
        self.assertTrue(hunk["retrieved_unit_candidates"])
        self.assertTrue(any("bm25_sources" in value["engines"] for value in hunk["retrieved_source_candidates"]))
        attempt = self.fixture.root / "source-evaluation"
        import shutil
        shutil.copytree(folder, attempt / "addons" / "original")
        specification = dict(queries=[dict(module_name="original", reference_ids=["fix"])])
        batch.evaluate_sources(attempt, {"modules": [result]}, specification)
        self.assertTrue(all(score["P1_source"] is None for score in
                            batch.read(attempt / "source-evaluation.json")["queries"][0]["engines"].values()))
        path = attempt / "addons/original/source-judgments.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            row.update(relevant="true", reference_ids="fix", reviewer="Synthetic fixture", reason="Synthetic source relation")
        batch.table(path, rows, list(rows[0]))
        batch.evaluate_sources(attempt, {"modules": [result]}, specification)
        self.assertTrue(all(score["P1_source"] == 100 for score in
                            batch.read(attempt / "source-evaluation.json")["queries"][0]["engines"].values()))

    def test_supplement_preserves_local_capture_and_adds_admitted_web_source(self):
        from r2.evaluation.normalized import coverage
        from r2.records import connect, load
        from r2.report import search_units
        fixture = self.fixture
        inventory = next((fixture.output / "temp_data").rglob("inventory.json"))
        prepared = dict(inventory=str(inventory), bindings=str(fixture.bindings), revisions={})
        url = "https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html"
        catalog = dict(allowed_urls=[url], excluded_urls=[], oca_repositories=[], oca_addons=[])
        plan = [dict(id="web", kind="official_documentation", files={"guide.md": url}),
                dict(id="wide", kind="github_diff", files={"full.diff": "https://github.com/odoo/odoo/compare/16.0...17.0"})]
        configuration = dict(sources={"web": dict(from_version=None, to_version="17.0"),
                                      "wide": dict(from_version="16.0", to_version="17.0")})

        def capture(plan_path, folder, catalog_path):
            self.assertEqual(len(batch.read(plan_path)), 1)
            session = folder / uuid.uuid4().hex
            uid = uuid.uuid4().hex
            destination = session / uid
            destination.mkdir(parents=True)
            (destination / "guide.md").write_text("# ORM migration\nReview the `original.seed` model.\n", encoding="utf-8")
            rows = [dict(id=uid, source_id="supplement-0001", kind="official_documentation", status="accepted",
                         urls=[url], captures=[dict(url=url, status=200)], files=[uid + "/guide.md"])]
            batch.save(session / "inventory.json", rows)
            return dict(inventory=str(session / "inventory.json"), included=1)

        with patch("r2.adquisition.planner.make_plan", return_value=(plan, catalog, configuration, {})), patch(
                "r2.adquisition.capture_plan", side_effect=capture):
            result = supplement(prepared, [dict(name="original", path=self.addon)], "16.0", "17.0", fixture.root / "web")
        with connect(result["database"]) as con:
            sources = load(con, "sources")
            units = {unit["id"]: unit for unit in load(con, "information_units")}
        self.assertTrue(any(source["url"] == url for source in sources))
        self.assertGreater(len(sources), 1)
        self.assertEqual(result["acquisition_status"]["accepted"], 4)
        document = next(unit for unit in units.values() if unit["source_url"] == url)
        for engine in batch.ENGINES:
            report, _, _ = search_units(result["database"], self.addon, "16.0", "17.0", engine=engine)
            self.assertIn(document["id"], {row["source"]["unit_id"] for row in report["results"]})
        reference = dict(from_version="16.0", to_version="17.0", available_unit_ids=[document["id"]])
        self.assertEqual(coverage({"fix": reference}, units), {"fix"})
        with self.assertRaises(ValueError):
            coverage({"fix": dict(reference, to_version="18.0")}, units)

    def test_oca_comparison_limits_paths_and_excludes_reference_repository(self):
        from unittest.mock import Mock

        root = self.fixture.root
        metadata = root / "scope.json"
        batch.save(metadata, dict(scope=dict(selected_addons=["original"], manifest_dependencies=["stock", "sale"],
            core_modules=["stock"], technical_identifiers=["stock.picking"])))
        sources = Mock()
        sources.pin.side_effect = [(root, "first"), (root, "last")]
        trees = "\n".join(["original/__manifest__.py", "original/models/stock_picking.py",
            "aux/__manifest__.py", "aux/models/stock_picking.py", "aux/models/unrelated.py",
            "aux/tests/stock_picking.py"])
        sources.git.side_effect = [trees, trees,
            "--- a/aux/models/stock_picking.py\n+++ b/aux/models/stock_picking.py\n@@ -1 +1 @@\n-x\n+y"]
        result = acquire_oca(sources, dict(metadata=str(metadata)), "16.0", "17.0",
                             root / "oca", {"sale-workflow", "product-variant"})
        self.assertEqual([row["status"] for row in result["diagnostics"]], ["excluded", "excluded", "accepted"])
        self.assertEqual(sources.git.call_args.args[-2:], ("--", "aux/models/stock_picking.py"))
        inventory = batch.read(result["inventory"])
        self.assertEqual(inventory[0]["urls"], ["https://github.com/OCA/stock-logistics-warehouse/compare/first..last"])


if __name__ == "__main__":
    unittest.main()
