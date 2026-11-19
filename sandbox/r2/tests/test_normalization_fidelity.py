"""Reject source-content and entity-location tampering at validation/storage."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_normalization as fixtures
from examples.run_normalization_demo import DIFF
from r2.collection import compatibility_views, write_collection
from r2.normalization.schema import unit_id, validate_collection


class NormalizationFidelityTests(unittest.TestCase):
    captured = fixtures.NormalizationTests.captured
    converted = fixtures.NormalizationTests.converted

    def reject_change(self, original, change):
        modified = deepcopy(original)
        unit = next(iter(modified['units'].values()))
        change(unit)
        with self.assertRaises(ValueError):
            validate_collection(modified)

    def test_rejects_changed_text_for_every_supported_source_representation(self):
        samples = [
            ('Read `res.partner`.\r\n', 'capture/doc.txt', 'official_documentation'),
            ('# Title\nRead `res.partner`.\n', 'capture/doc.md', 'official_documentation'),
            ('Title\n=====\nRead `res.partner`.\n', 'capture/doc.rst', 'official_documentation'),
            ('def action():\n    return 1\n', 'capture/code.py', 'official_code'),
            ("{'name':'Example','depends':['base']}\n", 'capture/__manifest__.py', 'official_manifest'),
            ('<html><p>Read <code>res.partner</code></p></html>', 'capture/doc.html', 'official_documentation'),
            (json.dumps(dict(pull=dict(body='Description'), comments=[dict(id=1,body='Comment')],diff=DIFF)),
             'capture/pr.json', 'github_pr'),
        ]
        for text, path, kind in samples:
            with self.subTest(kind=kind, path=path):
                result, _ = self.converted(text, path, kind)
                self.assertTrue(validate_collection(result))
                for uid in result['units']:
                    broken = deepcopy(result)
                    broken['units'][uid]['text'] = 'Content that does not exist in the source'
                    with self.assertRaises(ValueError):
                        validate_collection(broken)

    def test_rejects_changed_diff_body_with_the_same_header_and_locator(self):
        result, _ = self.converted(DIFF, 'capture/change.diff', 'github_diff')
        self.reject_change(result, lambda u: u.update(text=u['text'].replace('self.related', 'self.invented')))

    def test_rejects_changes_to_diff_format_data_without_changing_text(self):
        result, _ = self.converted(DIFF, 'capture/change.diff', 'github_diff')
        for key, value in [('before', 'invented'), ('after', 'invented'),
                           ('removed', 'invented'), ('added', 'invented'),
                           ('file_path', 'wrong.py'), ('old_path', None),
                           ('before_start', 99999), ('after_end', 99999)]:
            with self.subTest(field=key):
                self.reject_change(result, lambda u: u['data'].update({key: value}))

    def test_rejects_entity_coordinates_outside_the_document_or_with_wrong_types(self):
        result, units = self.converted('Read `res.partner`.')
        self.assertTrue(units[0]['entities'])
        for coordinate in ('content_line', 'artifact_line'):
            for value in (99999, 0, -1, True, '1', 1.5):
                with self.subTest(coordinate=coordinate, value=value):
                    self.reject_change(result, lambda u: u['entities'][0]['location'].update({coordinate: value}))

    def test_rejects_an_existing_line_that_does_not_support_the_entity(self):
        result, _ = self.converted('Read `res.partner`.\nAnother existing line.\n')
        self.reject_change(result, lambda u: u['entities'][0]['location'].update(content_line=2,artifact_line=2))
        self.reject_change(result, lambda u: u['entities'][0].update(name='invented_model'))

    def test_rejects_false_diff_entity_side_and_original_code_coordinates(self):
        result, units = self.converted(DIFF, 'capture/change.diff', 'github_diff')
        index = next(i for i,e in enumerate(units[0]['entities']) if e['location'].get('side')=='after')
        for change in (dict(side='before'), dict(code_line=99999), dict(code_path='wrong.py'),dict(content_line=99999)):
            with self.subTest(change=change):
                self.reject_change(result, lambda u: u['entities'][index]['location'].update(change))

    def test_rejects_false_manifest_and_pr_entity_coordinates(self):
        for text, path, kind in [
            ("{'name':'Example','depends':['base']}\n", 'capture/__manifest__.py', 'official_manifest'),
            (json.dumps(dict(pull=dict(body='Read `res.partner`.\nAnother line.'),diff='')), 'capture/pr.json', 'github_pr'),
            ('<html><p>Read `res.partner`.</p></html>', 'capture/doc.html', 'official_documentation'),
        ]:
            with self.subTest(kind=kind, path=path):
                result, units = self.converted(text, path, kind)
                self.assertTrue(validate_collection(result))
                self.assertTrue(units[0]['entities'])
                self.reject_change(result, lambda u: u['entities'][0]['location'].update(artifact_line=99999))

    def test_rejects_noncanonical_json_pointers_even_after_recomputing_unit_id(self):
        bundle = dict(pull={}, comments=[dict(id=1,body='First'),dict(id=2,body='Second')],diff='')
        result, _ = self.converted(json.dumps(bundle), 'capture/pr.json', 'github_pr')
        for pointer in ('/comments/-1/body', '/comments/01/body', '/comments/99999/body'):
            with self.subTest(pointer=pointer):
                broken = deepcopy(result)
                uid = next(iter(broken['units']))
                unit = broken['units'].pop(uid)
                unit['source_locator']['json_pointer'] = pointer
                unit['id'] = unit_id(unit['source_id'],unit['source_locator'],unit['extraction_rule'])
                broken['units'][unit['id']] = unit
                with self.assertRaises(ValueError): validate_collection(broken)

    def test_valid_diff_crlf_no_final_newline_and_deleted_sides_remain_valid(self):
        diff = '--- /dev/null\r\n+++ b/new.py\r\n@@ -0,0 +1 @@\r\n+name = 1\r\n\\ No newline at end of file\r\n--- a/old.py\r\n+++ /dev/null\r\n@@ -1 +0,0 @@\r\n-def old(): return 1'
        result, units = self.converted(diff, 'capture/change.diff', 'github_diff')
        self.assertTrue(validate_collection(result))
        self.assertEqual(len(units),2)
        self.assertNotIn('No newline',units[0]['data']['diff_body'])

    def test_valid_escaped_identifiers_and_multiline_json_mentions_remain_valid(self):
        samples = [
            ('class Partner:\n    _name="res.\\x70artner"\n', 'capture/model.py','official_code'),
            ('<odoo><record id="view&#95;partner" model="ir.ui.view"/></odoo>', 'capture/view.xml','official_code'),
            (json.dumps(dict(pull={},comments=[dict(id=1,body='First\nRead `res.partner`.')],diff='')),
             'capture/pr.json','github_pr'),
        ]
        for text,path,kind in samples:
            with self.subTest(path=path):
                result,_=self.converted(text,path,kind)
                self.assertTrue(validate_collection(result))

    def test_rejects_modified_artifact_text_when_original_bytes_are_retained(self):
        result, _ = self.converted('Original evidence')
        artifact = next(iter(result['artifacts'].values()))
        artifact['text'] = 'Tampered evidence'
        with self.assertRaises(ValueError): validate_collection(result)

    def test_storage_writer_rejects_tampered_units_before_creating_database(self):
        result, _ = self.converted('Read `res.partner`.')
        next(iter(result['units'].values()))['text'] = 'Invented text'
        elements, changes, documents = compatibility_views(result)
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory)/'bad.sqlite'
            with self.assertRaises(ValueError):
                write_collection(result['sources'],elements,{},changes,database,None,None,[],False,[],0,
                                 result['artifacts'],documents,schema=4,normalized_units=result['units'])
            self.assertFalse(database.exists())

    def test_reparses_a_multiunit_artifact_only_once_per_validation(self):
        result, units = self.converted('# First\nRead `res.partner`.\n# Second\nRead `partner_id`.\n','capture/guide.md')
        self.assertEqual(len(units),2)
        from r2.normalization import schema
        with patch.object(schema,'parse_artifact',wraps=schema.parse_artifact) as parser:
            self.assertTrue(validate_collection(result))
        self.assertEqual(parser.call_count,1)
