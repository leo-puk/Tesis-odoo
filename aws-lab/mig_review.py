"""Suggest auditable links between archived MIG/FIX hunks and retrieved evidence."""
from collections import defaultdict
import json
import re


IDENTIFIER = re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\b", re.ASCII)


def identifiers(text):
    return {name for name in IDENTIFIER.findall(text) if "." in name or "_" in name.strip("_")}


def suggest_links(database, folder, reference_dir, commits, origin, target):
    from r2.evaluation.normalized import evidence_matches_transition
    from r2.normalization.diff import parse_diff
    from r2.records import connect

    def results(engine):
        return json.loads((folder / engine / "report.json").read_text(encoding="utf-8"))["results"]

    retrieved_units = defaultdict(list)
    retrieved_sources = defaultdict(list)
    for engine in ("graph", "bm25"):
        for row in results(engine):
            retrieved_units[row["source"]["unit_id"]].append({"engine": engine, "change_id": row["change_id"]})
            if engine == "graph":
                source = row["source"]["source_id"]
                if "graph_sources" not in retrieved_sources[source]:
                    retrieved_sources[source].append("graph_sources")
    if (folder / "bm25_sources" / "report.json").exists():
        for row in results("bm25_sources"):
            retrieved_sources[row["source_id"]].append("bm25_sources")

    hunks, warnings = [], []
    for commit in commits:
        sha = commit["sha"]
        patch = (reference_dir / commit.get("patch_file", f"{sha}.diff")).read_text(encoding="utf-8")
        try:
            parsed, notes = parse_diff(patch)
        except ValueError as error:
            warnings.append({"commit": sha, "detail": str(error)})
            continue
        warnings.extend({"commit": sha, "detail": note} for note in notes)
        for hunk in parsed:
            tokens = sorted(identifiers(hunk["removed"] + "\n" + hunk["added"]))
            hunks.append(dict(id=f"{sha}:{hunk['artifact_start']}", commit=sha,
                repository=commit.get("repository"), url=commit.get("url"), file=hunk["file_path"],
                patch_line=hunk["artifact_start"], identifiers=tokens, available_unit_candidates=[],
                retrieved_unit_candidates=[], retrieved_source_candidates=[]))

    by_token = defaultdict(list)
    for hunk in hunks:
        for token in hunk["identifiers"]:
            by_token[token].append(hunk)

    def matching_hunks(text):
        matches = defaultdict(list)
        for token in sorted(identifiers(text) & by_token.keys()):
            for hunk in by_token[token]:
                matches[hunk["id"]].append(token)
        return matches

    by_id = {hunk["id"]: hunk for hunk in hunks}
    if by_token:
        with connect(database) as connection:
            for unit_payload, content in connection.execute(
                    "SELECT u.payload,c.payload FROM information_units u JOIN unit_content c ON u.id=c.unit_id ORDER BY u.id"):
                unit = json.loads(unit_payload)
                uid = unit["id"]
                applicable = evidence_matches_transition(unit, origin, target)
                if not (applicable or uid in retrieved_units):
                    continue
                for hunk_id, tokens in matching_hunks(json.loads(content).get("text") or "").items():
                    entry = dict(unit_id=uid, identifiers=tokens, source_id=unit["source_id"])
                    hunk = by_id[hunk_id]
                    if applicable and unit.get("source_url"):
                        hunk["available_unit_candidates"].append(entry)
                    for result in retrieved_units.get(uid, []):
                        hunk["retrieved_unit_candidates"].append({**entry, **result})
            for (payload,) in connection.execute("SELECT payload FROM artifacts ORDER BY id"):
                artifact = json.loads(payload)
                source = artifact["source_id"]
                if source in retrieved_sources:
                    for hunk_id, tokens in matching_hunks(artifact.get("text") or "").items():
                        by_id[hunk_id]["retrieved_source_candidates"].append(
                            dict(source_id=source, engines=retrieved_sources[source], identifiers=tokens))

    return dict(status="pending_review", method="Exact shared qualified or underscore-separated identifiers",
                candidate_commits=len(commits), hunks=hunks, warnings=warnings)
