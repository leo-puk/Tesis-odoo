"""Read partner code as data, reusing the corrected entity recognition rules."""
import ast
from copy import deepcopy
import hashlib
import io
import os
from pathlib import Path
import re
import tokenize
from ..normalization.decoding import decode_artifact
from ..normalization.entities import extract_entities, manifest_entities
from ..normalization.parsers import parse_artifact
from ..records import fingerprint

EXTENSIONS = {'.py', '.xml', '.csv'}
IGNORED = {'.git', '__pycache__', '.venv', '.venv-repro', 'node_modules'}


def read_code(directory, module_name=None):
    entry = Path(directory).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (entry, *entry.parents)):
        raise ValueError('Partner module paths cannot contain links or junctions')
    if not entry.exists():
        raise ValueError('Partner code input does not exist')
    if not entry.is_file() and not entry.is_dir():
        raise ValueError('Partner code input must be a file or directory')
    single_file = entry.is_file()
    if single_file and entry.suffix.lower() not in EXTENSIONS:
        raise ValueError('Unsupported partner code format: '+entry.suffix)
    if module_name is not None and (not isinstance(module_name,str) or not re.fullmatch(r'[A-Za-z_]\w*', module_name, re.ASCII)):
        raise ValueError('module_name must be an explicit technical addon name')
    entry = entry.resolve()
    root = entry.parent if single_file else entry
    entities, files, errors, limitations = [], [], [], []

    def walk_error(exc):
        errors.append(dict(stage='reading', file=str(exc.filename), error=type(exc).__name__, detail=str(exc)))

    walk = [(str(root), [], [entry.name])] if single_file else os.walk(root, followlinks=False,onerror=walk_error)
    for folder, directories, names in walk:
        kept = []
        for name in sorted(directories):
            path = Path(folder)/name
            if name in IGNORED or name.startswith('.venv'):
                continue
            if path.is_symlink() or path.is_junction():
                limitations.append(dict(file=path.relative_to(root).as_posix(), reason='linked_directory_not_read'))
                continue
            kept.append(name)
        directories[:] = kept
        for name in sorted(names):
            path = Path(folder)/name
            relative = path.relative_to(root).as_posix()
            if path.suffix.lower() not in EXTENSIONS:
                continue
            if path.is_symlink() or path.is_junction():
                limitations.append(dict(file=relative, reason='linked_file_not_read'))
                continue
            try:
                raw = path.read_bytes()
                if path.suffix == '.py':
                    encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
                    text = raw.decode(encoding, errors='strict')
                else:
                    metadata = {}
                    declaration = re.match(br'\s*<\?xml[^>]*encoding\s*=\s*[\'"]([^\'"]+)', raw)
                    if declaration:
                        metadata['content_type'] = 'text/xml; charset='+declaration[1].decode('ascii')
                    text, decoding = decode_artifact(raw, metadata)
                    if text is None:
                        raise ValueError(decoding['message'])
                    encoding = decoding['encoding']
            except (OSError, UnicodeError, LookupError, SyntaxError, ValueError) as exc:
                errors.append(dict(stage='reading',file=relative,error=type(exc).__name__,detail=str(exc)))
                continue
            files.append(dict(path=relative,encoding=encoding,content_sha256=hashlib.sha256(raw).hexdigest()))
            locator = dict(artifact_path=relative,line_start=1,line_end=max(1,len(text.splitlines())))
            try:
                if name == '__manifest__.py':
                    parts, notes = parse_artifact(dict(path=relative,text=text),dict(kind='official_manifest'))
                    observed = manifest_entities(parts[0]['data']['manifest'],locator,text)
                else:
                    observed, notes = extract_entities(text,relative,locator,origin='code',module=module_name)
                    if path.suffix == '.py':
                        try:
                            ast.parse(text)
                        except SyntaxError as exc:
                            errors.append(dict(stage='parsing',file=relative,error='SyntaxError',line=exc.lineno,
                                               detail='Incomplete code; only supported partial patterns may be observed'))
            except (ValueError, SyntaxError, TypeError, RecursionError) as exc:
                errors.append(dict(stage='parsing',file=relative,error=type(exc).__name__,detail=str(exc)))
                continue
            limitations.extend(dict(file=relative,reason=note) for note in notes)
            for observation in observed:
                entity = deepcopy(observation)
                entity['context']['module'] = module_name
                entity['location']['code_path'] = relative
                entities.append(entity)
    # Refine self.attribute only when a unique declaration in the same model
    # establishes its type; never infer a field/method from a call or a name.
    declarations = {}
    for entity in entities:
        model = entity['context'].get('model')
        if model and entity['type'] in {'field','method'} and entity['context'].get('role') == 'declaration':
            declarations.setdefault((model,entity['name']),set()).add(entity['type'])
    for entity in entities:
        if entity['type'] == 'attribute_reference':
            kinds = declarations.get((entity['context'].get('model'),entity['name']),set())
            if len(kinds) == 1:
                entity['type'] = next(iter(kinds))+'_reference'
                entity['context']['observed_rule'] = entity['rule']
                entity['rule'] = 'input_unique_declaration_v1'
    entities.sort(key=lambda e:(e['location']['artifact_path'],e['location'].get('content_line',0),fingerprint(e)))
    files.sort(key=lambda f:f['path'])
    if not files:
        limitations.append(dict(file=None,reason='no_supported_readable_code_files'))
    return dict(module_path=str(entry),input_path=str(entry),input_kind='file' if single_file else 'directory',
                module_name=module_name,files=files,entities=entities,
                errors=errors,limitations=limitations,input_revision=fingerprint([module_name,files]))
