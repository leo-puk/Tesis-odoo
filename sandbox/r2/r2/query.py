"""Deterministic structural retrieval and lexical BM25 baseline."""
from collections import Counter
import time
from .graph import BACKEND, bfs_layers, new_graph
from .collection import connect, load, meta
from .extract import LAYERS, scan_module, tokens
from .extract import resolve_references

SEED_POLICY = "explicit_declarations_and_references_v2_no_unresolved_or_generic_symbols"
RANKING = {"version": "2", "order": ["verified_first", "minimum_depth", "typed_specificity", "match_count", "bm25", "stable_id"]}


def paths_by_depth(graph, seeds, maximum):
    """Stable multiorigin BFS; store one lexicographically stable shortest path."""
    seeds = sorted(set(seeds) & set(graph))
    paths = {key: [key] for key in seeds}
    depths = {key: 0 for key in seeds}
    for depth, nodes in enumerate(bfs_layers(graph, seeds)):
        if depth > maximum:
            break
        for node in sorted(nodes):
            if depth:
                parents = sorted(p for p in graph.predecessors(node) if depths.get(p) == depth - 1)
                parent = min(parents, key=lambda p: paths[p])
                paths[node] = paths[parent] + [node]
                depths[node] = depth
    return paths


def retrieve(database, module, from_version, to_version, *, layer="all", depth=3,
             limit=10, engine="graph", status="all", include_oca_migrations=False, module_name=None):
    if include_oca_migrations:
        raise ValueError("The OCA inclusion switch was removed")
    start = time.perf_counter()
    if not (0 <= depth <= 20) or not (1 <= limit <= 10):
        raise ValueError("Depth must be 0–20 and limit must be 1–10")
    versions = {"16.0", "17.0", "18.0", "19.0"}
    if from_version not in versions or to_version not in versions or from_version >= to_version:
        raise ValueError("Use an increasing version pair within 16.0–19.0")
    if layer not in (*LAYERS, "documentation", "all") or engine not in {"graph", "bm25"}:
        raise ValueError("Unknown layer or engine")
    if status not in {"all", "verified", "candidate", "unresolved"}:
        raise ValueError("Unknown status filter")
    data = scan_module(module, module_name)
    warnings = list(data["warnings"])
    with connect(database) as con:
        metadata = meta(con)
        sources = {s["id"]: s for s in load(con, "sources")}
        if metadata["schema_version"] not in {2, 3}:
            raise ValueError("Collection schema changed; rebuild from the frozen inventory")
        resolve_references(data, [e for e in load(con, "elements") if e["version"] == from_version])
        seeds = sorted({e["key"] for e in data["elements"] if e.get("role") in {"declaration", "reference"} and e["kind"] not in {"symbol", "xpath"}})
        seed_set = set(seeds)
        if not seeds:
            warnings.append("No statically recognizable seeds were found")
        if metadata.get("include_oca_migrations", False):
            raise ValueError("Source policy differs from collection; rebuild/use a matching database")
        changes = [c for c in load(con, "changes") if
                   from_version <= c["from_version"] < c["to_version"] <= to_version and
                   (layer == "all" or c["layer"] == layer) and c["status"] != "rejected" and
                   (status == "all" or c["status"] == status) and
                   set(c["required_elements"]) <= seed_set]
        allowed_ids = {c["id"] for c in changes}
        documents = {d["id"]: d for d in load(con, "documents")} if metadata["schema_version"] == 3 else {}
        relations = load(con, "relations")
        graph = new_graph()
        graph.add_nodes_from(seeds)
        # Only source-version relations can explain the ORIGINAL module. No
        # implicit propagation through an unexecuted intermediate transformation.
        def add_relation(r):
            a, b = r["source"], r["target"]
            if not graph.has_edge(a, b):
                graph.add_edge(a, b, evidences=[])
            if r not in graph[a][b]["evidences"]:
                graph[a][b]["evidences"].append(r)
        for r in sorted(relations, key=lambda x: (x["source"], x["target"], x["source_id"], x["path"], x["line"])):
            if r["version"] == from_version:
                add_relation(r)
        # Input-module relationships are explicitly identified as query evidence.
        for r in sorted(data["relations"], key=lambda x: (x["source"], x["target"], x["path"], x["line"])):
            add_relation({**r, "source_id": "input_module", "version": from_version})
        for c in changes:
            graph.add_nodes_from(c["elements"])
        paths = paths_by_depth(graph, seeds, depth) if engine == "graph" else {}
        # Build identical lexical queries for the reference, without relation expansion.
        query_tokens = sorted({t for seed in seeds for t in tokens(seed)})
        lexical = {}
        if query_tokens:
            expression = " OR ".join('"' + t + '"' for t in query_tokens)
            for row in con.execute("SELECT change_id,bm25(search) AS score FROM search WHERE search MATCH ? ORDER BY score,change_id", (expression,)):
                if row["change_id"] in allowed_ids:
                    lexical[row["change_id"]] = row["score"]
        ranked = []
        for change in changes:
            available = [paths[k] for k in change.get("affected_elements", change["elements"]) if k in paths]
            if engine == "graph" and not available:
                continue
            if engine == "bm25" and change["id"] not in lexical:
                continue
            path = min(available, key=lambda p: (len(p), p)) if available else []
            hops = [dict(source=a, target=b, version=from_version, evidences=graph[a][b]["evidences"]) for a, b in zip(path, path[1:])]
            result = {**change, "depth": len(path)-1 if path else None, "path": path,
                      "relation_evidence": hops,
                      "retrieval_basis": "structural" if engine == "graph" else "lexical",
                      "lexical_score": lexical.get(change["id"]),
                      "matching_terms": sorted(set(query_tokens) & set(tokens(str(change)))) if engine == "bm25" else [],
                      "applicability": "reviewed_conditions_match" if change["status"] == "verified" else "candidate_requires_review"}
            result["affected_element"] = path[-1] if path else None
            used_sources = {b["source_id"] for b in change.get("evidence_blocks", [change])}
            result["source_citations"] = [{k: sources[s].get(k) for k in
                ("id", "url", "repo", "from_revision", "to_revision", "captured_at", "scope", "captures", "unit_id", "session_id", "plan_source_id", "reference_basis")}
                for s in sorted(used_sources)]
            if metadata["schema_version"] == 3:
                context_ids = {d for s in used_sources for d in sources[s].get("context_document_ids", [])}
                result["context_documents"] = [documents[k] for k in sorted(context_ids)]
            # Verified status, minimum depth, exact semantic matches, lexical tie
            # breaker, stable ID. No learned weights and no random sampling.
            matched = seed_set & set(change["elements"])
            specificity = max((4 if k.startswith(("field:", "method:", "xml-attribute:")) else
                               3 if k in {"property:states", "property:readonly", "property:compute", "property:related"} else
                               2 if k.startswith("property:") else 1 for k in matched), default=0)
            rank = ((result["lexical_score"], change["id"]) if engine == "bm25" else
                    (change["status"] != "verified", result["depth"],
                     -specificity, -len(matched), lexical.get(change["id"], 0), change["id"]))
            ranked.append((rank, result))
        ranked.sort(key=lambda pair: pair[0])
        all_results = [r for _, r in ranked]
        first = all_results[:limit]
        by_depth = Counter(str(r["depth"]) for r in all_results if r["depth"] is not None)
        methods = {e for c in all_results for e in c["elements"] if e.startswith("method:")}
        summary = {
            "changes_found": len(all_results), "changes_shown": len(first),
            "matching_migrations": len({b["matching_migration"] for c in all_results
                                        for b in c.get("evidence_blocks", [c]) if b["matching_migration"]}),
            "methods_with_documented_changes": len(methods),
            "changes_by_layer": dict(sorted(Counter(r["layer"] for r in all_results).items())),
            "new_findings_by_depth": dict(sorted(by_depth.items(), key=lambda x: int(x[0]))),
            "changes_by_status": dict(sorted(Counter(r["status"] for r in all_results).items())),
        }
        if engine == "bm25":
            warnings.append("Lexical baseline: structural depth and paths are not assigned")
        if int(to_version[:2])-int(from_version[:2]) > 1:
            warnings.append("Intermediate changes are checked against the original module, not a transformed intermediate module")
        if metadata["schema_version"] == 3:
            warnings.extend(metadata.get("warnings", []))
            warnings.append("Diff hunks are partial source; absent anchors do not prove absence of impact")
        warnings.append("Static analysis cannot resolve all dynamic references or prove functional incompatibility")
        return dict(schema_version=metadata["schema_version"], engine_version=metadata["engine_version"],
                    collection_revision=metadata["collection_revision"], engine=engine,
                    graph_implementation=BACKEND,
                    include_oca_migrations=include_oca_migrations,
                    query=dict(from_version=from_version, to_version=to_version, layer=layer,
                               max_depth=depth, limit=limit, status=status, elements=seeds,
                               lexical_terms=query_tokens, seed_policy=SEED_POLICY, ranking=RANKING, module_name=module_name),
                    results=first, summary=summary, warnings=sorted(set(warnings)),
                    elapsed_seconds=time.perf_counter()-start)


def validate_output(output):
    """V1 structural and accounting checks, without asserting pertinence."""
    errors = []
    try:
        results, summary, query = output["results"], output["summary"], output["query"]
        ids = [r["id"] for r in results]
        if len(ids) != len(set(ids)) or len(ids) > min(10, query["limit"]):
            errors.append("Result uniqueness/limit mismatch")
        if summary["changes_shown"] != len(results) or summary["changes_found"] < len(results):
            errors.append("Shown/found counter mismatch")
        if sum(summary["changes_by_layer"].values()) != summary["changes_found"]:
            errors.append("Layer counter mismatch")
        if sum(summary["changes_by_status"].values()) != summary["changes_found"]:
            errors.append("State counter mismatch")
        if output["engine"] == "graph" and sum(summary["new_findings_by_depth"].values()) != summary["changes_found"]:
            errors.append("Depth counter mismatch")
        for r in results:
            for field in ("source_id", "from_revision", "to_revision", "file_path", "path", "layer", "before", "after", "status", "title"):
                if field not in r:
                    errors.append(f"Missing evidence field {field}")
            if not (query["from_version"] <= r["from_version"] < r["to_version"] <= query["to_version"]):
                errors.append("Result jump is incompatible with the query")
            if query["status"] != "all" and r["status"] != query["status"]:
                errors.append("Result state is incompatible with the query")
            if not r.get("evidence_ids") or not r.get("comparison_id"):
                errors.append("Comparison/evidence identifiers are missing")
            if r["status"] == "verified" and not r.get("review_history"):
                errors.append("Verified change lacks review history")
            if r["status"] == "verified" and (r.get("destination_validity", {}).get("status") != "checked" or
                    not (r.get("required_elements") or r.get("general_applicability", {}).get("justification"))):
                errors.append("Verified change lacks applicability/validity evidence")
            if r["status"] == "verified" and (r["destination_validity"].get("from_version"), r["destination_validity"].get("to_version")) != (r["from_version"], r["to_version"]):
                errors.append("Destination validity refers to a different jump")
            for block in r.get("evidence_blocks", [r]):
                if (block["from_version"], block["to_version"]) != (r["from_version"], r["to_version"]):
                    errors.append("Grouped evidence has an incompatible jump")
                if not block.get("source_id") or not block.get("from_revision") or not block.get("to_revision"):
                    errors.append("Grouped evidence lacks source revisions")
            if output["engine"] == "graph":
                path = r["path"]
                if not path or path[0] not in query["elements"] or path[-1] not in r["elements"] or len(path)-1 != r["depth"]:
                    errors.append("Invalid structural path")
                if r["depth"] > query["max_depth"]:
                    errors.append("Path exceeds configured depth")
                if len(r["relation_evidence"]) != len(path)-1:
                    errors.append("Missing relation evidence")
                for a, b, edge in zip(path, path[1:], r["relation_evidence"]):
                    if edge["source"] != a or edge["target"] != b or edge.get("version") != query["from_version"] or not edge.get("evidences"):
                        errors.append("Relation evidence mismatch")
                    for item in edge.get("evidences", []):
                        if item["source"] != a or item["target"] != b or not item.get("path") or item.get("version") != query["from_version"]:
                            errors.append("Invalid edge provenance/version")
    except (KeyError, TypeError, ValueError, AttributeError):
        errors.append("Malformed output")
    return dict(conformant=not errors, automatic_structural_conformant=not errors,
                conformance_scope="automatic structural checks only", full_V1_determined=False,
                human_checks_pending=["English free text", "semantic pertinence", "upstream provenance authenticity"], errors=sorted(set(errors)))


def render_text(output):
    s = output["summary"]
    lines = [f"Collection: {output['collection_revision']}", f"Engine: {output['engine']}",
             f"Graph implementation: {output['graph_implementation']}",
             f"Changes found / shown: {s['changes_found']} / {s['changes_shown']}",
             f"Matching migrations: {s['matching_migrations']}",
             f"Methods with documented changes: {s['methods_with_documented_changes']}",
             f"Changes by layer: {s['changes_by_layer']}", f"New findings by depth: {s['new_findings_by_depth']}"]
    lines.append(f"Changes by status: {s['changes_by_status']}")
    for n, r in enumerate(output["results"], 1):
        lines += [f"\n{n}. [{r['status']}] {r['title']}",
                  f"   ID: {r['id']} | Layer: {r['layer']} | Depth: {r['depth']}",
                  f"   Source: {r['source_id']} {r['from_revision']} -> {r['to_revision']}",
                  f"   File: {r['file_path']}:{r['before_start']} -> {r['after_start']}",
                  f"   Path: {' -> '.join(r['path']) or '(lexical match)'}"]
        lines += [f"   Versions: {r['from_version']} -> {r['to_version']}",
                  f"   Affected elements: {r.get('affected_elements', r['elements'])}",
                  f"   Conditions: {r['required_elements'] or r.get('general_applicability')}",
                  f"   Evidence IDs: {r['evidence_ids']} (use show for every evidence block)"]
    lines += [f"\nTime to first view and summary: {output['elapsed_seconds']:.6f}s"]
    lines += [f"Warning: {w}" for w in output["warnings"]]
    return "\n".join(lines)
