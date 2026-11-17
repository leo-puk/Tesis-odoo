"""odoolab — CLI de control del sandbox.

Se usa igual desde dentro (docker exec sbx-control odoolab ...)
que desde fuera (./odoolab.ps1 ... , que delega en el contenedor de control).
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

from . import compare as cmp_mod, docker_ctl as d, migrate, pg, report, seed
from .config import Scenario, VERSION_CHAIN

app = typer.Typer(add_completion=False, help="Sandbox de migracion Odoo: prod inmutable + forks.")
RUNS = Path(os.environ.get("ODOLAB_RUNS", "/workspace/runs"))


def _run_dir(name: str) -> Path:
    p = RUNS / f"{datetime.now():%Y%m%d-%H%M%S}-{name}"
    (p / "logs").mkdir(parents=True, exist_ok=True)
    return p


@app.command()
def status():
    """Estado del sandbox: produccion, forks vivos y bases de datos."""
    t = Table("contenedor", "rol", "estado")
    p = d.run(["docker", "ps", "-a", "--filter", "label=odolab.role",
               "--format", "{{.Names}}\t{{.Label \"odolab.role\"}}\t{{.Status}}"], check=False)
    for line in p.stdout.splitlines():
        t.add_row(*line.split("\t"))
    rprint(t)
    dbs = pg.q("postgres", "select datname from pg_database where datistemplate=false order by 1")
    rprint("[bold]bases:[/bold] " + ", ".join(r[0] for r in dbs))


@app.command()
def init_prod(scenario: str = typer.Argument(..., help="scenarios/<n>.yaml o ruta"),
              force: bool = typer.Option(False, "--force", help="recrear la DB de produccion")):
    """Siembra la instancia de produccion con los modulos del escenario."""
    sc = Scenario.load(scenario)
    rd = _run_dir(f"init-{sc.name}")
    info = seed.init_prod(sc, run_dir=rd, force=force)
    rprint(f"[green]produccion lista[/green] {info}")


@app.command("run")
def run_cmd(
    scenario: Optional[str] = typer.Argument(None, help="escenario YAML (o usar las opciones)"),
    version_from: Optional[str] = typer.Option(None, "--version-inicio", "--from"),
    version_to: Optional[str] = typer.Option(None, "--version-fin", "--to"),
    modules: Optional[str] = typer.Option(None, "--modulos", help="csv de modulos integrados"),
    name: Optional[str] = typer.Option(None, "--name"),
    arms: Optional[str] = typer.Option(None, "--arms",
        help="ramas a ejecutar; por defecto las del escenario (ours,oca)"),
    keep: bool = typer.Option(False, "--keep", help="no borrar las DBs resultantes"),
    no_compare: bool = typer.Option(False, "--no-compare"),
):
    """Ejecuta una simulacion completa: fork -> migrar (ours y oca) -> comparar -> reportar."""
    if scenario:
        sc = Scenario.load(scenario, version_from=version_from, version_to=version_to,
                           modules=modules.split(",") if modules else None, name=name)
    else:
        if not (version_from and version_to and name):
            raise typer.BadParameter("sin escenario hacen falta --name --version-inicio --version-fin")
        sc = Scenario.from_args(name, version_from, version_to,
                                modules.split(",") if modules else [])
    # solo se pisa el escenario si el flag vino explicito
    if arms:
        sc.arms = [a.strip() for a in arms.split(",") if a.strip()]

    rd = _run_dir(sc.name)
    rprint(f"[bold]run:[/bold] {rd.name}  ruta {' -> '.join(sc.path)}  modulos {sc.modules}")
    (rd / "scenario.json").write_text(json.dumps(sc.to_dict(), indent=2), encoding="utf-8")

    fp_before = seed.assert_prod_untouched()
    seed.init_prod(sc, run_dir=rd)

    results = {}
    port_base = int(os.environ.get("FORK_PORT_BASE", "8100"))
    for arm in sc.arms:
        rprint(f"[cyan]== rama {arm} ==[/cyan]")
        r = migrate.run_arm(sc, arm, run_dir=rd, port_base=port_base)
        results[arm] = r.dict()
        rprint(f"  {'OK' if r.ok else 'FALLO'} en {r.seconds:.0f}s -> db {r.db}")

    cmp_json = None
    if not no_compare and {"ours", "oca"} <= set(results):
        rprint("[cyan]== comparacion ours vs oca ==[/cyan]")
        c = cmp_mod.compare(results["ours"]["db"], results["oca"]["db"], sc.compare)
        cmp_json = c.dict()
        (rd / "comparison.json").write_text(json.dumps(cmp_json, indent=2, ensure_ascii=False),
                                            encoding="utf-8")
        rprint(f"  fidelidad {c.fidelity}%  ({len(c.errors)} divergencias criticas)")

    fp_after = seed.assert_prod_untouched(fp_before)
    data = report.build(rd, sc.to_dict(), results, cmp_json, fp_after)
    rprint(f"[green]reporte:[/green] {rd/'report.md'}")
    if data["effort"]:
        rprint(f"[green]esfuerzo estimado:[/green] {data['effort']['total_hours']} h")

    if not keep:
        for a in results.values():
            pg.drop(a["db"])


@app.command()
def compare(ours: str, oca: str, out: Optional[str] = None):
    """Compara dos bases ya migradas sin re-ejecutar la migracion."""
    c = cmp_mod.compare(ours, oca, Scenario("x", VERSION_CHAIN[0], VERSION_CHAIN[1]).compare)
    js = json.dumps(c.dict(), indent=2, ensure_ascii=False)
    Path(out).write_text(js, encoding="utf-8") if out else rprint(js)
    rprint(f"[bold]fidelidad {c.fidelity}%[/bold]")


@app.command()
def clean(all_: bool = typer.Option(False, "--all", help="tambien borra las DBs de runs")):
    """Elimina forks colgados (nunca toca produccion)."""
    p = d.run(["docker", "ps", "-aq", "--filter", "label=odolab.role=fork"], check=False)
    ids = [x for x in p.stdout.split() if x]
    if ids:
        d.run(["docker", "rm", "-f", *ids], check=False)
    rprint(f"forks eliminados: {len(ids)}")
    if all_:
        prod = os.environ.get("PG_DB_PROD", "prod")
        for (db,) in pg.q("postgres", "select datname from pg_database where datistemplate=false"):
            if db not in (prod, "postgres"):
                pg.drop(db)
                rprint(f"  drop {db}")


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def census(ctx: typer.Context):
    """Censo OCA de [MIG] y [FIX] por modulo (ver odoolab.census --help)."""
    from . import census as census_mod
    raise typer.Exit(census_mod.main(ctx.args))


# ---- experimento de casuisticas por modulo ---------------------------------
exp_app = typer.Typer(help="Bucle error -> hunk humano -> casuistica, por modulo OCA (16.0->17.0).")
app.add_typer(exp_app, name="exp")


@exp_app.command("prepare")
def exp_prepare(repo: str, module: str, force: bool = typer.Option(False, "--force"),
                group: Optional[str] = typer.Option(None, "--group",
                    help="id de grupo; con --extra repo/modulo,... agrega mas modulos"),
                extra: str = typer.Option("", "--extra")):
    """S0 (padre del [MIG]), hunks del [MIG] humano y dependencias."""
    from . import experiment as ex
    items = [(repo, module)] + [tuple(x.split("/", 1)) for x in extra.split(",") if x.strip()]
    m = ex.prepare(group or module, items, force=force)
    rprint({k: m[k] for k in ("depends", "hunks", "hunk_tags")})


@exp_app.command("auto")
def exp_auto(gid: str, phases: str = typer.Option("install,upgrade,test", "--phases"),
             max_iter: int = typer.Option(15, "--max-iter")):
    """Bucle automatico error -> hunks humanos, con registro de acciones."""
    from . import experiment as ex
    rprint(ex.auto(gid, phases=[p for p in phases.split(",") if p], max_iter=max_iter))


# ---- lote: N grupos de K modulos ------------------------------------------
lote_app = typer.Typer(help="Lote de grupos de modulos OCA migrados 16.0 -> 17.0.")
app.add_typer(lote_app, name="lote")


@lote_app.command("sample")
def lote_sample(groups: int = typer.Option(10, "--groups"), size: int = typer.Option(5, "--size"),
                seed: int = typer.Option(2026, "--seed"),
                fixed: str = typer.Option("", "--fixed", help="primer grupo fijo: repo/mod,..."),
                exclude: str = typer.Option("", "--exclude", help="modulos a excluir, csv")):
    """Muestra estratificada y validada desde el censo."""
    from . import batch
    fx = [[tuple(x.split("/", 1)) for x in fixed.split(",") if x.strip()]] if fixed else []
    d = batch.sample(groups, size, seed, fx, {x for x in exclude.split(",") if x})
    for g in d["groups"]:
        rprint(f"{g['id']}: " + ", ".join(f"{m['module']} ({m['stratum']})" for m in g["modules"]))
    rprint(f"pools {d['pool_sizes']} · descartados al validar {len(d['rejected'])}")


@lote_app.command("run")
def lote_run(sample_path: str = typer.Argument("research/lote_170/muestra.json"),
             parallel: int = typer.Option(2, "--parallel"),
             phases: str = typer.Option("install,upgrade,test", "--phases"),
             max_iter: int = typer.Option(15, "--max-iter"),
             only: str = typer.Option("", "--only", help="csv de grupos")):
    """prepare -> seed -> baseline -> auto -> report por grupo."""
    from pathlib import Path as P
    from . import batch
    res = batch.run(P(sample_path), parallel, [p for p in phases.split(",") if p], max_iter,
                    [x for x in only.split(",") if x] or None)
    rprint(res)


@lote_app.command("summary")
def lote_summary(sample_path: str = typer.Argument("research/lote_170/muestra.json")):
    """Agrega los grupos en RESULTADOS.md y casuisticas.csv."""
    from pathlib import Path as P
    from . import batch
    rprint(f"[green]{batch.summary(P(sample_path))}[/green]")


@exp_app.command("seed")
def exp_seed(module: str, force: bool = typer.Option(False, "--force")):
    """Plantillas de produccion v16 con y sin el modulo."""
    from . import experiment as ex
    rprint(ex.seed(module, force=force))


@exp_app.command("baseline")
def exp_baseline(module: str, phases: str = typer.Option("install,upgrade", "--phases")):
    """Corre las fases sin el modulo: sus firmas se descuentan de cada iteracion."""
    from . import experiment as ex
    rprint(ex.baseline(module, [p for p in phases.split(",") if p]))


@exp_app.command("run")
def exp_run(module: str, phase: str = typer.Argument(..., help="install | upgrade | test"),
            keep_db: bool = typer.Option(False, "--keep-db"),
            show: int = typer.Option(15, "--show", help="eventos nuevos a listar")):
    """Una iteracion: corre la fase sobre el codigo 17.0 actual y lista eventos nuevos."""
    from . import experiment as ex
    r = ex.run(module, phase, keep_db=keep_db)
    rprint(f"[bold]iter {r['iteration']} {phase}[/bold] codigo {r['code_head']} -> "
           f"{'[green]OK' if r['ok'] else '[red]FALLA'}[/] rc={r['returncode']} "
           f"{r['seconds']}s, {len(r['events_new'])} eventos nuevos de {r['events_total']}")
    t = Table("sig_id", "nivel", "cat", "regla", "guia", "ubicacion", "mensaje")
    order = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2}
    for e in sorted(r["events_new"], key=lambda e: order.get(e["level"], 3))[:show]:
        t.add_row(e["sig_id"], e["level"], e["category"], e["rule"], e["guide"],
                  e["location"], e["message"][:90])
    rprint(t)
    rprint(f"log: {r['log']}")


@exp_app.command("event")
def exp_event(module: str, sig_id: str):
    """Detalle completo (traceback) de un evento."""
    from . import experiment as ex
    _, e = ex._find_event(module, sig_id)
    rprint(e)


@exp_app.command("hunks")
def exp_hunks(module: str, pending: bool = typer.Option(True, "--pending/--all")):
    """Hunks del [MIG] humano con sus etiquetas de la guia."""
    from . import experiment as ex
    t = Table("id", "estado", "archivo", "lineas", "tags", "cabecera")
    for h in ex._hunks(module):
        if pending and h["state"] != "pending":
            continue
        t.add_row(f"{h['id']:03d}", h["state"], h["path"], f"-{h['removed']}+{h['added']}",
                  ",".join(h["tags"]), h["header"][:50])
    rprint(t)


@exp_app.command("fix")
def exp_fix(module: str,
            hunks: str = typer.Option("", "--hunks", help="csv de ids de hunks humanos"),
            event: Optional[str] = typer.Option(None, "--event", help="sig_id que resuelven"),
            category: Optional[str] = typer.Option(None, "--cat"),
            coverage: Optional[str] = typer.Option(None, "--cov", help="L A U C V R S"),
            severity: str = typer.Option("bloqueante", "--sev"),
            note: str = typer.Option("", "--note"),
            minutes: Optional[float] = typer.Option(None, "--min")):
    """Registra la casuistica y aplica los hunks que la resuelven (un commit)."""
    from . import experiment as ex
    ids = [int(x) for x in hunks.split(",") if x.strip()]
    rprint(ex.fix(module, event=event, hunks=ids, category=category, coverage=coverage,
                  severity=severity, note=note, minutes=minutes))


@exp_app.command("report")
def exp_report(module: str):
    """Escribe research/experiments/<modulo>/report.md."""
    from . import experiment as ex
    rprint(f"[green]{ex.report(module)}[/green]")


def main():
    app()


if __name__ == "__main__":
    main()
