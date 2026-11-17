import json, urllib.request, urllib.parse, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'r2-source-audit','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=60) as response:
        return json.load(response)

report={'branches':{},'prs':[],'errors':[]}
official=set()
for branch in ['16.0','17.0','18.0','19.0']:
    row={}
    for repo in ['odoo/odoo','OCA/OpenUpgrade']:
        try:
            data=get(f'https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1')
            (ROOT/f'{repo.replace("/","_")}-{branch}-tree.json').write_text(json.dumps(data),encoding='utf-8')
            paths=[x['path'] for x in data['tree']]
            row[repo]={'sha':data['sha'],'truncated':data.get('truncated'), 'paths':len(paths)}
            if repo=='odoo/odoo':
                names={p.split('/')[-2] for p in paths if p.endswith('/__manifest__.py') and (p.startswith('addons/') or p.startswith('odoo/addons/')) and len(p.split('/')) in (3,4)}
                official.update(names)
                row['official_names']=sorted(names)
            else:
                names={p.split('/')[2] for p in paths if p.startswith('openupgrade_scripts/scripts/') and len(p.split('/'))>3}
                row['script_modules']=sorted(names)
                row['root_directories']=sorted({p.split('/')[0] for p in paths})
        except Exception as exc:
            report['errors'].append({'branch':branch,'repo':repo,'error':str(exc)})
    report['branches'][branch]=row
for row in report['branches'].values():
    row['not_in_official_union']=sorted(set(row.get('script_modules',[]))-official)
for repo in ['odoo/odoo','OCA/OpenUpgrade','OCA/account-reconcile']:
    for status in ['is:merged','is:open','is:closed is:unmerged']:
        for migration in [True,False]:
            terms='migration in:title' if migration else '-migration in:title'
            query=f'repo:{repo} is:pr {status} {terms}'
            try:
                data=get('https://api.github.com/search/issues?'+urllib.parse.urlencode({'q':query,'per_page':2}))
                report['prs'].append({'repo':repo,'status':status,'migration_title':migration,'query':query,'count':data['total_count'],'incomplete':data.get('incomplete_results'),'examples':[{'number':x['number'],'title':x['title'],'url':x['html_url'],'body':x.get('body'),'state':x['state'],'pull_request':x.get('pull_request')} for x in data['items']]})
            except Exception as exc:
                report['errors'].append({'query':query,'error':str(exc)})
            time.sleep(2)
(ROOT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'branches':[{k:v for k,v in r.items() if k not in ['official_names','script_modules']} for r in report['branches'].values()],'prs':[{k:v for k,v in r.items() if k!='examples'} for r in report['prs']],'errors':report['errors']},ensure_ascii=False))
