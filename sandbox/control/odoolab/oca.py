"""Gestion del baseline OCA (OpenUpgrade) — la migracion 'sin errores' de referencia."""
from __future__ import annotations

from . import docker_ctl as d

OPENUPGRADE_REPO = "https://github.com/OCA/OpenUpgrade.git"
CACHE = "/opt/oca"          # volumen compartido montado en control y forks


def ensure_branch(version: str) -> str:
    """Clona/actualiza OpenUpgrade branch <version> en /opt/oca/<version>. Idempotente."""
    dest = f"{CACHE}/{version}"
    script = (
        f'set -e; if [ -d "{dest}/.git" ]; then '
        f'  git -C "{dest}" fetch --depth 1 origin {version} && git -C "{dest}" reset --hard FETCH_HEAD; '
        f'else '
        f'  git clone --depth 1 -b {version} {OPENUPGRADE_REPO} "{dest}"; '
        f'fi'
    )
    d.run(["sh", "-lc", script])
    return dest


def addons_path(version: str) -> str:
    """addons-path que usa OpenUpgrade para esa version."""
    base = f"{CACHE}/{version}"
    return ",".join([
        f"{base}/openupgrade_scripts/scripts",   # scripts de migracion por modulo
        f"{base}/addons",
        f"{base}/odoo/addons",
    ])


def commit(version: str) -> str:
    p = d.run(["git", "-C", f"{CACHE}/{version}", "rev-parse", "--short", "HEAD"], check=False)
    return p.stdout.strip() or "unknown"
