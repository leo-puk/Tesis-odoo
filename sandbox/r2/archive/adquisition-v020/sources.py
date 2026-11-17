"""Collect the before/after general sources declared in a capture plan."""
import json
import time
from pathlib import Path
from .http import HttpCapture
from .provenance import save, sha, utcnow, validate_source_origin
from ..normalization import normalize


def capture_plan(plan_path, output):
    """Download only declared general sources; code for reserved cases is not fetched here."""
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8-sig"))
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Capture output must be a new or empty directory")
    output.mkdir(parents=True, exist_ok=True)
    client = HttpCapture(output / "captures")
    cache, inventory, failures = {}, [], []
    start = time.perf_counter()
    for entry in plan:
        if entry["kind"] not in {"official_code", "official_documentation", "oca_guidance", "openupgrade_analysis"}:
            raise ValueError("capture-plan accepts general sources only; case solutions require a reviewed assignment")
        record = {k: v for k, v in entry.items() if k not in {"before", "after"}}
        record.update(format="snapshot", split="construction", parent_ids=[], captures=[])
        try:
            for side in ("before", "after"):
                folder = output / entry["id"] / side
                folder.mkdir(parents=True, exist_ok=True)
                record[f"{side}_dir"] = str(folder.relative_to(output)).replace("\\", "/")
                for filename, url in entry[side].items():
                    validate_source_origin(entry["kind"], url)
                    relative = Path(filename)
                    if relative.is_absolute() or ".." in relative.parts:
                        raise ValueError("Invalid capture filename")
                    if url not in cache:
                        raw, capture = client.get(url)
                        normalized = normalize(raw, capture["headers"].get("content-type", ""))
                        cache[url] = (normalized, capture)
                    normalized, capture = cache[url]
                    dest = folder / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(normalized, encoding="utf-8", newline="\n")
                    record["captures"].append({**capture, "side": side, "file_path": relative.as_posix(),
                                               "normalized_sha256": sha(normalized.encode()),
                                               "normalized_file": str(dest), "extraction": "utf8-newlines-v2-no-trailing-trim/html-text-v1"})
            record["captured_at"] = max(c["captured_at"] for c in record["captures"])
            record.setdefault("license", {"status": "not_verified"})
            record["assignment"] = dict(rule="general_public_source_capture_v1", evidence_urls=sorted({c["url"] for c in record["captures"]}),
                                        reason="General framework/documentation source; not a case solution. Hidden-copy audit remains necessary.")
            inventory.append(record)
        except (ValueError, UnicodeError) as exc:
            failures.append(dict(id=entry["id"], reason=str(exc)))
    save(output/"inventory.json", inventory)
    save(output/"capture-report.json", dict(captured_at=utcnow(), sources_included=len(inventory),
         failures=failures, download_and_extraction_seconds=time.perf_counter()-start,
         scope="Progressive declared sources only; not a complete migration corpus"))
    return dict(inventory=str(output/"inventory.json"), included=len(inventory), failures=failures)
