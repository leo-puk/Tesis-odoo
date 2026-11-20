"""Catalogo estable de variantes y saltos; no reemplaza addons automaticamente."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import experiment as ex

SCHEMA = "odoolab.migration-plan.v1"
DEFAULT_PATH = "research/migration-plan/plan.json"
STEPS = (("16.0", "17.0"), ("17.0", "18.0"), ("18.0", "19.0"))


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate(data)
    return data


def validate(data: dict) -> None:
    if data.get("schema") != SCHEMA:
        raise ValueError("schema de plan desconocido")
    groups = data.get("groups", [])
    if len(groups) != 32:
        raise ValueError("el plan debe contener g01, g02 y treinta casos nuevos")
    ids, variants, owners = set(), {}, {}
    for g in groups:
        gid = ex.validate_gid(g["id"])
        if gid in ids:
            raise ValueError(f"id repetido: {gid}")
        ids.add(gid)
        pair = ex.validate_step(g["version_from"], g["version_to"])
        mods = g["modules"]
        names = [m["module"] for m in mods]
        if len(mods) != 5 or len(set(names)) != 5:
            raise ValueError(f"{gid}: se requieren cinco addons distintos")
        for m in mods:
            if not re.fullmatch(r"[a-z0-9_]+", m["module"]):
                raise ValueError(f"addon invalido en {gid}")
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", m["repo"]):
                raise ValueError(f"repositorio invalido en {gid}")
        if g["origin"] == "historical":
            if gid not in ("g01", "g02") or pair != STEPS[0] or g["variant_id"] != gid:
                raise ValueError("identidad historica invalida")
            continue
        vid = g["variant_id"]
        if not re.fullmatch(r"oca_v(?:0[1-9]|10)", vid):
            raise ValueError(f"variante invalida: {vid}")
        suffix = pair[0][:2] + pair[1][:2]
        if gid != f"{vid}_{suffix}":
            raise ValueError(f"id y salto inconsistentes: {gid}")
        variants.setdefault(vid, []).append(g)
        for name in names:
            if name in owners and owners[name] != vid:
                raise ValueError(f"{name}: repetido entre variantes nuevas")
            owners[name] = vid
    if not {"g01", "g02"} <= ids or len(variants) != 10:
        raise ValueError("faltan variantes historicas o nuevas")
    for vid, cases in variants.items():
        if {tuple((c["version_from"], c["version_to"])) for c in cases} != set(STEPS) or len(cases) != 3:
            raise ValueError(f"{vid}: faltan saltos")
        signatures = {tuple(sorted((m["repo"], m["module"]) for m in c["modules"])) for c in cases}
        if len(signatures) != 1:
            raise ValueError(f"{vid}: los addons cambian entre saltos")
    historical = {m["module"] for g in groups if g["origin"] == "historical" for m in g["modules"]}
    if historical & owners.keys():
        raise ValueError("los addons historicos no se reutilizan en la muestra nueva")


def selected(data: dict, only: list[str] | None = None, *, new_only=False) -> list[dict]:
    wanted = set(only or [])
    unknown = wanted - {g["id"] for g in data["groups"]}
    if unknown:
        raise ValueError(f"casos desconocidos: {sorted(unknown)}")
    return [g for g in data["groups"] if (g["id"] in wanted if wanted else not new_only or g["origin"] != "historical")]


def assert_metadata(case: dict, metadata: dict) -> None:
    if metadata.get("id", case["id"]) != case["id"]:
        raise ValueError(f"{case['id']}: identidad de metadatos inconsistente")
    if metadata.get("step") != f"{case['version_from']}->{case['version_to']}":
        raise ValueError(f"{case['id']}: el salto no coincide con los metadatos")
    actual = {(m["repo"], m["module"]) for m in metadata["modules"]}
    expected = {(m["repo"], m["module"]) for m in case["modules"]}
    if actual != expected or len(metadata["modules"]) != 5:
        raise ValueError(f"{case['id']}: los addons no coinciden con el catalogo")


def prepare_case(case: dict, *, force=False) -> dict:
    gid = case["id"]
    if (ex.exp_dir(gid) / "meta.json").exists() and not force:
        m = ex.meta(gid)
        assert_metadata(case, m)
        return m
    m = ex.prepare(gid, [(x["repo"], x["module"]) for x in case["modules"]],
                   force=force, source=case["version_from"], target=case["version_to"])
    m["variant_id"] = case["variant_id"]
    m["plan_schema"] = SCHEMA
    ex._jdump(ex.exp_dir(gid) / "meta.json", m)
    return m


def check_sources(case: dict) -> dict:
    """Read-only evidence checks, except Git caches; no experiment is prepared."""
    source, target = case["version_from"], case["version_to"]
    rows = ex._census_rows(target)
    index = ex.dependency_index(rows)
    modules = [ex._module_source(x["repo"], x["module"], rows, source=source, target=target)
               for x in case["modules"]]
    names = {x["module"] for x in modules}
    for m in modules:
        if names & set(m["depends"]):
            raise ValueError(f"{case['id']}: dependencia interna entre addons de estudio")
    deps = ex._resolve_oca_deps(sorted({d for m in modules for d in m["depends"]}),
                              index, set(), source=source, target=target)
    if names & set(deps):
        raise ValueError(f"{case['id']}: dependencia transitiva entre addons de estudio")
    core = set()
    for version in (source, target):
        path = ex.census_dir() / f"core_addons_{version.replace('.', '')}.txt"
        if not path.exists():
            raise ValueError(f"falta inventario core: {path}")
        inventory = set(path.read_text(encoding="utf-8").split())
        manifests = []
        for dep in deps:
            gd = ex.census.sync_repo(index[dep], version, ex.cache_dir())
            if gd is None:
                raise ValueError(f"{dep}: falta rama {version}")
            info = ex.manifest(gd, version, dep)
            if not info.get("installable", True):
                raise ValueError(f"{dep}: no instalable en {version}")
            manifests.append(info)
        for info in manifests:
            unknown = set(info.get("depends", [])) - index.keys() - inventory
            if unknown:
                raise ValueError(f"{version}: dependencias no resueltas {sorted(unknown)}")
        core_deps = {d for m in modules for d in m["depends"] if d not in index and d not in names}
        if not core_deps <= inventory:
            raise ValueError(f"{version}: addons core desconocidos {sorted(core_deps - inventory)}")
        core.update(core_deps)
    return {"id": case["id"], "status": "source_checked_not_installed",
            "core_dependencies": sorted(core), "oca_dependencies": deps,
            "scope_review": "pending_no_OWL_review", "installation": "not_run"}


def run(path: Path, only: list[str] | None = None, phases=ex.PHASES, max_iter=15) -> list[dict]:
    data = load(path)
    if not phases or set(phases) - set(ex.PHASES) or max_iter < 1:
        raise ValueError("fases o max_iter invalidos")
    results = []
    for case in selected(data, only, new_only=True):
        try:
            check_sources(case)
            prepare_case(case)
            ex.seed(case["id"])
            baseline_phases = tuple(p for p in phases if p != "test")
            if baseline_phases:
                ex.baseline(case["id"], baseline_phases)
            states = ex.auto(case["id"], phases=phases, max_iter=max_iter)
            ex.report(case["id"])
            result = {"id": case["id"], "status": "ok" if all(states.get(p) == "ok" for p in phases) else "failed",
                      "phases": states}
        except (Exception, SystemExit) as error:
            result = {"id": case["id"], "status": "blocked", "reason": str(error)}
        results.append(result)
        # Keep outcome evidence separate from immutable case definitions.
        outcomes = ex._jload(path.parent / "execution-status.json", {})
        outcomes[case["id"]] = result
        ex._jdump(path.parent / "execution-status.json", outcomes)
    summary(path)
    return results


def summary(path: Path) -> Path:
    data = load(path)
    outcomes = ex._jload(path.parent / "execution-status.json", {})
    rows = []
    for case in data["groups"]:
        gid = case["id"]
        state = outcomes.get(gid, {}).get("status", case["status"])
        rows.append([gid, case["variant_id"], f"{case['version_from']}->{case['version_to']}",
                     ", ".join(m["module"] for m in case["modules"]), state])
    text = "# Catalogo: 32 casos de migracion\n\n2 historicos + 10 variantes nuevas por 3 saltos.\n\n"
    text += "Los saltos se evalúan de forma independiente con los mismos addons; no se encadena una misma base de datos.\n\n"
    text += "Planificado y preparado no significan ejecutado ni aprobado. Las dependencias son adicionales a los cinco addons de estudio.\n\n"
    text += ex._tbl(rows, ["caso", "variante", "salto", "addons", "estado"]) + "\n"
    out = path.parent / "CATALOGO.md"
    out.write_text(text, encoding="utf-8")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "check", "prepare", "run", "summary"))
    parser.add_argument("--plan", type=Path, default=Path(DEFAULT_PATH))
    parser.add_argument("--only", help="ids de casos separados por comas")
    parser.add_argument("--verify-sources", action="store_true")
    parser.add_argument("--force", action="store_true", help="reconstruir codigo y borrar evidencia del caso seleccionado")
    parser.add_argument("--phases", default="install,upgrade,test")
    parser.add_argument("--max-iter", type=int, default=15)
    args = parser.parse_args(argv)
    try:
        data = load(args.plan)
        only = [x.strip() for x in (args.only or "").split(",") if x.strip()] or None
        cases = selected(data, only)
        if args.action == "list":
            for case in cases:
                print(f"{case['id']} {case['version_from']}->{case['version_to']}: " + ", ".join(x["module"] for x in case["modules"]))
        elif args.action == "check":
            if args.verify_sources:
                results = []
                for case in cases:
                    try:
                        results.append(check_sources(case))
                    except (Exception, SystemExit) as error:
                        results.append({"id": case["id"], "status": "blocked", "reason": str(error)})
                ex._jdump(args.plan.parent / "source-validation.json", results)
                print(json.dumps(results, ensure_ascii=False, indent=2))
                return int(any(x["status"] == "blocked" for x in results))
            print("32 casos; diez variantes nuevas conservan sus cinco addons en los tres saltos. Fuentes e instalacion pendientes.")
        elif args.action == "prepare":
            if not only or len(cases) != 1:
                raise ValueError("prepare requiere --only con un unico caso")
            check_sources(cases[0])
            print(json.dumps(prepare_case(cases[0], force=args.force), ensure_ascii=False, indent=2))
        elif args.action == "run":
            if args.force:
                raise ValueError("--force solo se admite con prepare")
            results = run(args.plan, only, [x.strip() for x in args.phases.split(",") if x.strip()], args.max_iter)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return int(any(x["status"] != "ok" for x in results))
        else:
            print(summary(args.plan))
    except (OSError, ValueError, KeyError, SystemExit) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
