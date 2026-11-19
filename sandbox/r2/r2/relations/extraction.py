"""Indexed extraction of evidenced edges in a neighborhood scoped to one query."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from ..records import connect, meta
from ..crossing.engine import validate_result
from ..crossing.rules import RULE_VERSION as CROSSING_RULES
from ..records import fingerprint
from .rules import EDGE_TYPE, RULE_VERSION, rule_catalog, identity_for, point_observation
from .store import UnitStore, collection_contract


def checked_crossing(value):
    if isinstance(value, (str, Path)):
        value = json.loads(Path(value).read_text(encoding='utf-8-sig'))
    value = deepcopy(value)
    try:
        if not isinstance(value, dict):
            raise ValueError('Crossing result must be an object')
        validate_result(value)
        if value.get('rules_version') != CROSSING_RULES:
            raise ValueError('Unsupported crossing rules')
        if value.get('status') not in {'complete', 'partial'}:
            raise ValueError('Crossing status must be explicit')
        if any(not uid or not uid.strip() for uid in value['matched_unit_ids']):
            raise ValueError('Crossing seed IDs cannot be empty')
        details = value['input']
        if not isinstance(details.get('errors'), list) or not isinstance(details.get('limitations'), list) or not isinstance(value['unresolved'], list):
            raise ValueError('Crossing partial-state evidence is missing')
        if value['status'] == 'complete' and (details['errors'] or details['limitations'] or value['unresolved']):
            raise ValueError('Crossing claims completeness despite partial analysis')
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Malformed crossing handoff') from exc
    return value


def _extract(database, seeds, maximum, crossing_context, expected_collection):
    if type(maximum) is not int or not 0 <= maximum <= 3:
        raise ValueError('maximum_hops must be an integer from zero through three')
    with connect(database) as con:
        # Keep all metadata, indexed candidates and unit payloads in one read
        # snapshot. Closing the read-only connection releases the transaction.
        con.execute('BEGIN')
        collection = collection_contract(meta(con))
        if collection != expected_collection:
            raise ValueError('Crossing/graph collection revision or normalization version differs')
        store = UnitStore(con)
        for seed in seeds:
            store.unit(seed)
        unit_ids = set(seeds)
        frontier = set(seeds)
        scanned = set()
        edge_map = {}

        def extract_frontier(boundary=False):
            neighbors = set()
            for uid in sorted(frontier):
                for ordinal, entity, module, identity in store.entities(uid):
                    for row in store.candidates(entity, module):
                        other = row['unit_id']
                        if other == uid or other in scanned:
                            continue
                        if boundary and other not in unit_ids:
                            continue
                        _, target, target_module = store.check_row(row)
                        if identity_for(target, target_module)[0] != identity:
                            continue
                        left, right = sorted((uid, other))
                        own_point = point_observation(uid, ordinal, entity, module)
                        other_point = point_observation(other, row['ordinal'], target, target_module)
                        left_point, right_point = (own_point, other_point) if uid == left else (other_point, own_point)
                        edge = edge_map.setdefault((left, right), dict(identities={}, matches={}))
                        edge['identities'][fingerprint(list(identity))] = list(identity)
                        evidence = dict(identity=list(identity), rule='shared_'+identity[0]+'_identity_v1',
                                        left=left_point, right=right_point)
                        match_id = 'unit-match-'+fingerprint([RULE_VERSION, evidence])[:32]
                        edge['matches'][match_id] = dict(id=match_id, **evidence)
                        neighbors.add(other)
                scanned.add(uid)
            return neighbors

        # Use already evidenced edges to decide which units to inspect next.
        # This scopes SQLite work. It does not produce a traversal explanation.
        for _ in range(maximum):
            neighbors = extract_frontier()
            frontier = neighbors - unit_ids
            unit_ids.update(neighbors)
            if not frontier:
                break
        extract_frontier(boundary=True)
        edges = []
        for (left,right), data in sorted(edge_map.items()):
            identities = [value for _,value in sorted(data['identities'].items())]
            matches = [value for _,value in sorted(data['matches'].items())]
            edges.append(dict(id='unit-edge-'+fingerprint([RULE_VERSION,left,right])[:32],
                left=left,right=right,type=EDGE_TYPE,directed=False,rule_version=RULE_VERSION,
                shared_identities=identities,matches=matches,shared_attribute_count=len(identities),raw_match_count=len(matches)))
        partial_units = sorted(uid for uid in unit_ids if store.unit(uid).get('normalization_status') == 'partial')
        ignored = dict(sorted(Counter(reason for _,_,reason in store.ignored).items()))
    return dict(rules_version=RULE_VERSION, rule_catalog=rule_catalog(),
                collection=collection, crossing=crossing_context, seeds=list(seeds),
                maximum_hops=maximum, unit_ids=sorted(unit_ids), edges=edges,
                partial_unit_ids=partial_units, ignored_observations=ignored)


def extract_relations(crossing, database, *, maximum_hops=3):
    """Form evidenced, undirected edges from indexed normalized observations."""
    handoff = checked_crossing(crossing)
    context = {key: handoff[key] for key in ('result_id', 'schema_version', 'rules_version', 'status')}
    return _extract(database, handoff['matched_unit_ids'], maximum_hops, context, handoff['collection'])
