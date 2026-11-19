"""Read Odoo source as data. Never import or evaluate the input module."""
import ast
import csv
import io
import re
from pathlib import Path
from lxml import etree

LAYERS = ("python", "xml", "data", "manifest")
FIELD_OPTIONS = {"states", "readonly", "required", "store", "compute", "inverse", "related",
                 "comodel_name", "inverse_name", "selection", "domain", "context", "default",
                 "tracking", "string", "help", "copy", "index", "ondelete", "check_company"}


def layer_for(path):
    # Inputs: path.
    # Does: Infer a code layer from a file path.
    # Output: The layer label.
    p = Path(path)
    if p.name == "__manifest__.py":
        return "manifest"
    if p.suffix == ".py":
        return "python"
    if p.suffix == ".xml":
        return "data" if any(x in p.parts for x in ("data", "security")) else "xml"
    if p.suffix == ".csv":
        return "data"
    return "documentation"


def tokens(text):
    # Inputs: text.
    # Does: Extract lexical tokens from the supplied text.
    # Output: The token sequence.
    """Stable lexical representation shared by BM25 corpus and queries."""
    return sorted(set(re.findall(r"[a-zA-Z_][a-zA-Z_0-9]*", text.lower())))


def extract(text, path, module=None):
    # Inputs: text, path, module.
    # Does: Extract legacy code entities and their relations.
    # Output: A code observation and relation record.
    layer = layer_for(path)
    module = module or (Path(path).parts[0] if len(Path(path).parts) > 1 else "__unknown__")
    elements, relations, warnings = [], [], []

    def add(key, kind, name, start=1, end=None, role="reference"):
        # Inputs: key, kind, name, start, end, role.
        # Does: Register a localized legacy code entity.
        # Output: An entry in the current entity collection.
        elements.append(dict(key=key, kind=kind, name=name, path=path,
                             line=start or 1, end_line=end or start or 1, layer=layer,
                             module=module, role=role))
        return key

    def xmlid(value):
        # Inputs: value.
        # Does: Apply the addon namespace to an XML identifier when available.
        # Output: The normalized XML identifier.
        return value if "." in value else f"{module}.{value}"

    def edge(a, b, kind, line=1):
        # Inputs: a, b, kind, line.
        # Does: Register a relation between two legacy code entities.
        # Output: An entry in the current relation collection.
        if a != b:
            relations.append(dict(source=a, target=b, kind=kind, path=path, line=line or 1))

    def literal(node, fallback=None):
        # Inputs: node, fallback.
        # Does: Read the value of an AST literal or use its fallback.
        # Output: A literal value or the fallback.
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError, SyntaxError, RecursionError):
            return fallback

    try:
        if Path(path).suffix == ".py":
            tree = ast.parse(text, filename=path)
            if layer == "manifest":
                value = next((literal(n.value) for n in tree.body if isinstance(n, ast.Expr)), None)
                if not isinstance(value, dict):
                    warnings.append(f"{path}: manifest is not a literal dictionary")
                else:
                    for key, val in sorted(value.items()):
                        a = add(f"manifest:{key}", "manifest_key", key, 1, len(text.splitlines()))
                        if key == "depends":
                            for dep in val:
                                b = add(f"module:{dep}", "module", dep)
                                edge(a, b, "depends")
                        if key in {"data", "demo"}:
                            for file in val:
                                edge(a, add(f"file:{file}", "file", file), "loads")
                return dict(elements=elements, relations=relations, warnings=warnings)
            for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
                names = {}
                for stmt in cls.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name) and target.id in {"_name", "_inherit"}:
                                names[target.id] = literal(stmt.value)
                inherited = names.get("_inherit", [])
                inherited = [inherited] if isinstance(inherited, str) else inherited or []
                models = [names["_name"]] if isinstance(names.get("_name"), str) else inherited
                models = models or [f"@{path}:{cls.name}"]
                class_key = add(f"class:{module}:{path}:{cls.name}", "class", cls.name, cls.lineno, cls.end_lineno, "declaration")
                known_fields = {t.id for stmt in cls.body if isinstance(stmt, ast.Assign) and
                                isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Attribute) and
                                isinstance(stmt.value.func.value, ast.Name) and stmt.value.func.value.id == "fields"
                                for t in stmt.targets if isinstance(t, ast.Name)}
                known_methods = {s.name for s in cls.body if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))}
                for model in models:
                    mk = add(f"model:{model}", "model", model, cls.lineno, cls.end_lineno)
                    edge(class_key, mk, "extends", cls.lineno)
                    for parent in inherited:
                        edge(mk, add(f"model:{parent}", "model", parent), "inherits", cls.lineno)
                    for stmt in cls.body:
                        owner = mk
                        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            owner = add(f"method:{model}.{stmt.name}", "method", f"{model}.{stmt.name}", stmt.lineno, stmt.end_lineno, "declaration")
                            edge(owner, mk, "belongs_to", stmt.lineno)
                            for dec in stmt.decorator_list:
                                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in {"depends", "onchange"}:
                                    for arg in dec.args:
                                        val = literal(arg)
                                        if isinstance(val, str):
                                            edge(owner, add(f"field:{model}.{val.split('.')[0]}", "field", f"{model}.{val.split('.')[0]}"), "depends_on", dec.lineno)
                        elif isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                            call = stmt.value
                            if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == "fields":
                                for target in stmt.targets:
                                    if not isinstance(target, ast.Name):
                                        continue
                                    owner = add(f"field:{model}.{target.id}", "field", f"{model}.{target.id}", stmt.lineno, stmt.end_lineno, "declaration")
                                    edge(owner, mk, "belongs_to", stmt.lineno)
                                    kw = {k.arg: literal(k.value) for k in call.keywords if k.arg}
                                    comodel = kw.get("comodel_name")
                                    if not comodel and call.func.attr in {"Many2one", "One2many", "Many2many"} and call.args:
                                        comodel = literal(call.args[0])
                                    if isinstance(comodel, str):
                                        edge(owner, add(f"model:{comodel}", "model", comodel), "comodel", stmt.lineno)
                                    if isinstance(kw.get("compute"), str):
                                        edge(owner, add(f"method:{model}.{kw['compute']}", "method", f"{model}.{kw['compute']}"), "computed_by", stmt.lineno)
                        for node in ast.walk(stmt):
                            if isinstance(node, ast.Attribute):
                                is_field_api = (cls.name == "Field" or any(isinstance(base, ast.Name) and base.id == "Field" for base in cls.bases)) and node.attr in FIELD_OPTIONS
                                key = f"property:{node.attr}" if is_field_api else f"attribute:{model}.{node.attr}"
                                prop = add(key, "property" if is_field_api else "attribute", node.attr, node.lineno, node.end_lineno)
                                edge(owner, prop, "uses_attribute", node.lineno)
                                if isinstance(node.value, ast.Name) and node.value.id == "self":
                                    kind = "field" if node.attr in known_fields else "method" if node.attr in known_methods else "unresolved"
                                    target = add(f"{kind}:{model}.{node.attr}", kind, f"{model}.{node.attr}", node.lineno,
                                                 role="unresolved" if kind == "unresolved" else "reference")
                                    edge(owner, target, "self_reference", node.lineno)
                            if isinstance(node, ast.keyword) and node.arg:
                                is_field_api = owner.startswith("field:") and node.arg in FIELD_OPTIONS
                                key = f"property:{node.arg}" if is_field_api else f"argument:{owner}.{node.arg}"
                                prop = add(key, "property" if is_field_api else "argument", node.arg, node.lineno, node.end_lineno)
                                edge(owner, prop, "uses_keyword", node.lineno)
                                if is_field_api:
                                    edge(prop, add(f"symbol:{node.arg}", "symbol", node.arg, node.lineno), "symbol", node.lineno)
                            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "env":
                                value = literal(node.slice)
                                if isinstance(value, str):
                                    edge(owner, add(f"model:{value}", "model", value, node.lineno), "env_reference", node.lineno)
                                else:
                                    warnings.append(f"{path}:{node.lineno}: unresolved dynamic env reference")
                            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "ref" and node.args:
                                value = literal(node.args[0])
                                if isinstance(value, str):
                                    value = xmlid(value)
                                    edge(owner, add(f"xmlid:{value}", "xmlid", value, node.lineno), "external_id", node.lineno)
                                else:
                                    warnings.append(f"{path}:{node.lineno}: unresolved dynamic external ID")
                            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "xpath" and node.args:
                                expression = literal(node.args[0])
                                if isinstance(expression, str):
                                    for name in re.findall(r"@([A-Za-z_][\w:-]*)", expression):
                                        edge(owner, add(f"xml-attribute:{name}", "xml_attribute", name, node.lineno), "validates_xml_attribute", node.lineno)
            # Module-level functions, imports and APIs not in Odoo model classes.
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add(f"function:{node.name}", "function", node.name, node.lineno, node.end_lineno)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add(f"symbol:{node.name}", "symbol", node.name, node.lineno, node.lineno)
        elif Path(path).suffix == ".xml":
            parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True, recover=False)
            root = etree.fromstring(text.encode(), parser)
            if root.getroottree().docinfo.doctype:
                raise ValueError("XML DTD is not accepted")
            owners = {}
            for node in root.iter():
                if not isinstance(node.tag, str):
                    continue
                record = node if node.tag in {"record", "template"} or node.get("t-name") else next(
                    (a for a in node.iterancestors() if a.tag in {"record", "template"} or a.get("t-name")), None)
                if record is not None and record not in owners:
                    rid = xmlid(record.get("id") or record.get("t-name") or f"@{path}:{record.sourceline}")
                    owners[record] = add(f"xmlid:{rid}", "view" if record.tag == "template" or record.get("t-name") or record.get("model") == "ir.ui.view" else "record", rid, record.sourceline, role="declaration")
                owner = owners.get(record) or f"file:{module}:{path}"
                fields = {n.get("name"): n for n in record.findall("field")} if record is not None else {}
                model = (fields["model"].text or "").strip() if "model" in fields else record.get("model", "") if record is not None else ""
                if model:
                    edge(owner, add(f"model:{model}", "model", model, node.sourceline), "model", node.sourceline)
                for attribute, value in sorted(node.attrib.items()):
                    prop = add(f"xml-attribute:{attribute}", "xml_attribute", attribute, node.sourceline)
                    edge(owner, prop, "xml_attribute", node.sourceline)
                    if attribute in {"ref", "inherit_id", "t-call", "t-inherit", "t-extend"}:
                        if re.fullmatch(r"[A-Za-z_][\w.]*", value):
                            target = xmlid(value)
                            edge(owner, add(f"xmlid:{target}", "xmlid", target, node.sourceline), "qweb_call" if attribute == "t-call" else "inherits_or_references", node.sourceline)
                        else:
                            warnings.append(f"{path}:{node.sourceline}: unresolved dynamic XML reference")
                    if attribute == "groups":
                        for group in value.split(","):
                            group = group.strip()
                            negative = group.startswith("!")
                            group = group.lstrip("!")
                            if group:
                                target = xmlid(group)
                                edge(owner, add(f"xmlid:{target}", "group", target, node.sourceline), "excludes_group" if negative else "requires_group", node.sourceline)
                    if attribute == "eval":
                        for target in re.findall(r"ref\(['\"]([^'\"]+)['\"]\)", value):
                            target = xmlid(target)
                            edge(owner, add(f"xmlid:{target}", "xmlid", target, node.sourceline), "data_reference", node.sourceline)
                if node.tag == "field" and node.get("name") and "arch" in fields and fields["arch"] in list(node.iterancestors()):
                    edge(owner, add(f"field:{model}.{node.get('name')}", "field", f"{model}.{node.get('name')}", node.sourceline), "displays", node.sourceline)
                if node.tag == "xpath":
                    add(f"xpath:{module}:{path}:{node.sourceline}", "xpath", node.get("expr", ""), node.sourceline)
        elif Path(path).suffix == ".csv":
            for i, row in enumerate(csv.DictReader(io.StringIO(text)), 2):
                owner = add(f"xmlid:{xmlid(row['id'])}", "record", xmlid(row['id']), i, role="declaration") if row.get("id") else f"file:{module}:{path}"
                for key, value in row.items():
                    if key and value and (key.endswith(":id") or key == "id"):
                        target = xmlid(value)
                        edge(owner, add(f"xmlid:{target}", "group" if key.startswith("group") else "xmlid", target, i), "security_reference", i)
        elif layer == "documentation":
            for number, line in enumerate(text.splitlines(), 1):
                # Code identifiers explicitly marked by Markdown/RST, not prose.
                for span in re.findall(r"`+([^`]+)`+", line):
                    for name in re.findall(r"[A-Za-z_][A-Za-z_0-9]*", span):
                        add(f"symbol:{name}", "symbol", name, number)
    except (SyntaxError, ValueError, etree.XMLSyntaxError, csv.Error) as exc:
        warnings.append(f"{path}: {type(exc).__name__}: {exc}")
    return dict(elements=elements, relations=relations, warnings=sorted(set(warnings)))


def module_files(directory):
    # Inputs: directory.
    # Does: Enumerate files supported by the legacy module scanner.
    # Output: The module paths to scan.
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError("Module directory does not exist")
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or any(x in path.relative_to(root).parts for x in (".git", "__pycache__", ".venv")):
            continue
        if path.suffix in {".py", ".xml", ".csv"}:
            yield path.relative_to(root).as_posix(), path.read_text(encoding="utf-8-sig")


def resolve_references(data, declarations=()):
    # Inputs: data, declarations.
    # Does: Resolve legacy references against known declarations.
    # Output: The enriched legacy observations.
    known = {e["key"] for e in [*data["elements"], *declarations] if e.get("role") == "declaration"}
    mapping = {}
    for element in data["elements"]:
        if element["kind"] == "unresolved":
            name = element["key"].split(":", 1)[1]
            candidates = [k for k in (f"field:{name}", f"method:{name}") if k in known]
            if len(candidates) == 1:
                mapping[element["key"]] = candidates[0]
    for element in data["elements"]:
        if element["key"] in mapping:
            element["key"] = mapping[element["key"]]
            element["kind"] = element["key"].split(":", 1)[0]
            element["role"] = "reference"
    for relation in data["relations"]:
        relation["source"] = mapping.get(relation["source"], relation["source"])
        relation["target"] = mapping.get(relation["target"], relation["target"])
    return data


def scan_module(directory, module_name=None):
    # Inputs: directory, module_name.
    # Does: Aggregate legacy observations across module files.
    # Output: The module scan and associated diagnostics.
    data = dict(elements=[], relations=[], warnings=[])
    for path, text in module_files(directory):
        for kind, values in extract(text, path, module_name or Path(directory).resolve().name).items():
            data[kind].extend(values)
    data["warnings"] = sorted(set(data["warnings"]))
    return resolve_references(data)
