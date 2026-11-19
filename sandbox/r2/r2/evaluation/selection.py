"""Auditable assignment, stratified sampling and protocol fingerprints."""
import hashlib
import json
import random
from datetime import datetime
from pathlib import Path

from ..records import fingerprint

CRITERIA = ("independent_maintainer_review", "single_module", "consecutive_versions",
            "automated_tests", "public_community_dependencies", "no_migration_behavior_fix")


def code_revision():
    return fingerprint({p.relative_to(Path(__file__).parent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.rglob("*.py")) if "__pycache__" not in p.parts})


def date(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Temporal cut and publication dates require a timezone")
    return result


def eligible(case, cutoff, excluded_modules):
    reasons = []
    if case.get("module") in excluded_modules or case.get("inspected_for_development"):
        return "excluded", ["used_for_construction_or_inspected"]
    if not case.get("case_id") or not case.get("module") or not case.get("published_at") or not case.get("author"):
        return "pending", ["case_identity_or_publication_missing"]
    if date(case["published_at"]) < date(cutoff):
        return "excluded", ["before_evaluation_cutoff"]
    criteria = case.get("criteria", {})
    for name in CRITERIA:
        item = criteria.get(name, {})
        if item.get("status") == "fail":
            return "excluded", [name]
        if item.get("status") != "pass" or not item.get("evidence") or not item.get("reviewer"):
            reasons.append(name)
    review = criteria.get("independent_maintainer_review", {})
    if review.get("status") == "pass":
        if not review.get("maintainer_identity_evidence") or not review.get("maintainer") or review.get("maintainer") == case.get("author"):
            reasons.append("maintainer_identity_or_independence_unproven")
    if case.get("to_version") not in {"17.0", "18.0", "19.0"} or case.get("from_version") != f"{int(case.get('to_version', '0').split('.')[0])-1}.0":
        reasons.append("invalid_consecutive_jump")
    return ("pending", reasons) if reasons else ("eligible", [])


def sample_cases(spec):
    cutoff = spec.get("cutoff", {})
    if not cutoff.get("date"):
        raise ValueError("A recorded temporal cutoff is required")
    cases = spec["candidates"]
    if len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate case IDs")
    rng = random.Random(spec["seed"])
    excluded = set(spec.get("excluded_modules", [])) | {"sale_advance_payment"}
    selected, events, blocks, orders = [], [], [], {}
    for target in ("17.0", "18.0", "19.0"):
        pool = sorted([c for c in cases if c.get("to_version") == target],
                      key=lambda c: (int(c["number"]), c.get("repository", "")))
        rng.shuffle(pool)
        orders[target] = [c["case_id"] for c in pool]
        count = 0
        for case in pool:
            status, reasons = eligible(case, cutoff["date"], excluded)
            events.append(dict(case_id=case["case_id"], stratum=target, decision=status, reasons=reasons))
            if status == "pending":
                blocks.append(dict(stratum=target, case_id=case["case_id"], missing=reasons))
                break  # Do not skip an unreviewed random candidate and bias selection.
            if status == "eligible":
                selected.append(case)
                count += 1
                if count == 10:
                    break
        if count < 10:
            blocks.append(dict(stratum=target, reason="fewer_than_ten_verified_cases", selected=count))
    if cutoff.get("status") != "confirmed":
        blocks.append(dict(reason="model_and_cutoff_not_confirmed"))
    if not spec.get("frame_evidence"):
        blocks.append(dict(reason="population_frame_not_audited"))
    return dict(seed=spec["seed"], cutoff=cutoff, selected=selected, orders=orders,
                excluded_modules=sorted(excluded), frame_evidence=spec.get("frame_evidence"),
                replacement_and_review_log=events, blocked=blocks,
                complete=not blocks and len(selected) == 30,
                scope="Selection preparation only; no relevance judgments generated")


def assign_sources(records, registry):
    """Run before opening any source content. Stronger than a manual split label."""
    if not registry:
        return records, [], False
    decisions = registry.get("assignments", {})
    blocked, admitted = [], []
    excluded_modules = set(registry.get("excluded_modules", [])) | {"sale_advance_payment"}
    reserved = set(registry.get("reserved_cases", []))
    for r in records:
        if r.get("case_id") in reserved or r.get("module") in excluded_modules or any(
                m in Path(r.get("prefix", "")).parts for m in excluded_modules):
            blocked.append(dict(id=r["id"], reason="reserved_or_inspected_case"))
            admitted.append({**r, "split": "evaluation_reference"})
            continue
        decision = decisions.get(r["id"], {})
        if decision.get("split") != r.get("split") or not decision.get("reason") or not decision.get("evidence"):
            raise ValueError(f"Unsubstantiated source assignment: {r['id']}")
        if r["kind"] in {"official_code", "official_documentation", "oca_guidance", "openupgrade_analysis"}:
            if r.get("captures"):
                from ..adquisition.provenance import validate_source_origin
                for capture in r["captures"]:
                    validate_source_origin(r["kind"], capture["url"])
            elif not decision.get("source_identity_evidence"):
                raise ValueError("A local general source needs explicit upstream identity evidence, not a construction label")
        if r["kind"] in {"oca_migration", "oca_fix"}:
            case = decision.get("case")
            cutoff = registry.get("cutoff", {})
            if not case or cutoff.get("status") != "confirmed":
                raise ValueError("OCA construction needs confirmed cutoff and six-criteria evidence")
            if r.get("case_id") != case.get("case_id"):
                raise ValueError("Source and assignment refer to different migration cases")
            if date(case["published_at"]) >= date(cutoff["date"]):
                raise ValueError("Construction migration is not earlier than the thesis cutoff")
            # Evaluate criteria without misusing the evaluation-side cutoff test.
            criteria_only = {**case, "published_at": cutoff["date"]}
            status, _ = eligible(criteria_only, cutoff["date"], excluded_modules)
            if status != "eligible":
                raise ValueError("Construction migration lacks verified selection criteria")
        admitted.append(r)
    return admitted, blocked, True


def freeze_protocol(spec, collection_revision, directory, selection=None):
    required = ("status", "limit", "depth", "seed_policy", "ranking", "P1_aggregation", "judgment_responsible", "cache_state", "repeats")
    missing = [key for key in required if key not in spec]
    if missing:
        raise ValueError("Protocol parameters missing: " + ", ".join(missing))
    if spec["status"] != "verified" or not 1 <= spec["limit"] <= 10 or spec["P1_aggregation"] != "macro_defined_queries":
        raise ValueError("Unsupported protocol status, limit or P1 aggregation")
    if not spec["judgment_responsible"]:
        raise ValueError("A real responsible reviewer must be provided, not generated")
    if not selection or not selection.get("complete"):
        raise ValueError("Independent evaluation needs a complete audited 30-case selection")
    selected = selection["selected"]
    if len({c["case_id"] for c in selected}) != 30 or any(
            len([c for c in selected if c["to_version"] == v]) != 10 for v in ("17.0", "18.0", "19.0")):
        raise ValueError("Frozen evaluation needs 30 distinct cases and ten per jump")
    for case in selected:
        if eligible(case, selection["cutoff"]["date"], set(selection.get("excluded_modules", [])))[0] != "eligible":
            raise ValueError("Frozen selection contains an unverified or excluded case")
    if set(spec.get("query_cases", [])) != {c["case_id"] for c in selected}:
        raise ValueError("Frozen queries must cover exactly the independent selected cases")
    payload = dict(parameters=spec, collection_revision=collection_revision, code_revision=code_revision(),
                   selection_revision=fingerprint(selection), selected_cases=sorted(spec["query_cases"]))
    payload["protocol_revision"] = fingerprint(payload)
    path = Path(directory)
    if path.exists():
        raise ValueError("Refusing to overwrite a frozen protocol")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
