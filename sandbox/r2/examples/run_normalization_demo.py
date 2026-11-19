"""Synthetic accepted captures via mocked HTTP; no live source claims or execution."""
import argparse
import difflib
import json
from pathlib import Path
from r2.adquisition import capture_plan
from r2.collection import build_session,connect,load
from r2.normalization import normalize_session

DIFF_URL='https://github.com/odoo/odoo/compare/16.0...17.0'
MD_URL='https://raw.githubusercontent.com/OCA/maintainer-tools/master/normalization-demo.md'
TXT_URL='https://www.odoo.com/documentation/17.0/normalization-demo.txt'
MANIFEST_URL='https://raw.githubusercontent.com/odoo/odoo/17.0/addons/sale/__manifest__.py'
PR_URL='https://github.com/odoo/odoo/pull/1'
BEFORE='class Field:\n    def setup(self):\n        pass\n'
AFTER='class Field:\n    def setup(self):\n        if self.related:\n            return self.related\n'
DIFF=''.join(difflib.unified_diff(BEFORE.splitlines(True),AFTER.splitlines(True),fromfile='a/odoo/fields.py',tofile='b/odoo/fields.py'))


def run(output):
    output=Path(output)
    if output.exists(): raise ValueError('Choose a new example output directory')
    output.mkdir(parents=True)
    def save(name,value):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    kinds={'diff':'github_diff','markdown':'oca_guidance','text':'official_documentation','manifest':'official_manifest','pr':'github_pr'}
    urls={'diff':DIFF_URL,'markdown':MD_URL,'text':TXT_URL,'manifest':MANIFEST_URL,'pr':PR_URL}
    names={'diff':'change.diff','markdown':'guide.md','text':'guide.txt','manifest':'__manifest__.py','pr':'pr.json'}
    save('plan.json',[dict(id=k,kind=kinds[k],files={names[k]:v}) for k,v in urls.items()])
    save('catalog.json',dict(allowed_urls=list(urls.values()),excluded_urls=[],oca_repositories=['OCA/excluded-fixture'],oca_addons=['excluded_fixture_addon']))
    save('bindings.json',dict(sources={k:dict(from_version='16.0',to_version='17.0',from_revision='16.0',to_revision='17.0') for k in kinds}))
    class Response:
        status=200
        headers={'Content-Type':'text/plain; charset=utf-8'}
        def __init__(self,value): self.raw=value if isinstance(value,bytes) else json.dumps(value).encode()
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return self.raw
    def transport(req,**kwargs):
        url=req.full_url
        if req.get_header('Accept')=='application/vnd.github.diff': return Response(DIFF.encode())
        if url==MD_URL: return Response(b'# Preparation\nRead `res.partner`.\n\n## Field options\nInspect `related`.\n')
        if url==TXT_URL: return Response('Documento íntegro sin límites estructurales verificables.\r\n'.encode())
        if url==MANIFEST_URL: return Response(b"{'name':'Fixture','version':'17.0.1.0.0','depends':['base'],'data':['views/demo.xml']}\n")
        if '?' not in url:
            return Response(dict(number=1,id=101,html_url=PR_URL,merged_at='2026-01-01',changed_files=1,commits=1,body='Describe `res.partner` without declaring a technical relationship.'))
        if '/files?' in url: return Response([dict(filename='odoo/fields.py',patch=DIFF)])
        if '/commits?' in url: return Response([dict(sha='fixture',commit=dict(message='Document `related` behavior'))])
        return Response([dict(id=201,body='Comment mentions `_compute_total`; this is commentary.')])
    captured=capture_plan(output/'plan.json',output,catalog_path=output/'catalog.json',transport=transport)
    normalized=normalize_session(captured['inventory'],output/'bindings.json')
    repeated=normalize_session(captured['inventory'],output/'bindings.json')
    assert normalized==repeated
    built=build_session(captured['inventory'],output/'bindings.json',output/'collection.sqlite')
    with connect(output/'collection.sqlite') as con:
        units=load(con,'information_units')
        assert load(con,'relations')==[]
    save('units.json',units)
    save('normalization.json',normalized['normalization'])
    report=dict(synthetic=True,http='mocked; no live downloads',capture=captured,build=built,
                kinds=sorted({u['kind'] for u in units}),unit_count=len(units),reprocessing_identical=True,
                search_relations_generated=0,issues=normalized['issues'])
    save('report.json',report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(run(args.output),ensure_ascii=False,indent=2))
