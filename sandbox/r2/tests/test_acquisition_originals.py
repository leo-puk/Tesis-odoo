"""Authorized raw-storage contract, encoding recovery and isolation checks."""
import codecs
from http.client import IncompleteRead
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from r2.adquisition import capture_plan, delete_units
from r2.adquisition.documents import decode_for_screening
from r2.adquisition.http import HttpCapture
from r2.ingestion import read_session


class Response:
    status = 200
    def __init__(self, raw, ctype): self.raw, self.headers = raw, {"Content-Type": ctype}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return self.raw


class AcquisitionOriginalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.urls = [f"https://www.odoo.com/documentation/17.0/case-{i}.html" for i in range(3)]
        self.catalog = self.root / "catalog.json"
        self.catalog.write_text(json.dumps(dict(allowed_urls=self.urls, excluded_urls=[],
            oca_repositories=["OCA/sale-workflow"], oca_addons=["sale_advance_payment", "knowledge"])), encoding="utf-8")

    def run_units(self, payloads, kinds=None):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps([dict(id=f"u{i}", kind=(kinds or {}).get(i, "official_documentation"),
            files={f"document-{i}.txt": self.urls[i]}) for i in range(len(payloads))]), encoding="utf-8")
        self.calls = []
        def transport(req, **kwargs):
            index = self.urls.index(req.full_url)
            self.calls.append(index)
            return Response(*payloads[index])
        self.result = capture_plan(plan, self.root, catalog_path=self.catalog, transport=transport)
        self.folder = Path(self.result["directory"])
        return json.loads(Path(self.result["inventory"]).read_text(encoding="utf-8"))

    def test_html_is_stored_byte_for_byte_without_conversion(self):
        raw = b'\xef\xbb\xbf<html>\r\n<p>Original &amp; complete</p><script>keep_me()</script></html>'
        rows = self.run_units([(raw, 'text/html; charset="UTF-8"')])
        unit = rows[0]
        self.assertEqual(unit["status"], "accepted")
        self.assertEqual((self.folder / unit["files"][0]).read_bytes(), raw)
        self.assertTrue(unit["files"][0].endswith(".html"))
        self.assertEqual(unit["file_metadata"][0]["text_conversion"], "not_performed")

    def test_unknown_charset_does_not_abort_and_utf8_fallback_is_lossless(self):
        bodies = [(b"First", "text/plain"), ("Español".encode(), "text/plain; charset=unknown-r2-codec"), (b"Last", "text/plain")]
        rows = self.run_units(bodies)
        self.assertEqual([r["status"] for r in rows], ["accepted"] * 3)
        self.assertEqual(self.calls, [0, 1, 2])
        self.assertEqual((self.folder / rows[1]["files"][0]).read_bytes(), bodies[1][0])
        self.assertTrue(rows[1]["file_metadata"][0]["fallback_used"])
        self.assertIn('"event": "finished"', (self.folder / "acquisition.jsonl").read_text())

    def test_unreadable_original_quarantined_next_unit_continues_and_is_not_admitted(self):
        raw = b"\xff\xfeX"  # Invalid UTF-16 length and invalid UTF-8; cannot safely screen.
        rows = self.run_units([(raw, "text/plain; charset=unknown-r2-codec"), (b"Last", "text/plain")])
        self.assertEqual([r["status"] for r in rows], ["quarantined", "accepted"])
        self.assertEqual(self.result["included"], 1)
        self.assertEqual(self.result["quarantined"], 1)
        self.assertEqual((self.folder / rows[0]["files"][0]).read_bytes(), raw)
        self.assertEqual(rows[0]["file_metadata"][0]["decode_state"], "unreadable")
        bindings = self.root / "bindings.json"
        bindings.write_text(json.dumps(dict(sources={"u1": dict(from_version="16.0", to_version="17.0")})))
        admitted, skipped = read_session(self.result["inventory"], bindings)
        self.assertEqual(len(admitted), 1)
        self.assertEqual(skipped, [dict(id=rows[0]["id"], reason="quarantined")])
        self.assertEqual(delete_units(self.result["session_id"], [rows[0]["id"]], self.root)[0]["status"], "deleted")
        self.assertTrue((self.folder / rows[1]["files"][0]).exists())

    def test_declared_latin1_is_screened_without_reencoding_original(self):
        raw = b"Espa\xf1ol\r\n"
        rows = self.run_units([(raw, 'text/plain; charset="iso-8859-1"')])
        self.assertEqual(rows[0]["status"], "accepted")
        self.assertEqual((self.folder / rows[0]["files"][0]).read_bytes(), raw)
        self.assertEqual(rows[0]["file_metadata"][0]["screening_encoding"], "iso-8859-1")
        bindings = self.root / "bindings.json"
        bindings.write_text(json.dumps(dict(sources={"u0": dict(from_version="16.0", to_version="17.0")})))
        admitted, skipped = read_session(self.result["inventory"], bindings)
        self.assertEqual(skipped, [])
        self.assertEqual(admitted[0]["files"][0]["text"], "Español\r\n")
        self.assertEqual(admitted[0]["files"][0]["raw"], raw)

    def test_unicode_boms_take_precedence_and_preserve_target_exclusion(self):
        for encoding in ("utf-16", "utf-32", "utf-8-sig"):
            with self.subTest(encoding=encoding):
                text, details = decode_for_screening("sale_advance_payment".encode(encoding), "text/plain; charset=unknown-r2-codec")
                self.assertEqual(text, "sale_advance_payment")
                self.assertEqual(details["decode_state"], "decoded")
        rows = self.run_units([("sale_advance_payment".encode("utf-16"), "text/plain; charset=unknown-r2-codec"), (b"Allowed", "text/plain")])
        self.assertEqual([r["status"] for r in rows], ["excluded", "accepted"])
        self.assertFalse((self.folder / rows[0]["id"]).exists())

    def test_nontext_codec_header_is_not_applied_as_a_transformation(self):
        text, details = decode_for_screening(b"Plain document", "text/plain; charset=rot_13")
        self.assertEqual(text, "Plain document")
        self.assertTrue(details["fallback_used"])

    def test_conservative_catalog_rejection_is_kept(self):
        rows = self.run_units([(b"<html><p>knowledge</p></html>", "text/html"), (b"Other", "text/plain")])
        self.assertEqual([r["status"] for r in rows], ["excluded", "accepted"])
        self.assertFalse((self.folder / rows[0]["id"]).exists())

    def test_invalid_utf8_is_quarantined_without_replacement_characters(self):
        raw = b"Original \xff byte"
        rows = self.run_units([(raw, "text/plain; charset=utf-8"), (b"Next", "text/plain")])
        self.assertEqual(rows[0]["status"], "quarantined")
        self.assertEqual((self.folder / rows[0]["files"][0]).read_bytes(), raw)
        self.assertEqual(rows[1]["status"], "accepted")

    def test_unknown_charset_cannot_bypass_html_entity_filter(self):
        rows = self.run_units([(b"<p>sale&#95;advance&#95;payment</p>", "text/html; charset=unknown-r2-codec")])
        self.assertEqual(rows[0]["status"], "excluded")
        self.assertFalse((self.folder / rows[0]["id"]).exists())

    def test_visible_excluded_identifier_is_rejected_even_with_invalid_bytes(self):
        rows = self.run_units([(b"sale_advance_payment \xff", "text/plain; charset=unknown-r2-codec"), (b"Other", "text/plain")])
        self.assertEqual([r["status"] for r in rows], ["excluded", "accepted"])
        self.assertFalse((self.folder / rows[0]["id"]).exists())

    def test_closed_response_connection_is_retried_without_saving_partial_body(self):
        count = 0
        def transport(*args, **kwargs):
            nonlocal count
            count += 1
            if count < 3:
                raise IncompleteRead(b"partial", 20)
            return Response(b"Complete", "text/plain")
        with patch("r2.adquisition.http.time.sleep"):
            raw, record = HttpCapture(self.root / "http", transport).get(self.urls[0])
        self.assertEqual(raw, b"Complete")
        self.assertEqual(count, 3)
        self.assertEqual(list((self.root / "http").iterdir()), [])

    def test_legacy_before_after_keys_are_rejected_without_network(self):
        plan = self.root / "bad-plan.json"
        plan.write_text(json.dumps([dict(id="bad", kind="official_documentation", files={"a.txt": self.urls[0]}, before={}, after={})]))
        with self.assertRaisesRegex(ValueError, "before/after"):
            capture_plan(plan, self.root, catalog_path=self.catalog, transport=lambda *a, **kw: self.fail("Unexpected network"))

    def test_explicit_odoo_code_and_oca_tool_are_downloaded_without_execution(self):
        urls = ["https://raw.githubusercontent.com/odoo/odoo/17.0/odoo/fields.py",
                "https://raw.githubusercontent.com/OCA/maintainer-tools/master/tools/ocb-sync.sh"]
        self.catalog.write_text(json.dumps(dict(allowed_urls=urls, excluded_urls=[],
            oca_repositories=["OCA/sale-workflow"], oca_addons=["sale_advance_payment"])))
        payloads = [b"raise RuntimeError('must never execute')\r\n", b"#!/bin/sh\nexit 23\n"]
        plan = self.root / "sources.json"
        plan.write_text(json.dumps([
            dict(id="core", kind="official_code", files={"fields.py": urls[0]}),
            dict(id="tool", kind="oca_guidance", files={"ocb-sync.sh": urls[1]}),
        ]))
        result = capture_plan(plan, self.root, catalog_path=self.catalog,
            transport=lambda req, **kw: Response(payloads[urls.index(req.full_url)], "text/plain; charset=utf-8"))
        rows = json.loads(Path(result["inventory"]).read_text())
        self.assertEqual([r["status"] for r in rows], ["accepted", "accepted"])
        for index, unit in enumerate(rows):
            self.assertEqual((Path(result["directory"]) / unit["files"][0]).read_bytes(), payloads[index])

    def test_exhausted_network_retries_are_reported_and_next_source_is_processed(self):
        plan = self.root / "network-plan.json"
        plan.write_text(json.dumps([dict(id=f"u{i}", kind="official_documentation", files={f"file{i}.txt": self.urls[i]}) for i in range(2)]))
        calls = []
        def transport(req, **kwargs):
            calls.append(req.full_url)
            if req.full_url == self.urls[0]:
                raise URLError("controlled connection failure")
            return Response(b"Complete next source", "text/plain; charset=utf-8")
        with patch("r2.adquisition.http.time.sleep"):
            result = capture_plan(plan, self.root, catalog_path=self.catalog, transport=transport)
        rows = json.loads(Path(result["inventory"]).read_text())
        self.assertEqual([r["status"] for r in rows], ["failed", "accepted"])
        self.assertEqual(calls, [self.urls[0]] * 3 + [self.urls[1]])
        self.assertEqual(result["counts"], {"accepted": 1, "failed": 1})
        self.assertTrue(rows[0]["reason"])
