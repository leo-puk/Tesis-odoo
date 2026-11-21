"""Verify the uploaded snapshot includes newly added R2 files and omits private state."""
from pathlib import Path
import subprocess
import tarfile
import unittest
from unittest.mock import patch

import sync


class SyncTests(unittest.TestCase):
    def test_working_snapshot_contains_chart_implementation(self):
        original_run = subprocess.run
        transferred = []

        def fake_run(command, *args, **kwargs):
            if command[0] == "git":
                return original_run(command, *args, **kwargs)
            if command[0] == "scp":
                with tarfile.open(Path(command[-2])) as archive:
                    names = archive.getnames()
                    self.assertIn("sandbox/r2/r2/charts.py", names)
                    self.assertIn("aws-lab/Dockerfile.dockerignore", names)
                    self.assertIn("aws-lab/source-revision.json", names)
                    self.assertFalse(any(name.startswith(("aws-lab/.state/", "aws-lab/data/")) for name in names))
                    self.assertNotIn("aws-lab/.env", names)
            transferred.append(command[0])
            return subprocess.CompletedProcess(command, 0)

        with patch("sys.argv", ["sync.py", "--host", "203.0.113.1", "--key", "unused.pem"]), patch(
                "sync.subprocess.run", side_effect=fake_run):
            sync.main()
        self.assertEqual(transferred, ["scp", "ssh"])


if __name__ == "__main__":
    unittest.main()
