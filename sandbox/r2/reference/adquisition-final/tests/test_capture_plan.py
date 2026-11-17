import json
from pathlib import Path
import tempfile
import unittest
from adquisition import capture_plan, delete_units

DOC = 'https://www.odoo.com/documentation/19.0/migration.html'
DIFF = 'https://github.com/odoo/odoo/compare/16.0...17.0'
PR = 'https://github.com/odoo/odoo/pull/123'


class Response:
    status = 200
    def __init__(self, value, ctype='application/json'):
        self.raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.headers = {'Content-Type': ctype}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return self.raw


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = self.root/'catalog.json'
        self.catalog.write_text(json.dumps(dict(allowed_urls=[DOC, DIFF, PR], excluded_urls=[],
            oca_repositories=['OCA/account-reconcile'], oca_addons=['account_reconcile_oca'])))
        self.calls = []

    def run_plan(self, kind='official_documentation', url=DOC, response=None):
        plan = self.root/'plan.json'
        plan.write_text(json.dumps([dict(id='one', kind=kind, files={'source.html':url})]))
        def transport(req, timeout):
            self.calls.append(req)
            return response(req) if callable(response) else Response(response or b'<p>Migration guide</p>', 'text/html; charset=utf-8')
        result = capture_plan(plan, self.root, catalog_path=self.catalog, transport=transport)
        self.session = result
        self.units = json.loads(Path(result['inventory']).read_text())
        return result

    def test_document_conversion_and_deletion(self):
        result = self.run_plan()
        unit = self.units[0]
        file = Path(result['directory'])/unit['files'][0]
        self.assertEqual(file.suffix, '.txt')
        self.assertIn('Migration guide', file.read_text())
        self.assertNotIn('sha256', json.dumps(unit))
        self.assertEqual(delete_units(result['session_id'], [unit['id']], self.root)[0]['status'], 'deleted')
        self.assertFalse(file.exists())
        self.assertTrue((Path(result['directory'])/'acquisition.jsonl').exists())
        self.assertFalse((Path(result['directory'])/'capture-report.json').exists())

    def test_unknown_url_rejected_without_network(self):
        self.run_plan(url='https://github.com/OCA/account-reconcile/pull/974')
        self.assertEqual(self.calls, [])
        self.assertEqual(self.units[0]['status'], 'excluded')

    def test_allowed_but_oca_repository_rejected(self):
        data = json.loads(self.catalog.read_text())
        url='https://github.com/OCA/account-reconcile/pull/974'
        data['allowed_urls'].append(url)
        self.catalog.write_text(json.dumps(data))
        self.run_plan(url=url)
        self.assertEqual(self.calls, [])

    def test_mixed_content_not_written(self):
        result = self.run_plan(response=b'<p>official and account_reconcile_oca</p>')
        self.assertEqual(self.units[0]['status'], 'excluded')
        self.assertEqual(list(Path(result['directory']).glob('**/*.bin')), [])
        self.assertEqual(list(Path(result['directory']).glob('**/*.txt')), [])

    def test_document_link_to_excluded_repository(self):
        self.run_plan(response=b'<a href="https://github.com/OCA/account-reconcile/pull/1">link</a>')
        self.assertEqual(self.units[0]['status'], 'excluded')

    def test_diff_saved_through_api(self):
        def response(req):
            self.assertEqual(req.get_header('Accept'), 'application/vnd.github.diff')
            self.assertIn('/repos/odoo/odoo/compare/', req.full_url)
            return Response(b'diff --git a/a b/a\n-old\n+new\n', 'text/plain')
        result = self.run_plan('github_diff', DIFF, response)
        self.assertEqual(result['included'], 1)
        file = Path(result['directory'])/self.units[0]['files'][0]
        self.assertEqual(file.suffix, '.diff')
        self.assertIn(b'+new', file.read_bytes())

    def pr_response(self, merged=True, mixed=False, files=1):
        def response(req):
            url = req.full_url
            if req.get_header('Accept') == 'application/vnd.github.diff':
                return Response(b'diff --git a/a b/a', 'text/plain')
            if '?' not in url:
                return Response(dict(merged_at='2026-01-01' if merged else None, changed_files=files, commits=1, body='description'))
            if '/files?' in url:
                return Response([dict(filename='a.py', patch='patch')])
            if '/commits?' in url: return Response([dict(sha='a', commit={'message':'change'})])
            if '/reviews?' in url: return Response([dict(body='review')])
            if '/issues/' in url: return Response([dict(body='account_reconcile_oca' if mixed else 'comment')])
            return Response([dict(body='inline')])
        return response

    def test_merged_pr_full_content(self):
        result = self.run_plan('github_pr', PR, self.pr_response())
        file = Path(result['directory'])/self.units[0]['files'][0]
        data = json.loads(file.read_text())
        self.assertEqual(set(data), {'pull','files','commits','comments','reviews','review_comments','diff'})
        self.assertEqual(data['comments'][0]['body'], 'comment')

    def test_unmerged_pr_excluded(self):
        self.run_plan('github_pr', PR, self.pr_response(merged=False))
        self.assertEqual(self.units[0]['status'], 'excluded')
        self.assertEqual(len(self.calls), 1)

    def test_pr_mixed_comment_excludes_entire_unit(self):
        self.run_plan('github_pr', PR, self.pr_response(mixed=True))
        self.assertEqual(self.units[0]['status'], 'excluded')
        self.assertEqual(self.units[0]['files'], [])

    def test_pr_incomplete_files(self):
        self.run_plan('github_pr', PR, self.pr_response(files=2))
        self.assertEqual(self.units[0]['status'], 'incomplete')

    def test_deletion_does_not_touch_other_units(self):
        first = self.run_plan()
        file = Path(first['directory'])/self.units[0]['files'][0]
        second = self.run_plan()
        delete_units(second['session_id'], [self.units[0]['id']], self.root)
        self.assertTrue(file.exists())
        with self.assertRaises(ValueError):
            delete_units('../outside', [], self.root)

    def test_pagination_collects_second_page(self):
        from adquisition.github import GitHubMetadata
        from adquisition.policy import SourcePolicy
        calls=[]
        def transport(req, timeout):
            calls.append(req.full_url)
            return Response([{'body':'ok'}]*100 if req.full_url.endswith('&page=1') else [{'body':'last'}])
        client=GitHubMetadata(self.root/'temp_data', transport, SourcePolicy(json.loads(self.catalog.read_text())))
        captures=[]
        values=client._pages('/repos/odoo/odoo/issues/123/comments', captures)
        self.assertEqual(len(values),101)
        self.assertEqual(len(calls),2)

    def test_network_failure_logged_without_token(self):
        from urllib.error import HTTPError
        def fail(req):
            raise HTTPError(req.full_url,403,'secret error body',{},None)
        result=self.run_plan(response=fail)
        self.assertEqual(self.units[0]['status'],'failed')
        log=(Path(result['directory'])/'acquisition.jsonl').read_text()
        self.assertIn('403',log)
        self.assertNotIn('secret error body',log)

    def test_html_encoded_identifier_excluded(self):
        self.run_plan(response=b'<p>account&#95;reconcile&#95;oca</p>')
        self.assertEqual(self.units[0]['status'],'excluded')

    def test_catalog_is_required(self):
        from adquisition.policy import SourcePolicy
        with self.assertRaises(ValueError):
            SourcePolicy(dict(allowed_urls=[DOC]))

    def test_path_escape_fails_before_network(self):
        plan=self.root/'invalid.json'
        plan.write_text(json.dumps([dict(id='one',kind='official_documentation',files={'../escape':DOC})]))
        with self.assertRaises(ValueError):
            capture_plan(plan,self.root,catalog_path=self.catalog,
                         transport=lambda *args,**kwargs:self.fail('No network expected'))

    def test_explicit_exclusion_overrides_allowlist(self):
        data=json.loads(self.catalog.read_text())
        data['excluded_urls']=[DOC]
        self.catalog.write_text(json.dumps(data))
        self.run_plan()
        self.assertEqual(self.calls,[])

    def test_binary_document_rejected(self):
        self.run_plan(response=lambda req:Response(b'%PDF-binary','application/pdf'))
        self.assertEqual(self.units[0]['status'],'excluded')

    def test_transient_http_error_retries(self):
        from adquisition.http import HttpCapture
        from urllib.error import HTTPError
        from unittest.mock import patch
        calls=[]
        def transport(req,timeout):
            calls.append(req)
            if len(calls)==1: raise HTTPError(req.full_url,503,'busy',{},None)
            return Response(b'ok','text/plain')
        with patch('adquisition.http.time.sleep'):
            raw,_=HttpCapture(self.root/'temp_data',transport).get(DOC)
        self.assertEqual(raw,b'ok')
        self.assertEqual(len(calls),2)

    def test_repeated_url_downloaded_once_with_independent_units(self):
        plan=self.root/'repeat.json'
        plan.write_text(json.dumps([dict(id=str(i),kind='official_documentation',files={'doc.html':DOC}) for i in range(2)]))
        calls=[]
        def transport(req,timeout):
            calls.append(req)
            return Response(b'<p>guide</p>','text/html')
        result=capture_plan(plan,self.root,catalog_path=self.catalog,transport=transport)
        units=json.loads(Path(result['inventory']).read_text())
        self.assertEqual(len(calls),1)
        self.assertEqual(result['included'],2)
        delete_units(result['session_id'],[units[0]['id']],self.root)
        self.assertTrue((Path(result['directory'])/units[1]['files'][0]).exists())

    def test_mixed_second_file_discards_whole_unit(self):
        second=DOC.replace('migration.html','second.html')
        catalog=json.loads(self.catalog.read_text())
        catalog['allowed_urls'].append(second)
        self.catalog.write_text(json.dumps(catalog))
        plan=self.root/'mixed.json'
        plan.write_text(json.dumps([dict(id='bundle',kind='official_documentation',files={'a.html':DOC,'b.html':second})]))
        def transport(req,timeout):
            return Response(b'<p>account_reconcile_oca</p>' if req.full_url==second else b'<p>official</p>','text/html')
        result=capture_plan(plan,self.root,catalog_path=self.catalog,transport=transport)
        unit=json.loads(Path(result['inventory']).read_text())[0]
        self.assertEqual(unit['status'],'excluded')
        self.assertFalse((Path(result['directory'])/unit['id']).exists())
