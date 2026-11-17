import ast, io, json, re, tarfile, urllib.request
from pathlib import Path
root=Path(__file__).resolve().parent
report={}
for branch in ['16.0','17.0','18.0','19.0']:
    with urllib.request.urlopen(f'https://codeload.github.com/OCA/OpenUpgrade/tar.gz/refs/heads/{branch}',timeout=60) as response:
        raw=response.read()
    (root/f'OpenUpgrade-{branch}.tar.gz').write_bytes(raw)
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        members=[m for m in tar.getmembers() if m.isfile()]
        apriori=next(m for m in members if m.name.endswith('/openupgrade_scripts/apriori.py'))
        text=tar.extractfile(apriori).read().decode()
        tokens=set()
        active=False
        for line in text.splitlines():
            if line.lstrip().startswith('#'):
                if 'OCA/' in line: active=True
                elif 'odoo' in line.lower(): active=False
            if active and not line.lstrip().startswith('#'):
                tokens.update(re.findall(r'"([a-z][a-z0-9_]+)"',line))
        official=set()
        for f in root.glob('odoo_odoo-*-tree.json'):
            official.update(x['path'].split('/')[-2] for x in json.loads(f.read_text())['tree'] if x['path'].endswith('/__manifest__.py') and len(x['path'].split('/')) in (3,4))
        tokens-=official
        hits=[]; count=0
        for member in members:
            if '/openupgrade_scripts/scripts/' not in member.name: continue
            count+=1
            data=tar.extractfile(member).read().decode('utf-8',errors='replace')
            matches=sorted(t for t in tokens if re.search(r'(?<![\w])'+re.escape(t)+r'(?![\w])',data))
            if matches:
                hits.append({'path':member.name.split('/',1)[1],'oca_names':matches,'lines':[{'line':i,'text':line} for i,line in enumerate(data.splitlines(),1) if any(re.search(r'(?<![\w])'+re.escape(t)+r'(?![\w])',line) for t in matches)]})
        report[branch]={'files_scanned':count,'oca_specific_names_from_apriori':sorted(tokens),'hits':hits}
(root/'content_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
