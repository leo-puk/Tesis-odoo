"""Integration through the actual normalizer, never a substituted extraction rule."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from r2.cli import main
from r2.relations import load_graph


class RealPipelineTests(unittest.TestCase):
    def test_G11_real_normalization_crossing_graph_and_verified_reload(self):
        path=Path(__file__).resolve().parents[1]/'examples/run_relation_extraction_demo.py'
        spec=importlib.util.spec_from_file_location('relation_extraction_demo',path)
        demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)
        with tempfile.TemporaryDirectory() as temporary:
            report=demo.run(Path(temporary)/'real-pipeline')
            self.assertEqual(report['counts']['relation_count'],8)
            self.assertEqual(report['counts']['node_count'],7)
            self.assertEqual(report['depths'],dict(A=0,B=1,C=1,D=2,E=2,F=3,G=3))
            self.assertTrue(report['original_inputs_unchanged']);self.assertTrue(report['reload_verified'])
            self.assertEqual(report['crossing_status'],'complete');self.assertEqual(report['graph_status'],'complete')

    def test_cli_extract_relations_replays_the_crossing_handoff(self):
        path=Path(__file__).resolve().parents[1]/'examples/run_relation_extraction_demo.py'
        spec=importlib.util.spec_from_file_location('relation_demo',path)
        demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            demo.run(root/'input')
            output=root/'cli.json'
            with redirect_stdout(StringIO()):
                main(['extract-relations',str(root/'input/crossing.json'),'--db',
                      str(root/'input/collection.sqlite'),'--output',str(output)])
            graph=load_graph(output,
                             database=root/'input/collection.sqlite',
                             crossing=root/'input/crossing.json')
            self.assertEqual(graph['counts']['node_count'],7)
            self.assertEqual(graph['counts']['relation_count'],8)
