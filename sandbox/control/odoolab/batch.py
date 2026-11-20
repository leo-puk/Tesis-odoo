"""Lote de experimentos: N grupos de K modulos OCA, muestreados y migrados 16.0 -> 17.0.

  sample   muestra estratificada y reproducible (semilla fija) desde el censo: cada grupo
           lleva un modulo por estrato (sale, stock, account, negocio, tecnico). Cada
           candidato se valida antes de entrar (S0 separable, existe en 16.0, sin
           dependencias Python externas, dependencias OCA disponibles en ambas ramas).
  run      prepare -> seed -> baseline -> auto -> report por grupo, `parallel` a la vez.
           Si un modulo no siembra en 16.0 se reemplaza por uno de reserva del mismo
           estrato y queda registrado.
  summary  agrega todos los grupos: research/lote_<v>/RESULTADOS.md y casuisticas.csv
"""
from __future__ import annotations

import csv
import json
import random
import re
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import casuistics as cz
from . import experiment as ex

STRATA = ("sale", "stock", "account", "negocio", "tecnico")
_BUSINESS = ("purchase", "mrp", "hr", "project", "crm", "maintenance", "fleet", "event",
             "website", "point_of_sale", "repair", "survey", "mass_mailing", "calendar",
             "contacts", "product", "uom", "quality", "helpdesk", "sign", "timesheet", "lunch")
_EXCLUDED_REPOS = re.compile(r"^(l10n-|connector|edi|vertical-|pms$|wms$|shopfloor|storage$|"
                             r"rest-framework|web-api|odoo-pim|interface-github|"
                             r"infrastructure|ai$|iot$|cooperative|donation)")


def stratum(core_deps: str) -> str:
    ds = core_deps.split()
    if any(d.startswith("sale") for d in ds):
        return "sale"
    if any(d.startswith(("stock", "delivery")) for d in ds):
        return "stock"
    if any(d.startswith("account") for d in ds):
        return "account"
    if any(d.startswith(_BUSINESS) for d in ds):
        return "negocio"
    return "tecnico"


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def eligible(exclude: set[str]) -> dict[str, list[dict]]:
    cd = ex.census_dir()
    v = ex.DST.replace(".", "")
    mods = {(r["repo"], r["module"]): r for r in _read(cd / f"modules_{v}.csv")}
    core = (set((cd / "core_addons_160.txt").read_text().split())
            & set((cd / f"core_addons_{v}.txt").read_text().split()))
    pools: dict[str, list[dict]] = {s: [] for s in STRATA}
    for e in _read(cd / f"mig_enriched_{v}.csv"):
        m = mods[(e["repo"], e["module"])]
        if (e["module"] in exclude or _EXCLUDED_REPOS.search(e["repo"])
                or m.get("mig_match") != "name" or m["has_tests"] != "True"
                or not 3 <= int(e["n_hunks_behaviour"]) <= 60
                or int(e["n_oca_deps"]) > 1
                or e["mig_touches_module_whole"] == "True"
                or not set(e["core_deps"].split()) <= core):
            continue
        pools[stratum(e["core_deps"])].append({"repo": e["repo"], "module": e["module"],
                                               "stratum": stratum(e["core_deps"]),
                                               "depends": e["depends"].split()})
    return pools


def _valid(c: dict, group: list[dict], rows: list[dict]) -> str:
    """'' si el candidato sirve; si no, el motivo."""
    names = {g["module"] for g in group}
    if names & set(c["depends"]) or any(c["module"] in g["depends"] for g in group):
        return "depende de otro modulo del grupo"
    try:
        src = ex._module_source(c["repo"], c["module"], rows)
        index = {r["module"]: r["repo"] for r in rows}
        for dep in ex._resolve_oca_deps(src["depends"], index, set()):
            g16 = ex.census.sync_repo(index[dep], ex.SRC, ex.cache_dir())
            if g16 is None or not ex._git_ok("cat-file", "-e", f"{ex.SRC}:{dep}", cwd=g16):
                return f"dependencia OCA {dep} no existe en {ex.SRC}"
    except Exception as e:                               # noqa: BLE001 - motivo de descarte
        return str(e)[:200]
    return ""


def sample(n_groups: int = 10, size: int = 5, seed: int = 2026,
           fixed: list[list[tuple[str, str]]] | None = None,
           exclude: set[str] | None = None, out: Path | None = None) -> dict:
    rows = ex._census_rows()
    fixed = fixed or []
    used = set(exclude or set()) | {m for g in fixed for _, m in g}
    pools = eligible(used)
    rng = random.Random(seed)
    for p in pools.values():
        rng.shuffle(p)
    groups, rejected = [], []
    for gi, g in enumerate(fixed, 1):
        groups.append({"id": f"g{gi:02d}", "origin": "muestra propuesta",
                       "modules": [{"repo": r, "module": m, "stratum": "fijo"} for r, m in g]})
    while len(groups) < n_groups:
        group: list[dict] = []
        for s in (STRATA * 2)[:size]:
            while pools[s]:
                c = pools[s].pop()
                why = _valid(c, group, rows)
                if why:
                    rejected.append({**c, "motivo": why})
                    continue
                group.append(c)
                break
        groups.append({"id": f"g{len(groups) + 1:02d}", "origin": f"aleatorio semilla {seed}",
                       "modules": [{k: c[k] for k in ("repo", "module", "stratum")} for c in group]})
    data = {"version": ex.DST, "seed": seed, "size": size, "groups": groups,
            "reserves": {s: [{k: c[k] for k in ("repo", "module", "stratum", "depends")}
                             for c in pools[s][-15:]] for s in STRATA},
            "pool_sizes": {s: len(p) for s, p in pools.items()},
            "rejected": rejected, "replacements": []}
    out = out or ex._root() / "research" / f"lote_{ex.DST.replace('.', '')}" / "muestra.json"
    ex._jdump(out, data)
    return data


# ------------------------------------------------------------------ correr
_lock = threading.Lock()


def _replace(sample_: dict, sample_path: Path, gid: str, module: str, reason: str) -> dict | None:
    with _lock:
        g = next(x for x in sample_["groups"] if x["id"] == gid)
        old = next(m for m in g["modules"] if m["module"] == module)
        strat = old["stratum"] if old["stratum"] in STRATA else "tecnico"
        rows = ex._census_rows()
        others = [m for m in g["modules"] if m["module"] != module]
        others_full = [{**m, "depends": []} for m in others]
        new = None
        for s in (strat,) + tuple(x for x in STRATA if x != strat):
            while sample_["reserves"][s]:
                c = sample_["reserves"][s].pop()
                if not _valid(c, others_full, rows):
                    new = {k: c[k] for k in ("repo", "module", "stratum")}
                    break
            if new:
                break
        if not new:
            return None
        g["modules"] = others + [new]
        sample_["replacements"].append({"group": gid, "out": module, "in": new["module"],
                                        "reason": reason})
        ex._jdump(sample_path, sample_)
        return new


def run_group(sample_: dict, sample_path: Path, gid: str, phases, max_iter: int) -> dict:
    g = next(x for x in sample_["groups"] if x["id"] == gid)
    for attempt in range(5):
        items = [(m["repo"], m["module"]) for m in g["modules"]]
        ex.act(gid, f"prepare (intento {attempt + 1}): {', '.join(m for _, m in items)}")
        try:
            meta_ = ex.prepare(gid, items, force=True)
            ex.act(gid, f"prepare: {meta_['hunks']} hunks, deps core={meta_['depends']['core']} "
                        f"oca={[d['module'] for d in meta_['depends']['oca']]}, tags={meta_['hunk_tags']}")
            ex.seed(gid, force=True)
            break
        except ex.SeedError as e:
            ex.act(gid, f"seed fallo en {ex.SRC} (culpable: {e.culprit or '?'}): {e}")
            bad = e.culprit or g["modules"][-1]["module"]
        except RuntimeError as e:
            ex.act(gid, f"prepare fallo: {e}")
            bad = next((m for _, m in items if m in str(e)), g["modules"][-1]["module"])
        new = _replace(sample_, sample_path, gid, bad, "no instala en 16.0 o no se puede preparar")
        if not new:
            ex.act(gid, "sin reservas: grupo abortado")
            return {"group": gid, "status": "abortado"}
        ex.act(gid, f"reemplazo: {bad} -> {new['module']} ({new['stratum']})")
    else:
        return {"group": gid, "status": "abortado"}
    ex.baseline(gid)
    res = ex.auto(gid, phases=phases, max_iter=max_iter)
    ex.act(gid, f"reporte: {ex.report(gid)}")
    return {"group": gid, "status": "ok", "phases": res}


def run(sample_path: Path, parallel: int = 2, phases=ex.PHASES, max_iter: int = 15,
        only: list[str] | None = None) -> list[dict]:
    sample_ = json.loads(sample_path.read_text(encoding="utf-8"))
    if sample_.get("schema") == "odoolab.migration-plan.v1":
        from . import migration_plan
        if parallel != 1:
            raise ValueError("el plan multiversion usa --parallel 1; no cambia globals")
        return migration_plan.run(sample_path, only, phases, max_iter)
    gids = [g["id"] for g in sample_["groups"] if not only or g["id"] in only]

    def one(gid):
        try:
            return run_group(sample_, sample_path, gid, phases, max_iter)
        except Exception as e:                           # noqa: BLE001 - un grupo no tumba el lote
            ex.act(gid, f"ERROR del orquestador: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            return {"group": gid, "status": f"error: {e}"[:300]}

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        results = list(pool.map(one, gids))
    summary(sample_path)
    return results


# ------------------------------------------------------------------ agregar
def summary(sample_path: Path) -> Path:
    sample_ = json.loads(sample_path.read_text(encoding="utf-8"))
    if sample_.get("schema") == "odoolab.migration-plan.v1":
        from . import migration_plan
        return migration_plan.summary(sample_path)
    out = sample_path.parent
    allc, rows, its_total = [], [], 0
    for g in sample_["groups"]:
        gid = g["id"]
        if not (ex.exp_dir(gid) / "meta.json").exists():
            rows.append([gid, "-", "-", "-", "-", "no corrido"])
            continue
        cas = ex._casuistics(gid)
        hs = ex._hunks(gid)
        its = ex._iterations(gid)
        its_total += len(its)
        au = ex._jload(ex.exp_dir(gid) / "auto.json", {})
        for c in cas:
            allc.append({"group": gid, **{k: (",".join(map(str, v)) if isinstance(v, list) else v)
                                          for k, v in c.items() if k not in ("signature",)}})
        rows.append([gid, ", ".join(ex.modules_of(gid)), len(its), len(cas),
                     f"{sum(1 for h in hs if h['state'] == 'applied')}/{len(hs)}",
                     " ".join(f"{k}={v}" for k, v in au.items())])
    if allc:
        cols = list(dict.fromkeys(k for r in allc for k in r))
        with (out / "casuisticas.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(allc)
    block = [c for c in allc if c["severity"] == "bloqueante"]
    L = [f"# Lote {sample_['version']}: {len(sample_['groups'])} grupos de {sample_['size']} modulos", "",
         f"- Muestra: `muestra.json` (semilla {sample_['seed']}); reemplazos: "
         f"{len(sample_['replacements'])}",
         f"- Iteraciones de Odoo: {its_total} · casuisticas: {len(allc)} "
         f"({len(block)} bloqueantes, {len(allc) - len(block)} avisos)", "",
         "## Grupos", "", ex._tbl(rows, ["grupo", "modulos", "iter", "casuisticas",
                                          "hunks aplicados", "fases"]), ""]
    if allc:
        L += ["## Bloqueantes por cobertura del estandar", "",
              ex._tbl([[k, v, cz.COVERAGE.get(k, "por codificar")] for k, v in ex._count("coverage", block)],
                      ["etiqueta", "n", "significado"]), ""]
        L += ["## Bloqueantes por categoria", "",
              ex._tbl([[k, v, cz.CATEGORIES.get(k, "")] for k, v in ex._count("category", block)],
                      ["cat", "n", "nombre"]), ""]
        L += ["## Bloqueantes por fase", "", ex._tbl(ex._count("phase", block), ["fase", "n"]), ""]
        L += ["## Avisos (candidatos a silenciosa) por categoria", "",
              ex._tbl([[k, v, cz.CATEGORIES.get(k, "")] for k, v in
                       ex._count("category", [c for c in allc if c["severity"] == "aviso"])],
                      ["cat", "n", "nombre"]), ""]
    if sample_["replacements"]:
        L += ["## Reemplazos", "", ex._tbl([[r["group"], r["out"], r["in"], r["reason"]]
                                             for r in sample_["replacements"]],
                                            ["grupo", "sale", "entra", "motivo"]), ""]
    p = out / "RESULTADOS.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p
