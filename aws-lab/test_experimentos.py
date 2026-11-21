"""Batch recovery and evidence accounting checks with temporary fixtures."""
import argparse
from contextlib import redirect_stdout
import csv
import importlib.util
import io
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import experimentos as batch


class BatchTests(unittest.TestCase):
    def test_source_resume_restores_frozen_ref_without_fetching(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed = root / "seed"
            seed.mkdir()

            def git(directory, *arguments):
                return subprocess.check_output(["git", "-C", str(directory), *arguments],
                    text=True, stderr=subprocess.DEVNULL).strip()

            git(seed, "init", "-q")
            source = seed / "model.py"
            source.write_text("first\n")
            git(seed, "add", "model.py")
            commit_options = ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                              "-c", "commit.gpgsign=false", "commit", "-qm")
            git(seed, *commit_options, "first")
            frozen = git(seed, "rev-parse", "HEAD")
            source.write_text("second\n")
            git(seed, "add", "model.py")
            git(seed, *commit_options, "second")
            latest = git(seed, "rev-parse", "HEAD")
            cache, output = root / "cache", root / "output"
            output.mkdir()
            bare = cache / "git" / "OCA-fixture.git"
            bare.parent.mkdir(parents=True)
            git(root, "clone", "--bare", str(seed), str(bare))
            git(bare, "remote", "set-url", "origin", "https://github.com/OCA/fixture.git")
            git(bare, "update-ref", "refs/heads/16.0", latest)
            batch.save(output / "sources.json", {"OCA/fixture@16.0": frozen})
            sources = batch.Sources(cache, output, output / "sources.log")
            original = sources.git

            def offline(directory, *arguments):
                self.assertNotEqual(arguments[0], "fetch")
                return original(directory, *arguments)

            with patch.object(sources, "git", side_effect=offline):
                snapshot, sha = sources.snapshot("OCA", "fixture", "16.0")
            self.assertEqual(sha, frozen)
            self.assertEqual((snapshot / "model.py").read_text(), "first\n")
            self.assertEqual(git(bare, "rev-parse", "refs/heads/16.0"), frozen)

    def test_catalog_selects_thirty_cases_and_one_hundred_fifty_addon_queries(self):
        cases = batch.catalog(batch.DEFAULT_PLAN)
        self.assertEqual(len(cases), 30)
        self.assertEqual(sum(len(case["modules"]) for case in cases), 150)
        self.assertNotIn("g01", {case["id"] for case in cases})

    def test_artifact_edits_invalidate_a_completed_query(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / "report.json"
            report.write_text("original")
            payload = {"artifacts": {"report.json": batch.digest(report)}}
            self.assertTrue(batch.verify_artifacts(root, payload))
            report.write_text("changed")
            self.assertFalse(batch.verify_artifacts(root, payload))

    def test_case_failure_does_not_stop_batch_and_retry_preserves_successes(self):
        cases = batch.catalog(batch.DEFAULT_PLAN)[:2]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = argparse.Namespace(output=root / "output", cache=root / "cache", plan=batch.DEFAULT_PLAN,
                                      only=[case["id"] for case in cases], repeats=3, case_timeout=1)
            calls = []

            def worker(command, log, timeout):
                cid = command[command.index("--only") + 1]
                calls.append(cid)
                attempt = Path(command[command.index("--attempt") + 1])
                if len(calls) == 2:
                    return 124
                database = attempt / "db.sqlite"
                database.write_bytes(b"synthetic test database")
                modules = []
                for item in next(case for case in cases if case["id"] == cid)["modules"]:
                    module = attempt / "addons" / item["module"]
                    module.mkdir(parents=True)
                    output = module / "report.txt"
                    output.write_text("synthetic output")
                    modules.append(dict(module=item["module"], artifacts={"report.txt": batch.digest(output)},
                        engines={engine: dict(summary={"changes_found": 1, "changes_shown": 1},
                                              median_T1_seconds=0.1) for engine in ("graph", "bm25")}))
                batch.save(attempt / "result.json", dict(status="completed", database=str(database),
                    database_sha256=batch.digest(database), modules=modules))
                return 0

            with patch("experimentos.run_worker", side_effect=worker), redirect_stdout(io.StringIO()):
                self.assertEqual(batch.run(args), 1)
                self.assertEqual(batch.run(args), 0)
            self.assertEqual(calls, [cases[0]["id"], cases[1]["id"], cases[1]["id"]])
            self.assertEqual(batch.read(args.output / "summary.json")["statuses"]["completed"], 2)
            with (args.output / "metrics.csv").open(encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 20)
            self.assertTrue(all(row["P1"] == "" for row in rows))

    @unittest.skipUnless(importlib.util.find_spec("r2"), "Run with the R2 environment for the real query fixture")
    def test_real_graph_and_bm25_outputs_are_archived_with_pending_judgments(self):
        fixture_path = str(batch.ROOT / "sandbox/r2/tests")
        sys.path.insert(0, fixture_path)
        try:
            import test_normalized_workflow as fixtures
            fixture = fixtures.NormalizedWorkflowTests()
            fixture.setUp()
            try:
                fixture.run_workflow()
                addon = fixture.root / "original"
                addon.mkdir()
                (addon / "models.py").write_bytes(fixture.module.read_bytes())
                case = dict(version_from="16.0", version_to="17.0")
                output = fixture.root / "batch-query"
                result = batch.measure_module(fixture.db, addon, case, output, 2)
                self.assertTrue(batch.verify_artifacts(output, result))
                self.assertIsNone(result["engines"]["graph"]["P1"])
                self.assertTrue((output / "graph" / "relations.json").exists())
                self.assertTrue((output / "bm25" / "bars.txt").exists())
                self.assertEqual(len(batch.read(output / "timing.json")), 4)
                case = batch.catalog(batch.DEFAULT_PLAN)[0]
                run_root = fixture.root / "metrics-run"
                attempt = run_root / "cases" / case["id"] / "attempt-test"
                attempt.mkdir(parents=True)
                batch.save(run_root / "manifest.json", {"cases": [case], "protocol": {"code": {}}})
                batch.save(attempt.parent / "latest.json", {"status": "partial", "attempt": str(attempt.relative_to(run_root))})
                batch.save(attempt / "result.json", dict(database=str(fixture.db), database_sha256=batch.digest(fixture.db),
                    modules=[result]))
                graph = batch.read(output / "graph" / "report.json")
                bm25 = batch.read(output / "bm25" / "report.json")
                direct = graph["results"][0]["change_id"]
                judgments = {row["change_id"]: dict(relevant=row["change_id"] == direct,
                    reference_ids=["fix"] if row["change_id"] == direct else []) for report in (graph, bm25)
                    for row in report["results"]}
                spec = dict(reviewer="Synthetic test fixture", collection_revision=graph["collection_revision"],
                    references={"fix": dict(migration_id=case["id"], from_version="16.0", to_version="17.0",
                                            available_unit_ids=[direct])},
                    queries=[dict(id=case["id"] + "/original", module=str(addon), reference_ids=["fix"],
                                  judgments=judgments, **graph["query"])])
                batch.save(attempt / "evaluation-spec.json", spec)
                args = argparse.Namespace(output=run_root, plan=batch.DEFAULT_PLAN, repeats=1)
                with redirect_stdout(io.StringIO()):
                    batch.evaluate(args)
                self.assertEqual(batch.read(run_root / "summary.json")["C1"], 100)
                spec["reviewer"] = "Updated synthetic reviewer"
                batch.save(attempt / "evaluation-spec.json", spec)
                with redirect_stdout(io.StringIO()):
                    batch.summary(run_root)
                self.assertIsNone(batch.read(run_root / "summary.json")["C1"])
            finally:
                fixture.doCleanups()
        finally:
            sys.path.remove(fixture_path)


if __name__ == "__main__":
    unittest.main()
