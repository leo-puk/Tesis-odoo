"""Envoltorio fino sobre el CLI de docker. Funciona igual dentro del sandbox
(socket montado) que fuera (docker del host)."""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
from pathlib import Path

ROOT = Path(os.environ.get("ODOLAB_ROOT", "/workspace" if os.environ.get("ODOLAB_IN_SANDBOX") else "."))


class DockerError(RuntimeError):
    pass


def run(cmd: list[str], *, check=True, capture=True, env=None, timeout=None) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=capture, text=True,
                       env={**os.environ, **(env or {})}, timeout=timeout)
    if check and p.returncode != 0:
        raise DockerError(f"$ {shlex.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p


def exec_in(container: str, cmd: list[str], *, user=None, check=True, timeout=None, workdir=None):
    base = ["docker", "exec"]
    if user:
        base += ["-u", user]
    if workdir:
        base += ["-w", workdir]
    return run(base + [container] + cmd, check=check, timeout=timeout)


def container_state(name: str) -> str | None:
    p = run(["docker", "inspect", "-f", "{{.State.Status}}", name], check=False)
    return p.stdout.strip() or None


def wait_healthy(name: str, timeout=120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if container_state(name) == "running":
            return
        time.sleep(1)
    raise DockerError(f"{name} no llego a running en {timeout}s")


def compose(args: list[str], *, project: str, file: str, env: dict | None = None, check=True):
    return run(["docker", "compose", "-p", project, "-f", str(ROOT / file)] + args,
               env=env, check=check)


def fork_up(run_id: str, *, version: str, port: int, arm: str, mounts: dict[str, str]) -> str:
    env = {
        "RUN_ID": run_id,
        "ARM": arm,
        "FORK_ODOO_VERSION": version,
        "FORK_HTTP_PORT": str(port),
        "SANDBOX_NET": os.environ.get("SANDBOX_NET", "odolab-net"),
        "PG_USER": os.environ.get("PG_USER", "odoo"),
        "PG_PASSWORD": os.environ.get("PG_PASSWORD", "odoo"),
        "OCA_CACHE_VOLUME": mounts["oca"],
        "TOOL_MOUNT": mounts["tool"],
        "CUSTOM_ADDONS_MOUNT": mounts["custom"],
    }
    compose(["up", "-d"], project=f"odolab-fork-{run_id}", file="stacks/fork.compose.yml", env=env)
    name = f"sbx-fork-{run_id}"
    wait_healthy(name)
    return name


def fork_down(run_id: str, *, keep_volumes=False):
    args = ["down"] + ([] if keep_volumes else ["-v"])
    compose(args, project=f"odolab-fork-{run_id}", file="stacks/fork.compose.yml",
            env={"RUN_ID": run_id, "ARM": "", "FORK_ODOO_VERSION": "0",
                 "FORK_HTTP_PORT": "0", "SANDBOX_NET": os.environ.get("SANDBOX_NET", "odolab-net"),
                 "PG_USER": "x", "PG_PASSWORD": "x",
                 "OCA_CACHE_VOLUME": os.environ.get("OCA_CACHE_VOLUME", "odolab-oca-cache"),
                 "TOOL_MOUNT": "/tmp", "CUSTOM_ADDONS_MOUNT": "/tmp"},
            check=False)


def ensure_image(version: str) -> str:
    """Construye odolab/odoo:<version> si falta."""
    tag = f"odolab/odoo:{version}"
    if run(["docker", "image", "inspect", tag], check=False).returncode == 0:
        return tag
    run(["docker", "build", "--build-arg", f"ODOO_VERSION={version}", "-t", tag,
         str(ROOT / "images" / "odoo")], capture=False)
    return tag


def free_port(base: int) -> int:
    used = set()
    p = run(["docker", "ps", "--format", "{{json .}}"], check=False)
    for line in p.stdout.splitlines():
        try:
            for m in json.loads(line).get("Ports", "").split(","):
                if "->" in m:
                    used.add(int(m.split("->")[0].rsplit(":", 1)[-1]))
        except Exception:
            continue
    port = base
    while port in used:
        port += 1
    return port
