"""End-to-end regression on a real local OCA 16 addon, with HTTP mocked."""
import tempfile
from pathlib import Path
import unittest
from examples.run_oca_functional_test import run


class OCAFunctionalityTests(unittest.TestCase):
    def test_sale_advance_payment_16_to_17(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run(Path(directory) / "run")
            self.assertTrue(result["passed"])
            self.assertTrue(all(result["checks"].values()))
            self.assertEqual(result["reviewed_query_summaries"]["graph"]["changes_found"], 2)
            self.assertEqual(result["reviewed_query_summaries"]["bm25"]["changes_found"], 2)
