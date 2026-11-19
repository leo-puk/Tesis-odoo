"""Review regressions: ID handoff, side policies, single files and real CSV units."""
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_crossing as fixtures
from r2.cli import main
from r2.crossing import cross_module, save_result
from r2.crossing.code import read_code
from r2.crossing.rules import partner_identity, unit_identity
from r2.normalization.schema import validate_collection
from r2.normalization.units import convert_units


class CrossingCorrectionTests(unittest.TestCase):
    setUp = fixtures.CrossingTests.setUp
    captured = fixtures.CrossingTests.captured
    code = fixtures.CrossingTests.code
    database = fixtures.CrossingTests.database

    def test_handoff_contains_only_ids_and_point_evidence_not_unit_content(self):
        self.code(fixtures.PARTNER)
        original='"""DOCUMENT_CONTENT_SENTINEL_'+('large prose '*1000)+'"""\n'+fixtures.PARTNER
        database=self.database(self.captured(original,'capture/partner.py','official_code'))
        before=hashlib.sha256(database.read_bytes()).hexdigest()
        first=cross_module(database,self.module,output=self.root/'result.json')
        second=cross_module(database,self.module)
        self.assertEqual(first,second)
        self.assertEqual(first,json.loads((self.root/'result.json').read_text(encoding='utf-8')))
        ids=first['matched_unit_ids']
        self.assertEqual(ids,sorted(set(ids)))
        self.assertEqual(ids,[r['information_unit_id'] for r in first['results']])
        self.assertEqual(first['summary']['units_matched'],len(ids))
        self.assertEqual(first['summary']['evidences'],sum(len(r['evidences']) for r in first['results']))
        for result in first['results']:
            self.assertEqual(set(result),{'information_unit_id','evidences'})
            self.assertGreater(len(result['evidences']),1)
            for evidence in result['evidences']:
                self.assertIn('location',evidence['input_entity'])
                self.assertIn('location',evidence['unit_entity'])
                self.assertNotIn('text',evidence['unit_entity'])
                self.assertNotIn('data',evidence['unit_entity'])
                self.assertNotIn('terms',evidence['unit_entity'])
        self.assertNotIn('DOCUMENT_CONTENT_SENTINEL',json.dumps(first))
        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(),before)

    def test_partner_comments_are_not_seeds_but_typed_unit_comments_are_eligible(self):
        entity=dict(name='action',type='method',location=dict(artifact_path='pr.json',json_pointer='/comments/0/body'),
                    rule='explicit_typed_fixture',context=dict(origin='comment',model='res.partner',scope='class'),
                    lookup_keys=['deliberately_untrusted'])
        self.assertEqual(partner_identity(entity),(None,'non_code_mention'))
        self.assertEqual(unit_identity(entity)[0],('method','res.partner','action'))
        # No normalization currently emits typed method comments. This checks
        # eligibility in isolation, without fabricating a normalized collection.
        documented=deepcopy(entity);documented['context']['origin']='documentation'
        self.assertEqual(unit_identity(documented)[0],('method','res.partner','action'))
        for model in ('res.company',None):
            wrong=deepcopy(entity);wrong['context']['model']=model
            self.assertNotEqual(unit_identity(wrong)[0],('method','res.partner','action'))
        wrong=deepcopy(entity);wrong['type']='field'
        self.assertNotEqual(unit_identity(wrong)[0],unit_identity(entity)[0])
        generic=deepcopy(entity);generic['type']='identifier_mention'
        self.assertIsNone(unit_identity(generic)[0])

    def test_generic_document_mentions_remain_unmatched_in_real_normalization(self):
        self.code(fixtures.PARTNER)
        database=self.database(self.captured('Read `res.partner` and `partner_id`.','capture/doc.md'))
        self.assertEqual(cross_module(database,self.module)['matched_unit_ids'],[])

    def test_python_file_reads_only_that_file_and_does_not_execute(self):
        self.code('raise RuntimeError("must not execute")\nimport missing_crossing_package\n'+fixtures.PARTNER,'partner.py')
        (self.module/'bad_neighbor.py').write_bytes(b'\xff')
        database=self.database(self.captured(fixtures.PARTNER,'capture/partner.py','official_code'))
        entry=self.module/'partner.py'
        result=cross_module(database,entry)
        self.assertEqual(result['input']['input_kind'],'file')
        self.assertEqual(result['input']['module_path'],str(entry.resolve()))
        self.assertEqual([f['path'] for f in result['input']['files']],['partner.py'])
        self.assertEqual(result['input']['errors'],[])
        self.assertEqual(len(result['matched_unit_ids']),1)

    def test_xml_and_literal_manifest_files_are_supported(self):
        self.code('<odoo><record id="demo.view"/></odoo>','one.xml')
        self.code("{'name':'Fixture','depends':['base']}\n",'__manifest__.py')
        database=self.database(self.captured('<odoo><record id="demo.view"/></odoo>','capture/one.xml','official_code'),
                               self.captured("{'name':'Other','depends':['base']}\n",'capture/__manifest__.py','official_manifest'))
        for name in ('one.xml','__manifest__.py'):
            with self.subTest(name=name):
                result=cross_module(database,self.module/name,module_name='demo')
                self.assertEqual(result['summary']['files_read'],1)
                self.assertTrue(result['matched_unit_ids'])

    def test_missing_unsupported_invalid_and_unreadable_inputs_are_distinct(self):
        with self.assertRaisesRegex(ValueError,'does not exist'): read_code(self.root/'missing.py')
        self.code('plain text','readme.txt')
        with self.assertRaisesRegex(ValueError,'Unsupported'): read_code(self.module/'readme.txt')
        self.code('def broken(\n','bad.py')
        self.assertEqual(read_code(self.module/'bad.py')['errors'][0]['stage'],'parsing')
        (self.module/'bytes.py').write_bytes(b'\xff')
        self.assertEqual(read_code(self.module/'bytes.py')['errors'][0]['stage'],'reading')

    def test_linked_single_file_is_rejected_before_reading(self):
        self.code(fixtures.PARTNER,'partner.py')
        entry=self.module/'partner.py'
        original=Path.is_symlink
        def linked(path): return path==entry or original(path)
        # Portable guard test: Windows symlink creation needs extra privileges.
        with patch.object(Path,'is_symlink',linked), patch.object(Path,'read_bytes',side_effect=AssertionError('link read')):
            with self.assertRaisesRegex(ValueError,'links'): read_code(entry)

    def test_csv_explicit_ids_cross_on_both_sides_without_model_inference(self):
        text='id,name,model_id:id,group_id:id,perm_read\naccess_demo,Description,base.model_res_partner,base.group_user,1\n'
        self.code(text,'security/access.csv')
        captured=self.captured(text,'capture/access.csv','official_code',dict(module='demo'))
        normalized=convert_units([captured])
        self.assertTrue(validate_collection(normalized))
        entities=next(iter(normalized['units'].values()))['entities']
        self.assertEqual({e['type'] for e in entities},{'external_id'})
        self.assertEqual({e['name'] for e in entities},{'access_demo','base.model_res_partner','base.group_user'})
        self.assertFalse(any(e['name']=='res.partner' for e in entities))
        database=self.database(captured)
        result=cross_module(database,self.module/'security/access.csv',module_name='demo')
        self.assertEqual(len(result['matched_unit_ids']),1)
        names={e['input_entity']['name'] for r in result['results'] for e in r['evidences']}
        self.assertEqual(names,{'access_demo','base.model_res_partner','base.group_user'})
        self.assertTrue(all(e['identity'][0]=='external_id' for r in result['results'] for e in r['evidences']))

    def test_csv_namespaces_unknown_locals_and_descriptive_columns(self):
        self.code('id,description,group_id:id,count\nlocal_id,base.group_user,other.group_user,42\n','input.csv')
        database=self.database(self.captured('id,group_id:id\nsource_id,base.group_user\n','capture/other.csv','official_code'))
        result=cross_module(database,self.module/'input.csv')
        self.assertEqual(result['matched_unit_ids'],[])
        self.assertTrue(any(r['entity']['name']=='local_id' and r['reason']=='unknown_external_id_namespace' for r in result['unresolved']))
        self.assertEqual({e['name'] for e in result['input']['entities']},{'local_id','other.group_user'})

    def test_csv_physical_locations_quoted_rows_and_malformed_rows(self):
        text='id,description,group_id:id\nfirst,"two\nphysical lines",base.group_user\nmissing,column\nsecond,ok,base.group_system\n'
        self.code(text,'input.csv')
        code=read_code(self.module/'input.csv',module_name='demo')
        group=next(e for e in code['entities'] if e['name']=='base.group_user')
        self.assertEqual(group['location']['content_line'],2)
        self.assertEqual(group['location']['artifact_line'],2)
        self.assertEqual(group['location']['content_end_line'],3)
        self.assertEqual(group['location']['csv_row'],2)
        self.assertEqual(group['location']['csv_column'],3)
        self.assertEqual(group['context']['original_value'],'base.group_user')
        self.assertTrue(any('column count' in n['reason'] for n in code['limitations']))
        last=next(e for e in code['entities'] if e['name']=='base.group_system')
        self.assertEqual(last['location']['artifact_line'],5)
        bad='id,group_id:id\nx,"unterminated\n'
        self.code(bad,'bad.csv')
        self.assertTrue(any('CSV parse error' in n['reason'] for n in read_code(self.module/'bad.csv')['limitations']))

    def test_csv_invalid_identifiers_and_partial_diff_header_are_not_invented(self):
        self.code('id,other_id:id,note\n123,has spaces,res.partner\n','input.csv')
        code=read_code(self.module/'input.csv')
        self.assertEqual(code['entities'],[])
        self.assertTrue(code['limitations'])
        from r2.csv_entities import extract_csv_entities
        rows,warnings=extract_csv_entities('id,group_id:id\nx,base.group_user\n',dict(artifact_path='diff'),side='after',start=20,path='security/x.csv')
        self.assertEqual(rows,[])
        self.assertTrue(warnings)

    def test_cli_file_input_and_persistence_use_the_id_handoff(self):
        self.code(fixtures.PARTNER,'partner.py')
        database=self.database(self.captured(fixtures.PARTNER,'capture/p.py','official_code'))
        output=self.root/'result.json'
        with redirect_stdout(io.StringIO()) as stdout:
            main(['cross',str(self.module/'partner.py'),'--db',str(database),'--output',str(output)])
        result=json.loads(stdout.getvalue())
        self.assertEqual(result,json.loads(output.read_text(encoding='utf-8')))
        self.assertEqual(len(result['matched_unit_ids']),1)
        self.assertNotIn('unit',result['results'][0])

    def test_persistence_rejects_copied_units_or_inconsistent_id_accounting(self):
        self.code(fixtures.PARTNER)
        database=self.database(self.captured(fixtures.PARTNER,'capture/p.py','official_code'))
        result=cross_module(database,self.module)
        for mutate in (lambda r:r['results'][0].update(unit={'text':'document copy'}),
                       lambda r:r.update(matched_unit_ids=[]),
                       lambda r:r['summary'].update(evidences=99999)):
            broken=deepcopy(result);mutate(broken)
            output=self.root/'invalid-report.json'
            with self.assertRaises(ValueError): save_result(broken,output)
            self.assertFalse(output.exists())
