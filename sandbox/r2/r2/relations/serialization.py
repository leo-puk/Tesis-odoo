"""Ordered JSON, structural validation, optional collection replay, no pickle."""
import json
from copy import deepcopy
from pathlib import Path
import networkx as nx
from ..normalization.schema import RULE_VERSION as NORMALIZATION_RULES
from ..crossing.rules import RULE_VERSION as CROSSING_RULES
from ..records import fingerprint
from .traversal import TRAVERSAL_VERSION, traverse_relations
from .rules import (RULE_VERSION, EDGE_TYPE, rule_catalog, identity_for,
                    LOCATION_FIELDS, CONTEXT_FIELDS)


def _ids(values):
    return isinstance(values,list) and all(isinstance(v,str) and v.strip() for v in values) and values==sorted(set(values))


def _point(value, uid):
    if not isinstance(value,dict) or set(value)!={'unit_id','entity_ordinal','source_module','observation'}:
        raise ValueError('Graph evidence must contain only one localized observation')
    if value['unit_id']!=uid or type(value['entity_ordinal']) is not int or value['entity_ordinal']<0:
        raise ValueError('Evidence endpoint or ordinal is invalid')
    if value['source_module'] is not None and (not isinstance(value['source_module'],str) or not value['source_module']):
        raise ValueError('Evidence source namespace is invalid')
    entity=value['observation']
    if not isinstance(entity,dict) or set(entity)!={'name','type','location','rule','context'}:
        raise ValueError('Graph cannot contain document copies in place of observations')
    if (not isinstance(entity['context'],dict) or not set(entity['context'])<=set(CONTEXT_FIELDS)
            or not isinstance(entity['location'],dict) or not set(entity['location'])<=set(LOCATION_FIELDS)):
        raise ValueError('Evidence contains unsupported context or locator fields')
    identity,_=identity_for(entity,value['source_module'])
    if identity is None:
        raise ValueError('Graph evidence has no enabled, scoped technical identity')
    return list(identity)


def _networkx(report):
    graph=nx.Graph()
    graph.graph.update(deepcopy({k:v for k,v in report.items() if k not in {'nodes','edges'}}))
    for node in report['nodes']:
        graph.add_node(node['unit_id'], **deepcopy({k:v for k,v in node.items() if k != 'unit_id'}))
    for edge in report['edges']:
        graph.add_edge(edge['left'],edge['right'],**deepcopy({k:v for k,v in edge.items() if k not in {'left','right'}}))
    return graph


def validate_graph(report, *, database=None, crossing=None):
    from .engine import graph_id, graph_counts, query_report
    from .extraction import checked_crossing, _extract
    expected={'schema_version','component','rules_version','rule_catalog','collection','crossing','seeds',
              'maximum_hops','construction_status','status','outcome','partial_unit_ids','nodes','edges',
              'counts','ignored_observations','meaning','graph_id','traversal_version'}
    if not isinstance(report,dict) or set(report)!=expected:
        raise ValueError('Invalid unit graph schema fields')
    if (report['schema_version']!=2 or report['component']!='relation_extraction'
            or report['rules_version']!=RULE_VERSION or report['traversal_version']!=TRAVERSAL_VERSION):
        raise ValueError('Unsupported unit graph schema or rules')
    if report['rule_catalog']!=rule_catalog() or report['construction_status']!='complete':
        raise ValueError('Incomplete construction or incompatible rule catalog')
    maximum=report['maximum_hops']
    if type(maximum) is not int or not 0<=maximum<=3:
        raise ValueError('Invalid hop bound')
    if not _ids(report['seeds']) or not _ids(report['partial_unit_ids']):
        raise ValueError('Seed and partial-unit IDs must be sorted and unique')
    collection=report['collection']
    if (not isinstance(collection,dict) or set(collection)!={'revision','schema_version','normalization_rules_version'}
            or not isinstance(collection['revision'],str) or not collection['revision']
            or collection['schema_version']!=4 or collection['normalization_rules_version']!=NORMALIZATION_RULES):
        raise ValueError('Invalid graph collection contract')
    context=report['crossing']
    if (not isinstance(context,dict) or set(context)!={'result_id','schema_version','rules_version','status'}
            or not isinstance(context['result_id'],str) or not context['result_id']
            or context['schema_version']!=2 or context['rules_version']!=CROSSING_RULES
            or context['status'] not in {'complete','partial'}):
        raise ValueError('Invalid crossing provenance')
    expected_status='partial' if context['status']=='partial' or report['partial_unit_ids'] else 'complete'
    if report['status']!=expected_status or report['outcome']!=('traversal_complete' if report['seeds'] else 'no_seeds'):
        raise ValueError('Graph lost partial/empty-state information')
    if not isinstance(report['nodes'],list) or not isinstance(report['edges'],list):
        raise ValueError('Graph nodes and edges must be lists')
    nodes=[]
    for node in report['nodes']:
        if not isinstance(node,dict) or set(node)!={'unit_id','is_seed','minimum_hops','predecessors'}:
            raise ValueError('Node must contain only its ID, seed flag, distance and predecessors')
        uid=node['unit_id'];distance=node['minimum_hops']
        if (not isinstance(uid,str) or not uid or type(node['is_seed']) is not bool
                or node['is_seed']!=(uid in report['seeds']) or type(distance) is not int or not 0<=distance<=maximum):
            raise ValueError('Invalid node state or fourth-hop node')
        nodes.append(uid)
    if not _ids(nodes) or not set(report['seeds'])<=set(nodes) or not set(report['partial_unit_ids'])<=set(nodes):
        raise ValueError('Node IDs, seeds or partial units are inconsistent')
    node_ids = set(nodes)
    edge_pairs=[];observations={}
    for edge in report['edges']:
        if not isinstance(edge,dict) or set(edge)!={'id','left','right','type','directed','rule_version',
                'shared_identities','matches','shared_attribute_count','raw_match_count'}:
            raise ValueError('Invalid edge fields')
        left,right=edge['left'],edge['right']
        if left not in node_ids or right not in node_ids or not left<right:
            raise ValueError('Edge endpoint missing, unsorted or self-referential')
        if edge['type']!=EDGE_TYPE or edge['directed'] is not False or edge['rule_version']!=RULE_VERSION:
            raise ValueError('Unsupported or unjustified directed relation')
        if edge['id']!='unit-edge-'+fingerprint([RULE_VERSION,left,right])[:32]:
            raise ValueError('Invalid edge ID')
        edge_pairs.append((left,right))
        identities={};pairs=set();match_ids=[]
        if not isinstance(edge['matches'],list) or not edge['matches']:
            raise ValueError('Edge evidence is missing')
        for match in edge['matches']:
            if not isinstance(match,dict) or set(match)!={'id','identity','rule','left','right'}:
                raise ValueError('Invalid raw match fields')
            identity=_point(match['left'],left)
            if identity!=_point(match['right'],right) or match['identity']!=identity:
                raise ValueError('Evidence identities or owners differ')
            if match['rule']!='shared_'+identity[0]+'_identity_v1':
                raise ValueError('Identity rule is incorrect')
            if match['id']!='unit-match-'+fingerprint([RULE_VERSION,{k:v for k,v in match.items() if k!='id'}])[:32]:
                raise ValueError('Raw match ID is invalid')
            pair=(match['left']['entity_ordinal'],match['right']['entity_ordinal'])
            if pair in pairs: raise ValueError('Repeated observation pair')
            pairs.add(pair);match_ids.append(match['id']);identities[fingerprint(identity)]=identity
            for side in ('left','right'):
                point=match[side];key=(point['unit_id'],point['entity_ordinal']);value=fingerprint(point)
                if key in observations and observations[key]!=value: raise ValueError('One observation has conflicting evidence')
                observations[key]=value
        expected_identities=[v for _,v in sorted(identities.items())]
        if (match_ids!=sorted(set(match_ids)) or edge['shared_identities']!=expected_identities
                or type(edge['shared_attribute_count']) is not int or edge['shared_attribute_count']!=len(identities)
                or type(edge['raw_match_count']) is not int or edge['raw_match_count']!=len(pairs)):
            raise ValueError('Distinct identities and raw observation counts differ')
    if edge_pairs!=sorted(set(edge_pairs)):
        raise ValueError('Edges must be unique and ordered')
    counts=report['counts']
    if (not isinstance(counts,dict) or any(type(v) is not int or v<0 for v in counts.values())
            or counts!=graph_counts(report['nodes'],report['edges'])):
        raise ValueError('Graph counters differ from persisted evidence')
    traversal = traverse_relations(dict(unit_ids=nodes, seeds=report['seeds'],
                                       edges=report['edges'], maximum_hops=maximum))
    if traversal['nodes'] != report['nodes']:
        raise ValueError('Missing paths, incorrect distance or invalid traversal predecessors')
    if report['graph_id']!=graph_id(report):
        raise ValueError('Graph ID differs from its content')
    if crossing is not None:
        handoff=checked_crossing(crossing)
        if (handoff['result_id']!=context['result_id'] or handoff['matched_unit_ids']!=report['seeds']
                or handoff['collection']!=collection or handoff['status']!=context['status']):
            raise ValueError('Graph differs from the supplied crossing search')
    if database is not None:
        extracted = _extract(database, report['seeds'], maximum, context, collection)
        replay = query_report(extracted, traverse_relations(extracted))
        if replay!=report:
            raise ValueError('Graph is incomplete or differs from the normalized collection')
    return True


def save_graph(report, destination):
    validate_graph(report)
    payload=json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    path=Path(destination)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(payload)


def load_graph(path, *, database=None, crossing=None):
    report=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    validate_graph(report,database=database,crossing=crossing)
    return report


def to_networkx(report):
    validate_graph(report)
    return _networkx(report)
