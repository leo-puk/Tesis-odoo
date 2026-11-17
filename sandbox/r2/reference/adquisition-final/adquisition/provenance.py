"""Capture timestamps, origin validation and JSON records."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib import parse


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def validate_source_origin(kind, url):
    parsed = parse.urlparse(url)
    host, path = parsed.hostname, parsed.path.lower()
    allowed = {
        "official_code": host == "raw.githubusercontent.com" and path.startswith("/odoo/odoo/"),
        "official_documentation": (host == "raw.githubusercontent.com" and path.startswith("/odoo/documentation/")) or (host in {"odoo.com", "www.odoo.com"} and path.startswith("/documentation/")),
        "oca_guidance": (host == "raw.githubusercontent.com" and path.startswith("/wiki/oca/maintainer-tools/")) or (host == "github.com" and path.startswith("/oca/maintainer-tools/wiki/")),
        "openupgrade_analysis": (host == "raw.githubusercontent.com" and path.startswith("/oca/openupgrade/")) or host == "oca.github.io",
    }
    if parsed.scheme != "https" or not allowed.get(kind):
        raise ValueError("Source URL is outside the declared official/OCA origin policy")


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
