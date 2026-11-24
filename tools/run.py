"""Single entry point for the complete R1-R4 tool."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
import sys


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_COMPONENT_MODULES = (
    "components.R1",
    "components.R2",
    "components.R3",
    "components.R4",
)


def _load_entrypoints() -> list[Callable[[], object]]:
    if str(_REPOSITORY_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPOSITORY_ROOT))

    entrypoints: list[Callable[[], object]] = []
    missing: list[str] = []

    for module_name in _COMPONENT_MODULES:
        module = import_module(module_name)
        entrypoint = getattr(module, "run", None)
        if callable(entrypoint):
            entrypoints.append(entrypoint)
        else:
            missing.append(module_name)

    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            "The approved run() contract is not implemented for: "
            f"{names}. Define each method before executing the complete tool."
        )

    return entrypoints


def main() -> int:
    try:
        entrypoints = _load_entrypoints()
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for entrypoint in entrypoints:
        entrypoint()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
