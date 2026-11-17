"""Collection boundaries exercised without accessing external services."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from r2.adquisition import HttpCapture
from r2.adquisition.provenance import sha
from r2.cli import main
from r2.collection import connect, load


class AdquisitionTests(unittest.TestCase):
    def test_cli_capture_can_build_offline_and_detect_tampering(self):
        class Response:
            status = 200
            headers = {"Content-Type": "text/plain"}

            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self):
                return self.data

        before = "https://raw.githubusercontent.com/odoo/odoo/16.0/odoo/fields.py"
        after = "https://raw.githubusercontent.com/odoo/odoo/17.0/odoo/fields.py"
        bodies = {before: b"value = 1  \r\n", after: b"value = 2  \r\n"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "plan.json"
            plan.write_text(json.dumps([dict(
                id="core", kind="official_code", from_version="16.0", to_version="17.0",
                before={"fields.py": before}, after={"fields.py": after},
            )]), encoding="utf-8")
            output = root / "capture"
            with patch("r2.adquisition.http.request.build_opener") as opener:
                opener.return_value.open.side_effect = lambda req, **kw: Response(bodies[req.full_url])
                with redirect_stdout(io.StringIO()):
                    main(["capture-plan", str(plan), "--output", str(output)])
                self.assertEqual(opener.return_value.open.call_count, 2)
            manifest = output / "inventory.json"
            record = json.loads(manifest.read_text(encoding="utf-8"))[0]
            capture = record["captures"][0]
            self.assertEqual(Path(capture["stored_file"]).read_bytes(), bodies[before])
            self.assertEqual(Path(capture["normalized_file"]).read_bytes(), b"value = 1  \n")
            self.assertEqual(capture["response_sha256"], sha(bodies[before]))
            self.assertNotEqual(capture["response_sha256"], capture["normalized_sha256"])
            # Build uses the capture on disk; any unexpected HTTP call fails.
            with patch("r2.adquisition.http.request.build_opener", side_effect=AssertionError("unexpected network")):
                with redirect_stdout(io.StringIO()):
                    main(["build", str(manifest), "--db", str(root / "valid.sqlite")])
                with connect(root / "valid.sqlite") as con:
                    self.assertEqual(len(load(con, "sources")), 1)
                    self.assertTrue(load(con, "changes"))
                Path(capture["stored_file"]).write_bytes(b"tampered")
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        main(["build", str(manifest), "--db", str(root / "invalid.sqlite")])

    def test_http_error_retains_status_and_rate_limit_diagnostics(self):
        def denied(req, **kwargs):
            raise HTTPError(req.full_url, 403, "denied", {"X-RateLimit-Remaining": "0"}, None)

        with tempfile.TemporaryDirectory() as directory:
            client = HttpCapture(directory, transport=denied)
            with self.assertRaisesRegex(ValueError, "HTTP 403"):
                client.get("https://api.github.com/repos/OCA/example/pulls/1")
            records = list(Path(directory).glob("error-*.json"))
            self.assertEqual(len(records), 1)
            record = json.loads(records[0].read_text(encoding="utf-8"))
            self.assertEqual(record["status"], 403)
            self.assertEqual(record["headers"]["x-ratelimit-remaining"], "0")

    def test_legacy_imports_keep_public_entry_points(self):
        from r2 import acquire
        from r2.adquisition import GitHubMetadata, capture_plan
        from r2.normalization import normalize

        self.assertIs(acquire.HttpCapture, HttpCapture)
        self.assertIs(acquire.GitHubMetadata, GitHubMetadata)
        self.assertIs(acquire.capture_plan, capture_plan)
        self.assertIs(acquire.normalize, normalize)
