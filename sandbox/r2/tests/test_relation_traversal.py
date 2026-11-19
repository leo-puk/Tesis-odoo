"""Traversal tests use only formed edges, with no collection or entities."""
import unittest

from r2.relations import traverse_relations


def formed_graph(pairs, seeds):
    edges = [
        dict(id=f'{left}-{right}', left=left, right=right, directed=False)
        for left, right in pairs
    ]
    unit_ids = sorted(set(seeds) | {uid for pair in pairs for uid in pair})
    return dict(unit_ids=unit_ids, edges=edges, seeds=seeds, maximum_hops=3)


class TraversalTests(unittest.TestCase):
    def test_fourth_hop_stays_out_even_if_the_edge_already_exists(self):
        graph = formed_graph([('A', 'B'), ('B', 'C'), ('C', 'D'), ('D', 'E')], ['A'])
        result = traverse_relations(graph)
        self.assertEqual([node['unit_id'] for node in result['nodes']], ['A', 'B', 'C', 'D'])
        self.assertEqual(result['reached_edge_ids'], ['A-B', 'B-C', 'C-D'])
        self.assertEqual(len(graph['edges']), 4)
        self.assertEqual(result['nodes'][-1]['predecessors'], [dict(unit_id='C', edge_id='C-D')])

    def test_equal_shortest_steps_from_two_seeds_keep_lateral_edges_separate(self):
        graph = formed_graph([
            ('A', 'Z'), ('A', 'B'), ('Z', 'C'), ('B', 'C'),
            ('B', 'D'), ('C', 'D'), ('D', 'E'), ('E', 'F'),
        ], ['A', 'Z'])
        result = traverse_relations(graph)
        nodes = {node['unit_id']: node for node in result['nodes']}
        self.assertEqual({uid: node['minimum_hops'] for uid, node in nodes.items()},
                         dict(A=0, Z=0, B=1, C=1, D=2, E=3))
        self.assertEqual(nodes['D']['predecessors'], [
            dict(unit_id='B', edge_id='B-D'), dict(unit_id='C', edge_id='C-D')])
        self.assertEqual(nodes['B']['predecessors'], [dict(unit_id='A', edge_id='A-B')])
        self.assertEqual(nodes['A']['predecessors'], [])
        self.assertIn('A-Z', result['reached_edge_ids'])
        self.assertIn('B-C', result['reached_edge_ids'])
        zero = traverse_relations(graph, maximum_hops=0)
        self.assertEqual(zero['reached_edge_ids'], ['A-Z'])
        self.assertEqual([node['unit_id'] for node in zero['nodes']], ['A', 'Z'])
        graph['edges'].reverse()
        graph['seeds'].reverse()
        self.assertEqual(traverse_relations(graph), result)

    def test_traversal_rejects_missing_seed_invalid_edge_or_scope(self):
        graph = formed_graph([('A', 'B')], ['A'])
        with self.assertRaises(ValueError):
            traverse_relations(graph, maximum_hops=4)
        graph['seeds'] = ['absent']
        with self.assertRaises(ValueError):
            traverse_relations(graph)
        graph['seeds'] = ['A']
        graph['edges'][0]['directed'] = True
        with self.assertRaises(ValueError):
            traverse_relations(graph)
