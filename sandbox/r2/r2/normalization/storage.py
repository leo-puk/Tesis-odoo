"""Persist the normalized corpus and its technical and lexical indexes."""
import os
import sqlite3
import tempfile
import time
from pathlib import Path

from .. import __version__
from ..records import canonical, split_unit, streaming_fingerprint
from .pipeline import normalize_session
from .terms import term_counts


def build_normalized(inventory, bindings, destination):
    # Inputs: inventory, bindings, destination.
    # Does: Normalize the admitted inventory and write its search indexes.
    # Output: An indexed SQLite database and build summary.
    started = time.perf_counter()
    corpus = normalize_session(inventory, bindings)
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ValueError("Choose a new collection path")

    metadata = dict(schema_version=4, layout="normalized-units", engine_version=__version__,
                    collection_revision=streaming_fingerprint(["normalized-units", corpus]),
                    normalization=corpus["normalization"], normalization_issues=corpus["issues"],
                    warnings=corpus["warnings"], excluded=corpus["excluded"],
                    include_oca_migrations=False, information_unit_count=len(corpus["units"]),
                    source_count=len(corpus["sources"]), artifact_count=len(corpus["artifacts"]),
                    bm25_fields=["text"], bm25_tokenizer="unicode61 normalized terms")
    fd, temporary = tempfile.mkstemp(prefix="r2-build-", suffix=".sqlite", dir=destination.parent)
    os.close(fd)
    con = sqlite3.connect(temporary)
    try:
        with con:
            con.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            records = {"sources": {source["id"]: source for source in corpus["sources"]},
                       "artifacts": corpus["artifacts"], "information_units": corpus["units"]}
            for table, rows in records.items():
                con.execute(f"CREATE TABLE {table}(id TEXT PRIMARY KEY,payload TEXT NOT NULL)")
                if table != "information_units":
                    con.executemany(f"INSERT INTO {table} VALUES (?,?)",
                                    ((key, canonical(row)) for key, row in sorted(rows.items())))
            con.execute("CREATE TABLE unit_content(unit_id TEXT PRIMARY KEY,payload TEXT NOT NULL)")
            for uid, unit in sorted(corpus["units"].items()):
                attributes, content = split_unit(unit)
                con.execute("INSERT INTO information_units VALUES (?,?)", (uid, canonical(attributes)))
                con.execute("INSERT INTO unit_content VALUES (?,?)", (uid, canonical(content)))
            con.execute("CREATE TABLE unit_entities(unit_id TEXT,ordinal INTEGER,name TEXT,type TEXT,"
                        "payload TEXT,PRIMARY KEY(unit_id,ordinal))")
            con.execute("CREATE INDEX unit_entity_lookup ON unit_entities(name,type)")
            con.execute("CREATE TABLE unit_terms(unit_id TEXT,term TEXT,frequency INTEGER,tfidf REAL,"
                        "PRIMARY KEY(unit_id,term))")
            con.execute("CREATE INDEX unit_term_lookup ON unit_terms(term)")
            con.execute("CREATE VIRTUAL TABLE unit_search USING fts5(unit_id UNINDEXED,text,tokenize='unicode61')")
            for uid, unit in sorted(corpus["units"].items()):
                con.executemany("INSERT INTO unit_entities VALUES (?,?,?,?,?)",
                                ((uid, i, entity["name"], entity["type"], canonical(entity))
                                 for i, entity in enumerate(unit["entities"])))
                con.executemany("INSERT INTO unit_terms VALUES (?,?,?,?)",
                                ((uid, term["term"], term["frequency"], term["tfidf"]) for term in unit["terms"]))
                text = " ".join(term_counts(unit["text"]).elements())
                con.execute("INSERT INTO unit_search VALUES (?,?)", (uid, text))
            con.executemany("INSERT INTO metadata VALUES (?,?)",
                            ((key, canonical(value)) for key, value in metadata.items()))
        con.close()
        # Windows rename and POSIX hard linking both refuse an existing target.
        if os.name == "nt":
            os.rename(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        con.close()
        Path(temporary).unlink(missing_ok=True)
    return {**metadata, "database": str(destination), "preparation_seconds": time.perf_counter() - started}
