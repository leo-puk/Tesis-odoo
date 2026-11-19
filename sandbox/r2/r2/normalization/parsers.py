"""Format boundaries with locators in the captured artifact, not invented files."""
import ast
import json
import re
from pathlib import PurePosixPath
from lxml import html
from .diff import parse_diff


def sections(text, rst=False):
    lines = text.splitlines(keepends=True)
    starts, fenced = [], None
    for i, line in enumerate(lines):
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker and not rst:
            if fenced is None:
                fenced = marker[1]
            elif marker[1][0] == fenced[0] and len(marker[1])>=len(fenced) and not line[marker.end():].strip():
                fenced = None
            continue
        if fenced:
            continue
        heading = re.match(r"^ {0,3}#{1,6}\s+\S", line) if not rst else None
        underline = (i + 1 < len(lines) and bool(line.strip()) and
                     bool(re.fullmatch(r"\s*([=~-])\1{2,}\s*", lines[i+1])) and
                     (rst or lines[i+1].lstrip().startswith(('=', '-'))))
        if heading or underline:
            starts.append(i)
    bounds = sorted({0, *starts, len(lines)})
    if not lines:
        bounds = [0, 0]
    for start, end in zip(bounds, bounds[1:]):
        value = ''.join(lines[start:end])
        if value.strip():
            yield dict(text=value, locator=dict(line_start=start+1, line_end=end),
                       data=dict(heading=lines[start].strip() if start in starts else None))


def diff_parts(text, pointer=None):
    hunks, warnings = parse_diff(text)
    parts = []
    for hunk in hunks:
        locator = dict(line_start=hunk.pop('artifact_start'), line_end=hunk.pop('artifact_end'))
        if pointer is not None:
            locator['json_pointer'] = pointer
            locator['lines_in'] = 'decoded_json_string'
        parts.append(dict(kind='diff_hunk', text=hunk['diff_header']+'\n'+hunk['diff_body'],
                          locator=locator, rule='unified_diff_hunk_v1', data=hunk,
                          origin='code', warnings=list(warnings)))
    return parts, warnings


def pr_parts(text):
    bundle = json.loads(text)
    if not isinstance(bundle, dict):
        raise ValueError('PR bundle must be an object')
    parts, warnings = [], []
    pull = bundle.get('pull', {})
    if not isinstance(pull, dict):
        raise ValueError('PR pull metadata must be an object')
    context = dict(pr_id=pull.get('number') or pull.get('id'), pr_url=pull.get('html_url'),pr_title=pull.get('title'))

    def prose(value, pointer, kind, resource_id=None, resource=None, resource_pointer=None):
        if value is not None and not isinstance(value, str):
            raise ValueError('PR prose must be text or null')
        locator=dict(json_pointer=pointer)
        if isinstance(resource,dict) and 'body' not in resource and kind in {'pr_comment','pr_review','pr_review_comment'}:
            locator=dict(json_pointer=pointer.rsplit('/',1)[0],representation='resource_without_body')
        if resource_pointer is not None:
            locator=dict(json_pointer=resource_pointer,representation='resource_without_text')
        parts.append(dict(kind=kind, text=value or '', locator=locator,
                          rule='github_pr_resource_v1', origin='documentation' if kind=='pr_description' else 'comment',
                          data={**context, 'resource_id':resource_id,'resource':resource,
                                'body_missing':value is None}, warnings=[]))

    if 'body' in pull:
        prose(pull.get('body'), '/pull/body', 'pr_description', pull.get('id'))
    for key, kind in (('comments','pr_comment'), ('reviews','pr_review'), ('review_comments','pr_review_comment')):
        values = bundle.get(key, [])
        if not isinstance(values, list):
            raise ValueError('PR resources must be lists')
        for i, value in enumerate(values):
            if not isinstance(value, dict):
                raise ValueError('PR resource must be an object')
            prose(value.get('body'), f'/{key}/{i}/body', kind, value.get('id'),value)
    for i, value in enumerate(bundle.get('commits', [])):
        if not isinstance(value, dict):
            raise ValueError('PR commit must be an object')
        message=value.get('commit', {}).get('message')
        pointer=None if 'message' in value.get('commit',{}) else f'/commits/{i}'
        prose(message, f'/commits/{i}/commit/message', 'pr_commit', value.get('sha'),value,pointer)
    # The canonical /diff is authoritative when present. GitHub file.patch is
    # retained as provenance, never emitted again as independent evidence.
    canonical = bundle.get('diff')
    files = bundle.get('files', [])
    if not isinstance(files, list) or any(not isinstance(f,dict) for f in files):
        raise ValueError('PR files must be objects in a list')
    if canonical is not None:
        if not isinstance(canonical, str):
            raise ValueError('PR diff must be text')
        try:
            blocks, notes = diff_parts(canonical, '/diff')
        except ValueError as exc:
            blocks,notes=[],['Canonical PR diff parsing failed; original retained: '+str(exc)]
        warnings.extend(notes)
        for block in blocks:
            block['data'].update(context)
            block['data']['provenance_references'] = [dict(json_pointer='/diff')]
            for i, value in enumerate(files):
                if value.get('filename') in {block['data']['old_path'], block['data']['new_path']} and value.get('patch'):
                    block['data']['provenance_references'].append(dict(json_pointer=f'/files/{i}/patch'))
            parts.append(block)
    else:
        # Standalone per-file patches often lack ---/+++ headers. Do not invent
        # those headers or coordinates to make a truncated patch parseable.
        warnings.append('PR bundle has no canonical diff; file patches retained only in original artifact')
    return parts, warnings


def html_text(text):
    root = html.fromstring(text, parser=html.HTMLParser(no_network=True))
    for node in root.xpath('//script|//style|//nav|//footer'):
        node.drop_tree()
    blocks = {'p','div','h1','h2','h3','h4','h5','h6','li','tr','pre','section','br'}
    def render(node):
        body = node.text or ''
        for child in node:
            body += render(child) + (child.tail or '')
        if node.tag == 'a' and node.get('href'):
            body += ' ('+node.get('href')+')'
        if node.tag in {'td','th'}:
            body += '\t'
        return ('\n'+body+'\n') if node.tag in blocks else body
    return render(root).strip()


def parse_artifact(artifact, source):
    text = artifact['text']
    suffix = PurePosixPath(artifact['path']).suffix.lower()
    kind = source['kind']
    if kind == 'github_diff' or suffix == '.diff':
        return diff_parts(text)
    if kind == 'github_pr':
        return pr_parts(text)
    if kind == 'official_manifest' or PurePosixPath(artifact['path']).name.endswith('__manifest__.py'):
        tree = ast.parse(text)
        if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr):
            raise ValueError('Manifest must contain only a literal dictionary expression')
        value = ast.literal_eval(tree.body[0].value)
        if not isinstance(value, dict):
            raise ValueError('Manifest must be a literal dictionary')
        if any(not isinstance(k,str) for k in value):
            raise ValueError('Manifest keys must be strings')
        for key in ('depends','data','demo'):
            if key in value and (not isinstance(value[key],(list,tuple)) or any(not isinstance(v,str) for v in value[key])):
                raise ValueError('Manifest lists must contain literal strings')
        # Reject values not representable in the collection's JSON contract.
        json.dumps(value, allow_nan=False)
        return [dict(kind='manifest',text=text,locator=dict(line_start=1,line_end=max(1,len(text.splitlines()))),
                     rule='literal_manifest_v1',data=dict(manifest=value),origin='code',warnings=[])], []
    if suffix in {'.md','.markdown','.rst'}:
        rst = suffix == '.rst'
        return [dict(part, kind='rst_section' if rst else 'markdown_section',
                     rule='rst_headings_v1' if rst else 'markdown_headings_v1', origin='documentation', warnings=[])
                for part in sections(text,rst)], []
    if suffix in {'.html','.htm'} or 'html' in artifact.get('metadata',{}).get('content_type','').lower():
        return [dict(kind='html_document',text=html_text(text),locator={},rule='html_structure_v1',
                     data={},origin='documentation',warnings=[])], []
    is_code = suffix in {'.py','.xml','.csv','.sh'}
    return [dict(kind='code' if is_code else 'text',text=text,
                 locator=dict(line_start=1,line_end=max(1,len(text.splitlines()))),
                 rule='whole_code_file_v1' if is_code else 'whole_text_no_verified_boundaries_v1',
                 data=dict(language=suffix.lstrip('.') if is_code else None),
                 origin='code' if is_code else 'documentation',warnings=[])], []
