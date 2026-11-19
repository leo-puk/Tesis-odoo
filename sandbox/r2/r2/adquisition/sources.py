"""Acquire complete units into temp_data; no relevance analysis or chunking."""
import json
from pathlib import Path
import re
import shutil
from uuid import uuid4
from .documents import decode_for_screening, ScreeningDecodeError
from .github import GitHubMetadata, Incomplete
from .http import HttpCapture
from .policy import SourcePolicy, Excluded
from .provenance import save, utcnow, validate_source_origin
from urllib.parse import urlparse


def _original_suffix(name, url, content_type):
    if 'html' in content_type.lower():
        return '.html'
    suffix = Path(urlparse(url).path).suffix.lower() or Path(name).suffix.lower()
    return suffix if suffix in {'.txt', '.md', '.rst', '.py', '.xml', '.csv', '.json', '.sh'} else '.txt'


def _log(folder, event, **fields):
    with (folder / 'acquisition.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(time=utcnow(), event=event, **fields), ensure_ascii=False) + '\n')


def _root(base):
    path = Path(base).absolute()
    if path.name != 'temp_data':
        path /= 'temp_data'
    for part in [path, *path.parents]:
        if part.is_symlink() or part.is_junction():
            raise ValueError('Storage cannot use symlinks or junctions')
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def capture_plan(plan_path, output='temp_data', *, catalog_path, transport=None):
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8-sig'))
    policy = SourcePolicy(json.loads(Path(catalog_path).read_text(encoding='utf-8-sig')))
    if not isinstance(plan, list):
        raise ValueError('Plan must be an array')
    ids = set()
    for entry in plan:
        if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not re.fullmatch(r'[\w-]+', entry['id']):
            raise ValueError('Entry requires a simple id')
        if 'before' in entry or 'after' in entry:
            raise ValueError('Acquisition accepts files, not before/after source states')
        if entry['id'] in ids:
            raise ValueError('Duplicate entry id')
        ids.add(entry['id'])
        if entry.get('kind') not in {'official_code', 'official_manifest', 'official_documentation', 'oca_guidance', 'openupgrade_analysis', 'github_diff', 'github_pr'}:
            raise ValueError('Unknown source kind; entire source repositories are not supported')
        if not isinstance(entry.get('files'), dict) or not entry['files']:
            raise ValueError('Each entry needs a nonempty files mapping')
        for name, url in entry['files'].items():
            if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*', name) or not isinstance(url, str):
                raise ValueError('Expected flat filenames and URL strings')
    root = _root(output)
    session = root / uuid4().hex
    session.mkdir()
    http = HttpCapture(session, transport)
    github = GitHubMetadata(session, transport, policy)
    inventory = []
    cache = {}
    for entry in plan:
        unit_id = uuid4().hex
        unit = dict(id=unit_id, source_id=entry['id'], kind=entry['kind'],
                    urls=list(entry['files'].values()), status='pending', files=[], captures=[],
                    file_metadata=[], storage_form='original', created_at=utcnow())
        payloads = []
        try:
            # Validate all URLs before making the first request for this unit.
            for url in entry['files'].values():
                policy.url(url)
            for i, (name, url) in enumerate(entry['files'].items()):
                kind = entry['kind']
                cached = cache.get((kind, url))
                if cached is not None:
                    raw, records, suffix, details = cached
                    payloads.append((f'{i+1:03d}-{Path(name).stem}{suffix}', raw, details))
                    unit['captures'].extend(records)
                    continue
                if kind == 'github_pr':
                    value, records = github.pull(url)
                    raw = json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')
                    suffix = '.json'
                    details = dict(representation='github_resource_bundle', decode_state='decoded',
                                   screening_encoding='utf-8', text_conversion='not_performed')
                elif kind == 'github_diff':
                    raw, records = github.diff_bytes(url)
                    suffix = '.diff'
                    details = dict(representation='original_bytes', decode_state='decoded',
                                   screening_encoding='utf-8', text_conversion='not_performed')
                else:
                    validate_source_origin('official_code' if kind == 'official_manifest' else kind, url)
                    if kind == 'official_manifest' and not url.endswith('/__manifest__.py'):
                        raise Excluded('Only explicitly linked manifests are allowed as official code')
                    if url not in cache:
                        cache[url] = http.get(url, persist=False)
                    raw, record = cache[url]
                    records = [record]
                    ctype = record.get('headers', {}).get('content-type', '')
                    if any(x in ctype.lower() for x in ('pdf', 'image/', 'zip', 'octet-stream')):
                        raise Excluded('Binary document cannot be screened by this component')
                    # Positive rejection only: visible forbidden ASCII identifiers
                    # must not be hidden by an unrelated invalid byte. This view
                    # is never persisted or sufficient to admit unreadable data.
                    policy.content(raw.decode('utf-8', errors='replace'))
                    try:
                        text, details = decode_for_screening(raw, ctype)
                        policy.content(text)  # Includes original HTML, links and scripts.
                    except ScreeningDecodeError as exc:
                        details = exc.details
                    details = {**details, 'representation': 'original_bytes', 'content_type': ctype}
                    suffix = '.py' if kind == 'official_manifest' else _original_suffix(name, url, ctype)
                if kind in {'github_pr', 'github_diff'}:
                    policy.content(raw.decode('utf-8'))
                details = {**details, 'url': url}
                cache[(kind, url)] = raw, records, suffix, details
                payloads.append((f'{i+1:03d}-{Path(name).stem}{suffix}', raw, details))
                unit['captures'].extend(records)
            folder = session / unit_id
            folder.mkdir()
            try:
                for name, raw, details in payloads:
                    (folder / name).write_bytes(raw)
                    unit['files'].append(f'{unit_id}/{name}')
                    unit['file_metadata'].append(dict(path=f'{unit_id}/{name}', **details))
            except OSError:
                # This exact directory was created above, inside the resolved session.
                shutil.rmtree(folder)
                unit.update(files=[], file_metadata=[])
                raise
            unreadable = any(details['decode_state'] != 'decoded' for _, _, details in payloads)
            unit.update(status='quarantined' if unreadable else 'accepted', captured_at=utcnow())
            if unreadable:
                unit['reason'] = 'Original retained; decoding required before admission; not indexable'
        except Excluded as exc:
            unit.update(status='excluded', reason=str(exc), captures=[])
        except (ValueError, OSError, UnicodeError) as exc:
            unit.update(status='incomplete' if isinstance(exc, Incomplete) else 'failed', reason=str(exc), captures=[])
        inventory.append(unit)
        save(session / 'inventory.json', inventory)
        _log(session, unit['status'], id=unit_id, source_id=entry['id'], reason=unit.get('reason'))
    save(session / 'inventory.json', inventory)
    _log(session, 'finished', accepted=sum(x['status']=='accepted' for x in inventory))
    return dict(session_id=session.name, directory=str(session), inventory=str(session/'inventory.json'),
                included=sum(x['status']=='accepted' for x in inventory),
                quarantined=sum(x['status']=='quarantined' for x in inventory),
                counts={status: sum(x['status']==status for x in inventory)
                        for status in sorted({x['status'] for x in inventory})})


def delete_units(session_id, unit_ids, output='temp_data'):
    root = _root(output)
    if not re.fullmatch(r'[a-f0-9]{32}', session_id):
        raise ValueError('Invalid session id')
    session = root / session_id
    if session.is_symlink() or session.is_junction() or not session.resolve().is_relative_to(root):
        raise ValueError('Invalid session directory')
    inventory = json.loads((session / 'inventory.json').read_text(encoding='utf-8'))
    by_id = {x['id']: x for x in inventory}
    results = []
    for unit_id in unit_ids:
        if not isinstance(unit_id, str) or not re.fullmatch(r'[a-f0-9]{32}', unit_id):
            raise ValueError('Invalid unit id')
        unit = by_id.get(unit_id)
        status = 'not_found'
        if unit is not None:
            folder = session / unit_id
            try:
                # Validate the absolute deletion target and every child before recursion.
                paths = [folder, *folder.rglob('*')] if folder.exists() else [folder]
                if any(p.is_symlink() or p.is_junction() or not p.resolve().is_relative_to(session.resolve()) for p in paths):
                    raise ValueError('Unsafe deletion target')
                if folder.exists():
                    shutil.rmtree(folder)
                status = 'deleted'
                unit.update(status='deleted', files=[], file_metadata=[])
            except (OSError, ValueError) as exc:
                status = 'failed'
                _log(session, 'delete_failed', id=unit_id, reason=str(exc))
        results.append(dict(id=unit_id, status=status))
        save(session / 'inventory.json', inventory)
        _log(session, 'deletion', id=unit_id, status=status)
    return results
