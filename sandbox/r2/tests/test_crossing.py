"""C01-C15: typed initial crossing against real normalized SQLite fixtures."""
from contextlib import redirect_stdout, closing
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import test_normalization as fixtures
from r2.cli import main
from r2.collection import compatibility_views, write_collection, connect
from r2.crossing import cross_module, save_result
from r2.crossing.code import read_code
from r2.normalization.units import convert_units

PARTNER = 'class Partner:\n    _name="res.partner"\n    partner_id=fields.Many2one("res.partner")\n    def action(self): return self.partner_id\n'


class CrossingTests(unittest.TestCase):
    captured = fixtures.NormalizationTests.captured

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.module = self.root/'partner_module'
        self.module.mkdir()
        self.sequence = 0

    def code(self,text,path='models/partner.py'):
        file = self.module/path
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(text,encoding='utf-8')

    def database(self,*captured):
        self.sequence += 1
        converted = convert_units(list(captured))
        elements,changes,documents = compatibility_views(converted)
        database = self.root/f'collection-{self.sequence}.sqlite'
        write_collection(converted['sources'],elements,{},changes,database,None,None,[],False,[],0,
            converted['artifacts'],documents,schema=4,normalized_units=converted['units'],normalization=converted['normalization'])
        return database

    def test_exact_model_field_and_method_matches_keep_both_locations(self):
        self.code(PARTNER)
        database=self.database(self.captured(PARTNER,'capture/partner.py','official_code'))
        result=cross_module(database,self.module)
        self.assertEqual(result['outcome'],'matches')
        self.assertEqual(result['summary']['units_matched'],1)
        evidences=result['results'][0]['evidences']
        self.assertTrue({'model','field','method'} <= {e['identity'][0] for e in evidences})
        self.assertTrue(all(e['input_entity']['location']['artifact_path']=='models/partner.py' for e in evidences))
        self.assertTrue(all(e['unit_entity']['location']['artifact_path']=='capture/partner.py' for e in evidences))

    def test_same_names_in_different_models_are_rejected(self):
        self.code(PARTNER)
        other=PARTNER.replace('res.partner','res.company')
        database=self.database(self.captured(other,'capture/company.py','official_code'))
        result=cross_module(database,self.module)
        self.assertEqual(result['results'],[])
        self.assertIn('incompatible_type_or_scope',result['summary']['rejection_reasons'])

    def test_unknown_owner_is_not_guessed_from_a_method_name(self):
        self.code('class Partner:\n    _name="res.partner"\n    def action(self): return 1\n')
        database=self.database(self.captured('class Unknown:\n    def action(self): return 1\n','capture/unknown.py','official_code'))
        result=cross_module(database,self.module)
        self.assertEqual(result['results'],[])
        self.assertIn('unknown_model_owner',result['summary']['rejection_reasons'])

    def test_local_helper_never_matches_a_model_method(self):
        self.code('class Partner:\n    _name="res.partner"\n    def action(self):\n        def helper(): return 1\n        return helper()\n')
        database=self.database(self.captured('class Partner:\n    _name="res.partner"\n    def helper(self): return 2\n','capture/partner.py','official_code'))
        result=cross_module(database,self.module)
        self.assertTrue(any(r['entity']['name']=='helper' and r['reason']=='local_function_not_a_model_member' for r in result['unresolved']))
        self.assertFalse(any(e['input_entity']['name']=='helper' for r in result['results'] for e in r['evidences']))

    def test_document_and_comment_mentions_are_not_technical_matches(self):
        self.code(PARTNER+'\n# `res.company`\n')
        database=self.database(self.captured('Read `res.partner` and `partner_id`.','capture/guide.md'),
            self.captured('class Other:\n    _name="res.company"\n','capture/company.py','official_code'))
        result=cross_module(database,self.module)
        self.assertEqual(result['results'],[])
        self.assertTrue(any(r['reason']=='non_code_mention' for r in result['unresolved']))

    def test_input_is_read_without_executing_imports_or_top_level_code(self):
        self.code('raise RuntimeError("must never execute")\nimport definitely_missing_crossing_module\n'+PARTNER)
        database=self.database(self.captured(PARTNER,'capture/partner.py','official_code'))
        self.assertEqual(cross_module(database,self.module)['summary']['units_matched'],1)

    def test_units_are_deduplicated_while_occurrences_keep_distinct_evidences(self):
        self.code(PARTNER)
        self.code(PARTNER,'models/second.py')
        database=self.database(self.captured(PARTNER,'capture/partner.py','official_code'))
        result=cross_module(database,self.module)
        self.assertEqual(len(result['results']),1)
        paths={e['input_entity']['location']['artifact_path'] for e in result['results'][0]['evidences']}
        self.assertEqual(paths,{'models/partner.py','models/second.py'})
        ids=[e['id'] for e in result['results'][0]['evidences']]
        self.assertEqual(len(ids),len(set(ids)))

    def test_distinct_units_with_identical_identifiers_are_preserved(self):
        self.code(PARTNER)
        database=self.database(self.captured(PARTNER,'capture/first.py','official_code'),
                               self.captured(PARTNER,'capture/second.py','official_code'))
        self.assertEqual(cross_module(database,self.module)['summary']['units_matched'],2)

    def test_incomplete_partner_python_reports_error_separately_from_no_matches(self):
        self.code('class Broken(\n')
        database=self.database(self.captured(PARTNER,'capture/partner.py','official_code'))
        result=cross_module(database,self.module)
        self.assertEqual(result['outcome'],'undetermined')
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['input']['errors'][0]['stage'],'parsing')

    def test_incomplete_diff_with_a_local_pattern_can_match_only_that_pattern(self):
        self.code('class Partner:\n    _name="res.partner"\n    name=fields.Char(related="partner_id.name")\n')
        diff='--- a/odoo/fields.py\n+++ b/odoo/fields.py\n@@ -20,2 +20,2 @@\n-    )\n+    ))\n     if self.related:\n'
        database=self.database(self.captured(diff,'capture/fields.diff','github_diff'))
        result=cross_module(database,self.module)
        self.assertEqual(len(result['results']),1)
        self.assertTrue(all(e['identity']==['field_option','related'] for e in result['results'][0]['evidences']))

    def test_global_functions_require_matching_module_file_and_scope(self):
        self.code('def helper(): return 1\n','models/helper.py')
        diff='--- a/addons/demo/models/helper.py\n+++ b/addons/demo/models/helper.py\n@@ -1 +1 @@\n-def helper(): return 1\n+def helper(): return 2\n'
        database=self.database(self.captured(diff,'capture/helper.diff','github_diff',dict(module='demo')))
        self.assertEqual(cross_module(database,self.module,module_name='demo')['summary']['units_matched'],1)
        self.assertEqual(cross_module(database,self.module,module_name='other')['results'],[])
        unknown=cross_module(database,self.module)
        self.assertEqual(unknown['results'],[])
        self.assertTrue(any(r['reason']=='unknown_python_namespace_or_file' for r in unknown['unresolved']))

    def test_explicit_external_id_namespaces_match_without_confusing_modules(self):
        self.code('<odoo><record id="view_partner" model="ir.ui.view"/></odoo>','views/partner.xml')
        database=self.database(self.captured('<odoo><record id="demo.view_partner"/></odoo>','capture/view.xml','official_code'))
        self.assertEqual(cross_module(database,self.module,module_name='demo')['summary']['units_matched'],1)
        other=cross_module(database,self.module,module_name='other')
        self.assertFalse(any(e['identity'][0]=='external_id' for r in other['results'] for e in r['evidences']))

    def test_model_identifier_case_and_underscores_are_preserved(self):
        self.code('class A:\n    _name="x.example"\n    def _compute_total(self): return 1\n')
        database=self.database(self.captured('class B:\n    _name="x.example"\n    def _compute_Total(self): return 2\n','capture/a.py','official_code'))
        result=cross_module(database,self.module)
        self.assertFalse(any(e['identity'][0]=='method' for r in result['results'] for e in r['evidences']))

    def test_invalid_code_encoding_is_an_error_and_valid_files_continue(self):
        self.code(PARTNER)
        (self.module/'bad.py').write_bytes(b'\xff\xfeX')
        database=self.database(self.captured(PARTNER,'capture/a.py','official_code'))
        result=cross_module(database,self.module)
        self.assertEqual(result['summary']['units_matched'],1)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['input']['errors'][0]['stage'],'reading')

    def test_manifest_is_literal_not_executed(self):
        self.code("{'name': __import__('os').system('forbidden')}\n",'__manifest__.py')
        database=self.database(self.captured("{'name':'Fixture','depends':['base']}\n",'capture/__manifest__.py','official_manifest'))
        with patch('os.system',side_effect=AssertionError('executed manifest')):
            result=cross_module(database,self.module,module_name='demo')
        self.assertEqual(result['results'],[])
        self.assertEqual(result['outcome'],'undetermined')

    def test_lookup_uses_the_existing_index_and_does_not_scan_unit_text(self):
        self.code(PARTNER)
        database=self.database(self.captured(PARTNER,'capture/a.py','official_code'))
        with connect(database) as con:
            plan=con.execute('EXPLAIN QUERY PLAN SELECT e.payload FROM unit_entities e INDEXED BY unit_entity_lookup WHERE e.name=? AND e.type IN (?)',('res.partner','model')).fetchall()
            self.assertTrue(any('SEARCH' in r[3] and 'unit_entity_lookup' in r[3] for r in plan))
        from r2.crossing import engine
        original=engine.connect
        statements=[]
        from contextlib import contextmanager
        @contextmanager
        def traced(path):
            with original(path) as con:
                con.set_trace_callback(statements.append)
                yield con
        with patch.object(engine,'connect',traced):
            cross_module(database,self.module)
        self.assertTrue(any('JOIN information_units' in q for q in statements))
        self.assertFalse(any('FROM changes' in q or 'FROM unit_terms' in q or 'FROM search ' in q for q in statements))
        self.assertFalse(any('SELECT payload FROM information_units' in q for q in statements))

    def test_reproducibility_persistence_and_inputs_stay_unchanged(self):
        self.code(PARTNER)
        database=self.database(self.captured(PARTNER,'capture/a.py','official_code'))
        before=hashlib.sha256(database.read_bytes()).hexdigest()
        files={p.relative_to(self.module).as_posix():p.read_bytes() for p in self.module.rglob('*') if p.is_file()}
        first=cross_module(database,self.module,output=self.root/'result.json')
        second=cross_module(database,self.module)
        self.assertEqual(first,second)
        self.assertEqual(json.loads((self.root/'result.json').read_text(encoding='utf-8')),first)
        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(),before)
        self.assertEqual({p.relative_to(self.module).as_posix():p.read_bytes() for p in self.module.rglob('*') if p.is_file()},files)
        with self.assertRaises(FileExistsError): save_result(first,database)
        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(),before)

    def test_old_rules_missing_indexes_and_corrupt_index_are_rejected(self):
        self.code(PARTNER)
        for mode in ('old_rules','missing_index','corrupt_entity'):
            with self.subTest(mode=mode):
                database=self.database(self.captured(PARTNER,'capture/a.py','official_code'))
                with closing(sqlite3.connect(database)) as con, con:
                    if mode=='old_rules':
                        value=json.loads(con.execute("SELECT value FROM metadata WHERE key='normalization'").fetchone()[0])
                        value['rules_version']='normalization-1'
                        con.execute("UPDATE metadata SET value=? WHERE key='normalization'",(json.dumps(value),))
                    elif mode=='missing_index': con.execute('DROP INDEX unit_entity_lookup')
                    else:
                        row=con.execute("SELECT unit_id,ordinal,payload FROM unit_entities WHERE type='model'").fetchone()
                        value=json.loads(row[2]);value['location']['content_line']=99999
                        con.execute('UPDATE unit_entities SET payload=? WHERE unit_id=? AND ordinal=?',(json.dumps(value),row[0],row[1]))
                with self.assertRaises(ValueError): cross_module(database,self.module)

    def test_cli_saves_and_prints_the_same_structured_result(self):
        self.code(PARTNER)
        database=self.database(self.captured(PARTNER,'capture/a.py','official_code'))
        with redirect_stdout(io.StringIO()) as stdout:
            main(['cross',str(self.module),'--db',str(database),'--output',str(self.root/'cli.json')])
        self.assertEqual(json.loads(stdout.getvalue()),json.loads((self.root/'cli.json').read_text(encoding='utf-8')))

    def test_clean_absence_is_separate_from_failed_analysis(self):
        self.code('class Other:\n    _name="x.unrelated"\n')
        database=self.database(self.captured(PARTNER,'capture/a.py','official_code'))
        result=cross_module(database,self.module)
        self.assertEqual(result['outcome'],'no_matches')
        self.assertEqual(result['input']['errors'],[])
        self.assertEqual(result['results'],[])

    def test_old_collection_schema_is_refused_instead_of_falling_back_to_changes(self):
        self.code(PARTNER)
        database=self.database(self.captured(PARTNER,'capture/a.py','official_code'))
        with closing(sqlite3.connect(database)) as con, con:
            con.execute("UPDATE metadata SET value='3' WHERE key='schema_version'")
        with self.assertRaisesRegex(ValueError,'schema 4'):
            cross_module(database,self.module)

    def test_cli_reports_an_invalid_database_as_an_error_not_empty_matches(self):
        self.code(PARTNER)
        bad=self.root/'not-sqlite';bad.write_text('not a SQLite collection',encoding='utf-8')
        from contextlib import redirect_stderr
        with redirect_stderr(io.StringIO()) as stderr, self.assertRaises(SystemExit):
            main(['cross',str(self.module),'--db',str(bad)])
        self.assertIn('error:',stderr.getvalue())
