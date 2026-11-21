"""Reproducible R2 laboratory batch using the thirty catalogued migration groups."""
import argparse
import ast
from collections import Counter
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import statistics
import subprocess
import sys
import time
import traceback
import uuid

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "sandbox/research/migration-plan/plan.json"
STAGE_NAMES = {"graph": "relations_seconds", "bm25": "bm25_units_seconds",
               "bm25_sources": "bm25_sources_search_seconds"}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@contextmanager
def exclusive_lock(path):
    with Path(path).open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            stream.write(b"0")
            stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def table(path, rows, fields):
    path = Path(path)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def catalog(path):
    data = read(path)
    if data.get("schema") != "odoolab.migration-plan.v1":
        raise ValueError("Unsupported migration catalog")
    cases = [case for case in data["groups"] if case["origin"] != "historical"]
    counts = Counter((case["version_from"], case["version_to"]) for case in cases)
    if counts != {("16.0", "17.0"): 10, ("17.0", "18.0"): 10, ("18.0", "19.0"): 10}:
        raise ValueError("Expected ten new cases per consecutive jump")
    if len({case["id"] for case in cases}) != 30:
        raise ValueError("Duplicate case IDs")
    for case in cases:
        if not re.fullmatch(r"oca_v(?:0[1-9]|10)_(?:1617|1718|1819)", case["id"]):
            raise ValueError("Invalid case identity")
        if len(case["modules"]) != 5 or len({item["module"] for item in case["modules"]}) != 5:
            raise ValueError("Each case must contain five distinct addons")
        for item in case["modules"]:
            if not re.fullmatch(r"[a-z0-9_-]+", item["repo"]) or not re.fullmatch(r"[a-z0-9_]+", item["module"]):
                raise ValueError("Invalid OCA repository or addon name")
    return cases


class Sources:
    """Freeze fetched SHAs per batch and reuse clean detached worktrees."""
    def __init__(self, cache, output, log):
        self.cache, self.output, self.log = Path(cache), Path(output), Path(log)
        self.lock_path = self.output / "sources.json"
        self.pins = read(self.lock_path) if self.lock_path.exists() else {}

    def git(self, directory, *arguments):
        command = ["git", "-C", str(directory), *arguments]
        result = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True,
                                timeout=3600, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        with self.log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(command) + "\n" + result.stdout + result.stderr + "\n")
        if result.returncode:
            raise RuntimeError(f"Git {arguments[0]} failed: {result.stderr[-1800:]}")
        return result.stdout.strip()

    def snapshot(self, organization, repository, version):
        identity = f"{organization}/{repository}@{version}"
        bare = self.cache / "git" / f"{organization}-{repository}.git"
        bare.parent.mkdir(parents=True, exist_ok=True)
        if not bare.exists():
            self.git(bare.parent, "init", "--bare", str(bare))
        url = f"https://github.com/{organization}/{repository}.git"
        remotes = self.git(bare, "remote").splitlines()
        if "origin" not in remotes:
            self.git(bare, "remote", "add", "origin", url)
        if self.git(bare, "remote", "get-url", "origin") != url:
            raise ValueError("Repository cache has an unexpected origin")
        if organization == "OCA":
            self.git(bare, "config", "remote.origin.promisor", "true")
            self.git(bare, "config", "remote.origin.partialclonefilter", "blob:none")
        if identity not in self.pins:
            options = ["--depth=1"] if organization == "odoo" else ["--filter=blob:none"]
            self.git(bare, "fetch", *options, "origin", f"refs/heads/{version}:refs/heads/{version}")
            self.pins[identity] = self.git(bare, "rev-parse", f"refs/heads/{version}")
            save(self.lock_path, self.pins)
        sha = self.pins[identity]
        self.git(bare, "update-ref", f"refs/heads/{version}", sha)
        checkout = self.cache / "snapshots" / f"{organization}-{repository}-{sha}"
        if not checkout.exists():
            checkout.parent.mkdir(parents=True, exist_ok=True)
            self.git(bare, "worktree", "add", "--detach", str(checkout), sha)
        if self.git(checkout, "rev-parse", "HEAD") != sha or self.git(checkout, "status", "--porcelain"):
            raise ValueError(f"Source snapshot changed: {checkout}")
        return checkout, sha

    def references(self, item, target, destination):
        """Write MIG candidates only into a reference dossier, outside the R2 corpus."""
        repository = self.cache / "git" / f"OCA-{item['repo']}.git"
        sha = self.pins[f"OCA/{item['repo']}@{target}"]
        history = self.git(repository, "log", "--format=%H%x09%s", sha, "--", item["module"])
        candidates = []
        for line in history.splitlines():
            commit, _, subject = line.partition("\t")
            if ("[MIG]" in subject.upper() and target in subject
                    and re.search(r"\b" + re.escape(item["module"]) + r"\b", subject)):
                candidates.append(dict(sha=commit, subject=subject))
        destination.mkdir(parents=True, exist_ok=True)
        for candidate in candidates:
            patch = self.git(repository, "show", "--format=fuller", "--no-ext-diff", "--no-textconv",
                             candidate["sha"], "--", item["module"])
            (destination / (candidate["sha"] + ".diff")).write_text(patch + "\n", encoding="utf-8")
        save(destination / "candidates.json", {"status": "pending_review", "candidates": candidates,
             "note": "Review eligibility, group manual corrections and exclude mechanical changes before defining C1."})
        return candidates


def verify_artifacts(directory, payload):
    return bool(payload.get("artifacts")) and all(
        (directory / name).is_file() and digest(directory / name) == value for name, value in payload["artifacts"].items())


def verify_protocol_code(output):
    manifest = read(output / "manifest.json")
    if any(digest(ROOT / name) != expected for name, expected in manifest["protocol"]["code"].items()):
        raise ValueError("The current code differs from the archived experimental protocol")
    return manifest


def measure_module(database, module, case, destination, repeats, source_baseline=None):
    from r2.assistant import _save_report
    from r2.charts import graph_statistics, render_charts
    from r2.report import render_report, search_units, validate_report

    destination.mkdir(parents=True)
    reports, timings, statuses, pool = {}, {"graph": [], "bm25": []}, [], {}
    if source_baseline is not None:
        timings["bm25_sources"] = []
    for repetition in range(repeats):
        engines = ("graph", "bm25", "bm25_sources") if source_baseline is not None else ("graph", "bm25")
        order = engines if repetition % 2 == 0 else tuple(reversed(engines))
        for engine in order:
            started = time.perf_counter()
            stages = {}
            if engine == "bm25_sources":
                report = source_baseline.search(module, module.name, timings=stages)
                serialized = json.dumps(report, ensure_ascii=False, allow_nan=False, indent=2)
                elapsed = time.perf_counter() - started
                timings[engine].append(elapsed)
                statuses.append(dict(repetition=repetition + 1, engine=engine, seconds=elapsed,
                                     stages=stages, boundary="Full-source BM25 query through JSON serialization"))
                if engine in reports and reports[engine] != report:
                    raise ValueError("Full-source BM25 changed across repetitions")
                if engine not in reports:
                    reports[engine] = report
                    folder = destination / engine
                    folder.mkdir()
                    (folder / "report.json").write_text(serialized, encoding="utf-8")
                    (folder / "report.txt").write_text("\n".join(
                        f"{rank}. {row['url']} | {row['source_id']} | BM25 {row['bm25_score']}"
                        for rank, row in enumerate(report["results"], 1)), encoding="utf-8")
                continue
            result = search_units(database, module, case["version_from"], case["version_to"],
                                  module_name=module.name, engine=engine, layer="all", maximum_hops=3, limit=10,
                                  timings=stages)
            report, crossing, graph = result
            render_report(report)
            json.dumps(report, ensure_ascii=False, allow_nan=False)
            elapsed = time.perf_counter() - started
            timings[engine].append(elapsed)
            validate_report(report)
            if engine in reports and reports[engine] != report:
                raise ValueError("Search results changed across repetitions")
            if engine not in reports:
                reports[engine] = report
                _save_report(destination / engine, result)
                (destination / engine / "bars.txt").write_text(render_charts(
                    graph_statistics(report, crossing, graph), ascii_only=True, width=100), encoding="utf-8")
                for row in report["results"]:
                    uid = row["change_id"]
                    entry = pool.setdefault(uid, dict(unit_id=uid, relevant="", reference_ids="", reviewer="",
                        reason="", source=json.dumps(row["source"], ensure_ascii=False),
                        before=row["before"], after=row["after"]))
                    entry[engine + "_rank"] = next(i for i, value in enumerate(report["results"], 1) if value["change_id"] == uid)
            statuses.append(dict(repetition=repetition + 1, engine=engine, seconds=elapsed,
                                 stages=stages, structural_V1=True))
            del result, crossing, graph
    if reports["graph"]["query"] != reports["bm25"]["query"]:
        raise ValueError("Query inputs differ between engines")
    if reports["graph"]["collection_revision"] != reports["bm25"]["collection_revision"] or (
        reports["graph"]["summary"]["eligible_units"] != reports["bm25"]["summary"]["eligible_units"]):
        raise ValueError("Graph and BM25 used different corpora")
    table(destination / "judgments.csv", [pool[uid] for uid in sorted(pool)],
          ["unit_id", "relevant", "reference_ids", "reviewer", "reason", "source", "before", "after", "graph_rank", "bm25_rank"])
    save(destination / "timing.json", statuses)
    stage_samples = {engine: [] for engine in reports}
    for row in statuses:
        stage = STAGE_NAMES[row["engine"]]
        if stage in row.get("stages", {}):
            stage_samples[row["engine"]].append(row["stages"][stage])
    stage_medians = {}
    for engine, samples in stage_samples.items():
        stage_medians[engine] = {STAGE_NAMES[engine]: statistics.median(samples)} if samples else {}
    if source_baseline is not None:
        source_pool = {row["source_id"]: dict(source_id=row["source_id"], url=row["url"], relevant="",
            reference_ids="", reviewer="", reason="") for row in reports["bm25_sources"]["results"]}
        for row in reports["graph"]["results"]:
            source = row["source"]
            source_pool.setdefault(source["source_id"], dict(source_id=source["source_id"], url=source["url"],
                                   relevant="", reference_ids="", reviewer="", reason=""))
        table(destination / "source-judgments.csv", [source_pool[sid] for sid in sorted(source_pool)],
              ["source_id", "relevant", "reference_ids", "reviewer", "reason", "url"])
    result = dict(module=module.name, collection_revision=reports["graph"]["collection_revision"],
                  query=reports["graph"]["query"], input_path=str(module), judgments_pending=len(pool),
                  engines={engine: dict(summary=report["summary"], P1=None, C2=None,
                      median_T1_seconds=statistics.median(timings[engine]),
                      median_stage_seconds=stage_medians[engine]) for engine, report in reports.items()})
    result["artifacts"] = {str(path.relative_to(destination)): digest(path) for path in destination.rglob("*")
                           if path.is_file() and path.name not in {"judgments.csv", "source-judgments.csv"}}
    save(destination / "complete.json", result)
    return result


def execute_case(case, args, attempt):
    from r2.assistant import prepare_local_source
    from experiment_sources import SourceBaseline, supplement
    attempt.mkdir(parents=True, exist_ok=True)
    sources = Sources(args.cache, args.output, attempt / "sources.log")
    origin, target = case["version_from"], case["version_to"]
    core, _ = sources.snapshot("odoo", "odoo", origin)
    sources.snapshot("odoo", "odoo", target)
    addons, failures, provenance = [], {}, {}
    for item in case["modules"]:
        name = item["module"]
        try:
            source, before = sources.snapshot("OCA", item["repo"], origin)
            destination, after = sources.snapshot("OCA", item["repo"], target)
            for root, version in ((source, origin), (destination, target)):
                manifest = ast.literal_eval((root / name / "__manifest__.py").read_text(encoding="utf-8-sig"))
                if not manifest.get("installable", True) or not str(manifest.get("version", "")).startswith(version + "."):
                    raise ValueError(f"Manifest is unavailable, non-installable or has a different major version ({version})")
            addons.append(dict(name=name, path=source / name))
            provenance[name] = dict(repository=item["repo"], source_sha=before, target_sha=after)
        except (OSError, RuntimeError, ValueError, SyntaxError) as exc:
            failures[name] = str(exc)
    if not addons:
        raise ValueError("No source/destination addon pairs available: " + json.dumps(failures))
    started = time.perf_counter()
    local = prepare_local_source(core, addons, origin, target, attempt / "local-source")
    local_seconds = time.perf_counter() - started
    started = time.perf_counter()
    prepared = supplement(local, addons, origin, target, attempt / "acquisition", args.source_catalog)
    acquisition_seconds = time.perf_counter() - started
    database = Path(prepared["database"])
    started = time.perf_counter()
    baseline = SourceBaseline(database, attempt / "source-baseline.sqlite", origin, target)
    prepared["preparation_timing"] = dict(local_seconds=local_seconds, acquisition_and_normalization_seconds=acquisition_seconds,
                                         source_index_seconds=time.perf_counter() - started)
    save(attempt / "acquisition.json", prepared)
    from r2.crossing import cross_module, save_result
    initial = {}
    for addon in addons:
        name = addon["name"]
        try:
            crossing = cross_module(database, addon["path"], module_name=name)
            save_result(crossing, attempt / "r21-crossing" / (name + ".json"))
            initial[name] = dict(result_id=crossing["result_id"], matched_unit_ids=crossing["matched_unit_ids"])
        except (ValueError, OSError) as exc:
            failures[name] = str(exc)
    save(attempt / "initial-crossing.json", dict(component="R2.1", addons=initial,
         matched_unit_ids=sorted({uid for value in initial.values() for uid in value["matched_unit_ids"]})))
    save(attempt / "provenance.json", dict(core=prepared["revisions"], addons=provenance,
        database_sha256=digest(database), collection_revision=prepared["build"]["collection_revision"]))
    modules = []
    for addon in addons:
        name = addon["name"]
        print(f"{case['id']} / {name}", flush=True)
        try:
            modules.append(measure_module(database, addon["path"], case, attempt / "addons" / name, args.repeats, baseline))
        except Exception as exc:
            failures[name] = str(exc)
            traceback.print_exc()
    for item in case["modules"]:
        if item["module"] in provenance:
            try:
                sources.references(item, target, attempt / "references" / item["module"])
            except (RuntimeError, OSError) as exc:
                save(attempt / "references" / item["module"] / "error.json", {"status": "pending", "reason": str(exc)})
    specification = dict(reviewer=None, collection_revision=prepared["build"]["collection_revision"], references={},
        queries=[dict(id=case["id"] + "/" + module["module"], module=module["input_path"],
            module_name=module["module"], input_revision=module["query"]["input_revision"], from_version=origin,
            to_version=target, layer="all", maximum_hops=3, limit=10, reference_ids=[], judgments={}) for module in modules])
    save(attempt / "evaluation-spec.json", specification)
    status = dict(id=case["id"], status="completed" if len(modules) == 5 and not failures else "partial",
                  finished_at=now(), modules=modules, failures=failures, database=str(database),
                  database_sha256=digest(database), C1=None, academic_review="pending")
    status["acquisition_status"] = prepared["acquisition_status"]
    status["baseline_contract"] = "bm25_sources ranks complete sources; bm25 retains the unit-level control"
    save(attempt / "result.json", status)
    return status


def summary(output):
    rows, source_rows, case_rows, counts, evaluated = [], [], [], Counter(), []
    manifest = read(output / "manifest.json")
    for case in manifest["cases"]:
        pointer = output / "cases" / case["id"] / "latest.json"
        state = read(pointer) if pointer.exists() else dict(status="pending")
        counts[state["status"]] += 1
        case_rows.append(dict(case=case["id"], jump=case["version_from"] + "->" + case["version_to"],
                              status=state["status"], evidence=state.get("attempt", "")))
        if "attempt" not in state:
            continue
        attempt = output / state["attempt"]
        result = read(attempt / "result.json") if (attempt / "result.json").exists() else {}
        evaluation = {}
        evaluation_status = read(attempt / "evaluation-status.json") if (attempt / "evaluation-status.json").exists() else {}
        if (evaluation_status.get("status") == "measured" and (attempt / "evaluation.json").exists()
                and evaluation_status.get("spec_sha256") == digest(attempt / "evaluation-spec.json")):
            evaluation = read(attempt / "evaluation.json")
        if evaluation:
            evaluated.append(evaluation)
        source_scores = {}
        if evaluation and (attempt / "source-evaluation.json").exists():
            source_evaluation = read(attempt / "source-evaluation.json")
            if all(digest(attempt / "addons" / module / "source-judgments.csv") == expected
                   for module, expected in source_evaluation["judgments_sha256"].items()):
                source_scores = {query["module"]: query["engines"] for query in source_evaluation["queries"]}
                for module, engines in source_scores.items():
                    for engine, score in engines.items():
                        source_rows.append(dict(case=case["id"], module=module, engine=engine,
                            shown=len(score["shown"]), P1_source=score["P1_source"],
                            C2_reference=score["C2_reference"], unjudged=len(score["unjudged"])))
        scores_by_module = {query["query"]["module_name"]: query["engines"] for query in evaluation.get("queries", [])}
        for module in result.get("modules", []):
            for engine, scores in module["engines"].items():
                rows.append(dict(case=case["id"], module=module["module"], engine=engine,
                    jump=case["version_from"] + "->" + case["version_to"], status=state["status"],
                    granularity="source" if engine == "bm25_sources" else "unit",
                    found=scores["summary"].get("changes_found", scores["summary"].get("sources_found")),
                    shown=scores["summary"].get("changes_shown", scores["summary"].get("sources_shown")),
                    median_T1_seconds=scores["median_T1_seconds"],
                    stage=STAGE_NAMES[engine],
                    median_stage_seconds=scores.get("median_stage_seconds", {}).get(STAGE_NAMES[engine]),
                    P1=(source_scores.get(module["module"], {}).get(engine, {}).get("P1_source") if engine == "bm25_sources"
                        else scores_by_module.get(module["module"], {}).get(engine, {}).get("P1")),
                    C2=(source_scores.get(module["module"], {}).get(engine, {}).get("C2_reference") if engine == "bm25_sources"
                        else scores_by_module.get(module["module"], {}).get(engine, {}).get("C2")),
                    C1=evaluation.get("C1"), evidence=str(attempt.relative_to(output))))
    table(output / "metrics.csv", rows, ["case", "module", "jump", "engine", "granularity", "status", "found", "shown",
          "median_T1_seconds", "stage", "median_stage_seconds", "C1", "P1", "C2", "evidence"])
    table(output / "cases.csv", case_rows, ["case", "jump", "status", "evidence"])
    table(output / "source-metrics.csv", source_rows, ["case", "module", "engine", "shown", "P1_source", "C2_reference", "unjudged"])
    references = sum(value["reference_count"] for value in evaluated)
    covered = sum(len(value["covered_reference_ids"]) for value in evaluated)
    pairs = [query["engines"] for value in evaluated for query in value["queries"]
             if all(query["engines"][engine]["P1"] is not None for engine in ("graph", "bm25"))]
    save(output / "summary.json", dict(updated_at=now(), cases_total=len(manifest["cases"]), statuses=dict(counts),
        module_engine_rows=len(rows), C1=100 * covered / references if references else None,
        reference_count=references, covered_reference_count=covered, measured_cases=len(evaluated),
        P1_defined_pairs=len(pairs), P1_macro_paired={engine: statistics.mean(pair[engine]["P1"] for pair in pairs)
            if pairs else None for engine in ("graph", "bm25")}, academic_review="sample_admission_pending",
        scope="30 laboratory groups, five addons each. Academic sample eligibility and relevance review are required separately."))
    print(json.dumps(dict(counts), ensure_ascii=False), flush=True)


def run_worker(command, log, timeout):
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   start_new_session=os.name != "nt", env={**os.environ, "PYTHONUNBUFFERED": "1"})
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return 124
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()


def run(args):
    cases = catalog(args.plan)
    args.output.mkdir(parents=True, exist_ok=True)
    args.cache.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(args.output / "batch.lock"), exclusive_lock(args.cache / "cache.lock"):
        code_paths = list((ROOT / "sandbox/r2/r2").rglob("*.py")) + list((ROOT / "aws-lab").glob("*.py"))
        code = {str(path.relative_to(ROOT)): digest(path) for path in code_paths}
        protocol = dict(plan_sha256=digest(args.plan), code=code, repeats=args.repeats, depth=3, limit=10,
                        cache=str(args.cache.resolve()), output=str(args.output.resolve()),
                        source_catalog_sha256=digest(args.source_catalog) if args.source_catalog else None)
        path = args.output / "manifest.json"
        if path.exists():
            manifest = read(path)
            if manifest["protocol"] != protocol:
                raise ValueError("Code, catalog, paths or parameters changed. Use a new --output for a new experiment.")
        else:
            save(path, dict(created_at=now(), python=sys.version, platform=platform.platform(), protocol=protocol, cases=cases,
                            cache_policy="Uncontrolled OS cache; engine order alternates per repetition"))
        wanted = set(args.only or [case["id"] for case in cases])
        if wanted - {case["id"] for case in cases}:
            raise ValueError("Unknown --only case")
        for case in cases:
            if case["id"] not in wanted:
                continue
            folder = args.output / "cases" / case["id"]
            folder.mkdir(parents=True, exist_ok=True)
            pointer = folder / "latest.json"
            if pointer.exists() and read(pointer)["status"] == "completed":
                prior = args.output / read(pointer)["attempt"]
                result = read(prior / "result.json")
                if digest(Path(result["database"])) != result["database_sha256"] or not all(
                    verify_artifacts(prior / "addons" / module["module"], module) for module in result["modules"]):
                    raise ValueError("Completed evidence was changed. Use a new output directory to rerun.")
                print(case["id"] + " already completed; evidence verified", flush=True)
                continue
            attempt = folder / ("attempt-" + uuid.uuid4().hex[:12])
            attempt.mkdir()
            state = dict(status="running", started_at=now(), attempt=str(attempt.relative_to(args.output)))
            save(pointer, state)
            command = [sys.executable, str(Path(__file__).resolve()), "case", "--plan", str(args.plan),
                       "--output", str(args.output), "--cache", str(args.cache), "--repeats", str(args.repeats),
                       "--only", case["id"], "--attempt", str(attempt)]
            if args.source_catalog:
                command.extend(["--source-catalog", str(args.source_catalog)])
            print(f"Starting {case['id']} -> {attempt}", flush=True)
            code = run_worker(command, attempt / "execution.log", args.case_timeout)
            payload = read(attempt / "result.json") if (attempt / "result.json").exists() else {
                "status": "failed", "reason": "Case timed out" if code == 124 else "Worker exited without a result",
                "returncode": code}
            if not (attempt / "result.json").exists():
                save(attempt / "result.json", payload)
            state.update(status=payload["status"], finished_at=now(), returncode=code)
            save(pointer, state)
            summary(args.output)
        summary(args.output)
        return int(any(read(args.output / "cases" / cid / "latest.json")["status"] != "completed" for cid in wanted))


def evaluate(args):
    from r2.evaluation.normalized import evaluate as evaluate_spec
    from r2.charts import render_evaluation
    verify_protocol_code(args.output)
    for case in catalog(args.plan):
        pointer = args.output / "cases" / case["id"] / "latest.json"
        if not pointer.exists():
            continue
        attempt = args.output / read(pointer)["attempt"]
        spec = attempt / "evaluation-spec.json"
        if not spec.exists():
            continue
        try:
            specification = read(spec)
            if not specification.get("references") or not specification.get("reviewer"):
                raise ValueError("Complete independent reference changes and reviewer first")
            result = read(attempt / "result.json")
            if not all(verify_artifacts(attempt / "addons" / module["module"], module) for module in result["modules"]):
                raise ValueError("Archived query outputs changed after execution")
            expected = {case["id"] + "/" + module["module"] for module in result["modules"]}
            if {query["id"] for query in specification["queries"]} != expected:
                raise ValueError("Review specification must cover every executed addon query")
            if digest(Path(result["database"])) != result["database_sha256"]:
                raise ValueError("Collection changed since the archived queries")
            value = evaluate_spec(result["database"], specification, spec.parent, repeats=args.repeats)
            save(attempt / "evaluation.json", value)
            (attempt / "evaluation-bars.txt").write_text(render_evaluation(value, ascii_only=True), encoding="utf-8")
            save(attempt / "evaluation-status.json", {"status": "measured", "updated_at": now(),
                 "spec_sha256": digest(spec)})
            evaluate_sources(attempt, result, specification)
            print(case["id"] + " evaluated", flush=True)
        except (ValueError, KeyError, OSError) as exc:
            save(attempt / "evaluation-status.json", {"status": "pending_review", "reason": str(exc)})
            print(case["id"] + ": " + str(exc), flush=True)
    summary(args.output)


def evaluate_sources(attempt, result, specification):
    """Use source-level judgments for both the baseline and projected Graph first view."""
    queries = {query["module_name"]: query for query in specification["queries"]}
    results = []
    for module in result["modules"]:
        folder = attempt / "addons" / module["module"]
        if not (folder / "bm25_sources" / "report.json").exists():
            continue
        graph = read(folder / "graph" / "report.json")
        baseline = read(folder / "bm25_sources" / "report.json")
        if baseline["collection_revision"] != graph["collection_revision"] or (
            baseline["query"]["input_revision"] != graph["query"]["input_revision"]):
            raise ValueError("Source baseline and Graph inputs differ")
        shown = dict(graph_sources=list(dict.fromkeys(row["source"]["source_id"] for row in graph["results"])),
                     bm25_sources=[row["source_id"] for row in baseline["results"]])
        with (folder / "source-judgments.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        judgments = {}
        expected = set(queries[module["module"]]["reference_ids"])
        for row in rows:
            label = row["relevant"].strip().lower()
            if not label:
                continue
            references = {value.strip() for value in row["reference_ids"].split(";") if value.strip()}
            if (label not in {"true", "false"} or not row["reviewer"].strip() or not row["reason"].strip()
                    or not references <= expected or (references and label == "false")
                    or row["source_id"] in judgments):
                raise ValueError("Invalid or duplicate complete-source relevance judgment")
            judgments[row["source_id"]] = dict(relevant=label == "true", references=references)
        scores = {}
        for engine, ids in shown.items():
            missing = sorted(set(ids) - judgments.keys())
            relevant = [sid for sid in ids if judgments.get(sid, {}).get("relevant")]
            covered = {reference for sid in relevant for reference in judgments[sid]["references"]}
            scores[engine] = dict(P1_source=100 * len(relevant) / len(ids) if ids and not missing else None,
                C2_reference=100 * len(covered) / len(expected) if expected and not missing else None,
                shown=ids, relevant_count=len(relevant), unjudged=missing, covered_reference_ids=sorted(covered))
        results.append(dict(module=module["module"], engines=scores))
    save(attempt / "source-evaluation.json", dict(queries=results, granularity="complete source",
        note="Graph sources project its first unit view; BM25 sources rank complete artifacts. View sizes may differ.",
        judgments_sha256={module["module"]: digest(attempt / "addons" / module["module"] / "source-judgments.csv")
                          for module in result["modules"] if (attempt / "addons" / module["module"] / "source-judgments.csv").exists()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "case", "summary", "evaluate"))
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path, default=Path("/results/lote30"))
    parser.add_argument("--cache", type=Path, default=Path("/data/batch-cache"))
    parser.add_argument("--repeats", type=int, choices=range(1, 11), default=3)
    parser.add_argument("--case-timeout", type=int, default=14400)
    parser.add_argument("--only", nargs="+")
    parser.add_argument("--attempt", type=Path)
    parser.add_argument("--source-catalog", type=Path,
        default=ROOT / "sandbox/r2/reference/adquisition-final/examples/catalog.json",
        help="Reviewed catalogue of supplementary sources")
    args = parser.parse_args()
    if os.name != "nt":
        signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(128 + signum))
    args.output, args.cache, args.plan = args.output.resolve(), args.cache.resolve(), args.plan.resolve()
    try:
        if args.action == "case":
            manifest = verify_protocol_code(args.output)
            if digest(args.plan) != manifest["protocol"]["plan_sha256"]:
                raise ValueError("The case plan differs from the experimental protocol")
            case = next(case for case in catalog(args.plan) if case["id"] == args.only[0])
            execute_case(case, args, args.attempt)
        elif args.action == "run":
            return run(args)
        elif args.action == "evaluate":
            with exclusive_lock(args.output / "batch.lock"), exclusive_lock(args.cache / "cache.lock"):
                evaluate(args)
        else:
            summary(args.output)
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
