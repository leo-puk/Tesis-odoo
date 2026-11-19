"""R2.1 entry point independent of the command line."""
from pathlib import Path

from .adquisition import capture_plan
from .adquisition.planner import write_plan
from .normalization.storage import build_normalized
from .report import search_units, version_key


def run_workflow(plan, catalog, bindings, module, output, from_version, to_version, *,
                 layer="all", maximum_hops=3, limit=10, module_name=None):
    # Inputs: An optional plan and bindings, a catalog, module, output, versions and query scope.
    # Does: Prepare acquisition inputs if needed and run the normalized graph workflow.
    # Output: The report, crossing and graph.
    if version_key(from_version) >= version_key(to_version):
        raise ValueError("Destination version must follow origin")
    if not Path(module).exists():
        raise ValueError("Module file or directory does not exist")
    if plan is None and bindings is not None:
        raise ValueError("Provide --plan to use custom bindings")
    output = Path(output)
    output.mkdir(parents=True)
    automatic_plan = plan is None
    if automatic_plan:
        planned = write_plan(module, from_version, to_version, catalog, output / "planning")
        plan, catalog, bindings = (planned[key] for key in ("plan", "catalog", "bindings"))
        planning_warnings = planned["warnings"]
    capture = capture_plan(plan, output / "temp_data", catalog_path=catalog)
    database = output / "collection.sqlite"
    build_normalized(capture["inventory"], bindings, database)
    result = search_units(database, module, from_version, to_version, layer=layer,
                          maximum_hops=maximum_hops, limit=limit, module_name=module_name)
    if automatic_plan:
        if capture["included"] == 0:
            planning_warnings.append("No planned source was admitted by acquisition.")
        elif result[0]["summary"]["eligible_distinct_changes"] == 0:
            planning_warnings.append("No version-bound change blocks were eligible for this query.")
        result[0]["warnings"] = sorted(set(result[0]["warnings"]) |
                                       {f"Planning: {message}" for message in planning_warnings})
    return result
