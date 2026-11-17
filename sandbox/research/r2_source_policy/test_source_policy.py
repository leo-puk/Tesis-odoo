import unittest
from source_policy import select_sources


def source(key, kind="official_code", split="construction", parents=()):
    return {"id": key, "kind": kind, "split": split, "parent_ids": list(parents)}


class SourcePolicyTests(unittest.TestCase):
    def test_default_excludes_mig_fix_and_transitive_derivatives(self):
        records = [source("core"), source("mig", "oca_migration"),
                   source("fix", "oca_fix"), source("patch", "derived", parents=["mig"]),
                   source("summary", "derived", parents=["core", "patch"])]
        self.assertEqual([r["id"] for r in select_sources(records)["accepted"]], ["core"])

    def test_switch_allows_construction_migrations(self):
        records = [source("mig", "oca_migration"), source("fix", "oca_fix"),
                   source("patch", "derived", parents=["mig", "fix"])]
        self.assertEqual(len(select_sources(records, include_oca_migrations=True)["accepted"]), 3)

    def test_reserved_solution_and_derivative_excluded_even_when_enabled(self):
        records = [source("reserved", "oca_migration", "evaluation_reference"),
                   source("copy", "derived", parents=["reserved"])]
        self.assertEqual(select_sources(records, include_oca_migrations=True)["accepted"], [])

    def test_missing_parent_aborts(self):
        with self.assertRaises(ValueError):
            select_sources([source("copy", "derived", parents=["missing"])])

    def test_cycle_aborts(self):
        with self.assertRaises(ValueError):
            select_sources([source("a", "derived", parents=["b"]),
                            source("b", "derived", parents=["a"])])

    def test_incomplete_provenance_and_duplicate_ids_abort(self):
        for records in ([source("a"), source("a")], [source("a", "derived")],
                        [{"id": "a", "kind": "official_code", "split": "construction"}]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                select_sources(records)


if __name__ == "__main__":
    unittest.main()
