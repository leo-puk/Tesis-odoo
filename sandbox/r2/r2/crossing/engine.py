"""Indexed crossing, evidence aggregation and reproducible result delivery."""
from collections import Counter
import json
from pathlib import Path
from ..records import connect, meta
from ..normalization.schema import RULE_VERSION as NORMALIZATION_RULES, SCHEMA_VERSION
from ..records import fingerprint
from .code import read_code
from .rules import FAMILY, FAMILIES, RULE_VERSION, partner_identity, unit_identity, lookup_names


def _candidates(con, name, kinds):
    placeholders = ','.join('?' for _ in kinds)
    return con.execute(
        'SELECT e.unit_id,e.ordinal,e.name,e.type,e.payload AS entity_payload,u.payload AS unit_payload '
        'FROM unit_entities AS e INDEXED BY unit_entity_lookup '
        'JOIN information_units AS u ON u.id=e.unit_id '
        f'WHERE e.name=? AND e.type IN ({placeholders}) ORDER BY e.unit_id,e.ordinal',
        (name,*kinds)).fetchall()


def cross_module(database, module, *, module_name=None, output=None):
    """Return exact typed matches; no graph, relevance ranking or code execution.

    Requires a normalized SQLite schema-4 collection with corrected scope rules.
    ``module_name`` supplies a technical addon namespace explicitly, if known.
    ``output`` optionally saves a new JSON result without changing the collection.
    """
    code = read_code(module,module_name)
    matches, unresolved, rejected = {}, {}, {}
    examined, eligible = set(), 0
    with connect(database) as con:
        metadata = meta(con)
        if metadata.get('schema_version') != 4:
            raise ValueError('Crossing requires normalized collection schema 4; rebuild the collection')
        normalization = metadata.get('normalization',{})
        if not isinstance(normalization,dict) or normalization.get('rules_version') != NORMALIZATION_RULES:
            raise ValueError('Rebuild with current normalization rules before crossing scoped identifiers')
        if not metadata.get('collection_revision'):
            raise ValueError('Collection revision is missing')
        for table in ('information_units','unit_entities','sources'):
            if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                raise ValueError('Missing normalized collection table: '+table)
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='unit_entity_lookup'").fetchone():
            raise ValueError('Missing entity index; rebuild the collection')
        cache, source_modules = {}, {}
        for entity in code['entities']:
            identity, reason = partner_identity(entity,module_name)
            if identity is None:
                unresolved[fingerprint(entity)] = dict(entity=entity,reason=reason)
                continue
            eligible += 1
            kinds = FAMILIES[FAMILY[entity['type']]]
            for name in lookup_names(entity,module_name):
                key = (name,kinds)
                if key not in cache:
                    cache[key] = _candidates(con,name,kinds)
                for row in cache[key]:
                    unit = json.loads(row['unit_payload'])
                    target = json.loads(row['entity_payload'])
                    if (unit.get('id') != row['unit_id'] or unit.get('schema_version') != SCHEMA_VERSION
                            or unit.get('rules_version') != NORMALIZATION_RULES):
                        raise ValueError('Unsupported or inconsistent normalized unit')
                    ordinal = row['ordinal']
                    if (type(ordinal) is not int or not 0 <= ordinal < len(unit.get('entities',[]))
                            or fingerprint(unit['entities'][ordinal]) != fingerprint(target)
                            or row['name'] != target.get('name') or row['type'] != target.get('type')):
                        raise ValueError('Entity index differs from its normalized unit; rebuild the collection')
                    examined.add((row['unit_id'],ordinal))
                    source_id = unit['source_id']
                    if source_id not in source_modules:
                        source = con.execute('SELECT payload FROM sources WHERE id=?',(source_id,)).fetchone()
                        if source is None:
                            raise ValueError('Normalized unit refers to a missing source')
                        source_modules[source_id] = json.loads(source[0]).get('binding',{}).get('module')
                    target_identity, target_reason = unit_identity(target,source_modules[source_id])
                    if target_identity != identity:
                        rejection=dict(unit_id=unit['id'],input_entity=entity,unit_entity=target,
                                       reason=target_reason or 'incompatible_type_or_scope')
                        rejected[fingerprint(rejection)] = rejection
                        continue
                    evidence = dict(information_unit_id=unit['id'],input_entity=entity,unit_entity=target,
                                    match_rule='exact_typed_scoped_identity_v1',identity=list(identity))
                    evidence['id'] = 'cross-evidence-'+fingerprint(evidence)[:32]
                    result = matches.setdefault(unit['id'],dict(evidences={}))
                    result['evidences'][evidence['id']] = evidence
    results = [dict(information_unit_id=uid,
                    evidences=[value for _,value in sorted(matches[uid]['evidences'].items())])
               for uid in sorted(matches)]
    unresolved_rows = [value for _,value in sorted(unresolved.items())]
    rejected_rows = [value for _,value in sorted(rejected.items())]
    partial = bool(code['errors'] or code['limitations'] or unresolved_rows)
    outcome = ('matches' if results else 'undetermined' if code['errors'] else
               'no_resolvable_identifiers' if not eligible else 'no_matches')
    result = dict(schema_version=2,component='crossing',rules_version=RULE_VERSION,
                  collection=dict(revision=metadata['collection_revision'],schema_version=4,
                                  normalization_rules_version=NORMALIZATION_RULES),
                  input=code,matched_unit_ids=sorted(matches),results=results,unresolved=unresolved_rows,rejected_candidates=rejected_rows,
                  status='partial' if partial else 'complete',outcome=outcome,
                  summary=dict(files_read=len(code['files']),entities_observed=len(code['entities']),
                      eligible_observations=eligible,unresolved_observations=len(unresolved_rows),
                      errors=len(code['errors']),indexed_candidates_examined=len(examined),
                      units_matched=len(results),evidences=sum(len(r['evidences']) for r in results),
                      rejection_reasons=dict(sorted(Counter(r['reason'] for r in rejected_rows).items()))),
                  limits=['Exact initial crossing only; no unit-to-unit relationship expansion or memory',
                          'Matching is not proof of migration applicability or incompatibility',
                          'A typed document/comment match does not validate the assertion it contains',
                          'No matches is not proof that the module has no migration problems'])
    result['result_id'] = 'cross-'+fingerprint(result)[:32]
    validate_result(result)
    if output is not None:
        save_result(result,output)
    return result


def validate_result(result):
    """Check the ID-only handoff and its accounting before returning or saving."""
    if result.get('schema_version') != 2 or result.get('component') != 'crossing':
        raise ValueError('Expected crossing output schema 2')
    ids = result.get('matched_unit_ids')
    rows = result.get('results')
    if (not isinstance(ids,list) or not all(isinstance(v,str) for v in ids)
            or ids != sorted(set(ids)) or not isinstance(rows,list)):
        raise ValueError('Matched unit IDs must be sorted and unique')
    if [r.get('information_unit_id') for r in rows] != ids:
        raise ValueError('Matched unit IDs and results differ')
    count = 0
    for row in rows:
        if set(row) != {'information_unit_id','evidences'} or not row['evidences']:
            raise ValueError('Results must contain only a unit ID and point evidences')
        seen = set()
        for evidence in row['evidences']:
            if evidence.get('information_unit_id') != row['information_unit_id'] or evidence.get('id') in seen:
                raise ValueError('Evidence unit IDs or uniqueness differ')
            seen.add(evidence.get('id'))
            for side in ('input_entity','unit_entity'):
                observation = evidence.get(side,{})
                if (not {'name','type','location','context','rule'} <= observation.keys()
                        or {'text','terms','data','entities','unit'} & observation.keys()):
                    raise ValueError('Evidence must reference one observation, not copy unit content')
        count += len(row['evidences'])
    if result.get('summary',{}).get('units_matched') != len(ids) or result['summary'].get('evidences') != count:
        raise ValueError('Crossing counters differ from IDs or evidences')
    if result.get('result_id') != 'cross-'+fingerprint({k:v for k,v in result.items() if k!='result_id'})[:32]:
        raise ValueError('Crossing result ID does not match the report')
    return True


def save_result(result, destination):
    """Persist a reproducible JSON report; never overwrite a collection or report."""
    validate_result(result)
    payload = json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    path = Path(destination)
    path.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation also prevents overwriting the input SQLite collection.
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(payload)
