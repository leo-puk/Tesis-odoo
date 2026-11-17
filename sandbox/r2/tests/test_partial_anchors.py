import unittest
from r2.conversion.anchors import partial_anchors


class PartialAnchorTests(unittest.TestCase):
    def test_incomplete_field_api_block_has_local_properties_without_relations(self):
        rows = partial_anchors("   )\n        if self.related:\n            self.setup()\n", "odoo/fields.py", None)
        self.assertEqual([r["key"] for r in rows], ["property:related"])
        self.assertEqual(rows[0]["line"], 2)
        self.assertEqual(partial_anchors("self.related", "addons/example/model.py", None), [])

    def test_xpath_identifiers_generalize_to_unknown_attribute(self):
        rows = partial_anchors("  if root.xpath('//*[@legacy_flag]'):\n", "odoo/view.py", None)
        self.assertEqual([r["key"] for r in rows], ["xml-attribute:legacy_flag"])

    def test_comments_strings_and_dynamic_xpath_do_not_invent_anchors(self):
        code = '# self.states\ntext = "self.related"\n# root.xpath("//*[@fake]")\nroot.xpath(expression)\n'
        self.assertEqual(partial_anchors(code, "odoo/fields.py", None), [])
