"""Escenario de simulacion: los parametros que define el tesista."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

import yaml

# Cadena oficial de versiones soportadas. La migracion salta de una a la siguiente.
VERSION_CHAIN = ["13.0", "14.0", "15.0", "16.0", "17.0", "18.0"]


@dataclass
class Scenario:
    name: str
    version_from: str                       # -version inicio
    version_to: str                         # -version fin
    modules: list[str] = field(default_factory=list)   # -modulos integrados
    demo_data: bool = True
    seed: str | None = None                 # script de siembra opcional (control/seeds/<seed>.py)
    arms: list[str] = field(default_factory=lambda: ["ours", "oca"])
    tool_cmd: str | None = None             # como invocar TU herramienta dentro del fork
    compare: dict = field(default_factory=lambda: {
        "schema": True,
        "data": True,
        "modules": True,
        "ignore_tables": ["ir_logging", "bus_bus", "mail_tracking_value"],
        "ignore_columns": ["write_date", "create_date", "write_uid", "create_uid"],
    })
    timeout_min: int = 90

    # ---- derivados -------------------------------------------------------
    @property
    def path(self) -> list[str]:
        """['16.0','17.0','18.0'] para un 16->18."""
        try:
            i, j = VERSION_CHAIN.index(self.version_from), VERSION_CHAIN.index(self.version_to)
        except ValueError as e:
            raise SystemExit(f"version fuera de VERSION_CHAIN: {e}")
        if j <= i:
            raise SystemExit(f"version_to ({self.version_to}) debe ser posterior a version_from")
        return VERSION_CHAIN[i:j + 1]

    @property
    def steps(self) -> list[tuple[str, str]]:
        p = self.path
        return list(zip(p, p[1:]))

    def validate(self) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,40}", self.name):
            raise SystemExit("name: solo [a-z0-9_-]")
        self.path  # dispara validacion de versiones
        for m in self.modules:
            if not re.fullmatch(r"[a-z0-9_]+", m):
                raise SystemExit(f"modulo invalido: {m}")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["path"] = self.path
        return d

    # ---- carga -----------------------------------------------------------
    @classmethod
    def load(cls, src: str | Path, **overrides) -> "Scenario":
        p = Path(src)
        if not p.exists():
            p = Path("scenarios") / f"{src}.yaml"
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        data.update({k: v for k, v in overrides.items() if v is not None})
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise SystemExit(f"claves desconocidas en {p}: {sorted(unknown)}")
        s = cls(**data)
        s.validate()
        return s

    @classmethod
    def from_args(cls, name, version_from, version_to, modules, **kw) -> "Scenario":
        s = cls(name=name, version_from=version_from, version_to=version_to,
                modules=list(modules or []), **kw)
        s.validate()
        return s


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)
