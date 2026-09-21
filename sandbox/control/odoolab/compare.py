"""Comparador: nuestra migracion (ours) vs la de OCA (oca, tomada como correcta)."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from . import pg


@dataclass
class Diff:
    kind: str
    severity: str          # "error" | "warning" | "info"
    ref: str               # tabla / modulo / modelo
    detail: str

    def dict(self):
        return asdict(self)


@dataclass
class CompareResult:
    ours_db: str
    oca_db: str
    diffs: list[Diff] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def errors(self):
        return [d for d in self.diffs if d.severity == "error"]

    @property
    def fidelity(self) -> float:
        """% de objetos comparados que coinciden. Metrica principal de la tesis."""
        total = self.stats.get("objects_compared", 0)
        return 100.0 if not total else round(100 * (1 - len(self.errors) / total), 3)

    def dict(self):
        return {"ours_db": self.ours_db, "oca_db": self.oca_db,
                "fidelity_pct": self.fidelity, "stats": self.stats,
                "diffs": [d.dict() for d in self.diffs]}


def _set(rows):
    return {tuple(r) for r in rows}


def compare(ours: str, oca: str, cfg: dict) -> CompareResult:
    r = CompareResult(ours_db=ours, oca_db=oca)
    ignore_tables = set(cfg.get("ignore_tables") or [])
    ignore_cols = set(cfg.get("ignore_columns") or [])
    compared = 0

    # --- 1. esquema ------------------------------------------------------
    if cfg.get("schema", True):
        a, b = _set(pg.q(ours, pg.SCHEMA_SQL)), _set(pg.q(oca, pg.SCHEMA_SQL))
        a = {x for x in a if x[0] not in ignore_tables}
        b = {x for x in b if x[0] not in ignore_tables}
        compared += len(b)
        for t, c, *_ in sorted(b - a):
            r.diffs.append(Diff("schema.missing_column", "error", f"{t}.{c}",
                                "existe en OCA y falta en la nuestra"))
        for t, c, *_ in sorted(a - b):
            r.diffs.append(Diff("schema.extra_column", "warning", f"{t}.{c}",
                                "existe en la nuestra y no en OCA"))
        # mismatch de tipo sobre columnas presentes en ambas
        ta = {(x[0], x[1]): x for x in a}
        for key, xb in {(x[0], x[1]): x for x in b}.items():
            xa = ta.get(key)
            if xa and xa[2] != xb[2]:
                r.diffs.append(Diff("schema.type_mismatch", "error", f"{key[0]}.{key[1]}",
                                    f"ours={xa[2]} oca={xb[2]}"))

        ca, cb = _set(pg.q(ours, pg.CONSTRAINTS_SQL)), _set(pg.q(oca, pg.CONSTRAINTS_SQL))
        compared += len(cb)
        for t, k, n in sorted(cb - ca):
            r.diffs.append(Diff("schema.missing_constraint", "error", f"{t}:{n}", k))
        ia, ib = _set(pg.q(ours, pg.INDEXES_SQL)), _set(pg.q(oca, pg.INDEXES_SQL))
        for t, n, _def in sorted({(x[0], x[1]) for x in ib} - {(x[0], x[1]) for x in ia}):
            r.diffs.append(Diff("schema.missing_index", "warning", f"{t}:{n}", ""))

    # --- 2. modulos ------------------------------------------------------
    if cfg.get("modules", True):
        ma = {n: (s, v) for n, s, v in pg.q(ours, pg.MODULES_SQL)}
        mb = {n: (s, v) for n, s, v in pg.q(oca, pg.MODULES_SQL)}
        compared += len(mb)
        for name, (state, ver) in mb.items():
            if name not in ma:
                r.diffs.append(Diff("module.missing", "error", name, f"OCA: {state}"))
            elif ma[name][0] != state:
                sev = "error" if state == "installed" else "warning"
                r.diffs.append(Diff("module.state", sev, name,
                                    f"ours={ma[name][0]} oca={state}"))
            elif ma[name][1] != ver:
                r.diffs.append(Diff("module.version", "warning", name,
                                    f"ours={ma[name][1]} oca={ver}"))

    # --- 3. datos --------------------------------------------------------
    if cfg.get("data", True):
        rca = pg.row_counts(ours, ignore_tables)
        rcb = pg.row_counts(oca, ignore_tables)
        compared += len(rcb)
        for t, n in sorted(rcb.items()):
            if t not in rca:
                r.diffs.append(Diff("data.missing_table", "error", t, f"oca rows={n}"))
            elif rca[t] != n:
                r.diffs.append(Diff("data.row_count", "error", t,
                                    f"ours={rca[t]} oca={n} (delta={rca[t]-n})"))

        # diff a nivel registro solo donde el conteo coincide (evita ruido)
        checked = 0
        for t, n in sorted(rcb.items()):
            if t not in rca or rca[t] != n or n == 0:
                continue
            cols_a = pg.columns_of(ours, t, ignore_cols)
            cols_b = pg.columns_of(oca, t, ignore_cols)
            common = [c for c in cols_b if c in set(cols_a)]
            if not common:
                continue
            da = dict(pg.table_digest(ours, t, common))
            db_ = dict(pg.table_digest(oca, t, common))
            bad = [k for k, v in db_.items() if da.get(k) != v]
            checked += len(db_)
            if bad:
                r.diffs.append(Diff("data.row_mismatch", "error", t,
                                    f"{len(bad)}/{len(db_)} filas difieren; ids ej.: {bad[:10]}"))
        r.stats["rows_digested"] = checked

    r.stats["objects_compared"] = compared
    r.stats["errors"] = len(r.errors)
    r.stats["warnings"] = len([d for d in r.diffs if d.severity == "warning"])
    return r
