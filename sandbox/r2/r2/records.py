"""Canonical records and read-only access shared by SQLite consumers."""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def canonical(value):
    # Inputs: value.
    # Does: Serialize the value using a canonical JSON representation.
    # Output: Deterministic JSON text.
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fingerprint(value):
    # Inputs: value.
    # Does: Hash the canonical representation of a value.
    # Output: A SHA-256 fingerprint.
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def streaming_fingerprint(value):
    # Hash the same canonical JSON without materializing its full text in memory.
    encoder = json.JSONEncoder(sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256()
    for piece in encoder.iterencode(value):
        digest.update(piece.encode())
    return digest.hexdigest()


@contextmanager
def connect(path):
    # Inputs: path.
    # Does: Open an existing SQLite collection for read-only queries.
    # Output: A managed SQLite connection.
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
    # Inputs: con.
    # Does: Decode the collection metadata rows.
    # Output: A metadata mapping.
    return {row[0]: json.loads(row[1]) for row in con.execute("SELECT key,value FROM metadata")}


def split_unit(unit):
    # Keep graph observations separate from the text used by reports and BM25.
    content_fields = {"text", "data", "terms"}
    attributes = {key: value for key, value in unit.items() if key not in content_fields}
    content = {key: unit[key] for key in content_fields if key in unit}
    return attributes, content


def load(con, table):
    # Inputs: con, table.
    # Does: Decode the stored payloads for a collection table.
    # Output: A list of decoded records.
    if table not in {"sources", "changes", "relations", "elements", "evidence", "comparisons",
                     "artifacts", "documents", "information_units"}:
        raise ValueError("Unknown collection table")
    if table == "information_units" and con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='unit_content'"
    ).fetchone():
        rows = con.execute(
            "SELECT u.payload, c.payload FROM information_units AS u "
            "LEFT JOIN unit_content AS c ON c.unit_id=u.id ORDER BY u.id"
        )
        units = []
        for attributes, content in rows:
            if content is None:
                raise ValueError("Unit content is missing from the collection")
            units.append(dict(json.loads(attributes), **json.loads(content)))
        return units
    return [json.loads(row[0]) for row in con.execute(f"SELECT payload FROM {table} ORDER BY id")]
