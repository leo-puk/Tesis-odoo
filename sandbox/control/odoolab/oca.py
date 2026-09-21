"""Gestion del baseline OCA (OpenUpgrade) — la migracion 'sin errores' de referencia.

Desde la 14.0 OpenUpgrade NO es un fork de Odoo: es un repositorio de addons que
se ejecuta contra un Odoo estandar. Aporta dos piezas:
  - openupgrade_framework : modulo server-wide, se carga con --load
  - openupgrade_scripts   : scripts pre/post/end por modulo, se pasan con --upgrade-path
"""
from __future__ import annotations

from . import docker_ctl as d

OPENUPGRADE_REPO = "https://github.com/OCA/OpenUpgrade.git"
CACHE = "/opt/oca"          # volumen compartido montado en control y forks
SERVER_WIDE = "base,web,openupgrade_framework"


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
    verify_layout(version)
    return dest


def verify_layout(version: str) -> None:
    """Falla temprano y claro si el repo no tiene la estructura esperada."""
    base = f"{CACHE}/{version}"
    for sub in ("openupgrade_framework", "openupgrade_scripts/scripts"):
        if d.run(["test", "-d", f"{base}/{sub}"], check=False).returncode != 0:
            raise SystemExit(
                f"OpenUpgrade {version}: falta {sub} en {base}. "
                f"Revisa que la rama {version} exista en {OPENUPGRADE_REPO}")


def addons_path(version: str, core: str) -> str:
    """Raiz del repo OpenUpgrade + los addons del Odoo estandar de esa version."""
    return f"{CACHE}/{version},{core}"


def upgrade_path(version: str) -> str:
    return f"{CACHE}/{version}/openupgrade_scripts/scripts"


def commit(version: str) -> str:
    p = d.run(["git", "-C", f"{CACHE}/{version}", "rev-parse", "--short", "HEAD"], check=False)
    return p.stdout.strip() or "unknown"
