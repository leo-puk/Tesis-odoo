"""Canonical records and read-only access shared by SQLite consumers."""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@contextmanager
def connect(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError("Collection does not exist; run build first")
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def meta(con):
    return {row[0]: json.loads(row[1]) for row in con.execute("SELECT key,value FROM metadata")}


def load(con, table):
    if table not in {"sources", "changes", "relations", "elements", "evidence", "comparisons",
                     "artifacts", "documents", "information_units"}:
        raise ValueError("Unknown collection table")
    return [json.loads(row[0]) for row in con.execute(f"SELECT payload FROM {table} ORDER BY id")]
