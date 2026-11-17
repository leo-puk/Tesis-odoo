import json
import tempfile
import unittest
from pathlib import Path
from r2.graph import new_graph
from r2.collection import build, connect, load
from r2.extract import extract, scan_module
from r2.query import paths_by_depth, retrieve, validate_output
from r2.evaluate import evaluate
from r2.policy import select_sources


OLD = '''from odoo import fields, models
class Payment(models.Model):
    _inherit = "account.payment"
    sale_id = fields.Many2one("sale.order", states={"draft": [("readonly", False)]})
'''
NEW = OLD.replace(', states={"draft": [("readonly", False)]}', '')
CORE_OLD = '''class Field:
    def setup(self):
        pass
'''
CORE_NEW = '''class Field:
    def setup(self):
        if self.states:
            print("states is no longer supported")
'''


def review_event(change, **values):
    evidence_ids = ["ev-"+change["id"][4:]]
    return dict(change_id=change["id"], status=values.pop("status", "verified"),
                reviewer=values.pop("reviewer", "synthetic fixture reviewer; not thesis evidence"),
                rationale=values.pop("rationale", "Synthetic unit test"), reviewed_at="2026-11-14T00:00:00Z",
                category="syntax", general_applicability={"justification": "Synthetic fixture only"},
                destination_validity={"status": "checked", "from_version": change["from_version"],
                                      "to_version": change["to_version"], "explanation": "Synthetic target code fixture",
                                      "evidence_ids": evidence_ids}, **values)


class R2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory, content in (("before", CORE_OLD), ("after", CORE_NEW), ("module", OLD)):
            path = self.root / directory
            path.mkdir()
            (path / "fields.py").write_text(content)
        self.manifest = self.root / "manifest.json"
        self.records = [dict(id="core", kind="official_code", split="construction", parent_ids=[],
                             format="snapshot", before_dir="before", after_dir="after",
                             from_version="16.0", to_version="17.0")]
        self.manifest.write_text(json.dumps(self.records))
        self.db = self.root / "collection.sqlite"

    def tearDown(self):
        self.temp.cleanup()

    def test_pipeline_traceability_determinism_baseline_and_versions(self):
        built = build(self.manifest, self.db)
        other = build(self.manifest, self.root / "other.sqlite")
        self.assertEqual(built["collection_revision"], other["collection_revision"])
        output = retrieve(self.db, self.root/"module", "16.0", "17.0")
        self.assertGreater(output["summary"]["changes_found"], 0)
        self.assertTrue(validate_output(output)["conformant"])
        self.assertEqual(output["results"][0]["file_path"], "fields.py")
        self.assertIn("states is no longer supported", output["results"][0]["after"])
        self.assertEqual(retrieve(self.db, self.root/"module", "17.0", "18.0")["results"], [])
        bm25 = retrieve(self.db, self.root/"module", "16.0", "17.0", engine="bm25")
        self.assertTrue(bm25["results"])
        self.assertEqual(bm25["results"][0]["path"], [])

    def test_bfs_cycles_multiorigin_stable_and_depth(self):
        graph = new_graph([("a", "b"), ("b", "c"), ("c", "a"), ("z", "c"), ("c", "d")])
        paths = paths_by_depth(graph, ["a", "z"], 2)
        self.assertEqual(paths["c"], ["z", "c"])
        self.assertEqual(paths["d"], ["z", "c", "d"])
        self.assertNotIn("d", paths_by_depth(graph, ["a"], 1))

    def test_source_switch_filters_derivatives_and_reserved_solutions(self):
        def row(key, kind, split="construction", parents=()):
            return {**self.records[0], "id": key, "kind": kind, "split": split, "parent_ids": list(parents)}
        records = [row("core", "official_code"), row("mig", "oca_migration"),
                   row("derived", "derived", parents=["mig"]),
                   row("reserved", "oca_fix", "evaluation_reference")]
        self.manifest.write_text(json.dumps(records))
        build(self.manifest, self.db)
        with connect(self.db) as con:
            self.assertEqual([s["id"] for s in load(con, "sources")], ["core"])
            self.assertNotIn("mig", {c["source_id"] for c in load(con, "changes")})
        with self.assertRaisesRegex(ValueError, "switch was removed"):
            select_sources(records, include_oca_migrations=True)
        with self.assertRaises(ValueError):
            retrieve(self.db, self.root/"module", "16.0", "17.0", include_oca_migrations=True)

    def test_no_execution_and_dynamic_references_warn(self):
        data = extract('raise RuntimeError("must not execute")\n'+OLD, "model.py")
        self.assertIn("field:account.payment.sale_id", {e["key"] for e in data["elements"]})
        data = extract('''class A:
    def go(self, name):
        return self.env[name]
''', "model.py")
        self.assertTrue(any("dynamic env" in w for w in data["warnings"]))

    def test_xml_references_and_reject_dtd_and_bad_syntax(self):
        text = '''<odoo><record id="view" model="ir.ui.view"><field name="model">sale.order</field>
        <field name="inherit_id" ref="sale.view_order_form"/><field name="arch" type="xml">
        <field name="amount_total" attrs="{}"/></field></record></odoo>'''
        data = extract(text, "views.xml")
        self.assertIn("field:sale.order.amount_total", {e["key"] for e in data["elements"]})
        self.assertIn("xml-attribute:attrs", {e["key"] for e in data["elements"]})
        self.assertTrue(extract('<!DOCTYPE a [<!ENTITY x SYSTEM "file:///etc/passwd">]><a>&x;</a>', "view.xml")["warnings"])
        self.assertTrue(extract("def broken(", "model.py")["warnings"])

    def test_immutable_build_and_reviewed_filter(self):
        build(self.manifest, self.db)
        with self.assertRaises(ValueError):
            build(self.manifest, self.db)
        self.assertEqual(retrieve(self.db, self.root/"module", "16.0", "17.0", status="verified")["results"], [])
        with connect(self.db) as con:
            change = load(con, "changes")[0]
        annotations = self.root / "review.json"
        annotations.write_text(json.dumps([review_event(change, status="verified", reviewer="test reviewer",
                                               rationale="Synthetic fixture explicitly changes states", title="States property changed")]))
        reviewed = self.root / "reviewed.sqlite"
        build(self.manifest, reviewed, annotations=annotations)
        self.assertTrue(retrieve(reviewed, self.root/"module", "16.0", "17.0", status="verified")["results"])

    def test_ten_limit_and_full_summary(self):
        for n in range(15):
            (self.root/"before"/f"f{n}.py").write_text(CORE_OLD)
            (self.root/"after"/f"f{n}.py").write_text(CORE_NEW)
        build(self.manifest, self.db)
        output = retrieve(self.db, self.root/"module", "16.0", "17.0")
        self.assertEqual(len(output["results"]), 10)
        self.assertEqual(output["summary"]["changes_found"], 16)
        self.assertTrue(validate_output(output)["conformant"])
        with self.assertRaises(ValueError):
            retrieve(self.db, self.root/"module", "16.0", "17.0", limit=11)

    def test_evaluation_formulas_require_judgments(self):
        build(self.manifest, self.db)
        with connect(self.db) as con:
            change = load(con, "changes")[0]
            key = change["id"]
        annotations = self.root/"eval-review.json"
        annotations.write_text(json.dumps([review_event(change, affected_elements=["property:states"])]))
        reviewed = self.root/"evaluated.sqlite"
        build(self.manifest, reviewed, annotations=annotations)
        spec = dict(reviewer="test fixture", references=[dict(id="r1", module_id="module", from_version="16.0", to_version="17.0",
                    element="property:states", covered_by=[key], justification="synthetic")],
                    queries=[dict(id="q1", module="module", from_version="16.0", to_version="17.0",
                                  module_id="module", status="verified", limit=10, depth=3,
                                  reference_ids=["r1"], judgments={key: dict(relevant=True, applicable=True, justification="synthetic", reference_ids=["r1"])})])
        output = evaluate(reviewed, spec, self.root, development=True, repeats=2, output_dir=self.root/"exports")
        self.assertEqual(output["C1"], 100)
        self.assertEqual(output["summary"]["graph"]["P1_macro"], 100)
        self.assertEqual(output["summary"]["graph"]["C2_macro"], 100)
        self.assertTrue((self.root/"exports"/"queries.csv").exists())
        self.assertEqual([m["engine"] for m in output["measurements"]],["graph","bm25","bm25","graph"])
        self.assertTrue(all(m["until_validated_serialized_view_seconds"] >= m["internal_seconds"] for m in output["measurements"]))
        spec["queries"][0]["judgments"] = {}
        with self.assertRaises(ValueError):
            evaluate(reviewed, spec, self.root, development=True)

    def test_empty_metrics_and_conformity(self):
        build(self.manifest, self.db)
        spec = dict(reviewer="test fixture", references=[], queries=[dict(id="q0", module="module",
                    module_id="module", status="verified", limit=10, depth=3,
                    from_version="17.0", to_version="18.0", reference_ids=[], judgments={})])
        output = evaluate(self.db, spec, self.root, development=True)
        self.assertIsNone(output["C1"])
        self.assertIsNone(output["summary"]["graph"]["P1_macro"])
        self.assertIsNone(output["summary"]["graph"]["C2_macro"])
        self.assertFalse(validate_output({})["conformant"])

    def test_review_narrows_path_to_actual_affected_element(self):
        build(self.manifest, self.db)
        with connect(self.db) as con:
            change = load(con, "changes")[0]
        review = self.root/"review.json"
        review.write_text(json.dumps([review_event(change, status="verified", reviewer="fixture",
                                          rationale="Explicit states addition", affected_elements=["property:states"])]))
        reviewed = self.root/"reviewed.sqlite"
        build(self.manifest, reviewed, annotations=review)
        result = retrieve(reviewed, self.root/"module", "16.0", "17.0")["results"][0]
        self.assertEqual(result["path"][-1], "property:states")

    def test_explicit_semantic_grouping_preserves_both_evidences(self):
        (self.root/"before"/"other.py").write_text(CORE_OLD)
        (self.root/"after"/"other.py").write_text(CORE_NEW)
        build(self.manifest, self.db)
        with connect(self.db) as con:
            changes = load(con, "changes")
        review = self.root/"review.json"
        review.write_text(json.dumps([review_event(c, group_id="one-logical-change", status="verified",
                     reviewer="fixture", rationale="Same explicit semantic change", title="States changed",
                     affected_elements=["property:states"]) for c in changes]))
        reviewed = self.root/"grouped.sqlite"
        build(self.manifest, reviewed, annotations=review)
        result = retrieve(reviewed, self.root/"module", "16.0", "17.0")
        self.assertEqual(result["summary"]["changes_found"], 1)
        self.assertEqual(len(result["results"][0]["evidence_blocks"]), 2)
        self.assertTrue(validate_output(result)["conformant"])


if __name__ == "__main__":
    unittest.main()
