"""Source collection, deterministic diff extraction and immutable SQLite builds."""
import difflib
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path
from ..extract_relations import extract, layer_for, tokens, resolve_references
from ..policy import select_sources
from ..review import apply_reviews, search_document
from ..selection import assign_sources
from .. import __version__
from ..records import canonical, connect, load, meta, fingerprint as digest


def git(repo, *args, binary=False):
    # Inputs: repo, binary, args.
    # Does: Read a Git revision or diff from the specified repository.
    # Output: Git command output.
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args],
                            capture_output=True, env=env, timeout=120)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip())
    return result.stdout if binary else result.stdout.decode("utf-8")


def within(base, value):
    # Inputs: base, value.
    # Does: Resolve a path and enforce containment in its base.
    # Output: A validated path.
    return (base / value).resolve()


def read_source(record, base, excluded_modules=()):
    # Inputs: record, base, excluded_modules.
    # Does: Read the legacy source and its provenance under the extraction policy.
    # Output: Source snapshots, metadata and warnings.
    """Materialize sources once, then queries never read remote or source files."""
    record = dict(record)
    fmt = record.get("format")
    old, new = {}, {}
    byte_hashes = {"before": {}, "after": {}}
    extensions = {".py", ".xml", ".csv", ".rst", ".md", ".txt"}
    if fmt == "git":
        repo = within(base, record["repo"])
        prefix = record.get("prefix") or "."
        for side, target in (("from", old), ("to", new)):
            rev = git(repo, "rev-parse", "--verify", record[f"{side}_revision"] + "^{commit}").strip()
            record[f"{side}_revision"] = rev
            paths = git(repo, "ls-tree", "-r", "-z", "--name-only", rev, "--", prefix).split("\0")
            for path in sorted(p for p in paths if p and Path(p).suffix in extensions):
                if set(Path(path).parts) & set(excluded_modules):
                    continue
                # Git blobs are read as data, not checked out and not executed.
                raw = git(repo, "show", f"{rev}:{path}", binary=True)
                target[path] = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
                byte_hashes["before" if side == "from" else "after"][path] = hashlib.sha256(raw).hexdigest()
    elif fmt == "snapshot":
        for side, target in (("before", old), ("after", new)):
            root = within(base, record[f"{side}_dir"])
            if not root.is_dir():
                raise ValueError(f"Snapshot directory does not exist: {root}")
            for path in sorted(root.rglob("*")):
                if path.is_symlink() or not path.is_file() or path.suffix not in extensions:
                    continue
                relative = path.relative_to(root)
                if any(x in relative.parts for x in (".git", "__pycache__", ".venv")):
                    continue
                if set(relative.parts) & set(excluded_modules):
                    continue
                raw = path.read_bytes()
                target[relative.as_posix()] = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
                byte_hashes[side][relative.as_posix()] = hashlib.sha256(raw).hexdigest()
        record["from_revision"] = "sha256:" + digest(old)
        record["to_revision"] = "sha256:" + digest(new)
    else:
        raise ValueError("Source format must be git or snapshot")
    if not old and not new:
        raise ValueError(f"No readable source files: {record['id']}")
    for name in ("from_version", "to_version"):
        if record.get(name) not in {"16.0", "17.0", "18.0", "19.0"}:
            raise ValueError("Versions must be within 16.0–19.0")
    if int(record["from_version"].split('.')[0]) >= int(record["to_version"].split('.')[0]):
        raise ValueError("Destination version must follow source version")
    record["file_hashes"] = {side: {p: hashlib.sha256(t.encode()).hexdigest() for p, t in files.items()}
                             for side, files in (("before", old), ("after", new))}
    record["snapshot_file_byte_hashes"] = byte_hashes
    record["original_byte_hashes"] = {side: dict(values) for side, values in byte_hashes.items()}
    for capture in record.get("captures", []):
        if capture["capture_form"] != "original_bytes":
            raise ValueError("Only original public source captures can be indexed, not selection metadata")
        raw_path = within(base, capture["stored_file"])
        if hashlib.sha256(raw_path.read_bytes()).hexdigest() != capture["stored_sha256"]:
            raise ValueError("Original source capture hash mismatch")
        key = capture["file_path"]
        if record["file_hashes"][capture["side"]].get(key) != capture["normalized_sha256"]:
            raise ValueError("Normalized text is not the captured extraction")
        record["original_byte_hashes"][capture["side"]][key] = capture["response_sha256"]
    record["normalization"] = "utf8-sig; CRLF/CR to LF; normalized hashes are file_hashes"
    record.setdefault("license", {"status": "not_verified"})
    return record, old, new


def changed_ranges(group, side):
    # Inputs: group, side.
    # Does: Extract affected line spans for the selected side of a diff.
    # Output: The affected ranges by path.
    offset = 1 if side == "old" else 3
    return [(op[offset] + 1, max(op[offset] + 1, op[offset + 1]))
            for op in group if op[0] != "equal"]


def impacted(data, ranges):
    # Inputs: data, ranges.
    # Does: Select extracted observations intersecting changed lines.
    # Output: The affected observations.
    hits = [e for e in data["elements"] if any(e["line"] <= hi and e["end_line"] >= lo for lo, hi in ranges)]
    # Classes/models provide context but should not seed every edit when a more
    # specific field, method or property location is available.
    precise = [e for e in hits if e["kind"] not in {"model", "class"}]
    return sorted({e["key"] for e in precise or hits})


def changes_for(source, before, after, old_data, new_data):
    # Inputs: source, before, after, old_data, new_data.
    # Does: Combine before and after snapshots and observations into legacy changes.
    # Output: The changes derived for one source.
    for path in sorted(set(before) | set(after)):
        a, b = before.get(path, ""), after.get(path, "")
        if a == b:
            continue
        al, bl = a.splitlines(), b.splitlines()
        for group in difflib.SequenceMatcher(None, al, bl, autojunk=False).get_grouped_opcodes(3):
            old_ranges, new_ranges = changed_ranges(group, "old"), changed_ranges(group, "new")
            old_start, old_end = group[0][1], group[-1][2]
            new_start, new_end = group[0][3], group[-1][4]
            removed = "\n".join("\n".join(al[i:j]) for tag, i, j, _, _ in group if tag != "equal")
            added = "\n".join("\n".join(bl[i:j]) for tag, _, _, i, j in group if tag != "equal")
            elements = sorted(set(impacted(old_data[path], old_ranges) + impacted(new_data[path], new_ranges)))
            record = dict(source_id=source["id"], file_path=path, layer=layer_for(path), source_layer=layer_for(path),
                          from_version=source["from_version"], to_version=source["to_version"],
                          from_revision=source["from_revision"], to_revision=source["to_revision"],
                          before_start=old_start + 1, before_end=old_end,
                          after_start=new_start + 1, after_end=new_end,
                          before="\n".join(al[old_start:old_end]), after="\n".join(bl[new_start:new_end]),
                          removed=removed, added=added, elements=sorted(set(elements)),
                          status="candidate", classification="textual_difference",
                          required_elements=[], title=f"Observed difference in {path}",
                          origin_kind=source["kind"],
                          matching_migration=source.get("case_id") if source["kind"] == "oca_migration" else None)
            record["comparison_id"] = "cmp-" + digest([source["id"], source["from_revision"], source["to_revision"]])[:24]
            if re.sub(r"\s", "", removed) == re.sub(r"\s", "", added):
                record["classification"] = "whitespace_difference_requires_review"
            if record["layer"] == "documentation":
                record["classification"] = "documentation"
            record["id"] = "chg-" + digest(record)[:24]
            yield record


def build(manifest, destination, include_oca_migrations=False, annotations=None, assignment_registry=None):
    # Inputs: manifest, destination, include_oca_migrations, annotations, assignment_registry.
    # Does: Build the archived snapshot-based migration collection.
    # Output: A persisted SQLite collection and build summary.
    start = time.perf_counter()
    manifest = Path(manifest).resolve()
    records = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("Manifest must be a JSON array")
    registry = json.loads(Path(assignment_registry).read_text(encoding="utf-8-sig")) if assignment_registry else None
    records, assignment_exclusions, audited = assign_sources(records, registry)
    selection = select_sources(records, include_oca_migrations=include_oca_migrations)
    selection["excluded"].extend(assignment_exclusions)
    sources, elements, relations, changes, warnings = [], {}, {}, {}, []
    for raw in selection["accepted"]:
        source, before, after = read_source(raw, manifest.parent, registry.get("excluded_modules", []) if registry else [])
        sources.append(source)
        by_side = []
        for side, files in (("before", before), ("after", after)):
            version = source["from_version"] if side == "before" else source["to_version"]
            def module_for(p):
                # Inputs: p.
                # Does: Infer an addon namespace from the legacy source path.
                # Output: The inferred addon name or no value.
                parts = Path(p).parts
                if "addons" in parts and parts.index("addons") + 1 < len(parts):
                    return parts[parts.index("addons") + 1]
                return source.get("module") or (parts[0] if len(parts) > 1 else source["id"])
            data = {p: extract(t, p, module_for(p)) for p, t in files.items()}
            declarations = [e for result in data.values() for e in result["elements"] if e.get("role") == "declaration"]
            for result in data.values():
                resolve_references(result, declarations)
            by_side.append(data)
            for path, result in data.items():
                warnings.extend(f"{source['id']} {side}: {w}" for w in result["warnings"])
                for item in result["elements"]:
                    row = {**item, "version": version, "source_id": source["id"], "side": side}
                    elements[digest(row)] = row
                for item in result["relations"]:
                    row = {**item, "version": version, "source_id": source["id"], "side": side}
                    relations[digest(row)] = row
        # Empty data for added/deleted paths is needed on the missing side.
        for data in by_side:
            for path in set(before) | set(after):
                data.setdefault(path, dict(elements=[], relations=[], warnings=[]))
        for change in changes_for(source, before, after, *by_side):
            changes[change["id"]] = change
    return write_collection(sources, elements, relations, changes, destination, annotations,
                            registry, selection["excluded"], audited, warnings, start)


def compatibility_views(converted):
    # Inputs: converted.
    # Does: Project normalized units into the legacy query representation.
    # Output: The legacy source, change and document structures.
    """Keep existing diff consumers working; never create search relations.

    These are projections of information units, not a second normalization.
    Non-diff units remain available through information_units and documents.
    """
    changes, elements, documents = {}, {}, {}
    sources = {s['id']:s for s in converted['sources']}
    for unit in converted['units'].values():
        source=sources[unit['source_id']]
        if unit['kind']!='diff_hunk':
            documents[unit['id']]=dict(id=unit['id'],source_id=unit['source_id'],artifact_id=unit['artifact_id'],
                                      kind=unit['kind'],text=unit['text'],role='context_only',source_locator=unit['source_locator'])
        for entity in unit['entities']:
            if entity['context'].get('origin')!='code': continue
            for key in entity.get('lookup_keys',[]):
                kind=key.split(':',1)[0]
                side=entity['location'].get('side','after')
                line=entity['location'].get('code_line') or entity['location'].get('artifact_line') or 1
                row=dict(key=key,kind=kind,name=entity['name'],path=unit['data'].get('file_path',
                    '__manifest__.py' if unit['kind']=='manifest' else unit['source_locator']['artifact_path']),
                    line=line,end_line=line,layer=unit['layers'][0],module=entity['context'].get('module'),
                    role=entity['context'].get('role','reference'),version=unit['version_from'] if side=='before' else unit['version_to'],
                    side=side,source_id=unit['source_id'],artifact_id=unit['artifact_id'],information_unit_id=unit['id'])
                elements[digest(row)]=row
        if unit['kind']!='diff_hunk': continue
        # Unknown intervals are retained in information_units, not fabricated
        # into an applicable migration interval for the legacy diff query.
        if not unit['version_from'] or not unit['version_to']: continue
        data=unit['data']
        keys=sorted({k for e in unit['entities'] if e['context'].get('origin')=='code' for k in e.get('lookup_keys',[])})
        cid='chg-'+unit['id'][5:]
        changes[cid]=dict(**{k:v for k,v in data.items() if k not in {'pr_id','pr_url','resource_id','provenance_references'}},
            id=cid,information_unit_id=unit['id'],source_locator=unit['source_locator'],source_id=unit['source_id'],
            artifact_id=unit['artifact_id'],layer=unit['layers'][0],source_layer=unit['layers'][0],
            from_version=unit['version_from'],to_version=unit['version_to'],from_revision=source.get('from_revision'),
            to_revision=source.get('to_revision'),comparison_id='cmp-'+digest([unit['source_id'],source.get('from_revision'),source.get('to_revision')])[:24],
            elements=keys,required_elements=[],status='candidate',classification='observed_diff_hunk',
            origin_kind=source['kind'],matching_migration=None,title=f"Observed diff in {data['file_path']}",
            evidence_scope='partial_source_hunk')
    return elements,changes,documents


def build_session(inventory, bindings, destination, annotations=None):
    # Inputs: inventory, bindings, destination, annotations.
    # Does: Normalize a session and write its legacy compatibility views.
    # Output: A persisted collection and build summary.
    """Build schema 4 from validated normalized units, without downloading."""
    from ..normalization import normalize_session
    start = time.perf_counter()
    converted = normalize_session(inventory, bindings)
    elements,changes,documents=compatibility_views(converted)
    return write_collection(converted["sources"], elements, {},
                            changes, destination, annotations, None, converted["excluded"], False,
                            converted["warnings"], start, converted["artifacts"], documents, schema=4,
                            normalized_units=converted['units'],normalization=converted['normalization'],issues=converted['issues'])


def write_collection(sources, elements, relations, changes, destination, annotations,
                     registry, excluded, audited, warnings, start, artifacts=None, documents=None, schema=2,
                     normalized_units=None,normalization=None,issues=None):
    # Inputs: sources, elements, relations, changes, destination, annotations, registry, excluded, audited, warnings, start, artifacts, documents, schema, normalized_units, normalization, issues.
    # Does: Write the supplied legacy collection and metadata to SQLite.
    # Output: The stored database and its build summary.
    include_oca_migrations = False
    artifacts, documents = artifacts or {}, documents or {}
    review = json.loads(Path(annotations).read_text(encoding="utf-8-sig")) if annotations else []
    changes, evidence = apply_reviews(changes, review)
    comparisons = {c["comparison_id"]: dict(id=c["comparison_id"], source_id=c["source_id"],
                    from_revision=c["from_revision"], to_revision=c["to_revision"],
                    from_version=c["from_version"], to_version=c["to_version"])
                   for c in evidence.values()}
    payload = dict(schema_version=schema, engine_version=__version__ if schema >= 3 else "0.2.0", include_oca_migrations=include_oca_migrations,
                   sources=sources, elements=elements, relations=relations, changes=changes,
                   evidence=evidence, comparisons=comparisons, artifacts=artifacts, documents=documents, assignment_registry=registry, excluded=excluded)
    if schema==4:
        from ..normalization.schema import validate_collection
        validate_collection(dict(sources=sources,artifacts=artifacts,units=normalized_units or {}))
        if relations:
            raise ValueError('Normalized collections cannot contain precomputed search relations')
        payload.update(information_units=normalized_units or {},normalization=normalization,normalization_issues=issues or [])
    revision = digest(payload)
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Refusing to overwrite a collection; choose a new --db path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="r2-build-", suffix=".sqlite", dir=destination.parent)
    os.close(fd)
    con = None
    try:
        con = sqlite3.connect(temp)
        with con:
            con.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            for table in ("sources", "elements", "relations", "changes", "evidence", "comparisons", "artifacts", "documents"):
                con.execute(f"CREATE TABLE {table}(id TEXT PRIMARY KEY,payload TEXT NOT NULL)")
            if schema==4:
                con.execute('CREATE TABLE information_units(id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
                con.execute('CREATE TABLE unit_terms(unit_id TEXT,term TEXT,frequency INTEGER,tfidf REAL,PRIMARY KEY(unit_id,term))')
                con.execute('CREATE INDEX unit_term_lookup ON unit_terms(term)')
                con.execute('CREATE TABLE unit_entities(unit_id TEXT,ordinal INTEGER,name TEXT,type TEXT,payload TEXT,PRIMARY KEY(unit_id,ordinal))')
                con.execute('CREATE INDEX unit_entity_lookup ON unit_entities(name,type)')
                for uid,unit in sorted((normalized_units or {}).items()):
                    con.execute('INSERT INTO information_units VALUES (?,?)',(uid,canonical(unit)))
                    con.executemany('INSERT INTO unit_terms VALUES (?,?,?,?)',[(uid,t['term'],t['frequency'],t['tfidf']) for t in unit['terms']])
                    con.executemany('INSERT INTO unit_entities VALUES (?,?,?,?,?)',[(uid,i,e['name'],e['type'],canonical(e)) for i,e in enumerate(unit['entities'])])
            con.execute("CREATE TABLE change_evidence(change_id TEXT,evidence_id TEXT,PRIMARY KEY(change_id,evidence_id))")
            con.execute("CREATE VIRTUAL TABLE search USING fts5(change_id UNINDEXED, text, tokenize='unicode61')")
            for table, rows in (("sources", {r['id']: r for r in sources}), ("elements", elements),
                                ("relations", relations), ("changes", changes), ("evidence", evidence), ("comparisons", comparisons), ("artifacts", artifacts), ("documents", documents)):
                con.executemany(f"INSERT INTO {table} VALUES (?,?)", [(k, canonical(v)) for k, v in sorted(rows.items())])
            for key, c in sorted(changes.items()):
                # Same change units for both systems; term frequencies are preserved.
                text = " ".join(re.findall(r"[a-zA-Z_][a-zA-Z_0-9]*", search_document(c).lower()))
                con.execute("INSERT INTO search VALUES (?,?)", (key, text))
                con.executemany("INSERT INTO change_evidence VALUES (?,?)", [(key, e) for e in c["evidence_ids"]])
            metadata = dict(schema_version=schema, engine_version=__version__ if schema >= 3 else "0.2.0", collection_revision=revision,
                            include_oca_migrations=include_oca_migrations, excluded=excluded,
                            assignment_audited=audited, assignment_revision=digest(registry) if registry else None,
                            bm25_fields=["title", "affected_elements", "removed", "added"],
                            warnings=sorted(set(warnings)), preparation_seconds=time.perf_counter()-start,
                            source_count=len(sources), change_count=len(changes),
                            artifact_count=len(artifacts), document_count=len(documents),
                            source_policy="normalized_capture_units_v1" if schema==4 else "final_catalog_admitted_units_v1" if schema == 3 else "historical_local_import",
                            review_count=len(review), bm25="SQLite FTS5 k1=1.2 b=0.75 unicode61; identifier tokens")
            if schema==4:
                metadata.update(information_unit_count=len(normalized_units or {}),normalization=normalization,
                                normalization_issues=issues or [],normalization_issue_count=len(issues or []),
                                search_relations_precomputed=False,
                                query_scope='Existing diff consumers only; document retrieval and dynamic unit relationships pending')
            con.executemany("INSERT INTO metadata VALUES (?,?)", [(k, canonical(v)) for k, v in sorted(metadata.items())])
        con.close()
        os.replace(temp, destination)
    finally:
        if con is not None:
            con.close()
        if os.path.exists(temp):
            os.unlink(temp)
    return {"database": str(destination), **metadata}

