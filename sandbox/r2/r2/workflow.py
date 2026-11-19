"""R2.1 entry point independent of the command line."""
from pathlib import Path

from .adquisition import capture_plan
from .normalization.storage import build_normalized
from .report import search_units, version_key


def run_workflow(plan, catalog, bindings, module, output, from_version, to_version, *,
                 layer="all", maximum_hops=3, limit=10, module_name=None):
    if version_key(from_version) >= version_key(to_version):
        raise ValueError("Destination version must follow origin")
    if not Path(module).exists():
        raise ValueError("Module file or directory does not exist")
    output = Path(output)
    output.mkdir(parents=True)
    capture = capture_plan(plan, output / "temp_data", catalog_path=catalog)
    database = output / "collection.sqlite"
    build_normalized(capture["inventory"], bindings, database)
    return search_units(database, module, from_version, to_version, layer=layer,
                        maximum_hops=maximum_hops, limit=limit, module_name=module_name)
