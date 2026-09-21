"""Acceso a Postgres del sandbox: clonado de DBs e introspeccion para el diff."""
from __future__ import annotations

import os
import psycopg

PGHOST = os.environ.get("PGHOST", "db")
PGUSER = os.environ.get("PGUSER", os.environ.get("PG_USER", "odoo"))
PGPASS = os.environ.get("PGPASSWORD", os.environ.get("PG_PASSWORD", "odoo"))


def dsn(db: str = "postgres") -> str:
    return f"host={PGHOST} user={PGUSER} password={PGPASS} dbname={db}"


def connect(db: str = "postgres", autocommit=False):
    return psycopg.connect(dsn(db), autocommit=autocommit)


def q(db: str, sql: str, params=()) -> list[tuple]:
    with connect(db) as c, c.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def exists(db: str) -> bool:
    return bool(q("postgres", "select 1 from pg_database where datname=%s", (db,)))


def terminate(db: str) -> None:
    with connect("postgres", autocommit=True) as c, c.cursor() as cur:
        cur.execute("select pg_terminate_backend(pid) from pg_stat_activity "
                    "where datname=%s and pid<>pg_backend_pid()", (db,))


def drop(db: str) -> None:
    terminate(db)
    with connect("postgres", autocommit=True) as c, c.cursor() as cur:
        cur.execute(f'drop database if exists "{db}"')


def clone(src: str, dst: str) -> None:
    """Copia fisica: es el 'fork' de produccion. src debe estar sin conexiones activas."""
    drop(dst)
    terminate(src)
    with connect("postgres", autocommit=True) as c, c.cursor() as cur:
        cur.execute(f'create database "{dst}" with template "{src}" owner "{PGUSER}"')


# ---- introspeccion para el comparador -----------------------------------

SCHEMA_SQL = """
select table_name, column_name, data_type, is_nullable, coalesce(column_default,'')
from information_schema.columns
where table_schema='public'
order by 1,2
"""

CONSTRAINTS_SQL = """
select tc.table_name, tc.constraint_type, tc.constraint_name
from information_schema.table_constraints tc
where tc.table_schema='public' and tc.constraint_type in ('PRIMARY KEY','FOREIGN KEY','UNIQUE')
order by 1,2,3
"""

INDEXES_SQL = """
select tablename, indexname, indexdef from pg_indexes
where schemaname='public' order by 1,2
"""

MODULES_SQL = """
select name, state, latest_version from ir_module_module order by name
"""

MODELS_SQL = """
select m.model, m.id from ir_model m where m.transient = false order by m.model
"""


def tables(db: str) -> list[str]:
    return [r[0] for r in q(db, "select table_name from information_schema.tables "
                                "where table_schema='public' and table_type='BASE TABLE' order by 1")]


def row_counts(db: str, ignore: set[str]) -> dict[str, int]:
    out = {}
    with connect(db) as c, c.cursor() as cur:
        for t in tables(db):
            if t in ignore:
                continue
            cur.execute(f'select count(*) from "{t}"')
            out[t] = cur.fetchone()[0]
    return out


def columns_of(db: str, table: str, ignore_cols: set[str]) -> list[str]:
    rows = q(db, "select column_name from information_schema.columns "
                 "where table_schema='public' and table_name=%s order by 1", (table,))
    return [r[0] for r in rows if r[0] not in ignore_cols]


def table_digest(db: str, table: str, cols: list[str], limit: int | None = None) -> list[tuple]:
    """(id, md5 de la fila) para diff a nivel registro sobre columnas comparables."""
    if not cols:
        return []
    expr = " || '|' || ".join(f"coalesce(\"{c}\"::text,'')" for c in cols)
    has_id = "id" in [r[0] for r in q(db, "select column_name from information_schema.columns "
                                          "where table_schema='public' and table_name=%s", (table,))]
    key = '"id"' if has_id else "row_number() over ()"
    sql = f'select {key} as k, md5({expr}) from "{table}" order by 1'
    if limit:
        sql += f" limit {int(limit)}"
    return q(db, sql)
