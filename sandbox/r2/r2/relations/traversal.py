"""Explain minimum distances using only already formed relations."""
from itertools import islice

import networkx as nx

TRAVERSAL_VERSION = 'shortest-predecessors-1'


def traverse_relations(extracted, *, maximum_hops=None):
    # Inputs: extracted, maximum_hops.
    # Does: Explain minimum distances and preceding edges from the seeds.
    # Output: Reached nodes and edge identifiers.
    """Return reached nodes and the IDs of relations between them.

    Each predecessor references a registered edge from the previous level.
    Following predecessors recursively recovers the shortest paths to seeds.
    """
    available_hops = extracted['maximum_hops']
    limit = available_hops if maximum_hops is None else maximum_hops
    if (type(available_hops) is not int or not 0 <= available_hops <= 3
            or type(limit) is not int or not 0 <= limit <= available_hops):
        raise ValueError('Traversal depth must be within the extracted scope and at most three')
    unit_ids = set(extracted['unit_ids'])
    seeds = set(extracted['seeds'])
    if not seeds <= unit_ids:
        raise ValueError('Traversal seed is absent from the extracted graph')
    graph = nx.Graph()
    graph.add_nodes_from(unit_ids)
    edge_ids = set()
    for edge in extracted['edges']:
        left, right, edge_id = edge['left'], edge['right'], edge['id']
        if (left not in unit_ids or right not in unit_ids or left == right
                or edge['directed'] is not False or edge_id in edge_ids or graph.has_edge(left, right)):
            raise ValueError('Invalid or duplicate extracted relation')
        graph.add_edge(left, right, id=edge_id)
        edge_ids.add(edge_id)

    layers = islice(nx.bfs_layers(graph, sorted(seeds)), limit + 1) if seeds else ()
    depths = {uid: depth for depth, layer in enumerate(layers) for uid in layer}
    nodes = []
    for uid, depth in sorted(depths.items()):
        predecessors = [
            dict(unit_id=neighbor, edge_id=graph[uid][neighbor]['id'])
            for neighbor in sorted(graph[uid])
            if depth > 0 and depths.get(neighbor) == depth - 1
        ]
        nodes.append(dict(unit_id=uid, is_seed=uid in seeds, minimum_hops=depth,
                          predecessors=predecessors))
    reached_edge_ids = sorted(data['id'] for left, right, data in graph.edges(data=True)
                              if left in depths and right in depths)
    return dict(maximum_hops=limit, nodes=nodes, reached_edge_ids=reached_edge_ids)
