"""Check shortest-path accounting when several shortest routes share an edge."""
import unittest
from unittest.mock import patch

from r2.charts import bars, graph_statistics, render_evaluation


class ChartTests(unittest.TestCase):
    def statistics(self, level=None):
        pairs = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E")]
        depths = dict(A=0, B=1, C=1, D=2, E=3)
        graph = {
            "collection": {"revision": "revision"}, "crossing": {"result_id": "cross"}, "maximum_hops": 3,
            "nodes": [dict(unit_id=uid, minimum_hops=depth, is_seed=uid == "A",
                           predecessors=[dict(unit_id=a, edge_id=a+b) for a, b in pairs if b == uid])
                      for uid, depth in depths.items()],
            "edges": [dict(id=a+b, left=a, right=b, raw_match_count=1,
                           matches=[dict(identity=["field", "stock.move", "quantity"])]) for a, b in pairs],
        }
        crossing = dict(result_id="cross", input={"input_revision": "input"}, results=[])
        report = dict(collection_revision="revision", engine="graph", summary={},
                      query={"input_revision": "input", "maximum_hops": 3})
        with patch("r2.charts.validate_report"), patch("r2.charts.validate_graph"), patch("r2.charts.validate_result"):
            return graph_statistics(report, crossing, graph, level)

    def test_shared_edges_count_all_shortest_paths_without_enumerating_them(self):
        self.assertEqual(self.statistics()["edge_paths"], dict(AB=3, AC=3, BD=2, CD=2, DE=2))
        level = self.statistics(2)
        self.assertEqual(level["edge_paths"], dict(AB=1, AC=1, BD=1, CD=1))
        self.assertEqual(level["node_matches"], dict(D=3))
        self.assertEqual(level["attributes"], {"field / stock.move / quantity": 3})
        self.assertEqual(self.statistics(0)["edge_paths"], {})

    def test_bars_handle_zero_empty_and_long_labels(self):
        text = bars("Counts", {"long" * 40: 0, "short": 0}, top=2, width=60, ascii_only=True)
        self.assertTrue(all(len(line) <= 60 for line in text.splitlines()))
        self.assertIn("no observations", bars("Empty", {}, top=2, width=60, ascii_only=True))

    def test_undefined_precision_is_preserved(self):
        text = render_evaluation({"C1": None, "queries": [dict(id="q", engines={"graph": {"P1": None, "C2": 0}})]},
                                 ascii_only=True)
        self.assertIn("Pending/undefined P1: q / graph", text)
        self.assertIn("C1: None", text)

    def test_labels_wrap_without_losing_filenames_or_merging_equal_labels(self):
        label = "addons/stock/models/stock_move.py [diff L61908]"
        text = bars("Nodes", {"id-one": 5000, "id-two": 3000}, top=2, width=60,
                    ascii_only=True, labels={"id-one": label, "id-two": label})
        self.assertIn("stock_move.py", text)
        self.assertIn("5,000", text)
        self.assertIn("3,000", text)
        self.assertNotIn("id-one", text)
        self.assertEqual(text.count("stock_move.py"), 2)
        self.assertTrue(all(len(line) <= 60 for line in text.splitlines()))

    def test_percentages_use_a_fixed_hundred_percent_scale(self):
        text = bars("P1", {"Graph": 10}, top=2, width=60, ascii_only=True, maximum=100)
        self.assertEqual(text.count("#"), 4)
