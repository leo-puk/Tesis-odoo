"""Conservative token anchors for Python hunks that need not form a full AST."""
import ast
import io
import re
import tokenize
from ..extract_relations import FIELD_OPTIONS, layer_for


def partial_anchors(code, path, module):
    # Inputs: code, path, module.
    # Does: Detect supported anchors in incomplete code fragments.
    # Output: The recoverable code observations.
    if not path.endswith(".py"):
        return []
    # Indentation is irrelevant to the two local token patterns below. Removing
    # it lets tokenize inspect a partial block without fabricating a class/AST.
    text = "\n".join(line.lstrip() for line in code.splitlines())
    stream, tokens = tokenize.generate_tokens(io.StringIO(text).readline), []
    try:
        for token in stream:
            if token.type not in {tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                                  tokenize.DEDENT, tokenize.COMMENT, tokenize.ENDMARKER}:
                tokens.append(token)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass  # Only already-observed complete token patterns may contribute.
    elements = {}

    def add(key, kind, name, line):
        # Inputs: key, kind, name, line.
        # Does: Register a partial code anchor at its observed line.
        # Output: An entry in the current anchor collection.
        elements[key, line] = dict(key=key, kind=kind, name=name, path=path,
                                   line=line, end_line=line, layer=layer_for(path),
                                   module=module or "__unknown__", role="reference",
                                   extraction_basis="local_python_tokens_no_owner_or_relation_inferred")

    field_api = path in {"odoo/fields.py", "odoo/orm/fields.py"}
    for index, token in enumerate(tokens):
        part = tokens[index:index+3]
        if (field_api and len(part) == 3 and token.type == tokenize.NAME and token.string == "self"
                and part[1].string == "." and part[2].type == tokenize.NAME
                and part[2].string in FIELD_OPTIONS):
            name = part[2].string
            add("property:" + name, "property", name, token.start[0])
        call = tokens[index:index+4]
        if (len(call) == 4 and token.string == "." and call[1].type == tokenize.NAME
                and call[1].string == "xpath" and call[2].string == "(" and call[3].type == tokenize.STRING):
            try:
                expression = ast.literal_eval(call[3].string)
            except (ValueError, SyntaxError):
                continue
            if isinstance(expression, str):
                for name in re.findall(r"@([A-Za-z_][\w:-]*)", expression):
                    add("xml-attribute:" + name, "xml_attribute", name, call[3].start[0])
    return list(elements.values())
