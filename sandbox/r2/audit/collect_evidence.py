"""Read-only evidence collection; the Word is hashed, never opened for writing."""
import hashlib
import json
import subprocess
from pathlib import Path
import pandas as pd
from r2.collection import connect, load, meta
from r2.selection import code_revision


def main():
    root = Path(__file__).resolve().parents[1]
    audit = root/"audit"
    with connect(audit/"corpus-delivery.sqlite") as con:
        metadata = meta(con)
        sources, changes = load(con,"sources"),load(con,"changes")
        counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in
                  ("sources","comparisons","evidence","changes","elements","relations","change_evidence")}
    pd.DataFrame([dict(source_id=s["id"],kind=s["kind"],jump=s["from_version"]+"->"+s["to_version"],
                      captured_at=s.get("captured_at"),scope=s.get("scope"),license_status=s.get("license",{}).get("status"),
                      captured_files=len(s.get("captures",[]))) for s in sources]).to_csv(audit/"source-coverage.csv",index=False)
    pd.DataFrame([dict(id=c["id"],layer=c["layer"],state=c["status"],jump=c["from_version"]+"->"+c["to_version"]) for c in changes]).groupby(
        ["jump","layer","state"]).size().rename("count").reset_index().to_csv(audit/"collection-counts.csv",index=False)
    paths = sorted([*root.glob("r2/*.py"),*root.glob("tests/*.py"),root/"pyproject.toml",root/"requirements-lock.txt"])
    state = dict(git_base=subprocess.check_output(["git","-C",str(root.parents[1]),"rev-parse","HEAD"],text=True).strip(),
                 git_status=subprocess.check_output(["git","-C",str(root.parents[1]),"status","--short"],text=True).splitlines(),
                 code_revision=code_revision(), package_version="0.2.0", files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                 collection_revision=metadata["collection_revision"], collection_counts=counts,
                 note="No new Git commit: R2 remains untracked/modified; content hashes identify the delivered state.")
    word = root.parents[2]/"chatgpt tesis -v11 -12-11.docx"
    state["word_sha256_final"] = hashlib.sha256(word.read_bytes()).hexdigest().upper()
    initial=json.loads((audit/"initial-state.json").read_text(encoding="utf-8-sig"))
    state["word_unchanged"] = state["word_sha256_final"] == initial["word_sha256"]
    if not state["word_unchanged"]:
        raise ValueError("Word hash changed; stop and investigate")
    (audit/"final-state.json").write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:state[k] for k in ("code_revision","collection_revision","collection_counts","word_unchanged")},indent=2))


if __name__ == "__main__":
    main()
