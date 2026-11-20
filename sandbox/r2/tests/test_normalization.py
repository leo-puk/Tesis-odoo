"""Normalization contracts, source locators and integrated schema-4 behavior."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from r2.collection import build_session,connect,load,compatibility_views,write_collection
from r2.query import retrieve,validate_output
from r2.normalization import normalize_session
from r2.normalization.readers import read_session
from r2.normalization.schema import validate_units,validate_collection
from r2.normalization.units import convert_units
from r2.normalization.entities import extract_entities
from r2.normalization.terms import attach_terms
from examples.run_normalization_demo import run,DIFF


class NormalizationTests(unittest.TestCase):
    def captured(self,text,path='capture/source.txt',kind='official_documentation',binding=None,raw=None):
        source=dict(id='session:unit',unit_id='unit',plan_source_id='fixture',kind=kind,
                    binding=binding or {},from_version=(binding or {}).get('from_version'),
                    to_version=(binding or {}).get('to_version'),url='https://example.invalid/source')
        return dict(source=source,files=[dict(path=path,text=text,raw=raw if raw is not None else text.encode(),
                    metadata={},decoding=dict(encoding='utf-8'),artifact_sha256=hashlib.sha256(text.encode()).hexdigest())])

    def converted(self,*args,**kwargs):
        result=convert_units([self.captured(*args,**kwargs)])
        validate_units(list(result['units'].values()))
        return result,list(result['units'].values())

    def test_diff_added_deleted_multiple_hunks_and_original_coordinates(self):
        text='--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n+x = 1\n--- a/old.py\n+++ /dev/null\n@@ -4 +0,0 @@\n-y = 1\n--- a/a.py\n+++ b/a.py\n@@ -2 +2 @@\n-a\n+b\n@@ -9 +9 @@\n-c\n+d\n'
        result,units=self.converted(text,'capture/core.diff','github_diff')
        self.assertEqual(len(units),4)
        self.assertEqual(sorted(u['source_locator']['line_start'] for u in units),[3,7,11,14])
        for unit in units:
            start,end=unit['source_locator']['line_start'],unit['source_locator']['line_end']
            self.assertEqual('\n'.join(text.splitlines()[start-1:end]),unit['text'])
        self.assertTrue(any(u['data']['old_path'] is None for u in units))
        self.assertTrue(any(u['data']['new_path'] is None for u in units))
        self.assertNotIn('relations',result)

    def test_incomplete_python_has_partial_status_and_no_invented_owner(self):
        text='--- a/odoo/fields.py\n+++ b/odoo/fields.py\n@@ -30,2 +30,2 @@\n-    if self.related:\n+    if self.readonly:\n         pass\n'
        _,units=self.converted(text,'capture/core.diff','github_diff')
        # Dedenting this local block is sufficient syntax; class/model ownership
        # remains unasserted even when the fragment can be parsed.
        self.assertTrue(all(e['context'].get('model') is None for e in units[0]['entities']))
        broken='--- a/odoo/fields.py\n+++ b/odoo/fields.py\n@@ -30,2 +30,2 @@\n-    )\n+    ))\n     if self.related:\n'
        _,units=self.converted(broken,'capture/core.diff','github_diff')
        self.assertEqual(units[0]['normalization_status'],'partial')
        self.assertIn('related',{e['name'] for e in units[0]['entities']})

    def test_markdown_sections_keep_headers_and_ignore_fenced_headers(self):
        text='Preface\n# One\n```python\n# a code comment\n```\n## Two\nRead `res.partner`.\n'
        _,units=self.converted(text,'capture/guide.md')
        self.assertEqual(len(units),3)
        self.assertEqual(''.join(u['text'] for u in sorted(units,key=lambda u:u['source_locator']['line_start'])),text)
        self.assertTrue(any(u['data']['heading']=='## Two' for u in units))

    def test_txt_without_verified_headings_remains_whole(self):
        text='First paragraph.\n\nSecond paragraph mentions `partner_id`.\n'
        _,units=self.converted(text)
        self.assertEqual(len(units),1)
        self.assertEqual(units[0]['text'],text)
        self.assertEqual(units[0]['layers'],['unknown'])
        self.assertEqual(units[0]['entities'][0]['context']['origin'],'documentation')

    def test_manifest_is_literal_complete_and_does_not_infer_version_interval(self):
        _,units=self.converted("{'name':'Fixture','version':'17.0.1.0.0','depends':['base']}",'capture/__manifest__.py','official_manifest')
        self.assertIsNone(units[0]['version_from']);self.assertIsNone(units[0]['version_to'])
        self.assertEqual(units[0]['data']['manifest']['depends'],['base'])
        with patch('os.system',side_effect=AssertionError('must not execute')):
            result,units=self.converted("{'name': __import__('os').system('echo forbidden')}",'capture/__manifest__.py','official_manifest')
        self.assertEqual(units,[]);self.assertEqual(result['issues'][0]['status'],'failed')
        self.assertTrue(next(iter(result['artifacts'].values()))['original_base64'])

    def test_pr_prose_and_duplicate_patch_are_separate_without_duplicate_evidence(self):
        bundle=dict(pull=dict(number=42,body='Description of `res.partner`'),
            comments=[dict(id=1,body='Mention `_compute_total`.')],reviews=[dict(id=2,body='Mention `partner_id`.')],
            review_comments=[dict(id=3,body='Inline `res.partner`.')],commits=[],
            files=[dict(filename='odoo/fields.py',patch=DIFF)],diff=DIFF)
        _,units=self.converted(json.dumps(bundle),'capture/pr.json','github_pr')
        self.assertEqual(len([u for u in units if u['kind']=='diff_hunk']),1)
        self.assertEqual({u['kind'] for u in units},{'pr_description','pr_comment','pr_review','pr_review_comment','diff_hunk'})
        for unit in units:
            self.assertEqual(unit['data']['pr_id'],42)
            self.assertIn('json_pointer',unit['source_locator'])
            if unit['kind'] in {'pr_comment','pr_review','pr_review_comment'}:
                self.assertTrue(all(e['context']['origin']=='comment' for e in unit['entities']))
        block=next(u for u in units if u['kind']=='diff_hunk')
        self.assertEqual(len(block['data']['provenance_references']),2)

    def test_exact_identifiers_and_comment_mentions_are_distinct(self):
        code='class Partner:\n    _name="res.partner"\n    partner_id=fields.Many2one("res.partner")\n    def _compute_total(self):\n        # mention `fake_method`\n        return self.partner_id\n'
        rows,_=extract_entities(code,'models/partner.py',dict(artifact_path='capture/partner.py',line_start=1,line_end=6))
        self.assertTrue({'res.partner','partner_id','_compute_total'} <= {e['name'] for e in rows})
        mention=next(e for e in rows if e['name']=='fake_method')
        self.assertEqual(mention['context']['origin'],'comment')
        self.assertEqual(mention['lookup_keys'],[])

    def test_xml_entity_names_preserve_already_decoded_non_utf8_declarations(self):
        text='<?xml version="1.0" encoding="ISO-8859-1"?><odoo><record id="vista_ñ" model="ir.ui.view"/></odoo>'
        rows,warnings=extract_entities(text,'views/test.xml',dict(artifact_path='capture/test.xml',line_start=1,line_end=1))
        self.assertEqual(warnings,[])
        self.assertIn('vista_ñ',{e['name'] for e in rows})

    def test_bad_diff_is_reported_and_next_source_is_processed(self):
        bad=self.captured('--- a/x\n+++ b/x\n@@ -1,2 +1,2 @@\n-a\n+b\n','capture/bad.diff','github_diff')
        good=self.captured('Read `res.partner`.','capture/good.txt')
        result=convert_units([bad,good])
        self.assertEqual(len(result['units']),1)
        self.assertEqual(result['issues'][0]['stage'],'parsing')
        self.assertEqual(len(result['artifacts']),2)

    def test_html_has_artifact_locator_without_fabricated_text_line_numbers(self):
        _,units=self.converted('<html><body><h1>Title</h1><p>Text <a href="/ref">link</a></p></body></html>','capture/page.html')
        self.assertEqual(units[0]['source_locator'],dict(artifact_path='capture/page.html'))
        self.assertIn('/ref',units[0]['text'])

    def test_tfidf_counts_stop_words_and_scope_are_reproducible(self):
        first=self.captured('the Partner partner value','capture/one.txt')
        second=self.captured('value','capture/two.txt')
        a=convert_units([first,second]);b=convert_units([second,first,deepcopy(first)])
        self.assertEqual(a,b)
        terms=next(u['terms'] for u in a['units'].values() if 'Partner' in u['text'])
        self.assertEqual({t['term']:t['frequency'] for t in terms},{'partner':2,'value':1})
        self.assertGreater(next(t['tfidf'] for t in terms if t['term']=='partner'),0)
        subset=convert_units([first])
        self.assertNotEqual(a['normalization']['terms']['corpus_id'],subset['normalization']['terms']['corpus_id'])
        self.assertEqual({u['id'] for u in subset['units'].values()}, {u['id'] for u in a['units'].values() if 'Partner' in u['text']})

    def test_schema_rejects_missing_provenance_bad_terms_and_relationships(self):
        _,units=self.converted('Read `res.partner`.')
        for mutate in (lambda u:u.pop('source_locator'),lambda u:u.update(terms=[dict(term='x',frequency=0,tfidf=1)]),
                       lambda u:u.update(relations=[]),lambda u:u.update(id='invented')):
            value=deepcopy(units[0]);mutate(value)
            with self.assertRaises(ValueError): validate_units([value])

    def test_empty_corpus_or_stopword_only_document_has_valid_terms_metadata(self):
        self.assertEqual(convert_units([])['normalization']['terms']['document_count'],0)
        _,units=self.converted('the and el la')
        self.assertEqual(units[0]['terms'],[])

    def test_documented_encodings_failed_decoding_and_next_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            session=Path(directory)/('a'*32);session.mkdir()
            rows=[]
            payloads=[(b'Espa\xf1ol',dict(content_type='text/plain; charset=iso-8859-1')),
                      (b'\xff',dict(content_type='text/plain; charset=undefined-codec')),
                      ('Nombre'.encode('utf-16'),{}),(b'Next',{})]
            for i,(raw,details) in enumerate(payloads,1):
                uid=f'{i:032x}';folder=session/uid;folder.mkdir()
                relative=uid+'/source.txt';(folder/'source.txt').write_bytes(raw)
                rows.append(dict(id=uid,source_id=f's{i}',kind='official_documentation',status='accepted',
                    captures=[dict(status=200)],urls=['https://example.invalid/'+str(i)],files=[relative],
                    file_metadata=[dict(path=relative,**details)]))
            inventory=session/'inventory.json';inventory.write_text(json.dumps(rows),encoding='utf-8')
            converted=normalize_session(inventory)
            self.assertEqual({u['text'] for u in converted['units'].values()},{'Español','Nombre','Next'})
            self.assertEqual(len(converted['issues']),1)
            self.assertEqual(converted['issues'][0]['stage'],'decoding')
            self.assertEqual(len(converted['artifacts']),4)
            self.assertTrue(all(u['version_from'] is None for u in converted['units'].values()))

    def test_review_without_body_has_a_real_resource_locator(self):
        bundle=dict(pull=dict(number=42),reviews=[dict(id=3,state='APPROVED')],diff='')
        result,units=self.converted(json.dumps(bundle),'capture/pr.json','github_pr')
        self.assertEqual(len(units),1)
        self.assertEqual(units[0]['source_locator']['json_pointer'],'/reviews/0')
        self.assertEqual(units[0]['data']['resource']['state'],'APPROVED')
        self.assertTrue(validate_collection(result))

    def test_commit_without_message_retains_resource_without_invented_pointer(self):
        result,units=self.converted(json.dumps(dict(pull={},commits=[dict(sha='fixture')],diff='')),'capture/pr.json','github_pr')
        self.assertEqual(units[0]['kind'],'pr_commit')
        self.assertEqual(units[0]['source_locator']['json_pointer'],'/commits/0')
        self.assertTrue(validate_collection(result))

    def test_invalid_pr_diff_keeps_independently_valid_comments(self):
        bundle=dict(pull=dict(number=42,body='Description'),comments=[dict(id=2,body='A comment')],
                    diff='--- a/x\n+++ b/x\n@@ -1,2 +1,2 @@\n-a\n+b\n')
        result,units=self.converted(json.dumps(bundle),'capture/pr.json','github_pr')
        self.assertEqual({u['kind'] for u in units},{'pr_description','pr_comment'})
        self.assertTrue(any('parsing failed' in w for w in result['warnings']))

    def test_locator_validation_checks_the_retained_source(self):
        result,units=self.converted(DIFF,'capture/change.diff','github_diff')
        self.assertTrue(validate_collection(result))
        broken=deepcopy(result)
        next(iter(broken['artifacts'].values()))['text']='Not the captured diff'
        with self.assertRaises(ValueError): validate_collection(broken)

    def test_schema3_collections_keep_the_existing_diff_query_contract(self):
        captured=self.captured(DIFF,'capture/core.diff','github_diff',dict(from_version='16.0',to_version='17.0'))
        captured['source'].update(from_revision='16.0',to_revision='17.0')
        converted=convert_units([captured])
        elements,changes,documents=compatibility_views(converted)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);module=root/'module';module.mkdir()
            (module/'models.py').write_text('class A:\n    _name="fixture"\n    name=fields.Char(related="partner_id.name")\n',encoding='utf-8')
            database=root/'schema3.sqlite'
            write_collection(converted['sources'],elements,{},changes,database,None,None,[],False,[],0,
                             converted['artifacts'],documents,schema=3)
            output=retrieve(database,module,'16.0','17.0')
            self.assertEqual(output['schema_version'],3)
            self.assertEqual(output['summary']['changes_found'],1)
            self.assertTrue(validate_output(output)['conformant'])

    def test_integrated_examples_store_originals_units_terms_entities_and_no_relations(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'demo'
            report=run(output)
            self.assertTrue(report['reprocessing_identical'])
            self.assertEqual(report['build']['schema_version'],4)
            self.assertEqual(report['issues'],[])
            with connect(output/'collection.sqlite') as con:
                self.assertEqual(load(con,'relations'),[])
                stored = json.loads(con.execute(
                    'SELECT payload FROM information_units LIMIT 1').fetchone()[0])
                self.assertFalse({'text', 'data', 'terms'} & stored.keys())
                self.assertGreater(con.execute('SELECT count(*) FROM unit_terms').fetchone()[0],0)
                self.assertGreater(con.execute('SELECT count(*) FROM unit_entities').fetchone()[0],0)
                self.assertEqual(len(load(con,'information_units')),report['unit_count'])
                for artifact in load(con,'artifacts'):
                    original=base64.b64decode(artifact['original_base64'])
                    path=Path(report['capture']['directory'])/artifact['path']
                    self.assertEqual(original,path.read_bytes())
            new_db=output/'repeat.sqlite'
            rebuilt=build_session(report['capture']['inventory'],output/'bindings.json',new_db)
            self.assertEqual(rebuilt['collection_revision'],report['build']['collection_revision'])
