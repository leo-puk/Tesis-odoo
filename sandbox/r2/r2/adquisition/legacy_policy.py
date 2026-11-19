"""Select R2 source records before extraction/indexing. No ingestion is implemented here."""
import argparse
import json
from pathlib import Path

ALLOWED_KINDS = {
    "official_code", "official_documentation", "oca_guidance",
    "openupgrade_analysis", "oca_migration", "oca_fix", "derived",
}


def select_sources(records, *, include_oca_migrations=False):
    """Historical local imports: reserved and OCA-specific evidence are excluded.

    Records require id, kind, split and parent_ids. A derived record must name
    its parents. Selection cannot detect dishonest or incomplete provenance.
    """
    if include_oca_migrations:
        raise ValueError("The OCA inclusion switch was removed; acquisition admission is fixed")
    by_id = {}
    for record in records:
        key = record["id"]
        if not isinstance(key, str) or not key or key in by_id:
            raise ValueError("Source IDs must be unique nonempty strings")
        by_id[key] = record
    decisions = {}

    def decide(key, visiting):
        if key in decisions:
            return decisions[key]
        if key not in by_id:
            raise ValueError(f"Missing provenance source: {key}")
        if key in visiting:
            raise ValueError(f"Provenance cycle: {key}")
        record = by_id[key]
        kind = record.get("kind")
        split = record.get("split")
        parents = record.get("parent_ids")
        if kind not in ALLOWED_KINDS or split not in {"construction", "evaluation_reference"}:
            raise ValueError(f"Unknown kind or split: {key}")
        if not isinstance(parents, list) or not all(isinstance(p, str) for p in parents):
            raise ValueError(f"Explicit parent_ids required: {key}")
        if kind == "derived" and not parents:
            raise ValueError(f"Derived source requires parents: {key}")
        parent_results = [decide(p, visiting | {key}) for p in parents]
        if split == "evaluation_reference":
            result = (False, "reserved_evaluation_reference")
        elif any(not allowed for allowed, _ in parent_results):
            result = (False, "excluded_provenance")
        elif kind in {"oca_migration", "oca_fix"} :
            result = (False, "oca_specific_sources_excluded")
        else:
            result = (True, "allowed")
        decisions[key] = result
        return result

    for key in by_id:
        decide(key, set())
    return {
        "policy_version": 1,
        "include_oca_migrations": include_oca_migrations,
        "accepted": [r for r in records if decisions[r["id"]][0]],
        "excluded": [
            {"id": r["id"], "reason": decisions[r["id"]][1]}
            for r in records if not decisions[r["id"]][0]
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON array of source records")
    args = parser.parse_args()
    try:
        records = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        result = select_sources(records)
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
