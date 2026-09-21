"""Orquestacion de una rama (arm) de migracion sobre la cadena de versiones."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

from . import docker_ctl as d, oca, pg
from .config import Scenario
from .odoo_run import run_odoo, core_addons_path


@dataclass
class StepResult:
    step: str                 # "16.0->17.0"
    arm: str
    ok: bool
    seconds: float
    phase_seconds: dict = field(default_factory=dict)
    errors: int = 0
    warnings: int = 0
    tracebacks: int = 0
    manual_interventions: int = 0     # lo incrementa --intervene (ver cli)
    logs: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class ArmResult:
    arm: str
    db: str
    ok: bool
    seconds: float
    steps: list[StepResult] = field(default_factory=list)
    oca_commits: dict = field(default_factory=dict)

    def dict(self):
        dd = asdict(self)
        return dd


def _mounts() -> dict[str, str]:
    # Los bind-mounts los resuelve el daemon del host, no el contenedor de control:
    # hacen falta rutas del HOST. El wrapper (odoolab.ps1/.sh) inyecta ODOLAB_HOST_ROOT.
    root = os.environ.get("ODOLAB_HOST_ROOT")
    if not root:
        raise SystemExit("ODOLAB_HOST_ROOT no definido: usa ./odoolab.ps1 o exportalo en .env")
    root = root.replace("\\", "/")
    tool = os.environ.get("MIGRATION_TOOL_PATH", f"{root}/../tool")
    return {"oca": os.environ.get("OCA_CACHE_VOLUME", "odolab-oca-cache"),
            "tool": tool,
            "custom": f"{root}/custom-addons"}


def run_arm(sc: Scenario, arm: str, *, run_dir: Path, port_base: int) -> ArmResult:
    """Clona prod y la lleva de version_from a version_to con la estrategia del arm."""
    src_db = os.environ.get("PG_DB_PROD", "prod")
    db = f"{sc.name}_{arm}"
    pg.clone(src_db, db)

    t0 = time.time()
    res = ArmResult(arm=arm, db=db, ok=True, seconds=0.0)

    for src, dst in sc.steps:
        run_id = f"{sc.name}-{arm}-{dst.replace('.', '')}"
        d.ensure_image(dst)
        port = d.free_port(port_base)
        container = d.fork_up(run_id, version=dst, port=port, arm=arm, mounts=_mounts())
        step = StepResult(step=f"{src}->{dst}", arm=arm, ok=True, seconds=0.0)
        s0 = time.time()
        try:
            if arm == "oca":
                oca.ensure_branch(dst)
                res.oca_commits[dst] = oca.commit(dst)
                r = run_odoo(container, db=db,
                             addons_path=oca.addons_path(dst),
                             upgrade_path=f"{oca.CACHE}/{dst}/openupgrade_scripts/scripts",
                             update="all", log_dir=run_dir / "logs", tag=f"{arm}-{dst}-upgrade",
                             timeout_min=sc.timeout_min)
            else:
                if not sc.tool_cmd:
                    raise SystemExit("scenario.tool_cmd no definido: no se como invocar tu herramienta")
                cmd = sc.tool_cmd.format(db=db, src=src, dst=dst,
                                         modules=",".join(sc.modules), tool="/opt/tool")
                t1 = time.time()
                p = d.run(["docker", "exec", container, "sh", "-lc", cmd],
                          check=False, timeout=sc.timeout_min * 60)
                (run_dir / "logs").mkdir(parents=True, exist_ok=True)
                (run_dir / "logs" / f"{arm}-{dst}-tool.log").write_text(
                    (p.stdout or "") + (p.stderr or ""), encoding="utf-8", errors="replace")
                step.phase_seconds["tool"] = time.time() - t1
                if p.returncode != 0:
                    step.ok = False
                    step.note = f"tool_cmd salio con {p.returncode}"
                # validacion: Odoo debe poder levantar y actualizar todo
                r = run_odoo(container, db=db, addons_path=core_addons_path(dst),
                             update="all", log_dir=run_dir / "logs",
                             tag=f"{arm}-{dst}-validate", timeout_min=sc.timeout_min)

            step.phase_seconds["odoo"] = r.seconds
            step.errors = r.counts.get("ERROR", 0) + r.counts.get("CRITICAL", 0)
            step.warnings = r.counts.get("WARNING", 0)
            step.tracebacks = r.tracebacks
            step.logs.append(str(r.log_path.relative_to(run_dir)))
            step.ok = step.ok and r.ok
        except Exception as e:                      # noqa: BLE001 - se registra, no se propaga
            step.ok = False
            step.note = f"{type(e).__name__}: {e}"[:2000]
        finally:
            step.seconds = time.time() - s0
            d.fork_down(run_id)

        res.steps.append(step)
        if not step.ok:
            res.ok = False
            break       # cadena rota: no tiene sentido seguir al siguiente salto

    res.seconds = time.time() - t0
    return res
