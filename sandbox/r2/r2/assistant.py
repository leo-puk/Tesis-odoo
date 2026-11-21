"""Interactive R2.2 front end for local Odoo checkouts and addon selection."""
from __future__ import annotations

import ast
import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from .adquisition.provenance import utcnow
from .normalization.storage import build_normalized
from .report import render_report, search_units
from .crossing import save_result
from .relations import save_graph
from .crossing.code import read_code


DEFAULT_CONFIG = Path.home() / ".r2" / "config.json"
IGNORED = {".git", ".venv", "node_modules", "temp_data", "build", "dist", "__pycache__"}


def _git(repo, *arguments, check=True):
    # Inputs: A repository and Git arguments.
    # Does: Execute Git without invoking a shell.
    # Output: Standard output text, or an empty string for commands without output.
    process = subprocess.run(
        ["git", "-C", os.fspath(repo), *arguments], capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
    )
    if check and process.returncode:
        raise ValueError(process.stderr.strip() or "Git command failed")
    return process.stdout


def is_odoo_checkout(path):
    # Inputs: A candidate directory.
    # Does: Check for an Odoo source checkout and Git metadata.
    # Output: True when the directory can provide local version diffs.
    path = Path(path)
    return path.is_dir() and (path / "odoo-bin").is_file() and _git(path, "rev-parse", "--git-dir", check=False).strip() != ""


def detect_odoo_checkout(start):
    # Inputs: The directory from which discovery starts.
    # Does: Inspect the directory, its parents and nearby children for Odoo.
    # Output: The first deterministic matching checkout, or None.
    start = Path(start).absolute()
    for candidate in (start, *start.parents):
        if is_odoo_checkout(candidate):
            return candidate.resolve()
    if start.is_dir():
        for candidate in sorted(start.iterdir(), key=lambda item: item.name.lower()):
            if candidate.is_dir() and candidate.name not in IGNORED and is_odoo_checkout(candidate):
                return candidate.resolve()
    return None


def discover_addons(root):
    # Inputs: A directory containing one addon or several addon repositories.
    # Does: Find technical addons by their __manifest__.py without importing code.
    # Output: Sorted records containing technical name and absolute path.
    root = Path(root).absolute()
    if not root.is_dir():
        raise ValueError("The addons directory does not exist")
    found = []
    for folder, directories, files in os.walk(root, followlinks=False):
        current = Path(folder)
        directories[:] = [name for name in sorted(directories)
                          if name not in IGNORED and not name.startswith(".venv")]
        if "__manifest__.py" in files:
            found.append(dict(name=current.name, path=str(current.resolve())))
            directories[:] = []
    return sorted(found, key=lambda item: (item["name"].lower(), item["path"].lower()))


def select_addons(addons, selection):
    # Inputs: Discovered addons and a comma-separated selection of names, indexes or ranges.
    # Does: Resolve a human selection while rejecting ambiguous or invalid choices.
    # Output: Selected addon records in display order.
    value = selection.strip()
    if value.lower() in {"all", "todos", "*"}:
        return list(addons)
    selected = set()
    by_name = {item["name"]: index for index, item in enumerate(addons)}
    for token in (part.strip() for part in value.split(",")):
        if token in by_name:
            selected.add(by_name[token])
        elif re.fullmatch(r"[1-9][0-9]*", token):
            selected.add(int(token) - 1)
        elif re.fullmatch(r"[1-9][0-9]*-[1-9][0-9]*", token):
            first, last = map(int, token.split("-"))
            selected.update(range(first - 1, last))
        else:
            raise ValueError(f"Unknown addon selection: {token}")
    if not selected or min(selected) < 0 or max(selected) >= len(addons):
        raise ValueError("Addon selection is empty or outside the displayed list")
    return [item for index, item in enumerate(addons) if index in selected]


def resolve_version_ref(repo, version):
    # Inputs: An Odoo repository and a major version label.
    # Does: Resolve a local branch, tag or remote-tracking branch without network access.
    # Output: A verified Git revision name.
    for candidate in (version, f"origin/{version}", f"refs/heads/{version}",
                      f"refs/remotes/origin/{version}", f"refs/tags/{version}"):
        process = subprocess.run(
            ["git", "-C", os.fspath(repo), "rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
        )
        if process.returncode == 0:
            return candidate
    raise ValueError(f"Odoo version {version} is not available locally")


def available_versions(repo):
    # Inputs: A local Odoo Git checkout.
    # Does: Inspect local, tag and remote-tracking refs for Odoo major branches.
    # Output: Numerically sorted major.0 labels available without a network request.
    refs = _git(repo, "for-each-ref", "--format=%(refname:short)",
                "refs/heads", "refs/remotes", "refs/tags")
    versions = set()
    for ref in refs.splitlines():
        match = re.search(r"(?:^|/)([1-9][0-9]*\.0)$", ref.strip())
        if match:
            versions.add(match.group(1))
    return sorted(versions, key=lambda value: int(value.split(".")[0]))


def local_diff(repo, origin, destination):
    # Inputs: A local Odoo checkout and origin/destination version labels.
    # Does: Resolve both revisions and produce the complete unified Git diff locally.
    # Output: Diff text and immutable revision metadata.
    first = resolve_version_ref(repo, origin)
    last = resolve_version_ref(repo, destination)
    first_sha = _git(repo, "rev-parse", f"{first}^{{commit}}").strip()
    last_sha = _git(repo, "rev-parse", f"{last}^{{commit}}").strip()
    text = _git(repo, "diff", "--no-ext-diff", "--no-textconv", "--no-color", "--unified=3", f"{first_sha}..{last_sha}")
    return text, dict(from_ref=first, to_ref=last, from_revision=first_sha, to_revision=last_sha)


def _manifest_dependencies(path):
    # Read literal addon dependencies without importing partner code.
    try:
        value = ast.literal_eval((Path(path) / "__manifest__.py").read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        raise ValueError(f"Cannot read literal addon manifest: {path}") from exc
    dependencies = value.get("depends", []) if isinstance(value, dict) else None
    if not isinstance(dependencies, (list, tuple)) or not all(
        isinstance(item, str) and item for item in dependencies
    ):
        raise ValueError(f"Addon manifest has invalid dependencies: {path}")
    return dependencies


def _core_addon_paths(repo, revisions):
    # Find addon roots in both revisions because modules may move between versions.
    paths = {}
    pattern = re.compile(r"^(addons|odoo/addons)/([^/]+)/__manifest__\.py$")
    for revision in revisions:
        for name in _git(repo, "ls-tree", "-r", "--name-only", revision).splitlines():
            match = pattern.fullmatch(name)
            if match:
                paths.setdefault(match.group(2), set()).add(name.rsplit("/", 1)[0])
    return paths


def relevant_diff_scope(repo, addons, revisions):
    # Resolve partner dependencies and technical identifiers before generating the Git diff.
    selected = {addon["name"]: Path(addon["path"]).resolve() for addon in addons}
    available = dict(selected)
    for parent in sorted({path.parent for path in selected.values()}, key=os.fspath):
        available.update({item["name"]: Path(item["path"]) for item in discover_addons(parent)})
    partner = {}
    pending = list(selected)
    dependencies = set()
    while pending:
        name = pending.pop(0)
        if name in partner:
            continue
        path = available[name]
        partner[name] = path
        for dependency in _manifest_dependencies(path):
            dependencies.add(dependency)
            if dependency in available and dependency not in partner:
                pending.append(dependency)

    core = _core_addon_paths(repo, (revisions["from_revision"], revisions["to_revision"]))
    core_modules = set(dependencies) & core.keys()
    identifiers = set()
    observations = {}
    for name, path in sorted(partner.items()):
        code = read_code(path, name)
        observations[name] = dict(files=len(code["files"]), entities=len(code["entities"]),
                                  errors=code["errors"], limitations=code["limitations"])
        for entity in code["entities"]:
            value = entity.get("name")
            if isinstance(value, str) and "." in value and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", value):
                identifiers.add(value)
                namespace = value.split(".", 1)[0]
                if namespace in core:
                    core_modules.add(namespace)

    addon_roots = {path for module in core_modules for path in core[module]}
    pathspecs = set(addon_roots)
    pathspecs.update({"odoo/api.py", "odoo/fields.py", "odoo/models.py",
                      "odoo/exceptions.py"})
    framework_components = {"api", "exceptions", "fields", "http", "models", "osv", "tools"}
    for identifier in identifiers:
        if identifier.startswith("odoo."):
            component = identifier.split(".", 2)[1]
            if component in framework_components:
                pathspecs.update({f"odoo/{component}.py", f"odoo/{component}"})
    changed = set(_git(repo, "diff", "--name-only",
                       f"{revisions['from_revision']}..{revisions['to_revision']}").splitlines())
    pathspecs.update({":(exclude)**/i18n/**", ":(exclude)**/tests/**",
                      ":(exclude)**/demo/**", ":(exclude)**/static/description/**"})
    if not pathspecs:
        raise ValueError("The selected addons did not resolve to relevant Odoo paths")
    return dict(selected_addons=sorted(selected), partner_addons=sorted(partner),
                manifest_dependencies=sorted(dependencies), core_modules=sorted(core_modules),
                technical_identifiers=sorted(identifiers), observations=observations,
                pathspecs=sorted(pathspecs), changed_files_in_full_diff=len(changed))


def write_relevant_local_diff(repo, addons, origin, destination, session):
    # Search the addons first, then stream one path-filtered Git diff to disk.
    first = resolve_version_ref(repo, origin)
    last = resolve_version_ref(repo, destination)
    first_sha = _git(repo, "rev-parse", f"{first}^{{commit}}").strip()
    last_sha = _git(repo, "rev-parse", f"{last}^{{commit}}").strip()
    revisions = dict(from_ref=first, to_ref=last, from_revision=first_sha, to_revision=last_sha)
    scope = relevant_diff_scope(repo, addons, revisions)
    command = ["git", "-C", os.fspath(repo), "diff", "--no-ext-diff", "--no-textconv",
               "--no-color", "--unified=3", f"{first_sha}..{last_sha}", "--", *scope["pathspecs"]]
    unit = session / uuid4().hex
    unit.mkdir()
    path = unit / "comparison-relevant.diff"
    digest = hashlib.sha256()
    with path.open("xb") as stream:
        process = subprocess.run(command, stdout=stream, stderr=subprocess.PIPE,
                                 env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"})
    if process.returncode:
        raise ValueError(process.stderr.decode("utf-8", errors="replace").strip() or "Git diff failed")
    if path.stat().st_size == 0:
        raise ValueError("The relevant Odoo paths have no changes between the selected revisions")
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    scope["changed_files_in_relevant_diff"] = len(_git(
        repo, "diff", "--name-only", f"{first_sha}..{last_sha}", "--", *scope["pathspecs"]
    ).splitlines())
    return dict(path=str(path), bytes=path.stat().st_size), revisions, digest.hexdigest(), scope


def prepare_local_source(repo, addons, origin, destination, output):
    # Inputs: Local Odoo versions and a new analysis output directory.
    # Does: Materialize a provenance-bearing local diff and acquisition inventory.
    # Output: Inventory, bindings, metadata and immutable source revisions.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    session = output / "temp_data" / uuid4().hex
    session.mkdir(parents=True)
    part, revisions, diff_sha256, scope = write_relevant_local_diff(
        repo, addons, origin, destination, session)
    source_url = f"local-git:{Path(repo).resolve().as_posix()}#{revisions['from_revision']}..{revisions['to_revision']}"
    captured = utcnow()
    path = Path(part["path"])
    relative = path.relative_to(session).as_posix()
    source_id = "local-odoo-relevant-diff"
    inventory = [dict(
        id=path.parent.name, source_id=source_id, kind="github_diff", urls=[source_url],
        status="accepted", files=[relative], captures=[dict(url=source_url, status=200, captured_at=captured)],
        file_metadata=[dict(path=relative, representation="original_bytes", decode_state="decoded",
                            screening_encoding="utf-8", text_conversion="not_performed",
                            content_type="text/x-diff", url=source_url)],
        storage_form="original", created_at=captured, captured_at=captured,
    )]
    bindings = {source_id: dict(from_version=origin, to_version=destination,
                                from_revision=revisions["from_revision"],
                                to_revision=revisions["to_revision"],
                                migration_id=f"local-odoo-{origin}-{destination}")}
    inventory_path = session / "inventory.json"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    bindings_path = output / "bindings.json"
    bindings_path.write_text(json.dumps({"sources": bindings}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metadata_path = output / "local-source.json"
    metadata_path.write_text(json.dumps({"repository": str(Path(repo).resolve()), **revisions,
                                         "diff_bytes": part["bytes"], "diff_sha256": diff_sha256,
                                         "diff_file": part, "scope": scope},
                                        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dict(inventory=str(inventory_path), bindings=str(bindings_path),
                metadata=str(metadata_path), revisions=revisions)


def prepare_local_collection(repo, addons, origin, destination, output):
    prepared = prepare_local_source(repo, addons, origin, destination, output)
    database = Path(output) / "collection.sqlite"
    build = build_normalized(prepared["inventory"], prepared["bindings"], database)
    return dict(**prepared, database=str(database), build=build)


def _save_report(folder, result):
    # Inputs: An addon output directory and the normal report tuple.
    # Does: Persist the R2 report and its crossing/relations evidence.
    # Output: Paths to the saved report files.
    report, crossing, graph = result
    folder.mkdir(parents=True, exist_ok=False)
    if crossing is not None:
        save_result(crossing, folder / "crossing.json")
    if graph is not None:
        save_graph(graph, folder / "relations.json")
    (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "report.txt").write_text(render_report(report) + "\n", encoding="utf-8")
    return dict(report=str(folder / "report.json"), text=str(folder / "report.txt"))


def run_local_analysis(repo, addons, origin, destination, output, *, layer="all", maximum_hops=3, limit=10):
    # Inputs: Local Odoo checkout, selected addons, versions and query settings.
    # Does: Build one local diff collection and query it for every selected addon.
    # Output: Collection metadata and a concise result for each addon.
    prepared = prepare_local_collection(repo, addons, origin, destination, output)
    results = []
    for addon in addons:
        result = search_units(prepared["database"], addon["path"], origin, destination,
                              layer=layer, maximum_hops=maximum_hops, limit=limit,
                              module_name=addon["name"])
        paths = _save_report(Path(output) / "addons" / addon["name"], result)
        results.append(dict(addon=addon["name"], path=addon["path"],
                            summary=result[0]["summary"], warnings=result[0]["warnings"], **paths))
    summary = dict(repository=str(Path(repo).resolve()), from_version=origin, to_version=destination,
                   collection=prepared, addons=results)
    (Path(output) / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8")
    return summary


def load_config(path=DEFAULT_CONFIG):
    # Inputs: Optional configuration path.
    # Does: Load a previous assistant session when available.
    # Output: A configuration dictionary.
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}


def save_config(config, path=DEFAULT_CONFIG):
    # Inputs: Assistant settings and destination path.
    # Does: Persist reusable paths and versions without analysis results.
    # Output: The saved configuration path.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def start(args, input_fn=input, output_fn=print):
    # Inputs: Parsed R2.2 start arguments and injectable terminal functions.
    # Does: Guide discovery, version choice, addon selection and optional execution.
    # Output: Discovery details or completed local-analysis summary.
    config_path = args.config or DEFAULT_CONFIG
    config = load_config(config_path)
    repo_value = args.odoo or config.get("odoo_repo")
    repo = Path(repo_value).expanduser() if repo_value else detect_odoo_checkout(Path.cwd())
    while repo is None or not is_odoo_checkout(repo):
        value = input_fn("Ruta del repositorio local de Odoo: ").strip()
        repo = Path(value).expanduser() if value else None
    addons_value = args.addons or config.get("addons_root")
    addons_root = Path(addons_value).expanduser() if addons_value else None
    while addons_root is None or not addons_root.is_dir():
        value = input_fn("Ruta de la carpeta o repositorio de addons: ").strip()
        addons_root = Path(value).expanduser() if value else None
    addons = discover_addons(addons_root)
    if not addons:
        raise ValueError("No __manifest__.py files were found in the addons directory")
    output_fn("Addons encontrados:")
    for index, addon in enumerate(addons, 1):
        output_fn(f"  {index}. {addon['name']}  [{addon['path']}]")
    selection = args.select or ("all" if len(addons) == 1 else input_fn("Elige números, rangos, nombres o 'all': "))
    chosen = select_addons(addons, selection)
    versions = available_versions(repo)
    output_fn("Versiones locales disponibles: " + (", ".join(versions) if versions else "ninguna detectada"))
    origin = args.from_version or config.get("from_version") or input_fn("Versión origen, por ejemplo 16.0: ").strip()
    destination = args.to_version or config.get("to_version") or input_fn("Versión destino, por ejemplo 17.0: ").strip()
    resolve_version_ref(repo, origin)
    resolve_version_ref(repo, destination)
    saved = dict(odoo_repo=str(repo.resolve()), addons_root=str(addons_root.resolve()),
                 from_version=origin, to_version=destination)
    save_config(saved, config_path)
    discovery = dict(config=str(Path(config_path).resolve()), repository=saved["odoo_repo"],
                     addons=chosen, from_version=origin, to_version=destination)
    if args.list_only:
        return discovery
    output = args.output_dir
    if output is None:
        output = Path.cwd() / "temp_data" / f"local-{origin}-to-{destination}-{uuid4().hex[:8]}"
    return run_local_analysis(repo, chosen, origin, destination, output,
                              layer=args.layer, maximum_hops=args.maximum_hops, limit=args.limit)
