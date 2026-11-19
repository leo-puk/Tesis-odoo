"""Plan reviewed Odoo migration sources from a local module tree."""
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from ..crossing.code import IGNORED, read_code
from .policy import Excluded, SourcePolicy
from .provenance import validate_source_origin

ODOO = "https://raw.githubusercontent.com/odoo/odoo"
DOCS = "https://raw.githubusercontent.com/odoo/documentation"
COMPARE = "https://github.com/odoo/odoo/compare"
GUIDE = "https://raw.githubusercontent.com/wiki/OCA/maintainer-tools"
ODOO_NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
URL = re.compile(r"""https://[^\s<>"'`\[\]{}]+""")
TEXT_EXTENSIONS = {".py", ".xml", ".csv", ".rst", ".md", ".txt", ".html",
                   ".json", ".toml", ".yml", ".yaml", ".cfg", ".ini"}
IGNORED_DIRS = IGNORED | {"temp_data", "build", "dist", ".tox", ".pytest_cache"}


def version_pairs(origin, destination):
    # Inputs: origin and destination Odoo major versions as major.0 strings.
    # Does: Expand an ascending interval into adjacent major migrations.
    # Output: Ordered version pairs for acquisition and normalization.
    if not all(isinstance(v, str) and re.fullmatch(r"[1-9][0-9]*\.0", v)
               for v in (origin, destination)):
        raise ValueError("Planner versions must use Odoo major.0 format")
    first, last = (int(v.split(".")[0]) for v in (origin, destination))
    if first >= last:
        raise ValueError("Destination version must follow origin")
    return [(f"{major}.0", f"{major + 1}.0") for major in range(first, last)]


def repository_links(directory):
    # Inputs: Local directory already validated by the code reader.
    # Does: Scan supported text files for URL references without following links.
    # Output: URL-to-file mapping and reading warnings.
    links, warnings = {}, []
    for folder, directories, filenames in os.walk(directory, followlinks=False):
        root = Path(folder)
        directories[:] = [name for name in sorted(directories)
                          if name not in IGNORED_DIRS and not name.startswith(".venv")
                          and not (root / name).is_symlink() and not (root / name).is_junction()]
        for name in sorted(filenames):
            path = root / name
            if path.suffix.lower() not in TEXT_EXTENSIONS or path.is_symlink() or path.is_junction():
                continue
            relative = path.relative_to(directory).as_posix()
            try:
                text = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                warnings.append(f"URL scan skipped {relative}: {type(exc).__name__}")
                continue
            for value in URL.findall(text):
                link = value.rstrip(".,;:!)")
                links.setdefault(link, set()).add(relative)
    return links, warnings


def input_scope(code):
    # Inputs: Static observations and file paths from the local code reader.
    # Does: Read manifests, qualified XML IDs and explicit Odoo addon imports.
    # Output: Local addons, upstream addon hints and explicitly imported paths.
    local = {Path(code["module_path"], item["path"]).parent.name for item in code["files"]
             if Path(item["path"]).name == "__manifest__.py"}
    dependencies, paths = set(), set()
    for entity in code["entities"]:
        name, kind = entity["name"], entity["type"]
        if kind == "module" and entity["rule"].startswith("manifest_") and ODOO_NAME.fullmatch(name):
            dependencies.add(name)
        if kind == "external_id" and "." in name:
            namespace = name.split(".", 1)[0]
            if ODOO_NAME.fullmatch(namespace):
                dependencies.add(namespace)
        match = re.fullmatch(r"odoo\.addons\.(\w+)((?:\.\w+)*)", name, re.ASCII)
        if kind == "module" and match and ODOO_NAME.fullmatch(match[1]):
            addon, suffix = match.groups()
            dependencies.add(addon)
            if suffix:
                paths.add((addon, suffix[1:].replace(".", "/") + ".py"))
    return local, dependencies - local, sorted((addon, path) for addon, path in paths if addon not in local)


def default_sources(pairs, dependencies, imports):
    # Inputs: Adjacent migrations and addon/path hints from the local code.
    # Does: Propose official comparisons, documentation, guides and code snapshots.
    # Output: Source tuples with version bindings, origin reason and addon scope.
    for origin, destination in pairs:
        yield ("github_diff", f"{COMPARE}/{origin}...{destination}",
               "official comparison", origin, destination, None)
        yield ("oca_guidance", f"{GUIDE}/Migration-to-version-{destination}.md",
               "OCA maintainer guide", origin, destination, None)
    versions = sorted({version for pair in pairs for version in pair})
    for version in versions:
        yield ("official_documentation", f"{DOCS}/{version}/content/developer/reference/backend/orm/changelog.rst",
               "official ORM changelog", None, version, None)
        core = "odoo/orm" if int(version.split(".")[0]) >= 19 else "odoo"
        for path in (f"{core}/fields.py", f"{core}/models.py", "odoo/addons/base/models/ir_ui_view.py"):
            yield ("official_code", f"{ODOO}/{version}/{path}", "core snapshot", None, version, None)
        for addon in sorted(dependencies):
            base = "odoo/addons" if addon == "base" else "addons"
            yield ("official_manifest", f"{ODOO}/{version}/{base}/{addon}/__manifest__.py",
                   "addon manifest candidate", None, version, addon)
        for addon, path in imports:
            base = "odoo/addons" if addon == "base" else "addons"
            yield ("official_code", f"{ODOO}/{version}/{base}/{addon}/{path}",
                   "explicit addon import candidate", None, version, addon)


def reviewed_source(url, versions):
    # Inputs: An approved URL and the versions covered by the plan.
    # Does: Identify its acquisition kind and infer only explicit version labels.
    # Output: A plan source tuple or None when unsupported or outside scope.
    parsed = urlsplit(url)
    path = unquote(parsed.path)
    compare = re.fullmatch(r"/(?:repos/)?odoo/odoo/compare/([\w.+-]+)\.\.\.([\w.+-]+)", path)
    if parsed.hostname in {"github.com", "api.github.com"} and compare:
        first, last = compare.groups()
        if any(re.fullmatch(r"\d+\.\d+", label) and label not in versions for label in (first, last)):
            return None
        bound = (first, last) if {first, last} <= versions and int(first[:-2]) < int(last[:-2]) else (None, None)
        return ("github_diff", url, "reviewed comparison", *bound, None)
    if parsed.hostname == "github.com" and re.fullmatch(r"/[\w.-]+/[\w.-]+/pull/[1-9][0-9]*", path):
        return ("github_pr", url, "reviewed pull request", None, None, None)
    for kind in ("official_code", "official_documentation", "oca_guidance", "openupgrade_analysis"):
        try:
            validate_source_origin(kind, url)
        except ValueError:
            continue
        label = re.search(r"(?:^|/|version-)([1-9][0-9]*\.0)(?:/|\.md$|$)", path)
        version = label[1] if label else None
        if version and version not in versions:
            return None
        first = f"{int(version.split('.')[0]) - 1}.0" if version and kind == "oca_guidance" else None
        if first not in versions:
            first = None
        if kind == "official_code" and path.endswith("/__manifest__.py"):
            kind = "official_manifest"
        return (kind, url, "reviewed source", first, version, None)
    return None


def make_plan(directory, origin, destination, catalog):
    # Inputs: Module or repository directory, version interval and policy catalog.
    # Does: Build a deterministic set of URLs and apply the admission policy.
    # Output: Acquisition plan, resolved catalog, bindings and planning diagnostics.
    pairs = version_pairs(origin, destination)
    SourcePolicy(catalog)
    overrides = catalog.get("source_bindings", {})
    if (not isinstance(overrides, dict) or not set(overrides) <= set(catalog["allowed_urls"])
            or any(not isinstance(binding, dict) for binding in overrides.values())):
        raise ValueError("source_bindings must map reviewed URLs to binding objects")
    root = Path(directory).absolute()
    if not root.is_dir():
        raise ValueError("Planner input must be a local module or repository directory")
    code = read_code(root)
    links, warnings = repository_links(root)
    local, dependencies, imports = input_scope(code)
    versions = {version for pair in pairs for version in pair}
    defaults = list(default_sources(pairs, dependencies, imports))
    candidates = {item[1]: item for item in defaults}
    for url in sorted(set(catalog["allowed_urls"]) - candidates.keys()):
        try:
            item = reviewed_source(url, versions)
        except ValueError:
            item = None
        if item:
            candidates[url] = item
    allowed = sorted(set(candidates) | set(catalog["allowed_urls"]))
    resolved = {**catalog, "allowed_urls": allowed}
    policy = SourcePolicy(resolved)
    plan, bindings, admitted, excluded = [], {}, [], []
    for url, (kind, _, reason, first, last, addon) in sorted(candidates.items()):
        try:
            policy.url(url)
            if kind not in {"github_pr", "github_diff"}:
                validate_source_origin("official_code" if kind == "official_manifest" else kind, url)
        except (Excluded, ValueError) as exc:
            excluded.append(dict(url=url, reason=str(exc)))
            continue
        override = overrides.get(url, {})
        if override:
            explicit = (override.get("from_version", first), override.get("to_version", last))
            if (any(v is not None and (not isinstance(v, str) or not re.fullmatch(r"[1-9][0-9]*\.0", v))
                    for v in explicit)
                    or (all(explicit) and int(explicit[0][:-2]) >= int(explicit[1][:-2]))
                    or any(known is not None and supplied != known for known, supplied in zip((first, last), explicit))):
                raise ValueError(f"Invalid version binding for reviewed source: {url}")
            if any(v is not None and v not in versions for v in explicit):
                continue
        source_id = f"source-{len(plan) + 1:03d}"
        filename = "comparison.diff" if kind == "github_diff" else (
            "pull.json" if kind == "github_pr" else Path(urlsplit(url).path).name)
        if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", filename):
            filename = "document.txt"
        plan.append(dict(id=source_id, kind=kind, files={filename: url}))
        bindings[source_id] = dict(from_version=first, to_version=last, **({"module": addon} if addon else {}))
        bindings[source_id].update(override)
        admitted.append(dict(id=source_id, url=url, kind=kind, reason=reason,
                             input_references=sorted(links.get(url, set()))))
    for first, last in pairs:
        diffs = {(entry["kind"], urlsplit(entry["url"]).path.removeprefix("/repos/").lstrip("/")) for entry in admitted
                 if entry["kind"] in {"github_diff", "github_pr"} and bindings[entry["id"]]["from_version"] == first
                 and bindings[entry["id"]]["to_version"] == last}
        count = len(diffs)
        if count < 2:
            warnings.append(f"{first} -> {last}: {count} version-bound diff/PR source(s); "
                            "candidate change coverage is limited to the planned change sources")
    if not dependencies:
        warnings.append("No external addon dependencies could be inferred from the input")
    if not code["files"]:
        warnings.append("No supported code files could be read from the input")
    ignored = sorted(set(links) - candidates.keys())
    diagnostics = dict(planned_url_count=len(plan), local_addons=sorted(local),
                       addon_candidates=sorted(dependencies), code_files=len(code["files"]),
                       code_errors=code["errors"], code_limitations=code["limitations"],
                       ignored_repo_url_count=len(ignored), policy_excluded=excluded,
                       sources=admitted, warnings=warnings, network_verified=False)
    return plan, resolved, {"sources": bindings}, diagnostics


def write_plan(directory, origin, destination, catalog_path, output):
    # Inputs: Local code, versions, a reviewed catalog file and a new destination.
    # Does: Generate and persist acquisition inputs plus the planning diagnostics.
    # Output: JSON paths, number of URLs planned and warning messages.
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8-sig"))
    files = make_plan(directory, origin, destination, catalog)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    paths = {}
    for name, value in zip(("plan", "catalog", "bindings", "planning"), files):
        path = output / f"{name}.json"
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths[name] = str(path)
    return {**paths, "planned_url_count": files[-1]["planned_url_count"],
            "warnings": files[-1]["warnings"]}
