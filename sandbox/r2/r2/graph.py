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
        self.adj = {}
        for a, b in edges:
            self.add_edge(a, b)

    def add_nodes_from(self, nodes):
        for n in nodes:
            self.adj.setdefault(n, {})

    def add_edge(self, a, b, **attributes):
        self.add_nodes_from([a, b])
        self.adj[a][b] = attributes

    def has_edge(self, a, b):
        return b in self.adj.get(a, {})

    def predecessors(self, node):
        return (a for a in self.adj if node in self.adj[a])

    def __iter__(self):
        return iter(self.adj)

    def __getitem__(self, key):
        return self.adj[key]


def new_graph(edges=()):
    return _nx.DiGraph(edges) if _nx else AdjacencyGraph(edges)


def bfs_layers(graph, seeds):
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
