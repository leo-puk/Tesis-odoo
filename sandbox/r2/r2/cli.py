"""English command line for the normalized-unit migration workflow."""
import argparse
import json
from pathlib import Path
from sqlite3 import DatabaseError

from . import __version__
from .adquisition import capture_plan, delete_units
from .adquisition.planner import write_plan
from .records import connect, load, meta
from .crossing import cross_module, save_result
from .normalization.schema import LAYERS
from .normalization.storage import build_normalized
from .relations import execute_query, save_graph
from .report import render_report, search_units, validate_report
from .workflow import run_workflow
from .assistant import start as start_assistant


def query_arguments(command, *, baseline=False):
    # Inputs: command, baseline.
    # Does: Register the shared CLI options for a migration query.
    # Output: An updated argument parser.
    command.add_argument("module", type=Path)
    command.add_argument("--from", dest="from_version", required=True)
    command.add_argument("--to", dest="to_version", required=True)
    command.add_argument("--layer", choices=sorted(LAYERS | {"all"}), default="all")
    command.add_argument("--depth", "--max-hops", dest="maximum_hops", type=int, choices=range(4), default=3)
    command.add_argument("--limit", type=int, choices=range(1, 11), default=10, metavar="1-10")
    command.add_argument("--module-name")
    if baseline:
        command.add_argument("--engine", choices=("graph", "bm25"), default="graph")
    command.add_argument("--format", choices=("text", "json"), default="text")


def parser():
    # Inputs: No explicit arguments.
    # Does: Define the public commands and argument contracts.
    # Output: The CLI argument parser.
    cli = argparse.ArgumentParser(prog="r2", description="Local Odoo migration evidence from normalized units")
    cli.add_argument("--version", action="version", version=__version__)
    commands = cli.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="Interactively select local Odoo versions and addons")
    start.add_argument("--odoo", type=Path, help="Local Odoo Git checkout containing odoo-bin")
    start.add_argument("--addons", type=Path, help="Addon folder or repository to scan")
    start.add_argument("--from", dest="from_version")
    start.add_argument("--to", dest="to_version")
    start.add_argument("--select", help="Addon names, indexes, ranges or 'all'")
    start.add_argument("--output-dir", type=Path)
    start.add_argument("--config", type=Path, help="Reusable assistant configuration file")
    start.add_argument("--list-only", action="store_true", help="Detect and select without running analysis")
    start.add_argument("--layer", choices=sorted(LAYERS | {"all"}), default="all")
    start.add_argument("--depth", "--max-hops", dest="maximum_hops", type=int, choices=range(4), default=3)
    start.add_argument("--limit", type=int, choices=range(1, 11), default=10, metavar="1-10")
    run = commands.add_parser("run", help="Acquire, normalize, cross, extract relations and write a report")
    run.add_argument("--plan", type=Path, help="Use an existing capture plan instead of planning from the module")
    run.add_argument("--catalog", required=True, type=Path)
    run.add_argument("--bindings", type=Path)
    run.add_argument("--output-dir", required=True, type=Path)
    query_arguments(run)
    planner = commands.add_parser("plan", help="Plan acquisition URLs from a local module or repository")
    planner.add_argument("module", type=Path)
    planner.add_argument("--from", dest="from_version", required=True)
    planner.add_argument("--to", dest="to_version", required=True)
    planner.add_argument("--catalog", required=True, type=Path)
    planner.add_argument("--output-dir", required=True, type=Path)
    search = commands.add_parser("query", aliases=["search-units"], help="Query a normalized collection")
    query_arguments(search, baseline=True)
    search.add_argument("--db", type=Path, required=True)
    search.add_argument("--output-dir", type=Path)
    build = commands.add_parser("build", help="Normalize admitted sources and index units in SQLite")
    build.add_argument("inventory", type=Path)
    build.add_argument("--bindings", type=Path)
    build.add_argument("--db", required=True, type=Path)
    capture = commands.add_parser("capture-plan", help="Capture whole sources according to a reviewed catalog")
    capture.add_argument("plan", type=Path)
    capture.add_argument("--catalog", required=True, type=Path)
    capture.add_argument("--output", type=Path, default=Path("temp_data"))
    delete = commands.add_parser("delete-units", help="Delete selected temporary acquisition units")
    delete.add_argument("session_id")
    delete.add_argument("unit_ids", nargs="+")
    delete.add_argument("--output", type=Path, default=Path("temp_data"))
    crossing = commands.add_parser("cross", help="Inspect exact indexed technical matches")
    crossing.add_argument("module", type=Path)
    crossing.add_argument("--db", required=True, type=Path)
    crossing.add_argument("--module-name")
    crossing.add_argument("--output", type=Path)
    relations = commands.add_parser("extract-relations", help="Inspect relations reached from exact matches")
    relations.add_argument("crossing_result", type=Path)
    relations.add_argument("--db", required=True, type=Path)
    relations.add_argument("--max-hops", type=int, choices=range(4), default=3)
    relations.add_argument("--output", type=Path)
    export = commands.add_parser("export", help="Export the normalized collection with provenance")
    export.add_argument("--db", required=True, type=Path)
    validate = commands.add_parser("validate-output", help="Check report counts and evidence paths")
    validate.add_argument("report", type=Path)
    evaluation = commands.add_parser("evaluate", help="Compare graph and BM25 using reviewed judgments")
    evaluation.add_argument("specification", type=Path)
    evaluation.add_argument("--db", required=True, type=Path)
    evaluation.add_argument("--repeats", type=int, default=1)
    return cli


def json_text(value):
    # Inputs: value.
    # Does: Serialize a value for CLI output.
    # Output: Indented JSON text.
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)


def write_report(output, report, crossing, graph):
    # Inputs: output, report, crossing, graph.
    # Does: Save the report and available crossing and graph artifacts.
    # Output: The report files in the selected directory.
    if crossing is not None:
        save_result(crossing, output / "crossing.json")
    if graph is not None:
        save_graph(graph, output / "relations.json")
    with (output / "report.json").open("x", encoding="utf-8") as stream:
        stream.write(json_text(report) + "\n")
    with (output / "report.txt").open("x", encoding="utf-8") as stream:
        stream.write(render_report(report) + "\n")


def run_query(args):
    # Inputs: args.
    # Does: Run or query the normalized workflow using parsed CLI options.
    # Output: The report formatted as JSON or text.
    output = args.output_dir
    if output is not None and output.exists():
        raise ValueError("Choose a new output directory")
    scope = dict(layer=args.layer, maximum_hops=args.maximum_hops, limit=args.limit, module_name=args.module_name)
    if args.command == "run":
        result = run_workflow(args.plan, args.catalog, args.bindings, args.module, output,
                              args.from_version, args.to_version, **scope)
    else:
        result = search_units(args.db, args.module, args.from_version, args.to_version,
                              engine=args.engine, **scope)
    if output is not None:
        if args.command != "run":
            output.mkdir(parents=True)
        write_report(output, *result)
    report = result[0]
    return render_report(report) if args.format == "text" else json_text(report)


def main(argv=None):
    # Inputs: argv.
    # Does: Dispatch the selected command and handle terminal output.
    # Output: CLI output and exit status.
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.command == "start":
            print(json_text(start_assistant(args)))
            return
        if args.command in {"run", "query", "search-units"}:
            print(run_query(args))
            return
        if args.command == "plan":
            result = write_plan(args.module, args.from_version, args.to_version, args.catalog, args.output_dir)
        elif args.command == "build":
            result = build_normalized(args.inventory, args.bindings, args.db)
        elif args.command == "capture-plan":
            result = capture_plan(args.plan, args.output, catalog_path=args.catalog)
        elif args.command == "delete-units":
            result = delete_units(args.session_id, args.unit_ids, args.output)
        elif args.command == "cross":
            result = cross_module(args.db, args.module, module_name=args.module_name, output=args.output)
        elif args.command == "extract-relations":
            result = execute_query(args.crossing_result, args.db, maximum_hops=args.max_hops, output=args.output)
        elif args.command == "export":
            with connect(args.db) as con:
                metadata = meta(con)
                if metadata.get("layout") != "normalized-units":
                    raise ValueError("Rebuild this collection with r2 build")
                result = dict(metadata=metadata, **{table: load(con, table)
                              for table in ("sources", "artifacts", "information_units")})
        elif args.command == "validate-output":
            result = dict(conformant=validate_report(json.loads(args.report.read_text(encoding="utf-8-sig"))))
        elif args.command == "evaluate":
            from .evaluation.normalized import evaluate
            spec = json.loads(args.specification.read_text(encoding="utf-8-sig"))
            result = evaluate(args.db, spec, args.specification.resolve().parent, repeats=args.repeats)
        print(json_text(result))
    except (ValueError, OSError, KeyError, TypeError, DatabaseError) as exc:
        cli.error(str(exc))
