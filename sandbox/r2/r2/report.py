"""Build the migration evidence report from normalized units and crossing."""
import re
from collections import Counter
from time import perf_counter

from .records import connect, load, meta
from .crossing import cross_module
from .crossing.code import read_code
from .normalization.schema import LAYERS
from .normalization.terms import term_counts
from .relations import execute_query
from .relations.traversal import traverse_relations

DOCUMENT_KINDS = {"markdown_section", "rst_section", "html_document", "pr_description"}


def version_key(version):
    # Inputs: version.
    # Does: Validate a major.minor version string and make it comparable.
    # Output: The numeric version pair.
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+", version):
        raise ValueError("Versions must use major.minor format")
    return tuple(map(int, version.split(".")))


def citation(unit):
    # Inputs: unit.
    # Does: Project the provenance and locator of a normalized unit.
    # Output: A source citation.
    return dict(unit_id=unit["id"], source_id=unit["source_id"], url=unit["source_url"],
                artifact_id=unit["artifact_id"], locator=unit["source_locator"],
                from_version=unit["version_from"], to_version=unit["version_to"], kind=unit["kind"])


def matches_transition(unit, first, last):
    """Use destination documentation as candidates with an explicit version anchor."""
    before, after = unit["version_from"], unit["version_to"]
    if unit["kind"] not in DOCUMENT_KINDS | {"diff_hunk"} or not after:
        return False
    if before is None:
        return unit["kind"] in DOCUMENT_KINDS and first < version_key(after) <= last
    return first <= version_key(before) < version_key(after) <= last


def graph_hits(graph, units, admissible):
    # Inputs: graph, units, admissible.
    # Does: Recompute admissible traversal paths under a query scope.
    # Output: One explained path per reachable unit.
    seeds = [uid for uid in graph["seeds"] if admissible(units[uid], context=True)]
    allowed = {node["unit_id"] for node in graph["nodes"] if admissible(units[node["unit_id"]], context=True)}
    edges = [edge for edge in graph["edges"] if {edge["left"], edge["right"]} <= allowed]
    nodes = traverse_relations(dict(unit_ids=allowed, seeds=seeds, edges=edges,
                                    maximum_hops=graph["maximum_hops"]))["nodes"]
    paths = {}
    for node in sorted(nodes, key=lambda row: (row["minimum_hops"], row["unit_id"])):
        uid = node["unit_id"]
        if node["is_seed"]:
            paths[uid] = ([uid], [])
        else:
            step = node["predecessors"][0]
            parents, relations = paths[step["unit_id"]]
            paths[uid] = (parents + [uid], relations + [step["edge_id"]])
    return paths


def changed_observations(unit):
    # Inputs: unit.
    # Does: Locate observations on added or removed code lines.
    # Output: The observations on changed lines.
    data = unit["data"]
    lines = {"before": data["before_start"], "after": data["after_start"]}
    changed = set()
    for line in data["diff_body"].splitlines():
        marker = line[0]
        if marker == "-":
            changed.add(("before", lines["before"]))
        if marker == "+":
            changed.add(("after", lines["after"]))
        lines["before"] += marker != "+"
        lines["after"] += marker != "-"
    return [entity for entity in unit["entities"] if entity["context"]["origin"] == "code"
            and (entity["location"].get("side"), entity["location"].get("code_line")) in changed]


def diff_key(unit):
    # Inputs: unit.
    # Does: Build a key for deduplicating identical diff hunks.
    # Output: The transition, path and diff content tuple.
    data = unit["data"]
    return (unit["version_from"], unit["version_to"], data["old_path"], data["new_path"],
            data["before_start"], data["after_start"], data["diff_body"])


def search_units(database, module, from_version, to_version, *, layer="all", maximum_hops=3,
                 limit=10, module_name=None, engine="graph", timings=None):
    # Inputs: database, module, from_version, to_version, layer, maximum_hops, limit, module_name, engine.
    # Does: Retrieve scoped changes by graph or BM25 and validate the result.
    # Output: The report and optional crossing and graph handoffs.
    """Return report and its intermediate evidence. BM25 uses the same corpus and filters."""
    first, last = version_key(from_version), version_key(to_version)
    if first >= last:
        raise ValueError("Destination version must follow origin")
    if layer not in LAYERS | {"all"} or type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError("Choose a supported layer and a limit between 1 and 10")
    if type(maximum_hops) is not int or not 0 <= maximum_hops <= 3 or engine not in {"graph", "bm25"}:
        raise ValueError("Choose graph or bm25 and a depth from 0 to 3")

    def admissible(unit, *, context=False):
        # Inputs: unit, context.
        # Does: Apply the query's version bounds to a result or context unit.
        # Output: A boolean eligibility decision.
        origin, target = unit["version_from"], unit["version_to"]
        if not context:
            return matches_transition(unit, first, last)
        if origin and target:
            return first <= version_key(origin) < version_key(target) <= last
        return context and all(first <= version_key(value) <= last
                               for value in (origin, target) if value)

    crossing = cross_module(database, module, module_name=module_name) if engine == "graph" else None
    code = crossing["input"] if crossing else read_code(module, module_name)
    with connect(database) as con:
        metadata = meta(con)
        if metadata.get("layout") != "normalized-units":
            raise ValueError("Rebuild this collection with r2 build for normalized-unit search")
        if crossing and metadata["collection_revision"] != crossing["collection"]["revision"]:
            raise ValueError("Collection changed during search")
        units = {unit["id"]: unit for unit in load(con, "information_units")}
        sources = {source["id"]: source for source in load(con, "sources")}
        observations = {uid: changed_observations(unit) if unit["kind"] == "diff_hunk" else []
                        for uid, unit in units.items() if admissible(unit)}
        layers = {uid: sorted(set(units[uid]["layers"]) | (
                  {"xml"} if any(entity["rule"] == "xpath_attribute_v1" for entity in entities) else set()))
                  for uid, entities in observations.items()}
        eligible = {uid for uid, unit_layers in layers.items() if layer == "all" or layer in unit_layers}
        keys = {uid: diff_key(units[uid]) if units[uid]["kind"] == "diff_hunk" else (uid,) for uid in eligible}
        change_ids = {}
        for uid in sorted(eligible):
            change_ids.setdefault(keys[uid], uid)
        graph = None
        paths, scores = {}, {}
        if engine == "graph":
            stage_started = perf_counter()
            graph = execute_query(crossing, database, maximum_hops=maximum_hops)
            if timings is not None:
                timings["relations_seconds"] = perf_counter() - stage_started
            if graph["collection"] != crossing["collection"]:
                raise ValueError("Collection changed during relation extraction")
            paths = graph_hits(graph, units, admissible)
            ordered = sorted(eligible & paths.keys(), key=lambda uid: (len(paths[uid][1]),
                             units[uid]["normalization_status"] != "valid", uid))
        else:
            stage_started = perf_counter()
            terms = sorted(term_counts(" ".join(entity["name"] for entity in code["entities"])))
            if terms:
                expression = " OR ".join(f'"{term}"' for term in terms)
                scores = {row[0]: row[1] for row in con.execute(
                    "SELECT unit_id, bm25(unit_search) FROM unit_search WHERE unit_search MATCH ?",
                    (expression,)) if row[0] in eligible}
            ordered = sorted(scores, key=lambda uid: (scores[uid], uid))
            if timings is not None:
                timings["bm25_units_seconds"] = perf_counter() - stage_started

    direct = {row["information_unit_id"]: row["evidences"] for row in crossing["results"]} if crossing else {}
    edge_by_id = {edge["id"]: edge for edge in graph["edges"]} if graph else {}
    results = []
    by_layer, by_depth = Counter(), Counter()
    migrations, methods = set(), set()
    seen = set()
    for uid in ordered:
        unit = units[uid]
        change_id = change_ids[keys[uid]]
        if change_id in seen:
            continue
        seen.add(change_id)
        data = unit["data"]
        path, edge_ids = paths.get(uid, ([], []))
        depth = len(edge_ids) if path else None
        by_layer.update(layers[uid])
        if depth is not None:
            by_depth[str(depth)] += 1
        migration_id = sources[unit["source_id"]].get("binding", {}).get("migration_id")
        if isinstance(migration_id, str) and migration_id:
            migrations.add(migration_id)
        methods.update((entity["context"]["model"], entity["name"]) for entity in observations[uid]
                       if entity["type"] in {"method", "method_reference"} and entity["context"].get("model"))
        if len(results) < limit:
            is_diff = unit["kind"] == "diff_hunk"
            title = (f"Observed diff in {data['file_path']}" if is_diff else
                     data.get("heading") or data.get("pr_title") or unit["source_locator"]["artifact_path"].rsplit("/", 1)[-1])
            results.append(dict(change_id=change_id, title=title,
                                status="candidate", layers=layers[uid], source_layers=unit["layers"], depth=depth,
                                before=data["removed"] if is_diff else "",
                                after=data["added"] if is_diff else unit["text"], source=citation(unit),
                                path=[citation(units[node]) for node in path],
                                relations=[edge_by_id[edge] for edge in edge_ids],
                                module_evidence=direct.get(path[0], []) if path else [],
                                bm25_score=scores.get(uid), warnings=unit["warnings"]))

    warnings = list(metadata["warnings"])
    warnings.extend(f"Acquisition unit {entry['id']}: {entry['reason']}" for entry in metadata["excluded"])
    if metadata["normalization_issues"]:
        warnings.append("Some admitted artifacts could not be normalized; see collection metadata.")
    if code["errors"] or code["limitations"] or (graph and graph["status"] == "partial"):
        warnings.append("Some technical observations are incomplete.")
    if engine == "graph" and not crossing["matched_unit_ids"]:
        warnings.append("No exact technical seeds were found.")
    report = dict(schema_version=1, collection_revision=metadata["collection_revision"], engine=engine,
                  ranking_version="depth-fidelity-id-2" if engine == "graph" else "fts5-score-id-2",
                  query=dict(from_version=from_version, to_version=to_version, layer=layer, limit=limit,
                             maximum_hops=maximum_hops, module_name=code["module_name"],
                             input_revision=code["input_revision"]),
                  summary=dict(changes_found=len(seen), changes_shown=len(results),
                               eligible_units=len(eligible), eligible_distinct_changes=len(change_ids),
                               matching_migrations=len(migrations),
                               methods_with_documented_changes=len(methods),
                               changes_by_layer=dict(sorted(by_layer.items())),
                               new_findings_by_depth=dict(sorted(by_depth.items()))),
                  results=results, warnings=sorted(set(warnings)))
    validate_report(report)
    return report, crossing, graph


def validate_report(report):
    # Inputs: report.
    # Does: Check the report scope, counts and traceable evidence.
    # Output: True or a validation error.
    query, summary = report["query"], report["summary"]
    results = report["results"]
    if report["schema_version"] != 1 or report["engine"] not in {"graph", "bm25"}:
        raise ValueError("Unsupported report schema or engine")
    first, last = version_key(query["from_version"]), version_key(query["to_version"])
    if first >= last or query["layer"] not in LAYERS | {"all"} or not 0 <= query["maximum_hops"] <= 3:
        raise ValueError("Invalid report query scope")
    if not (len(results) == summary["changes_shown"] == min(query["limit"], summary["changes_found"])
            and 1 <= query["limit"] <= 10
            and summary["changes_found"] <= summary["eligible_distinct_changes"] <= summary["eligible_units"]
            and len({row["change_id"] for row in results}) == len(results)):
        raise ValueError("Report counts, limits or unique change IDs are inconsistent")
    if report["engine"] == "graph" and sum(summary["new_findings_by_depth"].values()) != summary["changes_found"]:
        raise ValueError("Depth counts must include every graph result")
    for row in results:
        source = row["source"]
        if not source["unit_id"] or not source["locator"].get("artifact_path"):
            raise ValueError("A result must cite its own localized source")
        scope = dict(kind=source.get("kind", "diff_hunk"), version_from=source["from_version"],
                     version_to=source["to_version"])
        if (not matches_transition(scope, first, last)
                or (query["layer"] != "all" and query["layer"] not in row["layers"])):
            raise ValueError("Result falls outside the requested transition or layer")
        if report["engine"] == "graph":
            path = [step["unit_id"] for step in row["path"]]
            if (not path or path[-1] != source["unit_id"] or len(set(path)) != len(path)
                    or len(path) - 1 != row["depth"] or row["depth"] > query["maximum_hops"]
                    or len(row["relations"]) != row["depth"] or not row["module_evidence"]
                    or any(ev["information_unit_id"] != path[0] for ev in row["module_evidence"])):
                raise ValueError("Graph result lacks a valid path from the module")
            for left, right, edge in zip(path, path[1:], row["relations"]):
                if {edge["left"], edge["right"]} != {left, right} or not edge["matches"]:
                    raise ValueError("Path edge lacks evidence for its endpoints")
        elif row["path"] or row["relations"] or row["depth"] is not None or row["bm25_score"] is None:
            raise ValueError("BM25 result must use lexical scoring")
    return True


def render_report(report):
    # Inputs: report.
    # Does: Format the report summary, evidence and warnings for the terminal.
    # Output: The rendered report text.
    summary = report["summary"]
    lines = [f"Changes found / shown: {summary['changes_found']} / {summary['changes_shown']}",
             f"Matching migrations: {summary['matching_migrations']}",
             f"Methods with documented changes: {summary['methods_with_documented_changes']}",
             f"Changes by layer: {summary['changes_by_layer']}",
             f"New findings by depth: {summary['new_findings_by_depth']}"]
    for result in report["results"]:
        source = result["source"]
        lines.append(f"- {result['title']} [{result['status']}] | "
                     f"{source['from_version'] or '?'} -> {source['to_version']} | {', '.join(result['layers'])}")
        lines.append(f"  Source: {source['url'] or '(local artifact)'} | {source['locator']}")
        if result["path"]:
            evidence = result["module_evidence"][0]["input_entity"]["location"]
            lines.append(f"  Module: {evidence['code_path']} | line {evidence.get('code_line') or evidence.get('content_line')}")
            lines.append("  Path: " + " -> ".join(step["unit_id"] for step in result["path"]))
    lines.extend(f"Warning: {warning}" for warning in report["warnings"])
    return "\n".join(lines)
