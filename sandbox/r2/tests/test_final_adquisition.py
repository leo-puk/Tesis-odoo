"""Run the final component's original tests against the installed package."""
import importlib
import importlib.util
from pathlib import Path
import sys


def load_tests(loader, tests, pattern):
    # Only the external test harness adapts the original top-level imports.
    # The final component and the original 21 tests remain byte-identical.
    for suffix in ("", ".sources", ".http", ".github", ".provenance", ".policy", ".documents"):
        sys.modules["adquisition" + suffix] = importlib.import_module("r2.adquisition" + suffix)
    path = Path(__file__).resolve().parents[1] / "reference/adquisition-final/tests/test_capture_plan.py"
    spec = importlib.util.spec_from_file_location("final_adquisition_original_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)
