"""Convert units into diff-backed candidates and separate contextual documents."""
import json
import textwrap
from ..extract import extract, layer_for
from ..selection import fingerprint
from .diff import parse_diff
from .anchors import partial_anchors


def convert_units(units):
    sources, elements, relations, changes, artifacts, documents, warnings = [], {}, {}, {}, {}, {}, []
    for unit in units:
        source = unit["source"]
        sources.append(source)
        for artifact in unit["files"]:
            aid = "artifact-" + fingerprint([source["id"], artifact["path"], artifact["artifact_sha256"]])[:24]
            artifacts[aid] = dict(id=aid, source_id=source["id"], **artifact)
            text = artifact["text"]
            if source["kind"] == "github_pr":
                payload = json.loads(text)
                if not isinstance(payload, dict) or not isinstance(payload.get("diff"), str):
                    raise ValueError("PR artifact requires a diff string")
                text = payload["diff"]
            if source["kind"] not in {"github_diff", "github_pr"}:
                documents[aid] = dict(id=aid, source_id=source["id"], artifact_id=aid,
                                      kind=source["kind"], text=text, role="context_only")
                if source["kind"] == "official_manifest":
                    data = extract(text, "__manifest__.py", source["binding"].get("module"))
                    for item in data["elements"]:
                        row = {**item, "version": source["to_version"], "side": "after", "source_id": source["id"], "artifact_id": aid}
                        elements[fingerprint(row)] = row
                    warnings.extend(data["warnings"])
                continue
            hunks, notes = parse_diff(text)
            warnings.extend(notes)
            if hunks:
                warnings.append("Partial diff hunks do not reconstruct complete files or guarantee complete AST relationships")
            for hunk in hunks:
                keys = set()
                # AST fragments and explicit local token patterns supply anchors.
                # No padding, full-file reconstruction or cross-hunk AST is invented.
                for side, code in (("before", hunk["before"]), ("after", hunk["after"])):
                    path = hunk["old_path"] if side == "before" else hunk["new_path"]
                    if path is None:
                        continue
                    data = extract(textwrap.dedent(code), path, source["binding"].get("module"))
                    data["elements"].extend(partial_anchors(code, path, source["binding"].get("module")))
                    offset = hunk["before_start"] if side == "before" else hunk["after_start"]
                    for item in data["elements"]:
                        row = {**item, "line": item["line"] + offset - 1, "end_line": item["end_line"] + offset - 1,
                               "version": source["from_version"] if side == "before" else source["to_version"],
                               "side": side, "source_id": source["id"], "artifact_id": aid, "scope": "hunk_only"}
                        elements[fingerprint(row)] = row
                        keys.add(item["key"])
                    for item in data["relations"]:
                        row = {**item, "line": item["line"] + offset - 1,
                               "version": source["from_version"] if side == "before" else source["to_version"],
                               "source_id": source["id"], "artifact_id": aid, "scope": "hunk_only"}
                        relations[fingerprint(row)] = row
                    warnings.extend(f"{source['plan_source_id']} {path}: {w}" for w in data["warnings"])
                if not any(line.startswith(("+", "-")) for line in hunk["diff_body"].splitlines()):
                    continue
                change = dict(**hunk, source_id=source["id"], artifact_id=aid,
                              layer=layer_for(hunk["file_path"]), source_layer=layer_for(hunk["file_path"]),
                              from_version=source["from_version"], to_version=source["to_version"],
                              from_revision=source["from_revision"], to_revision=source["to_revision"],
                              comparison_id="cmp-" + fingerprint([source["id"], source["from_revision"], source["to_revision"]])[:24],
                              elements=sorted(keys), required_elements=[], status="candidate",
                              classification="observed_diff_hunk", origin_kind=source["kind"], matching_migration=None,
                              title=f"Observed diff in {hunk['file_path']}", evidence_scope="partial_source_hunk")
                change["id"] = "chg-" + fingerprint(change)[:24]
                changes[change["id"]] = change
    # Context is linked explicitly by acquisition unit ID or plan source ID, never by textual similarity.
    lookup = {s[k]: s["id"] for s in sources for k in ("unit_id", "plan_source_id")}
    for source in sources:
        linked = source["binding"].get("context_units", [])
        if not isinstance(linked, list) or any(k not in lookup for k in linked):
            raise ValueError("context_units must identify accepted units in this session")
        context_ids = {lookup[k] for k in linked}
        if any(s["kind"] in {"github_diff", "github_pr"} for s in sources if s["id"] in context_ids):
            raise ValueError("context_units must reference contextual documents, not other diffs")
        source["context_document_ids"] = sorted(k for k,v in documents.items() if v["source_id"] in context_ids)
    return dict(sources=sources, elements=elements, relations=relations, changes=changes,
                artifacts=artifacts, documents=documents, warnings=warnings)
