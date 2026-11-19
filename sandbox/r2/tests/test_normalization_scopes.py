"""Python namespaces must not fabricate Odoo model methods or fields."""
import unittest

from r2.normalization.entities import extract_entities


class NormalizationScopeTests(unittest.TestCase):
    def extract(self, code):
        rows, warnings = extract_entities(
            code, 'models/partner.py',
            dict(artifact_path='capture/partner.py', line_start=1,
                 line_end=len(code.splitlines())),
        )
        self.assertEqual(warnings, [])
        return rows

    def declarations(self, rows, name):
        return [row for row in rows if row['name'] == name
                and row['context'].get('role') == 'declaration']

    def test_local_helper_is_not_an_odoo_method_or_global_function(self):
        rows = self.extract('''class Partner:
    _name = "res.partner"
    def action(self):
        def helper():
            return 1
        return helper()
''')
        action, = self.declarations(rows, 'action')
        self.assertEqual(action['lookup_keys'], ['method:res.partner.action'])
        helper, = self.declarations(rows, 'helper')
        self.assertEqual(helper['type'], 'function')
        self.assertEqual(helper['lookup_keys'], [])
        self.assertIsNone(helper['context']['model'])
        self.assertEqual(helper['context']['scope'], 'local')
        self.assertEqual(helper['context']['qualified_name'],
                         'Partner.action.<locals>.helper')

    def test_async_nested_functions_and_sibling_names_keep_separate_scopes(self):
        rows = self.extract('''class Partner:
    _inherit = "res.partner"
    async def first(self):
        async def helper():
            def deep():
                return 1
            return deep()
        return await helper()
    def second(self):
        def helper():
            return 2
        return helper()
''')
        helpers = self.declarations(rows, 'helper')
        self.assertEqual(len(helpers), 2)
        self.assertEqual({h['context']['qualified_name'] for h in helpers}, {
            'Partner.first.<locals>.helper', 'Partner.second.<locals>.helper'})
        self.assertTrue(all(h['lookup_keys'] == [] and h['context']['model'] is None
                            for h in helpers))
        deep, = self.declarations(rows, 'deep')
        self.assertEqual(deep['context']['qualified_name'],
                         'Partner.first.<locals>.helper.<locals>.deep')
        self.assertEqual(deep['lookup_keys'], [])
        first, = self.declarations(rows, 'first')
        self.assertEqual(first['lookup_keys'], ['method:res.partner.first'])

    def test_module_functions_keep_their_keys_but_local_factories_do_not(self):
        rows = self.extract('''def factory():
    def helper():
        return 1
    return helper

async def other():
    return 2
''')
        factory, = self.declarations(rows, 'factory')
        other, = self.declarations(rows, 'other')
        helper, = self.declarations(rows, 'helper')
        self.assertEqual(factory['lookup_keys'], ['function:factory'])
        self.assertEqual(other['lookup_keys'], ['function:other'])
        self.assertEqual(helper['lookup_keys'], [])
        self.assertEqual(helper['context']['qualified_name'],
                         'factory.<locals>.helper')

    def test_nested_classes_do_not_inherit_the_outer_model(self):
        rows = self.extract('''class Partner:
    _name = "res.partner"
    class Container:
        def helper(self):
            return 1
    def action(self):
        class Local:
            def helper(self):
                return 2
        return Local()
''')
        helpers = self.declarations(rows, 'helper')
        self.assertEqual(len(helpers), 2)
        self.assertTrue(all(h['type'] == 'method' for h in helpers))
        self.assertTrue(all(h['lookup_keys'] == [] and h['context']['model'] is None
                            for h in helpers))
        self.assertEqual({h['context']['qualified_name'] for h in helpers}, {
            'Partner.Container.helper', 'Partner.action.<locals>.Local.helper'})

    def test_local_class_with_its_own_model_uses_only_its_own_explicit_owner(self):
        rows = self.extract('''class Partner:
    _name = "res.partner"
    def action(self):
        class Other:
            _name = "x.other"
            def helper(self):
                return 1
        return Other()
''')
        helper, = self.declarations(rows, 'helper')
        self.assertEqual(helper['lookup_keys'], ['method:x.other.helper'])
        self.assertEqual(helper['context']['model'], 'x.other')
        self.assertNotIn('method:res.partner.helper',
                         {key for row in rows for key in row['lookup_keys']})

    def test_local_assignments_do_not_declare_model_fields_or_owner_models(self):
        rows = self.extract('''class Partner:
    _name = "res.partner"
    partner_id = fields.Many2one("res.partner")
    def action(self):
        _name = "fake.method.model"
        temporary = fields.Char(compute="_compute_fake")
        def helper():
            _inherit = "fake.local.model"
            local_field = fields.Many2one("fake.comodel")
            return local_field
        return helper()
''')
        declared_fields = [r for r in rows if r['type'] == 'field'
                           and r['context'].get('role') == 'declaration']
        self.assertEqual([r['name'] for r in declared_fields], ['partner_id'])
        self.assertEqual(declared_fields[0]['lookup_keys'],
                         ['field:res.partner.partner_id'])
        names = {r['name'] for r in rows}
        self.assertFalse({'fake.method.model', 'fake.local.model',
                          '_compute_fake', 'fake.comodel'} & names)

    def test_local_lambda_references_do_not_inherit_model_ownership(self):
        rows = self.extract('''class Partner:
    _name = "res.partner"
    def action(self):
        callback = lambda: self.name
        return callback()
''')
        reference, = [r for r in rows if r['type'] == 'attribute_reference'
                       and r['name'] == 'name']
        self.assertIsNone(reference['context']['model'])


if __name__ == '__main__':
    unittest.main()
