"""Synthetic end-to-end evidence review; no labels from these tests are thesis data."""
import argparse
from contextlib import redirect_stdout
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import experimentos as batch
from mig_collection import collect_migs
from mig_review import suggest_links
from review_dossier import apply_case, export_case, judge_batch


class CollectionTests(unittest.TestCase):
    def test_other_addon_migs_and_fixes_are_archived_with_version_and_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = Mock()
            sources.pin.side_effect = [(root, "source"), (root, "frozen")]
            def git(directory, *args):
                if args[0] == "log":
                    self.assertNotIn("--", args)  # Whole repository, including other addons.
                    self.assertEqual(args[-1], "source..frozen")
                    return "a\t[17.0][MIG] another_addon\nb\t[18.0][MIG] wrong_version\nc\t[FIX] versionless"
                return "--- a/other/models.py\n+++ b/other/models.py\n@@ -1 +1 @@\n-old_name\n+new_name\n"
            sources.git.side_effect = git
            case = dict(id="oca_v01_1617", version_from="16.0", version_to="17.0",
                        modules=[dict(repo="fixture", module="original")])
            result = collect_migs(sources, case, root / "references")
            self.assertEqual([entry["sha"] for entry in result["candidates"]], ["a", "c"])
            self.assertEqual(result["candidates"][1]["tags"], ["FIX"])
            self.assertEqual(result["status"], "collected")
            self.assertTrue((root / "references/fixture-a.diff").exists())
            self.assertIn("not an exhaustive", result["scope"]["limitation"])


@unittest.skipUnless(importlib.util.find_spec("r2"), "Requires R2 environment")
class ReviewTests(unittest.TestCase):
    def setUp(self):
        fixture_path = str(batch.ROOT / "sandbox/r2/tests")
        sys.path.insert(0, fixture_path)
        self.addCleanup(lambda: sys.path.remove(fixture_path))
        import test_normalized_workflow as fixtures
        self.fixture = fixtures.NormalizedWorkflowTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.run_workflow()
        addon = self.fixture.root / "original"
        addon.mkdir()
        (addon / "models.py").write_bytes(self.fixture.module.read_bytes())
        self.case = dict(batch.catalog(batch.DEFAULT_PLAN)[0], modules=[dict(repo="fixture", module="original")])
        self.output = self.fixture.root / "run"
        self.attempt = self.output / "cases" / self.case["id"] / "attempt-fixture"
        module = batch.measure_module(self.fixture.db, addon, self.case, self.attempt / "addons/original", 1)
        self.assertEqual(set(module["engines"]), {"graph", "bm25"})
        self.assertFalse((self.attempt / "addons/original/source-judgments.csv").exists())
        batch.save(self.attempt / "result.json", dict(status="completed", database=str(self.fixture.db),
            database_sha256=batch.digest(self.fixture.db), modules=[module]))
        batch.save(self.output / "manifest.json", dict(cases=[self.case], protocol={"code": {}}))
        batch.save(self.attempt.parent / "latest.json", dict(status="completed", attempt=str(self.attempt.relative_to(self.output))))
        graph = batch.read(self.attempt / "addons/original/graph/report.json")
        self.direct = graph["results"][0]["change_id"]
        batch.save(self.attempt / "evaluation-spec.json", dict(reviewer=None,
            collection_revision=graph["collection_revision"], references={}, queries=[dict(
                id=self.case["id"] + "/original", module=str(addon), **graph["query"], reference_ids=[], judgments={})]))
        pool = self.attempt / "references/pool"
        pool.mkdir(parents=True)
        sha = "a" * 40
        self.hid = sha + ":3"
        (pool / "fixture.diff").write_text("--- a/original/models.py\n+++ b/original/models.py\n@@ -1 +1 @@\n"
            "-model = 'old.seed'\n+model = 'original.seed'\n", encoding="utf-8")
        candidates = [dict(repository="OCA/fixture", sha=sha, url="https://github.com/OCA/fixture/commit/" + sha,
                           subject="[17.0][MIG] original", patch_file="fixture.diff")]
        batch.save(pool / "candidates.json", dict(candidates=candidates, scope={"repositories": ["OCA/fixture"]}, failures={}))
        links = suggest_links(self.fixture.db, self.attempt / "addons/original", pool, candidates, "16.0", "17.0")
        self.assertTrue(links["hunks"][0]["retrieved_unit_candidates"])
        batch.save(self.attempt / "references/original/suggested-links.json", links)
        self.folder = export_case(self.attempt, self.case)
        self.review = batch.read(self.folder / "review-template.json")
        self.review.update(completed=True, reviewer="Synthetic fixture: not an academic reviewer", reference_decisions=[dict(
            id="fix", admitted=True, description="Synthetic incompatibility", modules=["original"], hunk_ids=[self.hid],
            available_unit_ids=[self.direct], reason="Synthetic patch evidence", uncertainty="Fixture only",
            affected_layer="python", affected_component="original.seed",
            unit_explanations={self.direct: "Synthetic technical evidence"},
            coverage_reason="Synthetic exact-jump evidence")])
        for judgments in self.review["judgments"].values():
            for uid, judgment in judgments.items():
                judgment.update(relevant=uid == self.direct, reference_ids=["fix"] if uid == self.direct else [],
                                affected_layer="python", affected_component="original.seed",
                                reason="Synthetic technical decision", uncertainty="Fixture only")
        self.path = self.output / "reviews" / (self.case["id"] + ".json")

    def apply(self, review=None):
        batch.save(self.path, review or self.review)
        return apply_case(self.attempt, self.path)

    def test_dossier_and_judgments_produce_real_evaluator_metrics(self):
        packet = batch.read(self.folder / "packet.json")
        self.assertGreater(packet["corpus_unit_count"], len(packet["queries"][0]["reports"]["graph"]["results"]))
        self.assertIn("models.py", batch.read(self.folder / "addon-sources.json")["original"]["files"])
        self.apply()
        self.assertTrue((self.folder / "JUICIOS.md").exists())
        args = argparse.Namespace(output=self.output, plan=batch.DEFAULT_PLAN, repeats=1, only=[self.case["id"]])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(batch.evaluate(args), 0)
        self.assertEqual(batch.read(self.output / "summary.json")["C1"], 100)
        self.assertEqual(batch.read(self.output / "summary.json")["admitted_migration_count"], 1)
        self.assertFalse((self.output / "source-metrics.csv").exists())

    def test_archived_evidence_can_be_reviewed_after_discarding_the_collection_and_addon(self):
        result_path = self.attempt / "result.json"
        result = batch.read(result_path)
        result["review_packet_sha256"] = batch.digest(self.folder / "packet.json")
        batch.save(result_path, result)
        manifest_path = self.output / "manifest.json"
        manifest = batch.read(manifest_path)
        manifest["protocol"]["repeats"] = 1
        manifest["cache_policy"] = "Fixture cache"
        batch.save(manifest_path, manifest)
        self.fixture.db.unlink()
        (self.fixture.root / "original" / "models.py").unlink()
        self.assertIn(self.direct, (self.folder / "unidades.html").read_text(encoding="utf-8"))
        self.assertTrue(batch.read(self.folder / "mig-fix-candidatos.json")["candidates"])
        specification = self.apply()
        self.assertTrue(batch.read(self.folder / "mig-fix-admitidos.json")["mig"])
        with (self.folder / "matriz-unidad-mig.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertTrue(any(row["scope"] == "collection" and row["covers_correction"] == "True"
                            and row["commit_urls"] for row in rows))
        self.assertTrue(any(row["engine"] == "graph" and row["unit_id"] == self.direct
                            and row["link_explanation"] for row in rows))
        args = argparse.Namespace(output=self.output, plan=batch.DEFAULT_PLAN, repeats=3, only=[self.case["id"]])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(batch.evaluate(args), 0)
        value = batch.read(self.attempt / "evaluation.json")
        self.assertEqual(value["C1"], 100)
        self.assertEqual(value["queries"][0]["engines"]["graph"]["C2"], 100)
        self.assertEqual(value["timing"]["repeats"], 1)
        self.assertEqual(value["reviewer"], specification["reviewer"])

    def test_final_gate_requires_real_migs_and_unexecuted_cases_are_not_successes(self):
        self.apply()
        args = argparse.Namespace(output=self.output, plan=batch.DEFAULT_PLAN, repeats=1, require_all=True,
                                  require_migs=30, only=None)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(batch.evaluate(args), 1)
        summary = batch.read(self.output / "summary.json")
        self.assertEqual(summary["measured_cases"], 1)
        self.assertEqual(summary["admitted_migration_count"], 1)

    def test_uncovered_correction_remains_in_reference_denominator(self):
        self.review["reference_decisions"].append(dict(self.review["reference_decisions"][0], id="missed",
            description="Another synthetic correction", available_unit_ids=[], unit_explanations={},
            coverage_reason="Absent from collection"))
        self.apply()
        args = argparse.Namespace(output=self.output, plan=batch.DEFAULT_PLAN, repeats=1, only=[self.case["id"]])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(batch.evaluate(args), 0)
        value = batch.read(self.attempt / "evaluation.json")
        self.assertEqual(value["C1"], 50)
        self.assertEqual(value["commit_coverage"][0]["status"], "partial")
        self.assertEqual(value["queries"][0]["engines"]["graph"]["C2"], 50)

    def test_incomplete_or_stale_or_unaccounted_reviews_are_rejected(self):
        for change in ({"completed": False}, {"packet_sha256": "wrong"}, {"reference_decisions": []},
                       {"judgments": {}}):
            review = copy.deepcopy(self.review)
            review.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.apply(review)
        self.assertIsNone(batch.read(self.attempt / "evaluation-spec.json")["reviewer"])
        (self.folder / "addon-sources.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.apply()

    def test_automated_judge_archives_real_response_once_and_applies_validation(self):
        args = argparse.Namespace(output=self.output, reviews=None, judge_command=["fixture-judge"],
                                  judge_timeout=5, retry_judgments=False, only=None)
        response = Mock(stdout=json.dumps(self.review))
        with patch("review_dossier.subprocess.run", return_value=response) as runner, redirect_stdout(io.StringIO()):
            self.assertEqual(judge_batch(args), 0)
            self.assertEqual(judge_batch(args), 0)
        runner.assert_called_once()
        self.assertEqual(runner.call_args.kwargs["cwd"], self.folder)
        self.assertEqual(batch.read(self.path), self.review)
        self.assertTrue(apply_case(self.attempt, self.path)["admitted_commits"])

    def test_rejects_positive_judgment_without_technical_scope(self):
        query = next(iter(self.review["judgments"].values()))
        query[self.direct]["affected_component"] = ""
        with self.assertRaisesRegex(ValueError, "layer and component"):
            self.apply()


if __name__ == "__main__":
    unittest.main()
