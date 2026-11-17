"""Selection-only PR dossiers. Never reads patches, imports code or marks criteria passed."""
import argparse
import copy
import json
from pathlib import Path
from r2.evaluation_sources import GitHubMetadata
from r2.evaluation_sources.provenance import save
from r2.selection import CRITERIA, sample_cases


def packet(candidate, metadata):
    if candidate["case_id"] != metadata["case_id"]:
        raise ValueError("Candidate and metadata refer to different PRs")
    result = copy.deepcopy(candidate)
    pr = metadata["pull"]
    manifests = sorted({f["filename"].rsplit("/", 1)[0] for f in metadata["files"]
                        if f["filename"].endswith("/__manifest__.py")})
    modules = [p.split("/")[-1] for p in manifests]
    if not result.get("module") and len(modules) == 1:
        result["module"] = modules[0]
        result["module_identity_basis"] = "one changed manifest path; not proof of migration eligibility"
    result["author"] = pr["author"]
    latest = {}
    for review in sorted(metadata["reviews"], key=lambda r: (r.get("submitted_at") or "", r["id"])):
        if review["state"] != "COMMENTED":
            latest[review["reviewer"]] = review
    approvals = [r for r in latest.values() if r["state"] == "APPROVED" and
                 r["reviewer"] != pr["author"] and r.get("commit_id") == pr["head"]["sha"]]
    result["metadata_observations"] = dict(
        merged=bool(pr["merged_at"]), base_ref=pr["base"]["ref"], head_sha=pr["head"]["sha"],
        merge_commit_sha=pr["merge_commit_sha"], changed_manifest_paths=manifests,
        test_paths=[f["filename"] for f in metadata["files"] if "/tests/" in f["filename"]],
        independent_head_approvals=approvals,
        caveats=["An approval does not establish maintainer identity",
                 "A changed test path does not establish executable passing tests",
                 "The manifest path does not prove consecutive source version",
                 "No dependency-installability or post-migration-FIX verdict was generated"])
    result["metadata_evidence"] = {k: metadata[k] for k in ("extracted_at", "captures")}
    for name in CRITERIA:
        result.setdefault("criteria", {}).setdefault(name, dict(status="pending", evidence=None, reviewer=None))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("specification", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--per-stratum", type=int, default=1)
    args = p.parse_args()
    if not 1 <= args.per_stratum <= 10:
        raise ValueError("Use 1â€“10 candidates per stratum to bound API usage")
    spec = json.loads(args.specification.read_text(encoding="utf-8-sig"))
    order = sample_cases(spec)["orders"]
    cases = {c["case_id"]: c for c in spec["candidates"]}
    args.output.mkdir(parents=True, exist_ok=True)
    outcomes = []
    blocked = None
    for stratum, ids in order.items():
        for index, case_id in enumerate(ids[:args.per_stratum]):
            case = cases[case_id]
            folder = args.output / stratum / str(index+1)
            folder.mkdir(parents=True, exist_ok=True)
            raw_path = folder/"metadata.json"
            if raw_path.exists():
                metadata = json.loads(raw_path.read_text(encoding="utf-8"))
            else:
                try:
                    if blocked:
                        raise ValueError("Not requested after an API access/rate-limit failure")
                    metadata = GitHubMetadata(folder/"http").pull(case["repository"], case["number"])
                    save(raw_path, metadata)
                except ValueError as exc:
                    blocked = str(exc)
                    save(folder/"review-packet.json", {**case,"metadata_blocked":blocked})
                    (folder/"REVIEW.md").write_text(f"# Pending review {case_id}\n\nMetadata access blocked: {blocked}\n\nNo criterion has been approved automatically. Re-run the same command after access is available.\n",encoding="utf-8")
                    outcomes.append(dict(case_id=case_id,stratum=stratum,blocked=blocked,criteria_passed_automatically=0))
                    continue
            reviewed = packet(case, metadata)
            save(folder/"review-packet.json", reviewed)
            cases[case_id] = reviewed
            lines = [f"# Review packet {case_id}", "", f"Stratum: {stratum}",
                     "", "Observations are not acceptance decisions.", "",
                     "| Criterion | State | Evidence and responsible reviewer |",
                     "|---|---|---|"]
            lines += [f"| {name} | {reviewed['criteria'][name]['status']} | Pending human evidence/reviewer |" for name in CRITERIA]
            lines += ["", "See review-packet.json and metadata.json for head SHA, approvals, paths and capture provenance.",
                      "No patch or solution is included, and these files are not an R2 source inventory."]
            (folder/"REVIEW.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
            outcomes.append(dict(case_id=case_id, stratum=stratum, packet=str(folder/"review-packet.json"),
                                 criteria_passed_automatically=0))
    spec["candidates"] = [cases[c["case_id"]] for c in spec["candidates"]]
    save(args.output/"selection-input-enriched.json", spec)
    save(args.output/"selection-status.json", sample_cases(spec))
    save(args.output/"summary.json", dict(packets=outcomes, scope="partial frame and selection metadata only; no evaluation results"))
    print(json.dumps(outcomes, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
