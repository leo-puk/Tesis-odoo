"""Reconstruct text from immutable captured bytes; never overwrite an older snapshot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from r2.normalization import normalize


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inventory", type=Path); p.add_argument("output", type=Path)
    args = p.parse_args()
    base = args.inventory.resolve().parent
    out = args.output.resolve()
    if out.exists():
        raise ValueError("Choose a new extraction directory")
    rows = json.loads(args.inventory.read_text(encoding="utf-8-sig"))
    out.mkdir(parents=True)
    for record in rows:
        for side in ("before", "after"):
            record[f"{side}_dir"] = f"{record['id']}/{side}"
        for capture in record["captures"]:
            original = (base/capture["stored_file"]).resolve()
            raw = original.read_bytes()
            if hashlib.sha256(raw).hexdigest() != capture["response_sha256"]:
                raise ValueError("Raw capture does not match the original response hash")
            text = normalize(raw, capture["headers"].get("content-type", ""))
            dest = out/record["id"]/capture["side"]/capture["file_path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8", newline="\n")
            capture.update(stored_file=os.path.relpath(original,out).replace("\\","/"),
                           normalized_file=dest.relative_to(out).as_posix(),
                           normalized_sha256=hashlib.sha256(text.encode()).hexdigest(),
                           extraction="utf8-newlines-v2-no-trailing-trim/html-text-v1")
    (out/"inventory.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")


if __name__ == "__main__":
    main()
