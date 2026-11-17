"""Read complete units; never download, execute or rewrite acquisition data."""
import hashlib
import json
import re
from pathlib import Path

KINDS = {"official_manifest", "official_documentation", "oca_guidance",
         "openupgrade_analysis", "github_diff", "github_pr"}
STATES = {"accepted", "excluded", "incomplete", "failed", "deleted"}


def read_session(inventory, bindings):
    inventory = Path(inventory).absolute()
    folder = inventory.parent
    if any(p.is_symlink() or p.is_junction() for p in [inventory, *inventory.parents]):
        raise ValueError("Session paths cannot contain symlinks or junctions")
    if not re.fullmatch(r"[a-f0-9]{32}", folder.name):
        raise ValueError("Expected an acquisition session directory")
    rows = json.loads(inventory.read_text(encoding="utf-8-sig"))
    config = json.loads(Path(bindings).read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or not isinstance(config, dict) or not isinstance(config.get("sources"), dict):
        raise ValueError("Expected acquisition inventory and bindings.sources mapping")
    seen, units, skipped = set(), [], []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Inventory entries must be objects")
        uid = row.get("id")
        if not isinstance(uid, str) or not re.fullmatch(r"[a-f0-9]{32}", uid) or uid in seen or row.get("status") not in STATES:
            raise ValueError("Invalid or duplicate acquisition unit/status")
        seen.add(uid)
        if row["status"] != "accepted":
            skipped.append(dict(id=uid, reason=row["status"]))
            continue
        if row.get("kind") not in KINDS or not row.get("captures") or not row.get("urls"):
            raise ValueError("Accepted units require a known kind, URLs and captures")
        binding = config["sources"].get(uid, config["sources"].get(row.get("source_id")))
        if not isinstance(binding, dict):
            raise ValueError(f"Missing processing binding for {row.get('source_id', uid)}")
        first, last = binding.get("from_version"), binding.get("to_version")
        versions = {"16.0", "17.0", "18.0", "19.0"}
        if first not in versions or last not in versions or first >= last:
            raise ValueError("Bindings require an increasing version pair within 16.0–19.0")
        if row["kind"] in {"github_diff", "github_pr"} and not all(binding.get(k) for k in ("from_revision", "to_revision")):
            raise ValueError("Diff bindings require explicit comparison references (not inferred immutable SHAs)")
        files = []
        if not isinstance(row.get("files"), list) or not row["files"]:
            raise ValueError("Accepted unit has no files")
        for name in row["files"]:
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != uid:
                raise ValueError("Unit file escapes its acquisition directory")
            path = folder / relative
            if any(p.is_symlink() or p.is_junction() for p in [path, *path.parents]):
                raise ValueError("Unit files cannot use links or junctions")
            if not path.resolve().is_relative_to((folder / uid).resolve()):
                raise ValueError("Unit file escapes its acquisition directory")
            raw = path.read_bytes()
            files.append(dict(path=relative.as_posix(), text=raw.decode("utf-8-sig"),
                              artifact_sha256=hashlib.sha256(raw).hexdigest(),
                              hash_scope="stored acquisition artifact; computed by ingestion, not original HTTP response"))
        units.append(dict(source={**row, "id": folder.name + ":" + uid,
                                  "unit_id": uid, "session_id": folder.name,
                                  "plan_source_id": row.get("source_id"),
                                  "binding": binding, "url": row["urls"][0],
                                  "from_version": first, "to_version": last,
                                  "from_revision": binding.get("from_revision", "not_recorded"),
                                  "to_revision": binding.get("to_revision", "not_recorded"),
                                  "reference_basis": "processing binding; immutable upstream revisions not asserted"},
                          files=files))
    # Keep complete artifacts in SQLite before any caller elects to delete temporaries.
    return units, skipped
