"""Ejecucion de odoo-bin dentro de un contenedor fork, con captura de log y metricas."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import docker_ctl as d

LOG_LEVEL_RE = re.compile(r"\b(CRITICAL|ERROR|WARNING)\b")
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
             upgrade_path: str | None = None, env: dict | None = None) -> OdooRun:
    cmd = ["odoo", "-d", db, "--db_host", "db", "--db_user", "odoo", "--db_password", "odoo",
           f"--addons-path={addons_path}", "--stop-after-init", "--no-http",
           "--log-level=info", "--workers=0"]
    if upgrade_path:
        cmd.append(f"--upgrade-path={upgrade_path}")
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

    counts = {lvl: len(re.findall(rf"\b{lvl}\b", out)) for lvl in ("CRITICAL", "ERROR", "WARNING")}
    return OdooRun(ok=p.returncode == 0, seconds=secs, log_path=log_path, counts=counts,
                   tracebacks=len(TRACEBACK_RE.findall(out)), returncode=p.returncode)


def core_addons_path(version: str) -> str:
    return "/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons"
