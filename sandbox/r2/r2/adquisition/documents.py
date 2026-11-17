"""Deterministic HTML-to-text conversion; no summarization."""
from html.parser import HTMLParser
import re


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "section", "h1", "h2", "h3", "li", "br", "tr", "pre"}:
            self.parts.append("\n")
        if not self.hidden:
            for name, value in attrs:
                if name == "href" and value:
                    self.parts.append(f" [{value}] ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {"p", "div", "li", "pre"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def document_text(raw, content_type):
    charset = re.search(r"charset=[\"']?([\w.-]+)", content_type, re.I)
    text = raw.decode(charset.group(1) if charset else "utf-8")
    if "html" in content_type.lower() or text.lstrip().lower().startswith(("<!doctype html", "<html")):
        parser = TextParser()
        parser.feed(text)
        return "".join(parser.parts).replace("\r\n", "\n")
    return text.replace("\r\n", "\n")
