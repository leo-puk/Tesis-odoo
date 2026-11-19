"""Measure the active pipeline with explicit, independent relevance judgments."""
import json
import platform
from statistics import median
from time import perf_counter

from ..records import connect, load, meta
from ..report import render_report, search_units


def coverage(references, units):
    # Inputs: references, units.
    # Does: Check which reference changes have admitted evidence in the corpus.
    # Output: The reference coverage result.
    covered = set()
    for ref_id, reference in references.items():
        for unit_id in reference["available_unit_ids"]:
            unit = units.get(unit_id)
            if unit is None or not unit["source_url"] or (
                    unit["version_from"], unit["version_to"]
            ) != (reference["from_version"], reference["to_version"]):
                raise ValueError(f"Coverage evidence for {ref_id} must exist and match the reference transition")
            covered.add(ref_id)
    return covered


def score(report, judgments, expected):
    # Inputs: report, judgments, expected.
    # Does: Apply reviewed judgments to ranked candidates.
    # Output: Precision and reference coverage metrics where defined.
    shown = [result["change_id"] for result in report["results"]]
    unjudged = [uid for uid in shown if uid not in judgments]
    relevant = [uid for uid in shown if uid in judgments and judgments[uid]["relevant"]]
    covered = {ref for uid in relevant for ref in judgments[uid]["reference_ids"]}
    return dict(P1=100 * len(relevant) / len(shown) if shown and not unjudged else None,
                C2=100 * len(covered) / len(expected) if expected and not unjudged else None,
                structural_V1=True, shown=shown, unjudged=unjudged, covered_reference_ids=sorted(covered),
                relevant_outside_reference=[uid for uid in relevant if not judgments[uid]["reference_ids"]])


def evaluate(database, specification, base, *, repeats=1):
    # Inputs: database, specification, base, repeats.
    # Does: Compare graph and BM25 on the same corpus and reviewed judgments.
    # Output: Coverage, per-query scores and timing.
    if type(repeats) is not int or repeats < 1:
        raise ValueError("Repetitions must be positive")
    reviewer = specification["reviewer"]
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("An explicit reviewer is required")
    with connect(database) as con:
        metadata = meta(con)
        if metadata.get("layout") != "normalized-units":
            raise ValueError("Evaluation requires a normalized-unit collection")
        units = {row["id"]: row for row in load(con, "information_units")}
    if specification["collection_revision"] != metadata["collection_revision"]:
        raise ValueError("Judgments must refer to the current collection revision")
    references = specification["references"]
    covered = coverage(references, units)
    cases, seen = [], set()
    for query in specification["queries"]:
        query_id = query["id"]
        if query_id in seen:
            raise ValueError("Duplicate evaluation query ID")
        seen.add(query_id)
        parameters = {key: query[key] for key in ("from_version", "to_version", "layer", "maximum_hops", "limit")}
        parameters["module_name"] = query.get("module_name")
        expected, judgments = set(query["reference_ids"]), query["judgments"]
        if not expected <= references.keys():
            raise ValueError("Query references an unknown change")
        for uid, judgment in judgments.items():
            refs = set(judgment["reference_ids"])
            if (uid not in units or type(judgment["relevant"]) is not bool
                    or not refs <= expected or (refs and not judgment["relevant"])):
                raise ValueError("Invalid relevance judgment")
            for ref_id in refs:
                unit, reference = units[uid], references[ref_id]
                if (unit["version_from"], unit["version_to"]) != (reference["from_version"], reference["to_version"]):
                    raise ValueError("A judgment maps results to a different transition")
        reports, samples = {}, {"graph": [], "bm25": []}
        for repeat in range(repeats):
            for engine in (("graph", "bm25") if repeat % 2 == 0 else ("bm25", "graph")):
                started = perf_counter()
                report, _, _ = search_units(database, base / query["module"], engine=engine, **parameters)
                render_report(report)
                json.dumps(report, ensure_ascii=False, allow_nan=False)
                samples[engine].append(perf_counter() - started)
                if report["collection_revision"] != metadata["collection_revision"]:
                    raise ValueError("Collection changed during evaluation")
                if engine in reports and report != reports[engine]:
                    raise ValueError("Search results changed across repetitions")
                reports[engine] = report
        graph, bm25 = reports["graph"], reports["bm25"]
        if graph["query"] != bm25["query"] or graph["summary"]["eligible_units"] != bm25["summary"]["eligible_units"]:
            raise ValueError("Engines used different query inputs or eligible corpora")
        if query["input_revision"] != graph["query"]["input_revision"]:
            raise ValueError("Judgments must refer to the original code revision")
        scores = {engine: dict(**score(report, judgments, expected),
                             T1_seconds=samples[engine], median_T1_seconds=median(samples[engine]))
                  for engine, report in reports.items()}
        p_graph, p_bm25 = scores["graph"]["P1"], scores["bm25"]["P1"]
        cases.append(dict(id=query_id, query=graph["query"], engines=scores,
                          P1_difference=p_graph - p_bm25 if p_graph is not None and p_bm25 is not None else None))
    if not cases:
        raise ValueError("At least one evaluation query is required")
    by_transition, by_migration = {}, {}
    for ref_id, reference in references.items():
        for groups, key in ((by_transition, reference["from_version"] + " -> " + reference["to_version"]),
                            (by_migration, reference["migration_id"])):
            group = groups.setdefault(key, {"reference_count": 0, "covered_count": 0})
            group["reference_count"] += 1
            group["covered_count"] += ref_id in covered
    return dict(schema_version=1, collection_revision=metadata["collection_revision"], reviewer=reviewer,
                C1=100 * len(covered) / len(references) if references else None,
                reference_count=len(references), covered_reference_ids=sorted(covered),
                C1_by_transition=by_transition, C1_by_migration=by_migration, queries=cases,
                timing=dict(repeats=repeats, environment=platform.platform(),
                            order="Alternated per repetition", cache="Uncontrolled operating-system cache",
                            boundary="Search through rendered and serialized first view and summary"),
                V1_scope="Automated structure and evidence paths; independent English review is required",
                protocol_status="Independent sampling and admission audit must be documented separately")
