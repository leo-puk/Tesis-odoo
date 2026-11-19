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
            self.assertEqual(set(result["expected_targets"]), {"python", "xml"})
            for summary in result["query_summaries"].values():
                self.assertGreater(summary["eligible_units"], 0)
                self.assertLessEqual(summary["changes_shown"], 10)
