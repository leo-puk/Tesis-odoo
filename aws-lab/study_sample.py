"""Freeze the study cohort using admitted references and their original queries."""
from collections import defaultdict
from statistics import mean

from experimentos import ENGINES, digest, now, read, save


def freeze_sample(output, manifest):
    candidates, fingerprints = defaultdict(lambda: defaultdict(list)), {}
    for case in manifest["cases"]:
        case_id = case["id"]
        state_path = output / "cases" / case_id / "latest.json"
        if not state_path.is_file() or (state := read(state_path))["status"] != "completed":
            raise ValueError(f"Complete {case_id} before freezing the study sample")
        path = output / state["attempt"] / "evaluation-spec.json"
        spec = read(path)
        if not spec.get("review_packet_sha256"):
            raise ValueError(f"Apply the review for {case_id} before freezing the study sample")
        packet = path.parent / "review" / "packet.json"
        if digest(packet) != spec["review_packet_sha256"]:
            raise ValueError(f"The dossier changed after importing the review for {case_id}")
        fingerprints[case_id] = dict(attempt=state["attempt"], spec_sha256=digest(path),
                                     packet_sha256=spec["review_packet_sha256"])
        commits = {f"{commit['repository']}@{commit['sha']}": commit for commit in spec["admitted_migrations"]}
        jump = f"{case['version_from']}->{case['version_to']}"
        for rid, reference in spec["references"].items():
            queries = sorted(query["id"] for query in spec["queries"] if rid in query["reference_ids"])
            for identity in reference["commit_ids"]:
                if identity in commits:
                    candidates[jump][commits[identity]["sha"]].append(
                        dict(commit=commits[identity], case=case_id, reference=rid,
                             hunk_ids=reference["hunk_ids"], queries=queries))
    jumps = sorted({f"{case['version_from']}->{case['version_to']}" for case in manifest["cases"]})
    if len(jumps) != 3:
        raise ValueError("The study requires three distinct version jumps")
    selected, used = [], set()
    for jump in jumps:
        available = sorted(set(candidates[jump]) - used)
        if len(available) < 10:
            raise ValueError(f"{jump} has {len(available)} distinct eligible MIGs; the frozen sample requires 10")
        for sha in available[:10]:
            used.add(sha)
            links = candidates[jump][sha]
            selected.append(dict(jump=jump, sha=sha, links=links))
    path = output / "study-sample.json"
    sample = dict(schema_version=1, rule="First ten distinct admitted MIG SHAs per jump, in SHA order",
                  cases=fingerprints, migrations=selected)
    if path.exists():
        existing = read(path)
        if sample != {key: value for key, value in existing.items() if key != "created_at"}:
            raise ValueError("A different study sample is already frozen for this batch")
    else:
        save(path, dict(created_at=now(), **sample))
    return path


def validate_sample(output, sample):
    for case, expected in sample["cases"].items():
        state = read(output / "cases" / case / "latest.json")
        attempt = output / state["attempt"]
        if (state["status"] != "completed" or state["attempt"] != expected["attempt"] or
                digest(attempt / "evaluation-spec.json") != expected["spec_sha256"] or
                digest(attempt / "review" / "packet.json") != expected["packet_sha256"]):
            raise ValueError(f"Evidence or review changed after the study sample was frozen for {case}")


def coverage_label(covered, expected):
    return "covered" if covered == expected else "partial" if covered else "uncovered"


def paired_precision(queries):
    pairs = [query["engines"] for query in queries
             if all(query["engines"][engine]["P1"] is not None for engine in ENGINES)]
    means = {engine: mean(pair[engine]["P1"] for pair in pairs) if pairs else None for engine in ENGINES}
    difference = means["graph"] - means["bm25"] if pairs else None
    return dict(P1_defined_pairs=len(pairs), P1_macro_paired=means, P1_difference=difference,
                graph_exceeds_bm25=difference > 0 if difference is not None else None)


def sample_metrics(sample, evaluated):
    query_ids, expected = set(), defaultdict(set)
    references = {(link["case"], link["reference"])
                  for entry in sample["migrations"] for link in entry["links"]}
    for entry in sample["migrations"]:
        for link in entry["links"]:
            for qid in link["queries"]:
                query_ids.add(qid)
                expected[qid].add(link["reference"])
    queries = [query for value in evaluated.values() for query in value["queries"] if query["id"] in query_ids]
    by_query = {query["id"]: query for query in queries}
    migrations = []
    for entry in sample["migrations"]:
        pairs = {(link["case"], link["reference"]) for link in entry["links"]}
        covered = sum(rid in evaluated[case]["covered_reference_ids"] for case, rid in pairs)
        label = coverage_label(covered, len(pairs))
        recovered = {engine: {(link["case"], link["reference"]) for link in entry["links"]
                              if any(link["reference"] in by_query[qid]["engines"][engine]["covered_reference_ids"]
                                     for qid in link["queries"])} for engine in ENGINES}
        migrations.append(dict(sha=entry["sha"], jump=entry["jump"], status=label, covered=label == "covered",
            covered_corrections=covered, reference_corrections=len(pairs),
            first_view={engine: coverage_label(len(recovered[engine]), len(pairs)) for engine in ENGINES}))
    covered_refs = sum(rid in evaluated[case]["covered_reference_ids"] for case, rid in references)
    c2 = {engine: mean(100 * len(expected[query["id"]] & set(query["engines"][engine]["covered_reference_ids"])) /
                       len(expected[query["id"]]) for query in queries) if queries else None for engine in ENGINES}
    return dict(migrations=migrations, query_count=len(queries), C1=100 * covered_refs / len(references),
                C2_macro=c2, **paired_precision(queries))
