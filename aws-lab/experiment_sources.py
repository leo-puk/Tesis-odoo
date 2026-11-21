"""Supplementary acquisition and BM25 over complete admitted source artifacts."""
import json
from pathlib import Path
import shutil
import sqlite3
import uuid
from time import perf_counter


def supplement(prepared, addons, origin, target, output, catalog_path=None):
    from r2.adquisition import capture_plan
    from r2.adquisition.planner import make_plan
    from r2.normalization.storage import build_normalized

    output = Path(output)
    output.mkdir()
    catalog_path = Path(catalog_path) if catalog_path else (
        Path(__file__).resolve().parent.parent / "sandbox/r2/reference/adquisition-final/examples/catalog.json")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    catalog["oca_addons"] = sorted(set(catalog["oca_addons"]) | {addon["name"] for addon in addons})
    entries, bindings, diagnostics, seen = [], {}, [], set()
    resolved = dict(catalog)
    for addon in addons:
        plan, policy, configuration, notes = make_plan(addon["path"], origin, target, catalog)
        resolved["allowed_urls"] = sorted(set(resolved["allowed_urls"]) | set(policy["allowed_urls"]))
        diagnostics.append(dict(addon=addon["name"], **notes))
        for entry in plan:
            url = next(iter(entry["files"].values()))
            # The scoped local diff is already captured. Keep broad version compares out.
            if url in seen or url.endswith(f"/odoo/odoo/compare/{origin}...{target}"):
                continue
            seen.add(url)
            source_id = f"supplement-{len(entries) + 1:04d}"
            bindings[source_id] = configuration["sources"][entry["id"]]
            entries.append({**entry, "id": source_id})
    for name, value in (("plan", entries), ("catalog", resolved), ("bindings", {"sources": bindings}),
                        ("planning", diagnostics)):
        (output / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    capture = capture_plan(output / "plan.json", output / "captures", catalog_path=output / "catalog.json")
    session = output / uuid.uuid4().hex
    session.mkdir()
    inventory, merged = [], {}
    for inventory_path, binding_path in ((Path(prepared["inventory"]), Path(prepared["bindings"])),
                                         (Path(capture["inventory"]), output / "bindings.json")):
        rows = json.loads(inventory_path.read_text(encoding="utf-8-sig"))
        config = json.loads(binding_path.read_text(encoding="utf-8-sig"))["sources"]
        for row in rows:
            uid = row["id"]
            if (session / uid).exists():
                raise ValueError("Duplicate acquisition unit while merging sessions")
            original = inventory_path.parent / uid
            if original.is_dir():
                shutil.copytree(original, session / uid)
            inventory.append(row)
            merged[uid] = config.get(uid, config.get(row.get("source_id"), {}))
    inventory_path, binding_path = session / "inventory.json", output / "merged-bindings.json"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    binding_path.write_text(json.dumps({"sources": merged}, ensure_ascii=False, indent=2), encoding="utf-8")
    database = output / "collection.sqlite"
    build = build_normalized(inventory_path, binding_path, database)
    return dict(database=str(database), inventory=str(inventory_path), bindings=str(binding_path),
                catalog=str(output / "catalog.json"),
                revisions=prepared["revisions"], build=build, capture=capture,
                acquisition_status={status: sum(row["status"] == status for row in inventory) for status in
                                    ("accepted", "failed", "excluded", "quarantined", "incomplete")})


class SourceBaseline:
    """One FTS5 document per complete stored artifact, without graph traversal."""
    def __init__(self, database, destination, origin, target):
        from r2.records import connect, load, meta
        from r2.normalization.terms import term_counts
        from r2.report import version_key
        self.destination = Path(destination)
        if self.destination.exists():
            raise ValueError("Choose a new source baseline index")
        self.origin, self.target = origin, target
        self.sources = {}
        with connect(database) as con:
            self.revision = meta(con)["collection_revision"]
            sources = {source["id"]: source for source in load(con, "sources")}
            artifacts = load(con, "artifacts")
        with sqlite3.connect(self.destination) as index:
            index.execute("CREATE VIRTUAL TABLE source_search USING fts5(source_id UNINDEXED,text)")
            for artifact in artifacts:
                source = sources[artifact["source_id"]]
                versions = [value for value in (source.get("from_version"), source.get("to_version")) if value]
                if (not versions or not all(version_key(origin) <= version_key(value) <= version_key(target) for value in versions)
                        or artifact.get("text") is None):
                    continue
                sid = source["id"]
                self.sources[sid] = dict(source_id=sid, artifact_id=artifact["id"], url=source["url"],
                    from_version=source.get("from_version"), to_version=source.get("to_version"),
                    artifact_sha256=artifact["artifact_sha256"], artifact_path=artifact["path"])
                index.execute("INSERT INTO source_search VALUES (?,?)", (sid, " ".join(term_counts(artifact["text"]).elements())))

    def search(self, module, module_name, limit=10, timings=None):
        from r2.crossing.code import read_code
        from r2.normalization.terms import term_counts
        code = read_code(module, module_name)
        terms = sorted(term_counts(" ".join(entity["name"] for entity in code["entities"])))
        rows = []
        started = perf_counter()
        if terms:
            expression = " OR ".join('"' + term + '"' for term in terms)
            with sqlite3.connect(self.destination.as_uri() + "?mode=ro", uri=True) as index:
                rows = index.execute("SELECT source_id,bm25(source_search) FROM source_search "
                                     "WHERE source_search MATCH ? ORDER BY 2,1", (expression,)).fetchall()
        if timings is not None:
            timings["bm25_sources_search_seconds"] = perf_counter() - started
        return dict(schema_version=1, engine="bm25_sources", collection_revision=self.revision,
            query=dict(module_name=module_name, input_revision=code["input_revision"], from_version=self.origin,
                       to_version=self.target, limit=limit),
            summary=dict(eligible_sources=len(self.sources), sources_found=len(rows), sources_shown=min(limit, len(rows))),
            results=[dict(**self.sources[sid], bm25_score=score) for sid, score in rows[:limit]])
