"""Preparacion del entorno de 'produccion': crear la DB base y sembrarla."""
from __future__ import annotations

import os
from pathlib import Path

from . import docker_ctl as d, pg
from .config import Scenario
from .odoo_run import run_odoo, core_addons_path

PROD = "sbx-prod"


def init_prod(sc: Scenario, *, run_dir: Path, force=False) -> dict:
    """Instala los modulos del escenario en la DB de produccion (idempotente)."""
    db = os.environ.get("PG_DB_PROD", "prod")
    if pg.exists(db) and not force:
        return {"db": db, "created": False}
    if force:
        pg.drop(db)

    mods = ",".join(sc.modules or ["base"])
    extra = [] if sc.demo_data else ["--without-demo=all"]
    r = run_odoo(PROD, db=db, addons_path=core_addons_path(sc.version_from),
                 init=mods, extra=extra, log_dir=run_dir / "logs", tag="prod-init",
                 timeout_min=sc.timeout_min)
    if not r.ok:
        raise SystemExit(f"fallo la siembra de produccion, ver {r.log_path}")

    if sc.seed:
        script = Path("/workspace/control/seeds") / f"{sc.seed}.py"
        if not script.exists():
            raise SystemExit(f"seed no encontrado: {script}")
        d.run(["docker", "cp", str(script), f"{PROD}:/tmp/seed.py"])
        p = d.run([
            "docker", "exec", PROD, "odoo", "shell", "-d", db,
            "--db_host", "db", "--db_user", "odoo", "--db_password", "odoo",
            f"--addons-path={core_addons_path(sc.version_from)}", "--no-http",
        ], check=False)
        (run_dir / "logs" / "prod-seed.log").write_text(
            (p.stdout or "") + (p.stderr or ""), encoding="utf-8", errors="replace")

    return {"db": db, "created": True, "modules": sc.modules, "seconds": r.seconds}


def prod_healthy() -> bool:
    return d.container_state(PROD) == "running"


def assert_prod_untouched(baseline: dict | None = None) -> dict:
    """Huella de produccion; se compara antes/despues de cada run."""
    db = os.environ.get("PG_DB_PROD", "prod")
    fp = {"state": d.container_state(PROD),
          "tables": len(pg.tables(db)),
          "modules": len(pg.q(db, pg.MODULES_SQL))}
    if baseline and baseline != fp:
        raise SystemExit(f"PRODUCCION ALTERADA: antes={baseline} despues={fp}")
    return fp
