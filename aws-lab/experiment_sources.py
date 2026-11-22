"""Supplementary acquisition and BM25 over complete admitted source artifacts."""
import json
from pathlib import Path
import re
import shutil
import sqlite3
from subprocess import TimeoutExpired
import uuid
from time import perf_counter


DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / "sandbox/r2/reference/adquisition-final/examples/catalog.json"
AUXILIARY_REPOSITORIES = {
    "stock-logistics-warehouse": {"stock", "stock_account"},
    "sale-workflow": {"sale", "sale_management", "sale_stock", "purchase", "purchase_stock"},
    "product-variant": {"product", "purchase", "sale"},
    "server-tools": {"base", "mail", "contacts"},
}


def read_catalog(path):
    return json.loads(Path(path or DEFAULT_CATALOG).read_text(encoding="utf-8-sig"))


def scoped_oca_paths(paths, dependencies, models, excluded):
    modules = {path.split("/")[0] for path in paths if re.fullmatch(r"[a-z0-9_]+/__manifest__\.py", path)}
    selected = []
    for path in sorted(paths):
        parts = path.split("/")
        addon, filename = parts[0], Path(parts[-1])
        if (addon not in modules or addon in excluded or set(parts) & {"tests", "i18n", "demo"}
                or filename.suffix not in {".py", ".xml", ".csv"}):
            continue
        if addon in dependencies or filename.stem in models or (
                filename.suffix == ".xml" and re.sub(r"_(?:views?|templates?)$", "", filename.stem) in models):
            selected.append(path)
    return selected


def acquire_oca(sources, local, origin, target, output, reference_repos, catalog_path=None, *, reference_shas=()):
    """Capture immutable, path-filtered diffs from a separate set of OCA repositories."""
    from r2.adquisition.policy import Excluded, SourcePolicy
    from experimentos import digest, now, save

    catalog = read_catalog(catalog_path)
    catalog["reference_shas"] = sorted(set(reference_shas))
    catalog["exclude_pull_requests"] = True
    excluded_addons = set(catalog["oca_addons"])
    excluded_repos = {value.lower().removeprefix("oca/") for value in catalog["oca_repositories"]}
    excluded_repos.update(reference_repos)
    catalog["oca_repositories"] = sorted(set(catalog["oca_repositories"]) | {"OCA/" + name for name in reference_repos})
    scope = json.loads(Path(local["metadata"]).read_text(encoding="utf-8"))["scope"]
    excluded_addons.update(scope["selected_addons"])
    catalog["oca_addons"] = sorted(excluded_addons)
    policy = SourcePolicy(catalog)
    dependencies = set(scope["manifest_dependencies"])
    models = {value.replace(".", "_") for value in scope["technical_identifiers"]
              if re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", value)}
    session = output / uuid.uuid4().hex
    session.mkdir(parents=True)
    inventory, bindings, diagnostics = [], {}, []
    for repository, triggers in sorted(AUXILIARY_REPOSITORIES.items()):
        matched = sorted(triggers & (dependencies | set(scope["core_modules"])))
        if not matched:
            continue
        entry = dict(repository="OCA/" + repository, trigger_dependencies=matched)
        diagnostics.append(entry)
        if repository in excluded_repos:
            entry.update(status="excluded", reason="Evaluation/reference repository or policy exclusion")
            continue
        try:
            bare, first = sources.pin("OCA", repository, origin)
            _, last = sources.pin("OCA", repository, target)
            paths = {path for sha in (first, last) for path in
                     sources.git(bare, "ls-tree", "-r", "--name-only", sha).splitlines()}
            selected = scoped_oca_paths(paths, dependencies, models, excluded_addons)
            url = f"https://github.com/OCA/{repository}/compare/{first}..{last}"
            entry.update(from_revision=first, to_revision=last, url=url, pathspecs=selected)
            if not selected:
                entry.update(status="empty")
                continue
            if url in policy.excluded:
                raise Excluded("Comparison excluded by catalogue")
            policy.content(url)
            diff = sources.git(bare, "diff", "--no-ext-diff", "--no-textconv", "--no-color",
                               "--no-renames", "--unified=3", first, last, "--", *selected)
            if not diff:
                entry.update(status="empty")
                continue
            policy.content(diff)
        except Excluded as error:
            entry.update(status="excluded", reason=str(error))
            continue
        except (OSError, RuntimeError, ValueError, TimeoutExpired) as error:
            entry.update(status="failed", reason=str(error))
            continue
        uid = uuid.uuid4().hex
        relative = f"{uid}/comparison-relevant.diff"
        path = session / relative
        path.parent.mkdir()
        path.write_bytes((diff + "\n").encode("utf-8"))
        inventory.append(dict(id=uid, source_id=f"oca-{repository}", kind="github_diff", urls=[url],
            status="accepted", files=[relative], captures=[dict(url=url, method="scoped git diff", captured_at=now())]))
        bindings[uid] = dict(from_version=origin, to_version=target, from_revision=first, to_revision=last)
        entry.update(status="accepted", sha256=digest(path))
    save(session / "inventory.json", inventory)
    save(output / "bindings.json", {"sources": bindings})
    save(output / "planning.json", diagnostics)
    return dict(inventory=str(session / "inventory.json"), bindings=str(output / "bindings.json"),
                diagnostics=diagnostics, reference_repos=sorted(reference_repos),
                reference_shas=catalog["reference_shas"])


def supplement(prepared, addons, origin, target, output, catalog_path=None, *, auxiliary=None):
    from r2.adquisition import SourcePolicy, capture_plan
    from r2.adquisition.planner import make_plan
    from r2.adquisition.policy import Excluded
    from r2.normalization.storage import build_normalized

    output = Path(output)
    output.mkdir()
    catalog = read_catalog(catalog_path)
    catalog["exclude_pull_requests"] = True
    catalog["oca_addons"] = sorted(set(catalog["oca_addons"]) | {addon["name"] for addon in addons})
    if auxiliary:
        catalog["oca_repositories"] = sorted(set(catalog["oca_repositories"]) |
                                              {"OCA/" + name for name in auxiliary["reference_repos"]})
        catalog["reference_shas"] = auxiliary.get("reference_shas", [])
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
    inputs = [prepared, {**capture, "bindings": output / "bindings.json"}]
    if auxiliary:
        inputs.append(auxiliary)
    reference_policy = SourcePolicy(catalog) if catalog.get("reference_shas") else None
    for item in inputs:
        inventory_path, binding_path = Path(item["inventory"]), Path(item["bindings"])
        rows = json.loads(inventory_path.read_text(encoding="utf-8-sig"))
        config = json.loads(binding_path.read_text(encoding="utf-8-sig"))["sources"]
        for row in rows:
            uid = row["id"]
            if (session / uid).exists():
                raise ValueError("Duplicate acquisition unit while merging sessions")
            original = inventory_path.parent / uid
            if item is prepared and row["status"] == "accepted" and reference_policy:
                try:
                    for name in row["files"]:
                        with (inventory_path.parent / name).open(encoding="utf-8", errors="replace") as stream:
                            for line in stream:
                                reference_policy.reference_content(line)
                except Excluded as error:
                    inventory.append(dict(row, status="excluded", reason=str(error)))
                    continue
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
