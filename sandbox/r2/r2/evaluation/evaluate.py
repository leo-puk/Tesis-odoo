"""C1/P1/C2: explicit units, external judgments and counterbalanced timing."""
import json
import os
import platform
import sqlite3
import sys
import time
import hashlib
from pathlib import Path
from importlib.metadata import version
import pandas as pd
from sklearn.metrics import precision_score, recall_score
from ..collection import connect, load, meta
from ..query import retrieve, validate_output, render_text, SEED_POLICY, RANKING
from ..selection import fingerprint, code_revision


def environment():
    return dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
                processor=platform.processor(), cpu_count=os.cpu_count(), sqlite=sqlite3.sqlite_version,
                packages={p: version(p) for p in ("networkx", "lxml", "pandas", "scikit-learn")})


def measure(database, module, from_version, to_version, **options):
    start = time.perf_counter()
    output = retrieve(database, module, from_version, to_version, **options)
    validation = validate_output(output)
    if not validation["automatic_structural_conformant"]:
        raise ValueError("Nonconformant output: " + str(validation["errors"]))
    json.dumps(output, ensure_ascii=False, allow_nan=False)
    render_text(output)
    return output, dict(internal_seconds=output["elapsed_seconds"],
                        until_validated_serialized_view_seconds=time.perf_counter()-start,
                        boundary="retrieval entry through validation and first JSON/text serialization; excludes terminal I/O")


def query_identity(q, base):
    root = (Path(base)/q["module"]).resolve()
    files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(root.rglob("*")) if p.is_file() and p.suffix in {".py", ".xml", ".csv"} and ".git" not in p.parts}
    return dict(parameters={k: v for k, v in q.items() if k not in {"judgments", "human_output_review"}}, files=files)


def checked_refs(specification, changes):
    references = specification["references"]
    if len({r["id"] for r in references}) != len(references):
        raise ValueError("Reference IDs must be unique")
    for ref in references:
        for field in ("module_id", "from_version", "to_version", "element", "justification"):
            if not ref.get(field):
                raise ValueError(f"Reference {ref['id']} lacks {field}")
        if ref.get("category") in {"format", "administrative", "documentation"} and ref.get("evaluable", True):
            raise ValueError("Non-migration changes must be separated from the evaluable denominator")
        for key in ref.get("covered_by", []):
            c = changes.get(key)
            if not c or c["status"] != "verified" or c.get("destination_validity", {}).get("status") != "checked":
                raise ValueError("C1 coverage requires verified destination-valid evidence")
            if c.get("category") in {"format", "administrative", "documentation"}:
                raise ValueError("C1 cannot count non-migration administrative/format changes as coverage")
            if (c["from_version"], c["to_version"]) != (ref["from_version"], ref["to_version"]):
                raise ValueError("C1 correspondence has the wrong jump")
            if ref["element"] not in c.get("affected_elements", c["elements"]):
                raise ValueError("C1 correspondence has the wrong element")
            if not c.get("evidence_ids"):
                raise ValueError("C1 correspondence has no concrete evidence")
    return references


def evaluate(database, specification, base, *, include_oca_migrations=False, repeats=1,
             development=False, output_dir=None):
    if include_oca_migrations:
        raise ValueError("The OCA inclusion switch was removed")
    if not 1 <= repeats <= 100 or not specification.get("reviewer"):
        raise ValueError("Evaluation requires a real reviewer and 1–100 repetitions")
    with connect(database) as con:
        collection = meta(con)
        changes = {c["id"]: c for c in load(con, "changes")}
    queries = specification["queries"]
    if len({q["id"] for q in queries}) != len(queries):
        raise ValueError("Duplicate query IDs")
    identities = [query_identity(q, base) for q in queries]
    if not development:
        from ..graph import BACKEND
        if BACKEND != "networkx.bfs_layers" or not collection.get("assignment_audited"):
            raise ValueError("Academic execution requires real NetworkX and audited assignments")
        if not specification.get("protocol_file"):
            raise ValueError("A frozen protocol is required; --development is only for engineering checks")
        protocol = json.loads((Path(base)/specification["protocol_file"]).read_text(encoding="utf-8-sig"))
        content = {k: v for k, v in protocol.items() if k != "protocol_revision"}
        if (fingerprint(content) != protocol.get("protocol_revision") or protocol["code_revision"] != code_revision() or
                protocol["collection_revision"] != collection["collection_revision"] or
                protocol["parameters"].get("queries_revision") != fingerprint(identities)):
            raise ValueError("Frozen protocol does not match code, collection or queries")
        if set(protocol["selected_cases"]) != {q.get("case_id") for q in queries} or protocol["parameters"].get("reference_revision") != fingerprint(specification["references"]):
            raise ValueError("Cases or reference correspondences differ from the frozen evaluation")
        params = protocol["parameters"]
        if (params["seed_policy"] != SEED_POLICY or params["ranking"] != RANKING or
                params["repeats"] != repeats or params["cache_state"] != specification.get("cache_state")):
            raise ValueError("Parameters differ from the frozen protocol")
        for q in queries:
            if any(q.get(k) != params[k] for k in ("status", "limit", "depth")):
                raise ValueError("Query filters differ from the frozen protocol")
    references = checked_refs(specification, changes)
    ref_map = {r["id"]: r for r in references}
    rows, measurements, extras, module_coverage, module_elements = [], [], [], {}, {}
    for qi, q in enumerate(queries):
        if any(k not in q for k in ("status", "limit", "depth", "module_id")) or q["status"] != "verified":
            raise ValueError("Queries must fix module_id, verified status, limit and depth")
        expected = set(q["reference_ids"])
        if not expected <= ref_map.keys():
            raise ValueError("Unknown query reference IDs")
        for key in expected:
            ref = ref_map[key]
            if (not ref.get("evaluable", True) or ref["module_id"] != q["module_id"] or
                    (ref["from_version"], ref["to_version"]) != (q["from_version"], q["to_version"])):
                raise ValueError("Query/reference has incompatible module or jump")
        runs = {"graph": [], "bm25": []}
        for rep in range(repeats):
            order = ("graph", "bm25") if (qi+rep) % 2 == 0 else ("bm25", "graph")
            for position, engine in enumerate(order):
                output, timing = measure(database, Path(base)/q["module"], q["from_version"], q["to_version"],
                                         engine=engine, layer=q.get("layer", "all"), depth=q["depth"], limit=q["limit"],
                                         status=q["status"], module_name=q.get("module_name"), include_oca_migrations=include_oca_migrations)
                runs[engine].append(output)
                module_elements.setdefault((q["module_id"], q["from_version"], q["to_version"]), set()).update(output["query"]["elements"])
                measurements.append(dict(query_id=q["id"], engine=engine, repetition=rep, position=position,
                                         graph_implementation=output["graph_implementation"], **timing))
        for engine, outputs in runs.items():
            ids = [r["id"] for r in outputs[0]["results"]]
            if any([r["id"] for r in o["results"]] != ids for o in outputs):
                raise ValueError("Repeated executions changed the first view")
            results, judgments = outputs[0]["results"], q["judgments"]
            missing = set(ids)-judgments.keys()
            if missing:
                raise ValueError(f"Unjudged results for {q['id']} {engine}: {sorted(missing)}")
            labels, found = [], set()
            for result in results:
                j = judgments[result["id"]]
                if not all(isinstance(j.get(k), bool) for k in ("relevant", "applicable")) or not j.get("justification"):
                    raise ValueError("Judgments require relevant/applicable booleans and justification")
                linked = set(j.get("reference_ids", []))
                if not linked <= expected:
                    raise ValueError("Judgment links a reference outside its query")
                correct = j["relevant"] and j["applicable"]
                if linked and not correct:
                    raise ValueError("Irrelevant entries cannot cover reference changes")
                labels.append(correct)
                if correct:
                    found.update(linked)
                    if not linked:
                        extras.append(dict(query_id=q["id"], engine=engine, change_id=result["id"], justification=j["justification"]))
            p1 = 100*precision_score(labels, [True]*len(labels), zero_division=0) if labels else None
            c2 = 100*recall_score([True]*len(expected), [key in found for key in sorted(expected)], zero_division=0) if expected else None
            human = q.get("human_output_review", {}).get(engine, {})
            v1 = float(human["english_checked"]) if isinstance(human.get("english_checked"), bool) and human.get("reviewer") else None
            rows.append(dict(query_id=q["id"], module=q["module_id"], jump=f"{q['from_version']}->{q['to_version']}",
                             engine=engine, status=q["status"], limit=q["limit"], depth=q["depth"], returned=len(results),
                             P1=float(p1) if p1 is not None else None, C2=float(c2) if c2 is not None else None,
                             V1=v1, V1_automatic=1.0, human_V1_pending=v1 is None, empty=not results))
            union = module_coverage.setdefault((q["module_id"], q["from_version"], q["to_version"], engine), dict(expected=set(), covered=set()))
            union["expected"].update(expected); union["covered"].update(found)
    for ref in references:
        for change_id in ref.get("covered_by", []):
            available = module_elements.get((ref["module_id"], ref["from_version"], ref["to_version"]), set())
            if not set(changes[change_id].get("required_elements", [])) <= available:
                raise ValueError("C1 correspondence does not satisfy the change applicability conditions")
    frame = pd.DataFrame(rows)
    summary = {}
    for engine in ("graph", "bm25"):
        part = frame[frame.engine == engine] if not frame.empty else pd.DataFrame()
        summary[engine] = {metric+"_macro": (None if part.empty or part[metric].dropna().empty else float(part[metric].mean())) for metric in ("P1", "C2", "V1")}
        summary[engine]["empty_queries"] = int(part["empty"].sum()) if not part.empty else 0
    refs_frame = pd.DataFrame([dict(id=r["id"], module=r["module_id"], jump=f"{r['from_version']}->{r['to_version']}",
                                    covered=bool(r.get("covered_by"))) for r in references if r.get("evaluable", True)])
    c1 = float(refs_frame.covered.mean()*100) if not refs_frame.empty else None
    by_jump = (refs_frame.groupby(["module", "jump"]).covered.agg(["sum", "count", "mean"]).reset_index()
               if not refs_frame.empty else pd.DataFrame())
    if not by_jump.empty:
        by_jump["C1"] = by_jump["mean"]*100
    report = dict(schema_version=2, development_only=development, reviewer=specification["reviewer"],
                  collection_revision=collection["collection_revision"], code_revision=code_revision(), queries_revision=fingerprint(identities),
                  C1=c1, C1_evaluable=len(refs_frame), C1_covered=int(refs_frame.covered.sum()) if not refs_frame.empty else 0,
                  C1_by_module_jump=by_jump.to_dict("records"), queries=rows, summary=summary,
                  valid_findings_absent_from_MIG=extras, measurements=measurements,
                  module_union=[dict(module=k[0], from_version=k[1], to_version=k[2], engine=k[3],
                                     C2=100*len(v["covered"])/len(v["expected"]) if v["expected"] else None) for k,v in sorted(module_coverage.items())],
                  P1_aggregation="macro_defined_queries", environment=environment(),
                  timing=dict(cache_state=specification.get("cache_state", "uncontrolled"), repetitions=repeats,
                              order="alternating_by_query_and_repetition", preparation_seconds=collection["preparation_seconds"]),
                  note="Development results are not empirical thesis results. V1 needs English review in addition to automatic checks.")
    if output_dir:
        directory = Path(output_dir); directory.mkdir(parents=True, exist_ok=True)
        frame.to_csv(directory/"queries.csv", index=False)
        refs_frame.to_csv(directory/"coverage.csv", index=False)
        by_jump.to_csv(directory/"coverage-by-module-jump.csv", index=False)
        pd.DataFrame(measurements).to_csv(directory/"measurements.csv", index=False)
        (directory/"report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report
