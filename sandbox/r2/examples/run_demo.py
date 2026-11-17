"""Reproduce an explicitly reviewed DEVELOPMENT example, not thesis evaluation."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from r2.collection import build, connect, load
from r2.query import retrieve, render_text, validate_output


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output" / "demo")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    raw = out / "candidates.sqlite"
    reviewed = out / "reviewed.sqlite"
    write(out / "build-candidates.json", build(root / "manifest.json", raw))
    with connect(raw) as con:
        changes = load(con, "changes")
    specs = [
        ("states is no longer supported", "States field property is no longer supported in Odoo 17",
         "property:states", "python"),
        ('attributes are no longer used', "XML attrs/states are rejected by the Odoo 17 view validator",
         "xml-attribute:attrs", "xml"),
    ]
    annotations = []
    for fragment, title, required, layer in specs:
        matches = [c for c in changes if fragment in c["added"]]
        if len(matches) != 1:
            raise ValueError(f"Expected one explicit core change for {fragment}, got {len(matches)}")
        annotations.append(dict(change_id=matches[0]["id"], title=title, status="verified",
                                reviewer="Codex developer review; not an independent relevance judgment",
                                reviewed_at=datetime.now(timezone.utc).isoformat(), category="syntax",
                                destination_validity=dict(status="checked", from_version="16.0", to_version="17.0",
                                    evidence_ids=["ev-"+matches[0]["id"][4:]],
                                    explanation="The captured destination source explicitly implements the shown warning/rejection."),
                                rationale=f"The added core code explicitly contains: {fragment}. Other changes in this block remain unclassified.",
                                required_elements=[required], affected_elements=[required], layer=layer))
    write(out / "annotations.json", annotations)
    write(out / "build-reviewed.json", build(root/"manifest.json", reviewed, annotations=out/"annotations.json"))
    for engine in ("graph", "bm25"):
        result = retrieve(reviewed, root/"original_module", "16.0", "17.0", engine=engine, status="verified", module_name="sale_advance_payment")
        write(out / f"query-{engine}.json", result)
        write(out / f"conformity-{engine}.json", validate_output(result))
        (out / f"query-{engine}.txt").write_text(render_text(result), encoding="utf-8")
        if not validate_output(result)["conformant"]:
            raise ValueError("Demo output is not conformant")
        print(render_text(result))


if __name__ == "__main__":
    main()
