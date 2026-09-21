"""Ejecucion de odoo-bin dentro de un contenedor fork, con captura de log y metricas."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import docker_ctl as d

# Una linea de log de Odoo es:
#   2026-09-21 20:45:15,201 15 ERROR <dbname> <logger>: <mensaje>
# Hay que anclar el nivel a su posicion: el cuerpo del mensaje puede repetir
# "ERROR:" (p.ej. el detalle de un error de Postgres) e inflar el conteo.
LOG_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \d+ (CRITICAL|ERROR|WARNING|INFO|DEBUG) ",
    re.M)
TRACEBACK_RE = re.compile(r"^Traceback \(most recent call last\)", re.M)


@dataclass
class OdooRun:
    ok: bool
    seconds: float
    log_path: Path
    counts: dict[str, int] = field(default_factory=dict)
    tracebacks: int = 0
    returncode: int = 0


def run_odoo(container: str, *, db: str, addons_path: str, update: str | None = None,
             init: str | None = None, extra: list[str] | None = None,
             log_dir: Path, tag: str, timeout_min: int = 90,
             upgrade_path: str | None = None, load: str | None = None,
             env: dict | None = None) -> OdooRun:
    cmd = ["odoo", "-d", db, "--db_host", "db", "--db_user", "odoo", "--db_password", "odoo",
           f"--addons-path={addons_path}", "--stop-after-init", "--no-http",
           "--log-level=info", "--workers=0"]
    if upgrade_path:
        cmd.append(f"--upgrade-path={upgrade_path}")
    if load:
        cmd.append(f"--load={load}")   # OpenUpgrade necesita openupgrade_framework server-wide
    if init:
        cmd += ["-i", init]
    if update:
        cmd += ["-u", update]
    cmd += extra or []

    envprefix = []
    for k, v in (env or {}).items():
        envprefix += ["-e", f"{k}={v}"]

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{tag}.log"
    t0 = time.time()
    p = d.run(["docker", "exec", *envprefix, container, *cmd],
              check=False, timeout=timeout_min * 60)
    secs = time.time() - t0
    out = (p.stdout or "") + (p.stderr or "")
    log_path.write_text(out, encoding="utf-8", errors="replace")

    levels = LOG_LINE_RE.findall(out)
    counts = {lvl: levels.count(lvl) for lvl in ("CRITICAL", "ERROR", "WARNING")}
    return OdooRun(ok=p.returncode == 0, seconds=secs, log_path=log_path, counts=counts,
                   tracebacks=len(TRACEBACK_RE.findall(out)), returncode=p.returncode)


# Candidatos de addons-path, en orden de prioridad.
ADDONS_CANDIDATES = [
    "/mnt/extra-addons",                             # modulos custom del partner
    "/usr/lib/python3/dist-packages/odoo/addons",    # core de la imagen oficial
    "/usr/lib/python3/dist-packages/odoo/odoo/addons",
]


def valid_addons_path(container: str, candidates: list[str] | None = None) -> str:
    """Filtra los candidatos dejando solo directorios de addons reales.

    Odoo rechaza con "is not a valid addons directory" cualquier ruta que no
    contenga al menos un modulo (subdirectorio con __manifest__.py), asi que un
    /mnt/extra-addons vacio rompe el arranque. Se resuelve dentro del contenedor
    porque las rutas son suyas, no del control.
    """
    cands = candidates or ADDONS_CANDIDATES
    probe = "; ".join(
        f'[ -d "{c}" ] && ls -d "{c}"/*/__manifest__.py >/dev/null 2>&1 && echo "{c}"'
        for c in cands
    )
    p = d.run(["docker", "exec", container, "sh", "-c", probe], check=False)
    found = [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]
    if not found:
        raise RuntimeError(f"{container}: ningun addons-path valido entre {cands}")
    return ",".join(found)
