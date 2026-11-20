"""White- and black-box checks for the R2.2 local assistant."""
import argparse
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import tempfile
import unittest

from r2.assistant import (available_versions, detect_odoo_checkout, discover_addons, local_diff,
                          resolve_version_ref, run_local_analysis, select_addons, start)
from r2.cli import main


class AssistantR22Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.odoo = self.root / "odoo"
        self.odoo.mkdir()
        (self.odoo / "odoo-bin").write_text("#!/usr/bin/env python\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.odoo)], check=True)
        subprocess.run(["git", "-C", str(self.odoo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.odoo), "config", "user.name", "R2 Test"], check=True)
        code = self.odoo / "odoo" / "models.py"
        code.parent.mkdir()
        code.write_text("class Model:\n    old_api = True\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.odoo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.odoo), "commit", "-qm", "16"], check=True)
        subprocess.run(["git", "-C", str(self.odoo), "branch", "16.0"], check=True)
        code.write_text("class Model:\n    new_api = True\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.odoo), "commit", "-qam", "17"], check=True)
        subprocess.run(["git", "-C", str(self.odoo), "branch", "17.0"], check=True)
        self.addons = self.root / "addons"
        for name in ("alpha_addon", "beta_addon", "zeta_addon"):
            folder = self.addons / name
            folder.mkdir(parents=True)
            (folder / "__manifest__.py").write_text("{'depends': ['base']}\n", encoding="utf-8")

    def test_detect_list_select_and_diff_are_local(self):
        self.assertEqual(detect_odoo_checkout(self.odoo / "odoo"), self.odoo.resolve())
        addons = discover_addons(self.addons)
        self.assertEqual([item["name"] for item in addons], ["alpha_addon", "beta_addon", "zeta_addon"])
        self.assertEqual([item["name"] for item in select_addons(addons, "1,3")],
                         ["alpha_addon", "zeta_addon"])
        self.assertEqual([item["name"] for item in select_addons(addons, "2-3")],
                         ["beta_addon", "zeta_addon"])
        self.assertEqual(resolve_version_ref(self.odoo, "16.0"), "16.0")
        self.assertEqual(available_versions(self.odoo), ["16.0", "17.0"])
        text, revisions = local_diff(self.odoo, "16.0", "17.0")
        self.assertIn("-    old_api = True", text)
        self.assertIn("+    new_api = True", text)
        self.assertEqual(len(revisions["from_revision"]), 40)

    def test_noninteractive_list_only_saves_reusable_configuration(self):
        config = self.root / "config.json"
        args = argparse.Namespace(odoo=self.odoo, addons=self.addons, from_version="16.0",
                                  to_version="17.0", select="alpha_addon,zeta_addon",
                                  output_dir=None, config=config, list_only=True,
                                  layer="all", maximum_hops=3, limit=10)
        lines = []
        result = start(args, output_fn=lines.append)
        self.assertEqual([item["name"] for item in result["addons"]], ["alpha_addon", "zeta_addon"])
        self.assertEqual(json.loads(config.read_text(encoding="utf-8"))["odoo_repo"], str(self.odoo.resolve()))
        self.assertTrue(any("alpha_addon" in line for line in lines))

    def test_cli_exposes_friendly_start_command(self):
        config = self.root / "cli-config.json"
        with redirect_stdout(io.StringIO()) as stdout:
            main(["start", "--odoo", str(self.odoo), "--addons", str(self.addons),
                  "--from", "16.0", "--to", "17.0", "--select", "2", "--config", str(config),
                  "--list-only"])
        result = json.loads(stdout.getvalue()[stdout.getvalue().rindex("\n{") + 1:])
        self.assertEqual(result["addons"][0]["name"], "beta_addon")

    def test_local_analysis_builds_one_collection_and_one_report_per_addon(self):
        selected = discover_addons(self.addons)[:2]
        output = self.root / "analysis"
        result = run_local_analysis(self.odoo, selected, "16.0", "17.0", output)
        self.assertTrue(Path(result["collection"]["database"]).is_file())
        self.assertTrue((output / "local-source.json").is_file())
        self.assertTrue((output / "summary.json").is_file())
        self.assertEqual([item["addon"] for item in result["addons"]],
                         ["alpha_addon", "beta_addon"])
        self.assertTrue(all(Path(item["report"]).is_file() for item in result["addons"]))


if __name__ == "__main__":
    unittest.main()
