"""Original regression cases adapted externally to the newly authorized raw storage."""
import importlib
import importlib.util
from pathlib import Path
import sys


def load_tests(loader, tests, pattern):
    # The original delivery and its tests remain unchanged in reference/.
    for suffix in ("", ".sources", ".http", ".github", ".provenance", ".policy", ".documents"):
        sys.modules["adquisition" + suffix] = importlib.import_module("r2.adquisition" + suffix)
    path = Path(__file__).resolve().parents[1] / "reference/adquisition-final/tests/test_capture_plan.py"
    spec = importlib.util.spec_from_file_location("final_adquisition_original_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    class CurrentContractTests(module.CaptureTests):
        def test_document_conversion_and_deletion(self):
            from r2.adquisition import delete_units
            result = self.run_plan()
            unit = self.units[0]
            file = Path(result['directory']) / unit['files'][0]
            self.assertEqual(file.suffix, '.html')
            self.assertEqual(file.read_bytes(), b'<p>Migration guide</p>')
            self.assertEqual(unit['storage_form'], 'original')
            self.assertEqual(unit['file_metadata'][0]['text_conversion'], 'not_performed')
            self.assertEqual(delete_units(result['session_id'], [unit['id']], self.root)[0]['status'], 'deleted')
            self.assertFalse(file.exists())
            self.assertTrue((Path(result['directory']) / 'acquisition.jsonl').exists())
            self.assertFalse((Path(result['directory']) / 'capture-report.json').exists())
    return loader.loadTestsFromTestCase(CurrentContractTests)
