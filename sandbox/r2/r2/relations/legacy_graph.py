"""NetworkX is preferred; explicit deterministic BFS fallback for offline hosts."""
import os
try:
    import networkx as _nx
except ModuleNotFoundError:
    _nx = None
if os.environ.get("R2_FORCE_COMPAT_BFS") == "1":
    _nx = None

BACKEND = "networkx.bfs_layers" if _nx else "stdlib_bfs_fallback"


class AdjacencyGraph:
    def __init__(self, edges=()):
        # Inputs: edges.
        # Does: Initialize the compatibility graph with its starting edges.
        # Output: A graph instance.
        self.adj = {}
        for a, b in edges:
            self.add_edge(a, b)

    def add_nodes_from(self, nodes):
        # Inputs: nodes.
        # Does: Register nodes in the fallback graph.
        # Output: An updated graph.
        for n in nodes:
            self.adj.setdefault(n, {})

    def add_edge(self, a, b, **attributes):
        # Inputs: a, b, attributes.
        # Does: Register an edge between two nodes in the fallback graph.
        # Output: An updated graph.
        self.add_nodes_from([a, b])
        self.adj[a][b] = attributes

    def has_edge(self, a, b):
        # Inputs: a, b.
        # Does: Check the fallback graph for an edge between two nodes.
        # Output: A boolean.
        return b in self.adj.get(a, {})

    def predecessors(self, node):
        # Inputs: node.
        # Does: Look up incoming neighbors in the fallback graph.
        # Output: The predecessor collection.
        return (a for a in self.adj if node in self.adj[a])

    def __iter__(self):
        # Inputs: No explicit arguments.
        # Does: Expose the nodes of the fallback graph for iteration.
        # Output: An iterator over graph nodes.
        return iter(self.adj)

    def __getitem__(self, key):
        # Inputs: key.
        # Does: Look up a node in the fallback graph.
        # Output: The node adjacency mapping.
        return self.adj[key]


def new_graph(edges=()):
    # Inputs: edges.
    # Does: Create a legacy graph using the available backend.
    # Output: A graph initialized with the supplied edges.
    return _nx.DiGraph(edges) if _nx else AdjacencyGraph(edges)


def bfs_layers(graph, seeds):
    # Inputs: graph, seeds.
    # Does: Traverse the given graph from its seed nodes.
    # Output: Successive layers of reached nodes.
    if _nx and isinstance(graph, _nx.DiGraph):
        yield from _nx.bfs_layers(graph, seeds)
        return
    layer = sorted(set(seeds))
    seen = set(layer)
    while layer:
        yield layer
        next_layer = sorted({b for a in layer for b in graph[a] if b not in seen})
        seen.update(next_layer)
        layer = next_layer
