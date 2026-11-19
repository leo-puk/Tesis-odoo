"""Semantic changes with many-to-many evidence and explicit review history."""
from copy import deepcopy
from ..selection import date
import hashlib
import json

STATES = {"candidate", "verified", "rejected", "unresolved"}
CATEGORIES = {"api_refactoring", "behavior", "syntax", "data", "security", "manifest",
              "format", "administrative", "documentation", "unclassified"}


def key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


def apply_reviews(candidates, annotations):
    evidence = {"ev-" + c["id"][4:]: {**deepcopy(c), "evidence_id": "ev-"+c["id"][4:]} for c in candidates.values()}
    changes = deepcopy(candidates)
    for c in changes.values():
        c.update(evidence_ids=["ev-"+c["id"][4:]], review_history=[], category="unclassified")
    originals = deepcopy(changes)
    for event in annotations:
        source_key = event.get("change_id")
        evidence_ids = event.get("evidence_ids") or (originals[source_key]["evidence_ids"] if source_key in originals else [])
        if not evidence_ids or not set(evidence_ids) <= set(evidence):
            raise ValueError("Review must cite existing, admitted evidence IDs")
        blocks = [evidence[i] for i in sorted(set(evidence_ids))]
        versions = {(b["from_version"], b["to_version"]) for b in blocks}
        if len(versions) != 1:
            raise ValueError("One semantic change cannot mix different version jumps")
        status = event.get("status")
        if status not in STATES:
            raise ValueError("Unknown review state")
        if not event.get("reviewer") or not event.get("rationale") or not event.get("reviewed_at"):
            raise ValueError("Review needs responsible reviewer, rationale and review date")
        date(event["reviewed_at"])
        elements = sorted({e for b in blocks for e in b["elements"]})
        affected = event.get("affected_elements", elements)
        if not isinstance(affected, list) or not affected or not set(affected) <= set(elements):
            raise ValueError("Affected elements must occur in concrete admitted evidence")
        required = event.get("required_elements", [])
        if not isinstance(required, list) or not all(isinstance(e, str) for e in required):
            raise ValueError("Conditions must contain element identifiers")
        category = event.get("category", "unclassified")
        if category not in CATEGORIES:
            raise ValueError("Unknown coding category")
        validity = event.get("destination_validity", {})
        general = event.get("general_applicability")
        if status == "verified":
            if not required and not (isinstance(general, dict) and general.get("justification")):
                raise ValueError("Verified change needs explicit conditions or justified general applicability")
            if (validity.get("status") != "checked" or
                (validity.get("from_version"), validity.get("to_version")) not in versions or
                not validity.get("explanation") or not validity.get("evidence_ids") or
                not set(validity["evidence_ids"]) <= set(evidence_ids)):
                raise ValueError("Verified change requires evidenced destination validity for its jump")
            if category == "unclassified":
                raise ValueError("Verified changes require a coding category")
        sid = event.get("semantic_id")
        target_id = "sem-"+key([sid, sorted(versions)]) if sid else source_key
        if not target_id:
            raise ValueError("Review requires change_id or semantic_id")
        change = deepcopy(changes.get(target_id, blocks[0]))
        history = change.get("review_history", []) + [deepcopy(event)]
        # The current primary citation follows the current evidence set; prior
        # citations remain in history, not incorrectly attached to the new text.
        for field in ("source_id", "comparison_id", "file_path", "source_layer", "from_version", "to_version",
                      "from_revision", "to_revision", "before_start", "before_end", "after_start", "after_end",
                      "before", "after", "removed", "added", "origin_kind", "matching_migration"):
            change[field] = blocks[0][field]
        change.update(id=target_id, status=status, title=event.get("title", change["title"]),
                      elements=elements, affected_elements=affected, required_elements=required,
                      evidence_ids=sorted(set(evidence_ids)), evidence_blocks=blocks,
                      reviewer=event["reviewer"], rationale=event["rationale"], category=category,
                      destination_validity=validity, general_applicability=general, review_history=history)
        if "layer" in event:
            if event["layer"] not in {"python", "xml", "data", "manifest", "documentation"}:
                raise ValueError("Unknown affected layer")
            change["layer"] = event["layer"]
        if event.get("group_id"):
            change["group_id"] = event["group_id"]
        changes[target_id] = change
        if sid:
            for original in changes.values():
                if original["id"].startswith("chg-") and set(original["evidence_ids"]) <= set(evidence_ids):
                    original["status"] = "rejected"
                    original["superseded_by_review"] = True
    groups = {}
    for c in list(changes.values()):
        if c.get("group_id"):
            groups.setdefault(c["group_id"], []).append(c)
    for group_id, members in sorted(groups.items()):
        if len({(c["from_version"], c["to_version"], c["title"], c["layer"], c["status"]) for c in members}) != 1 or members[0]["status"] != "verified":
            raise ValueError("Grouped reviewed blocks must share verified status, title, layer and jump")
        grouped = deepcopy(members[0])
        grouped.update(id="grp-"+key([group_id, sorted(c["id"] for c in members)]))
        for field in ("elements", "affected_elements", "required_elements", "evidence_ids"):
            grouped[field] = sorted({v for c in members for v in c[field]})
        grouped["evidence_blocks"] = [evidence[e] for e in grouped["evidence_ids"]]
        grouped["review_history"] = [ev for c in members for ev in c["review_history"]]
        for c in members:
            del changes[c["id"]]
        changes[grouped["id"]] = grouped
    return changes, evidence


def search_document(change):
    """Content-only whitelist, independent of administrative JSON and timing."""
    return "\n".join([change["title"], " ".join(change.get("affected_elements", change["elements"])),
                      *[b.get(field, "") for b in change.get("evidence_blocks", [change]) for field in ("removed", "added")]])
