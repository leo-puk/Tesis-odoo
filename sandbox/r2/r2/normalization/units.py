"""Build normalized information units and attributes, never search relations."""
import base64
from lxml.etree import LxmlError
from ..records import fingerprint
from .observations import part_entities
from .parsers import parse_artifact
from .schema import RULE_VERSION, SCHEMA_VERSION, unit_id
from .terms import attach_terms


def layer_for_path(path):
    # Inputs: path.
    # Does: Infer the normalized evidence layer from an artifact path.
    # Output: The layer label.
    if path.endswith('__manifest__.py'): return 'manifest'
    if path.endswith('.py'): return 'python'
    if path.endswith('.xml'): return 'data' if any(p in path.split('/') for p in ('data','security')) else 'xml'
    if path.endswith('.csv'): return 'data'
    return 'unknown'


def convert_units(captured):
    # Inputs: captured.
    # Does: Convert captured artifacts into located searchable units.
    # Output: Sources, artifacts, units and normalization diagnostics.
    sources, artifacts, records, issues, warnings = {}, {}, {}, [], []
    for group in sorted(captured,key=lambda u:u['source']['id']):
        for file in sorted(group['files'],key=lambda f:f['path']):
            source={**group['source']}
            sid='src-'+fingerprint([source['id'],file['path']])[:32]
            source.update(id=sid,acquisition_source_id=group['source']['id'],
                          artifact_path=file['path'],url=file.get('source_url',source.get('url')))
            sources[sid]=source
            aid='artifact-'+fingerprint([sid,file['path']])[:32]
            raw=file.get('raw')
            artifact={k:v for k,v in file.items() if k!='raw'}
            artifact.update(id=aid,source_id=sid)
            if raw is not None:
                artifact['original_base64']=base64.b64encode(raw).decode('ascii')
            artifacts[aid]=artifact
            if file['text'] is None:
                issues.append(dict(source_id=sid,artifact_id=aid,source_locator=dict(artifact_path=file['path']),
                                   stage='decoding',status='failed',detail=file.get('decoding')))
                continue
            try:
                parts, notes=parse_artifact(file,source)
            except (ValueError,SyntaxError,TypeError,KeyError,RecursionError,LxmlError) as exc:
                issues.append(dict(source_id=sid,artifact_id=aid,source_locator=dict(artifact_path=file['path']),
                                   stage='parsing',status='failed',error=type(exc).__name__,detail=str(exc)))
                continue
            warnings.extend(notes)
            for part in parts:
                locator=dict(artifact_path=file['path'],**part['locator'])
                data=part['data']
                record=dict(id=unit_id(sid,locator,part['rule']),source_id=sid,source_url=source.get('url'),
                    source_locator=locator,kind=part['kind'],text=part['text'],
                    version_from=source.get('from_version'),version_to=source.get('to_version'),
                    layers=['unknown'],entities=[],terms=[],extraction_rule=part['rule'],schema_version=SCHEMA_VERSION,
                    rules_version=RULE_VERSION,warnings=list(part['warnings']),artifact_id=aid,data=data,
                    normalization_status='valid',encoding=file.get('decoding',{}).get('encoding'))
                if record['version_from'] is None or record['version_to'] is None:
                    record['warnings'].append('Version interval is explicitly unknown or partial')
                if part['kind']=='diff_hunk':
                    record['layers']=[layer_for_path(data['file_path'])]
                    record['warnings'].append('Observed diff block; not a verified incompatibility or solution')
                elif part['kind']=='manifest':
                    record['layers']=['manifest']
                else:
                    layer=layer_for_path(file['path']) if part['kind']=='code' else 'documentation' if part['kind']!='text' else 'unknown'
                    record['layers']=[layer]
                record['entities'],notes=part_entities(part,source,locator,file['path'])
                record['warnings'].extend(notes)
                if notes: record['normalization_status']='partial'
                record['warnings']=sorted(set(record['warnings']))
                warnings.extend(sid+': '+message for message in record['warnings'])
                if record['id'] in records and records[record['id']] != record:
                    raise ValueError('Conflicting normalized records for one capture locator')
                records[record['id']]=record
    ordered=[records[k] for k in sorted(records)]
    terms=attach_terms(ordered)
    warnings.extend('Normalization '+i['stage']+' failed for '+i['source_id'] for i in issues)
    return dict(sources=[sources[k] for k in sorted(sources)],artifacts=artifacts,units=records,
                issues=issues,warnings=sorted(set(warnings)),normalization=dict(rules_version=RULE_VERSION,
                unit_schema_version=SCHEMA_VERSION,terms=terms))
