"""Offline synthetic demonstration of the final acquisition integration."""
import argparse
import difflib
import json
from pathlib import Path

from r2.adquisition import capture_plan
from r2.collection import build_session
from r2.query import retrieve, validate_output

DIFF_URL = "https://github.com/odoo/odoo/compare/16.0...17.0"
DOC_URL = "https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html"
OLD = "class Field:\n    def setup(self):\n        pass\n"
NEW = "class Field:\n    def setup(self):\n        if self.states:\n            print('states changed; synthetic fixture')\n"
MODULE = "from odoo import fields, models\nclass Order(models.Model):\n    _inherit = 'sale.order'\n    value = fields.Float(states={'draft': [('readonly', False)]})\n"


class Response:
    status = 200
    headers = {"Content-Type": "text/plain; charset=utf-8"}

    def __init__(self, raw): self.raw = raw
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return self.raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Choose a new output directory")
    output.mkdir(parents=True)

    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    save("plan.json", [dict(id="odoo-diff", kind="github_diff", files={"changes.diff": DIFF_URL}),
                       dict(id="guide", kind="official_documentation", files={"guide.txt": DOC_URL})])
    save("catalog.json", dict(allowed_urls=[DIFF_URL, DOC_URL], excluded_urls=[],
                              oca_repositories=["OCA/synthetic-excluded"], oca_addons=["synthetic_excluded_addon"]))
    save("bindings.json", dict(sources={
        "odoo-diff": dict(from_version="16.0", to_version="17.0", from_revision="16.0", to_revision="17.0", context_units=["guide"]),
        "guide": dict(from_version="16.0", to_version="17.0"),
    }))
    diff = "".join(difflib.unified_diff(OLD.splitlines(True), NEW.splitlines(True),
                                       fromfile="a/odoo/fields.py", tofile="b/odoo/fields.py"))
    def transport(req, **kwargs):
        if req.full_url == DOC_URL:
            return Response(b"Synthetic explanatory document; not academic evidence.")
        if req.full_url == "https://api.github.com/repos/odoo/odoo/compare/16.0...17.0":
            return Response(diff.encode())
        raise ValueError("Demo transport does not access the internet")

    captured = capture_plan(output / "plan.json", output, catalog_path=output / "catalog.json", transport=transport)
    built = build_session(captured["inventory"], output / "bindings.json", output / "collection.sqlite")
    module = output / "module"
    module.mkdir()
    (module / "models.py").write_text(MODULE, encoding="utf-8")
    result = retrieve(output / "collection.sqlite", module, "16.0", "17.0")
    validation = validate_output(result)
    if not validation["conformant"] or result["summary"]["changes_found"] != 1:
        raise ValueError("Synthetic integration demonstration failed")
    save("query.json", result)
    save("run.json", dict(synthetic=True, production_download=False, capture=captured, build=built, validation=validation))
    print(json.dumps(dict(output=str(output), synthetic=True, captured_units=captured["included"],
                          candidate_changes=built["change_count"], conformant=validation["conformant"])))


if __name__ == "__main__":
    main()
