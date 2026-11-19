"""Check planner policy, static hints and acquisition handoff internals."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from r2.adquisition.planner import COMPARE, make_plan, version_pairs, write_plan
from r2.adquisition.policy import SourcePolicy


class PlannerWhiteBoxTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = self.root / "checkout"
        self.module = self.repo / "local_addon"
        self.module.mkdir(parents=True)
        (self.module / "__manifest__.py").write_text(
            "{'name': 'Local', 'depends': ['sale', 'local_addon', 'reserved_addon']}\n", encoding="utf-8")
        (self.module / "views.xml").write_text('<odoo><field name="inherit_id" ref="stock.view_move"/></odoo>',
                                               encoding="utf-8")
        (self.module / "models.py").write_text(
            "from odoo.addons.purchase.models.purchase_order import PurchaseOrder\n"
            "raise RuntimeError('planner must never import this file')\n", encoding="utf-8")
        self.pr = "https://github.com/odoo/odoo/pull/123"
        self.unreviewed = "https://github.com/odoo/odoo/pull/456"
        self.excluded = f"{COMPARE}/17.0...18.0"
        (self.module / "README.md").write_text(f"[reviewed]({self.pr})\n[unreviewed]({self.unreviewed})\n",
                                              encoding="utf-8")
        self.catalog = dict(allowed_urls=[self.pr], excluded_urls=[self.excluded],
                            oca_repositories=["OCA/example"], oca_addons=["reserved_addon"],
                            source_bindings={self.pr: dict(from_version="16.0", to_version="17.0",
                                                           migration_id="reviewed")})

    def test_scope_admission_curated_links_and_explicit_bindings(self):
        plan, catalog, bindings, diagnostics = make_plan(self.repo, "16.0", "18.0", self.catalog)
        self.assertEqual((plan, catalog, bindings, diagnostics), make_plan(self.repo, "16.0", "18.0", self.catalog))
        self.assertEqual(diagnostics["local_addons"], ["local_addon"])
        self.assertEqual(diagnostics["addon_candidates"], ["purchase", "reserved_addon", "sale", "stock"])
        sources = {row["url"]: row for row in diagnostics["sources"]}
        self.assertIn(f"{COMPARE}/16.0...17.0", sources)
        self.assertIn("https://raw.githubusercontent.com/odoo/odoo/17.0/addons/purchase/models/purchase_order.py", sources)
        self.assertNotIn(self.unreviewed, sources)
        self.assertNotIn(self.excluded, sources)
        self.assertTrue(all("reserved_addon" not in url for url in sources))
        self.assertEqual(sources[self.pr]["input_references"], ["local_addon/README.md"])
        self.assertEqual(bindings["sources"][sources[self.pr]["id"]]["migration_id"], "reviewed")
        self.assertTrue(any("17.0 -> 18.0: 0" in warning for warning in diagnostics["warnings"]))
        policy = SourcePolicy(catalog)
        for entry in plan:
            for url in entry["files"].values():
                policy.url(url)

    def test_bindings_for_other_intervals_are_ignored_and_invalid_ones_fail(self):
        _, _, _, other = make_plan(self.repo, "17.0", "18.0", self.catalog)
        self.assertNotIn(self.pr, {row["url"] for row in other["sources"]})
        self.catalog["source_bindings"][self.pr]["from_version"] = "unknown"
        with self.assertRaisesRegex(ValueError, "Invalid version binding"):
            make_plan(self.repo, "16.0", "17.0", self.catalog)

    def test_empty_input_diagnostics_and_nonoverwriting_output(self):
        empty = self.root / "empty"
        empty.mkdir()
        catalog = self.root / "catalog.json"
        catalog.write_text(json.dumps(self.catalog), encoding="utf-8")
        output = self.root / "out"
        report = write_plan(empty, "16.0", "17.0", catalog, output)
        self.assertIn("No supported code files could be read from the input", report["warnings"])
        self.assertTrue(all(Path(report[name]).is_file() for name in ("plan", "catalog", "bindings", "planning")))
        with self.assertRaises(FileExistsError):
            write_plan(empty, "16.0", "17.0", catalog, output)
        with self.assertRaisesRegex(ValueError, "major.0"):
            version_pairs("16.4", "17.0")
