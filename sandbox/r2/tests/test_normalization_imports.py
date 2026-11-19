"""Compatibility checks for the normalization package consolidation."""
import unittest

from r2 import normalization
from r2.conversion import convert_units
from r2.conversion.anchors import partial_anchors
from r2.conversion.diff import HEADER, filename, parse_diff
from r2.ingestion import read_session
from r2.ingestion.session import KINDS, STATES
from r2.normalization import anchors, diff, readers, text, units


class NormalizationImportTests(unittest.TestCase):
    def test_legacy_imports_use_the_same_implementations(self):
        for old, new in (
            (convert_units, units.convert_units),
            (partial_anchors, anchors.partial_anchors),
            (filename, diff.filename),
            (parse_diff, diff.parse_diff),
            (HEADER, diff.HEADER),
            (read_session, readers.read_session),
            (KINDS, readers.KINDS),
            (STATES, readers.STATES),
            (normalization.normalize, text.normalize),
        ):
            with self.subTest(symbol=getattr(old, "__name__", repr(old))):
                self.assertIs(old, new)

    def test_legacy_text_entry_point_keeps_html_and_line_endings_behavior(self):
        self.assertEqual(normalization.normalize(b"\xef\xbb\xbfuno\r\ndos\rtres"), "uno\ndos\ntres")
        self.assertEqual(normalization.normalize(
            b"<html><body><nav>menu</nav><p>contenido</p><script>code</script></body></html>",
            "text/html"), "contenido")
