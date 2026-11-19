import argparse
import json
import sys
import time
from sqlite3 import DatabaseError
from pathlib import Path
from . import __version__
from .collection import build, build_session, canonical, connect, load, meta
from .extract import scan_module
from .query import render_text, retrieve, validate_output


def parser():
    p = argparse.ArgumentParser(prog="r2", description="Deterministic local Odoo migration evidence; no AI connection")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="Normalize accepted captures and build SQLite schema 4")
    b.add_argument("manifest", type=Path)
    b.add_argument("--db", required=True, type=Path)
    b.add_argument("--annotations", type=Path, help="Explicit reviewed changes with English titles")
    b.add_argument("--bindings", type=Path, help="Optional explicit processing metadata; missing versions remain unknown")
    legacy = sub.add_parser("build-legacy", help="Explicit historical local Git/snapshot reconstruction (schema 2)")
    legacy.add_argument("manifest", type=Path)
    legacy.add_argument("--db", required=True, type=Path)
    legacy.add_argument("--annotations", type=Path)
    legacy.add_argument("--audit-registry", type=Path)
    q = sub.add_parser("query", help="Analyze the original module and retrieve evidence offline")
    q.add_argument("module", type=Path)
    q.add_argument("--db", type=Path, required=True)
    q.add_argument("--from", dest="from_version", required=True)
    q.add_argument("--to", dest="to_version", required=True)
    q.add_argument("--layer", choices=["all", "python", "xml", "data", "manifest", "documentation"], default="all")
    q.add_argument("--depth", type=int, default=3)
    q.add_argument("--limit", type=int, default=10)
    q.add_argument("--engine", choices=["graph", "bm25"], default="graph")
    q.add_argument("--status", choices=["all", "candidate", "verified", "unresolved"], default="all")
    q.add_argument("--module-name", help="Technical addon name when directory was renamed")
    q.add_argument("--timing-log", type=Path, help="Separate JSONL measurement including stdout completion")
    q.add_argument("--format", choices=["text", "json"], default="text")
    q.add_argument("--log", type=Path, help="Append structured query output as JSONL")
    s = sub.add_parser("scan", help="Inspect a module without importing or executing it")
    s.add_argument("module", type=Path)
    s = sub.add_parser('cross', help='Cross partner code against indexed normalized units; no graph expansion')
    s.add_argument('module',type=Path,help='Partner code file or directory')
    s.add_argument('--db',type=Path,required=True)
    s.add_argument('--module-name',help='Explicit technical addon name for namespace-sensitive identifiers')
    s.add_argument('--output',type=Path,help='Save a new JSON report; never overwrite an existing file')
    for name in ("inventory", "export", "show"):
        s = sub.add_parser(name)
        s.add_argument("--db", type=Path, required=True)
        if name == "show":
            s.add_argument("change_id")
    s = sub.add_parser("validate-output", help="Check V1 contract and counters")
    s.add_argument("output", type=Path)
    s = sub.add_parser("evaluate", help="Measure metrics with external relevance and coverage judgments")
    s.add_argument("specification", type=Path)
    s.add_argument("--db", required=True, type=Path)
    s.add_argument("--repeats", type=int, default=1)
    s.add_argument("--development", action="store_true", help="Explicit engineering run; never academic evidence")
    s.add_argument("--output-dir", type=Path)
    s = sub.add_parser("capture-plan", help="Acquire complete admitted units using the reviewed catalog")
    s.add_argument("plan", type=Path)
    s.add_argument("--catalog", required=True, type=Path)
    s.add_argument("--output", type=Path, default=Path("temp_data"))
    s = sub.add_parser("delete-units", help="Delete complete temporary acquisition units")
    s.add_argument("session_id")
    s.add_argument("unit_ids", nargs="+")
    s.add_argument("--output", type=Path, default=Path("temp_data"))
    s = sub.add_parser("evaluation-metadata", help="Independent metadata-only evaluation collection; never indexed")
    s.add_argument("--query"); s.add_argument("--repo"); s.add_argument("--number", type=int)
    s.add_argument("--output", type=Path, required=True)
    s = sub.add_parser("sample", help="Prepare audited stratified sampling; stop at unreviewed criteria")
    s.add_argument("specification", type=Path)
    s = sub.add_parser("freeze", help="Freeze a complete independent protocol; refuse missing reviewers or cases")
    s.add_argument("parameters", type=Path); s.add_argument("--specification", type=Path, required=True)
    s.add_argument("--selection", type=Path, required=True); s.add_argument("--db", type=Path, required=True)
    s.add_argument("--output", type=Path, required=True)
    sub.add_parser("doctor", help="Probe actual versions, Git, FTS5 and NetworkX BFS")
    return p


def main(argv=None):
    cli_start = time.perf_counter()
    p = parser()
    args = p.parse_args(argv)
    try:
        if args.command == "build":
            output = build_session(args.manifest, args.bindings, args.db, args.annotations)
        elif args.command == "build-legacy":
            output = build(args.manifest, args.db, annotations=args.annotations, assignment_registry=args.audit_registry)
        elif args.command == "scan":
            output = scan_module(args.module)
        elif args.command == 'cross':
            from .crossing import cross_module
            output = cross_module(args.db,args.module,module_name=args.module_name,output=args.output)
        elif args.command == "query":
            from .evaluate import measure
            output, timing = measure(args.db, args.module, args.from_version, args.to_version,
                              layer=args.layer, depth=args.depth, limit=args.limit, engine=args.engine,
                              status=args.status, module_name=args.module_name)
            check = validate_output(output)
            if not check["conformant"]:
                raise ValueError("Output contract failed: " + "; ".join(check["errors"]))
            if args.log:
                args.log.parent.mkdir(parents=True, exist_ok=True)
                with args.log.open("a", encoding="utf-8") as f:
                    f.write(canonical(output) + "\n")
            output["timing"] = timing
            print(render_text(output) if args.format == "text" else json.dumps(output, ensure_ascii=False, indent=2), flush=True)
            if args.timing_log:
                args.timing_log.parent.mkdir(parents=True, exist_ok=True)
                with args.timing_log.open("a", encoding="utf-8") as f:
                    f.write(canonical({"collection_revision": output["collection_revision"], "engine": args.engine,
                                       **timing, "cli_until_stdout_completed_seconds": time.perf_counter()-cli_start})+"\n")
            return
        elif args.command in {"inventory", "export", "show"}:
            with connect(args.db) as con:
                output = meta(con)
                if args.command == "inventory":
                    output["sources"] = load(con, "sources")
                elif args.command == "export":
                    output = {"metadata": output, **{t: load(con, t) for t in (("sources", "comparisons", "evidence", "changes", "elements", "relations", "artifacts", "documents") if meta(con)["schema_version"] == 3 else ("sources", "comparisons", "evidence", "changes", "elements", "relations"))}}
                    if output['metadata']['schema_version']==4:
                        for table in ('artifacts','documents','information_units'):
                            output[table]=load(con,table)
                else:
                    output = next((r for r in load(con, "changes") if r["id"] == args.change_id), None)
                    if output is None:
                        raise ValueError("Change ID not found")
        elif args.command == "validate-output":
            output = validate_output(json.loads(args.output.read_text(encoding="utf-8-sig")))
            print(json.dumps(output, ensure_ascii=False, indent=2))
            if not output["conformant"]:
                sys.exit(1)
            return
        elif args.command == "evaluate":
            from .evaluate import evaluate
            output = evaluate(args.db, json.loads(args.specification.read_text(encoding="utf-8-sig")),
                              args.specification.resolve().parent,
                              repeats=args.repeats, development=args.development, output_dir=args.output_dir)
        elif args.command == "capture-plan":
            from .adquisition import capture_plan
            output = capture_plan(args.plan, args.output, catalog_path=args.catalog)
        elif args.command == "delete-units":
            from .adquisition import delete_units
            output = delete_units(args.session_id, args.unit_ids, args.output)
        elif args.command == "evaluation-metadata":
            from .evaluation_sources import GitHubMetadata
            from .evaluation_sources.provenance import save
            client = GitHubMetadata(args.output)
            output = client.search(args.query) if args.query else client.pull(args.repo, args.number)
            save(args.output/"result.json", output)
        elif args.command == "sample":
            from .selection import sample_cases
            output = sample_cases(json.loads(args.specification.read_text(encoding="utf-8-sig")))
        elif args.command == "freeze":
            from .selection import freeze_protocol, fingerprint
            from .evaluate import query_identity
            parameters = json.loads(args.parameters.read_text(encoding="utf-8-sig"))
            spec = json.loads(args.specification.read_text(encoding="utf-8-sig"))
            parameters["queries_revision"] = fingerprint([query_identity(q, args.specification.resolve().parent) for q in spec["queries"]])
            parameters["query_cases"] = sorted({q.get("case_id") for q in spec["queries"] if q.get("case_id")})
            parameters["reference_revision"] = fingerprint(spec["references"])
            with connect(args.db) as con:
                collection = meta(con)
            output = freeze_protocol(parameters, collection["collection_revision"], args.output,
                                     json.loads(args.selection.read_text(encoding="utf-8-sig")))
        else:
            import sqlite3, subprocess
            import networkx as nx
            from .evaluate import environment
            con = sqlite3.connect(":memory:")
            con.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
            con.close()
            output = {**environment(), "git": subprocess.check_output(["git", "--version"], text=True).strip(),
                      "fts5": True, "networkx_bfs_layers_probe": list(nx.bfs_layers(nx.path_graph(3), [0]))}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError, DatabaseError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
