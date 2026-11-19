"""Exercise the evaluation CLI with synthetic judgments on a local fixture."""
import argparse
import json
from pathlib import Path

from r2.cli import main
from .run_oca_functional_test import run


def demo(output):
    test_run = run(output)
    graph = json.loads((output / "query-graph.json").read_text(encoding="utf-8"))
    bm25 = json.loads((output / "query-bm25.json").read_text(encoding="utf-8"))
    targets = test_run["expected_targets"]
    references = {layer: dict(migration_id="local-demo", from_version="16.0", to_version="17.0",
                             available_unit_ids=[uid]) for layer, uid in targets.items()}
    reference_by_unit = {uid: layer for layer, uid in targets.items()}
    judgments = {}
    for report in (graph, bm25):
        for row in report["results"]:
            reference = reference_by_unit.get(row["source"]["unit_id"])
            judgments[row["change_id"]] = dict(relevant=reference is not None,
                                               reference_ids=[reference] if reference else [])
    query = dict(id="local-demo", module=test_run["module_path"], reference_ids=sorted(references),
                 judgments=judgments, **graph["query"])
    spec = dict(reviewer="Synthetic demonstration of the specification format",
                collection_revision=graph["collection_revision"], references=references, queries=[query])
    specification = output / "evaluation-spec.json"
    specification.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    main(["evaluate", str(specification), "--db", str(output / "candidates.sqlite"), "--repeats", "2"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    demo(parser.parse_args().output.resolve())
