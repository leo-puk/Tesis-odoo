"""Terminal charts derived from saved query evidence and shortest-path predecessors."""
from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import textwrap

from .crossing.engine import validate_result
from .relations.serialization import validate_graph
from .report import validate_report


def graph_statistics(report, crossing=None, graph=None, level=None):
    validate_report(report)
    stats = {"collection_revision": report["collection_revision"], "engine": report["engine"],
             "level": level, "summary": report["summary"], "nodes_by_level": {},
             "node_matches": {}, "attributes": {}, "edge_paths": {},
             "node_labels": {}, "edge_labels": {}}
    if graph is None:
        return stats
    validate_graph(graph)
    validate_result(crossing)
    if (graph["collection"]["revision"] != report["collection_revision"]
            or crossing["result_id"] != graph["crossing"]["result_id"]
            or crossing["input"]["input_revision"] != report["query"]["input_revision"]
            or graph["maximum_hops"] != report["query"]["maximum_hops"]):
        raise ValueError("Chart artifacts refer to different collections or module inputs")
    nodes = {node["unit_id"]: node for node in graph["nodes"]}
    chosen = {uid for uid, node in nodes.items() if level is None or node["minimum_hops"] == level}
    depths = Counter(str(n["minimum_hops"]) for n in nodes.values())
    stats["nodes_by_level"] = {str(depth): depths[str(depth)] for depth in range(graph["maximum_hops"] + 1)}
    matches, attributes = Counter(), Counter()
    locations = {}

    def remember_location(uid, observation):
        location = observation.get("location", {})
        path = location.get("code_path") or location.get("artifact_path")
        if path:
            label = path + f" [diff L{location.get('line_start', '?')}]"
            locations[uid] = min(locations.get(uid, label), label)

    for row in crossing["results"]:
        uid = row["information_unit_id"]
        for evidence in row["evidences"]:
            remember_location(uid, evidence.get("unit_entity", {}))
        if uid in chosen:
            matches[uid] += len(row["evidences"])
            attributes.update(" / ".join(ev["identity"]) for ev in row["evidences"])
    for edge in graph["edges"]:
        for match in edge["matches"]:
            for side in ("left", "right"):
                endpoint = match.get(side, {})
                if endpoint:
                    remember_location(endpoint["unit_id"], endpoint["observation"])
        for uid in (edge["left"], edge["right"]):
            if uid in chosen:
                matches[uid] += edge["raw_match_count"]
                attributes.update(" / ".join(ev["identity"]) for ev in edge["matches"])
    # Dynamic programming counts every shortest path once, including tied predecessors.
    ordered = sorted(nodes, key=lambda uid: (nodes[uid]["minimum_hops"], uid))
    prefixes = {}
    suffixes = {uid: int(uid in chosen) for uid in nodes}
    for uid in ordered:
        node = nodes[uid]
        prefixes[uid] = 1 if node["is_seed"] else sum(prefixes[p["unit_id"]] for p in node["predecessors"])
    paths = Counter()
    for uid in reversed(ordered):
        for predecessor in nodes[uid]["predecessors"]:
            parent = predecessor["unit_id"]
            paths[predecessor["edge_id"]] += prefixes[parent] * suffixes[uid]
            suffixes[parent] += suffixes[uid]
    stats.update(node_matches=dict(matches), attributes=dict(attributes),
                 edge_paths={edge: count for edge, count in paths.items() if count},
                 node_labels=locations,
                 edge_labels={edge["id"]: f"{locations.get(edge['left'], edge['left'])} <-> "
                              f"{locations.get(edge['right'], edge['right'])}" for edge in graph["edges"]})
    return stats


def bars(title, counts, *, top, width, ascii_only, labels=None, maximum=None, ranked=True):
    lines = [title]
    rows = sorted(counts.items(), key=lambda pair: (-pair[1], str(pair[0]))) if ranked else list(counts.items())
    rows = rows[:top]
    if not rows:
        return title + "\n  (no observations)"
    digits = max(len(f"{value:,}") for _, value in rows)
    bar_width = min(40, max(1, width - digits - 8))
    maximum = max(value for _, value in rows) if maximum is None else maximum
    glyph = "#" if ascii_only else "█"
    try:
        glyph.encode(sys.stdout.encoding or "utf-8")
    except UnicodeEncodeError:
        glyph = "#"
    for rank, (key, value) in enumerate(rows, start=1):
        label = str((labels or {}).get(key, key))
        lines.extend(textwrap.wrap(f"{rank}. {label}", width=width - 2,
                                   initial_indent="  ", subsequent_indent="     "))
        length = max(1, round(bar_width * value / maximum)) if value else 0
        lines.append(f"     {glyph * length:<{bar_width}}  {value:>{digits},}")
    return "\n".join(lines)


def render_charts(stats, *, top=10, width=None, ascii_only=False):
    width = width or min(shutil.get_terminal_size((100, 24)).columns, 120)
    options = dict(top=top, width=width, ascii_only=ascii_only)
    summary = stats["summary"]
    sections = [f"R2 {stats['engine']} | level {stats['level'] if stats['level'] is not None else 'all'}",
                f"Collection {stats['collection_revision'][:12]} | bars scaled within each chart",
                bars("Candidates and first view", {
                    "Eligible distinct changes": summary["eligible_distinct_changes"],
                    "Retrieved changes": summary["changes_found"], "Shown changes": summary["changes_shown"],
                }, **options)]
    if stats["engine"] == "graph":
        sections.extend([
            bars("Reached nodes by minimum level (whole extracted graph)", stats["nodes_by_level"],
                 labels={"0": "Level 0 - direct matches", "1": "Level 1 - one hop",
                         "2": "Level 2 - two hops", "3": "Level 3 - three hops"},
                 ranked=False, **(options | {"top": 4})),
            bars("Nodes by evidence incidences", stats["node_matches"], labels=stats.get("node_labels"), **options),
            bars("Technical attributes by evidence incidences", stats["attributes"], **options),
            bars("Edges by shortest-path participation to selected levels", stats["edge_paths"],
                 labels=stats.get("edge_labels"), **options),
            textwrap.fill("Node/attribute counts include direct crossing evidence and incident edge matches.", width),
            textwrap.fill("An edge match contributes once per selected endpoint. Path counts include tied paths.", width),
            textwrap.fill("Graph scope includes context units before final query filters. Counts describe structure.", width),
        ])
    return "\n\n".join(sections)


def load_charts(path, level=None):
    folder = path if path.is_dir() else path.parent
    report_path = folder / "report.json" if path.is_dir() else path
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    crossing = graph = None
    if report["engine"] == "graph":
        crossing = json.loads((folder / "crossing.json").read_text(encoding="utf-8-sig"))
        graph = json.loads((folder / "relations.json").read_text(encoding="utf-8-sig"))
    return graph_statistics(report, crossing, graph, level)


def render_evaluation(evaluation, *, top=10, width=None, ascii_only=False):
    width = width or min(shutil.get_terminal_size((100, 24)).columns, 120)
    options = dict(top=top, width=width, ascii_only=ascii_only)
    sections = ["R2 evaluation | percentages"]
    if evaluation.get("C1") is None:
        sections.append("C1: None")
    else:
        sections.append(bars("Collection coverage (%)", {"C1": round(evaluation["C1"], 2)}, maximum=100, **options))
    for metric in ("P1", "C2"):
        values, missing = {}, []
        for query in evaluation["queries"]:
            for engine, score in query["engines"].items():
                key = f"{query['id']} / {engine}"
                value = score.get(metric)
                if value is None:
                    missing.append(key)
                else:
                    values[key] = round(value, 2)
        sections.append(bars(metric + " (%)", values, maximum=100, **options))
        if missing:
            sections.append("Pending/undefined " + metric + ": " + ", ".join(missing))
    return "\n\n".join(sections)
