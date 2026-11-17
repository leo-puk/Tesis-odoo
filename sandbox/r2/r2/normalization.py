"""Offline text conversion; original captured bytes remain separate."""
from lxml import html


def normalize(raw, content_type=""):
    text = raw.decode("utf-8-sig")
    if "html" in content_type or text.lstrip().lower().startswith(("<!doctype html", "<html")):
        root = html.fromstring(raw)
        for node in root.xpath("//script|//style|//nav|//footer"):
            node.drop_tree()
        text = root.text_content()
    return text.replace("\r\n", "\n").replace("\r", "\n")
