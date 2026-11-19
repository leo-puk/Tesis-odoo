"""Compose relation extraction and traversal into a reproducible query report."""
from ..records import fingerprint
from .extraction import extract_relations
from .traversal import TRAVERSAL_VERSION, traverse_relations


def graph_counts(nodes, edges):
    identities = {fingerprint(identity) for edge in edges for identity in edge['shared_identities']}
    return dict(node_count=len(nodes), relation_count=len(edges), shared_attribute_count=len(identities),
                raw_match_count=sum(edge['raw_match_count'] for edge in edges))


def graph_id(report):
    return 'unit-graph-'+fingerprint({k:v for k,v in report.items() if k != 'graph_id'})[:32]


def query_report(extracted, traversal):
    nodes = traversal['nodes']
    # The query traverses the full extracted neighborhood for this same limit.
    if [node['unit_id'] for node in nodes] != extracted['unit_ids']:
        raise ValueError('Traversal did not reach the extracted neighborhood')
    report = {key: value for key, value in extracted.items() if key != 'unit_ids'}
    report.update(schema_version=2, component='relation_extraction',
                  traversal_version=TRAVERSAL_VERSION, construction_status='complete',
                  status='partial' if extracted['crossing']['status'] == 'partial'
                  or extracted['partial_unit_ids'] else 'complete',
                  outcome='traversal_complete' if extracted['seeds'] else 'no_seeds',
                  nodes=nodes, counts=graph_counts(nodes, extracted['edges']),
                  meaning='Undirected shared technical identity')
    report['graph_id'] = graph_id(report)
    return report


def execute_query(crossing, database, *, maximum_hops=3, output=None):
    """Extract, traverse, then optionally persist the explained query."""
    from .serialization import save_graph, validate_graph

    extracted = extract_relations(crossing, database, maximum_hops=maximum_hops)
    report = query_report(extracted, traverse_relations(extracted))
    if output is None:
        validate_graph(report)
    else:
        save_graph(report, output)
    return report
