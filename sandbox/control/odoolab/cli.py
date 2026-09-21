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
    arms: str = typer.Option("ours,oca", "--arms", help="ramas a ejecutar"),
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


def main():
    app()


if __name__ == "__main__":
    main()
