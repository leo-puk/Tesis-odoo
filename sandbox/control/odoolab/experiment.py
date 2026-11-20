"""Experimento de casuisticas: bucle error -> hunk humano -> registro, por grupo de modulos.

Un experimento (`gid`) es un grupo de modulos OCA que se instalan juntos en una
produccion 16.0 y se migran juntos a 17.0, como en un cliente real. Un experimento
de un solo modulo es un grupo de uno (gid = nombre del modulo).

  prepare   por modulo, S0 = padre de su commit [MIG] humano (el modulo tras los pasos
            mecanicos de la guia OCA: format-patch | git am + pre-commit). Cada [MIG] se
            parte en hunks: la verdad de referencia.
  seed      plantillas de produccion v16: deps + modulos (prod) y solo deps (base).
            Nunca se migran: se clonan.
  baseline  cada fase sin los modulos; esas firmas se descuentan de todo.
  run       una fase (install | upgrade | test) sobre el codigo 17.0 actual.
  fix       aplica los hunks humanos que resuelven un evento y registra la casuistica.
  auto      el bucle completo sin intervencion: por cada error bloqueante aplica los
            hunks humanos del archivo del error (nivel 1), si no alcanza los del modulo
            con el mismo tipo de archivo (2), si no todos los del modulo (3).
  report    resumen; los hunks que ningun error pidio son candidatos a silenciosas.

Codigo de trabajo:   custom-addons/<gid>/{16.0,17.0,17.0-base}/  (17.0 = repo git,
                     un commit por grupo de hunks aplicado)
Datos de la tesis:   research/experiments/<gid>/   (meta, hunks, iteraciones,
                     casuisticas, acciones.log)
Logs de Odoo:        runs/exp-<gid>/NN-<fase>.log
"""
from __future__ import annotations

import ast
import csv
import filecmp
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from . import casuistics as cz
from . import census

SRC, DST = "16.0", "17.0"
PHASES = ("install", "upgrade", "test")
BLOCKING = ("ERROR", "CRITICAL")


# ------------------------------------------------------------------ rutas
def _root() -> Path:
    from .docker_ctl import ROOT
    return ROOT



def validate_gid(gid: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,40}", gid):
        raise ValueError(f"id de experimento invalido: {gid!r}")
    return gid


def validate_step(source: str, target: str) -> tuple[str, str]:
    if source not in ("16.0", "17.0", "18.0") or target != f"{int(source.split('.')[0]) + 1}.0":
        raise ValueError(f"salto no soportado: {source}->{target}")
    return source, target


def versions_of(gid: str) -> tuple[str, str]:
    m = meta(gid)
    source, target = m.get("step", "16.0->17.0").split("->")
    pair = validate_step(source, target)
    if (m.get("version_from", source), m.get("version_to", target)) != pair:
        raise ValueError(f"versiones inconsistentes en {gid}")
    return pair


def dependency_index(rows: list[dict]) -> dict[str, str]:
    index = {}
    for row in rows:
        name, repo = row["module"], row["repo"]
        if name in index and index[name] != repo:
            raise ValueError(f"addon ambiguo {name}: {index[name]} / {repo}")
        index[name] = repo
    return index


def exp_dir(gid: str) -> Path:
    validate_gid(gid)
    return _root() / "research" / "experiments" / gid


def work_dir(gid: str, version: str) -> Path:
    """'17.0' = codigo en migracion; '17.0-base' = solo dependencias (linea base)."""
    return _root() / "custom-addons" / gid / version


def log_dir(gid: str) -> Path:
    return _root() / "runs" / f"exp-{gid}"


def cache_dir() -> Path:
    return _root() / ".cache" / "oca-git"


def census_dir() -> Path:
    return _root() / "research" / "census"


def _db(gid: str, suffix: str) -> str:
    base = f"x_{gid}"
    if len(base) + len(suffix) > 60:
        base = "x_" + hashlib.sha1(gid.encode()).hexdigest()[:12]
    return f"{base}_{suffix}"


def _git(*args, cwd: Path, check=True, binary=False):
    p = subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=cwd, capture_output=True,
                       text=not binary)
    if check and p.returncode != 0:
        err = p.stderr if not binary else p.stderr.decode(errors="replace")
        raise RuntimeError(f"git {' '.join(map(str, args))}: {err.strip()[:500]}")
    return p.stdout


def _git_ok(*args, cwd: Path) -> bool:
    return subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=cwd,
                          capture_output=True).returncode == 0


def _jload(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _jdump(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] \
        if p.exists() else []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def act(gid: str, msg: str) -> None:
    """Registro de acciones legible: lo que se hizo, en orden, con hora."""
    line = f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}Z [{gid}] {msg}"
    p = exp_dir(gid) / "acciones.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


# ---------------------------------------------------------------- prepare
def _census_rows(target: str = DST) -> list[dict]:
    p = census_dir() / f"modules_{target.replace('.', '')}.csv"
    if not p.exists():
        raise SystemExit(f"falta el censo {p}: corre `odoolab census` primero")
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _export(gitdir: Path, rev: str, path: str, dest: Path) -> None:
    """git archive <rev> <path> -> dest/<path> (sin depender de tar del sistema)."""
    data = _git("archive", "--format=tar", rev, path, cwd=gitdir, binary=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        t.extractall(dest, filter="data")


def manifest(gitdir: Path, rev: str, module: str) -> dict:
    for name in ("__manifest__.py", "__openerp__.py"):
        p = subprocess.run(["git", "-c", "safe.directory=*", "show", f"{rev}:{module}/{name}"],
                           cwd=gitdir, capture_output=True, text=True, encoding="utf-8")
        if p.returncode == 0:
            # el manifest es un dict literal, a veces precedido de comentarios de copyright
            return ast.literal_eval(p.stdout[p.stdout.index("{"):])
    raise RuntimeError(f"{module}@{rev}: sin manifest")


def _resolve_oca_deps(depends: list[str], index: dict[str, str], seen: set[str],
                      *, source: str = SRC, target: str = DST) -> list[str]:
    """Dependencias OCA transitivas, leidas en la version destino."""
    DST = target
    out = []
    for dep in depends:
        if dep in seen or dep not in index:
            continue
        seen.add(dep)
        sub = set()
        for version in (source, target):
            gd = census.sync_repo(index[dep], version, cache_dir())
            if gd is None:
                raise RuntimeError(f"{dep}: falta rama {version}")
            info = manifest(gd, version, dep)
            if not info.get("installable", True):
                raise RuntimeError(f"{dep}: no instalable en {version}")
            if any((info.get("external_dependencies") or {}).values()):
                raise RuntimeError(f"{dep}: dependencias externas requieren revision")
            sub.update(info.get("depends", []))
        out += _resolve_oca_deps(sorted(sub), index, seen, source=source, target=target) + [dep]
    return out


def _module_source(repo: str, module: str, rows: list[dict],
                   *, source: str = SRC, target: str = DST) -> dict:
    """Ubica S0, el origen y el [MIG]; valida antes de escribir."""
    SRC, DST = source, target
    row = next((r for r in rows if r["repo"] == repo and r["module"] == module), None)
    if not row or row["migrated"] != "True":
        raise RuntimeError(f"{repo}/{module} no tiene commit [MIG] a {DST} en el censo")
    gd17 = census.sync_repo(repo, DST, cache_dir())
    gd16 = census.sync_repo(repo, SRC, cache_dir())
    if gd16 is None or not _git_ok("cat-file", "-e", f"{SRC}:{module}", cwd=gd16):
        raise RuntimeError(f"{repo}/{module} no existe en la rama {SRC}")
    if gd17 is None:
        raise RuntimeError(f"{repo}: no existe la rama {DST}")
    mig = row["mig_sha"]
    parent = _git("rev-parse", f"{mig}^", cwd=gd17).strip()
    if not _git_ok("cat-file", "-e", f"{parent}:{module}", cwd=gd17):
        raise RuntimeError(f"{module}: el [MIG] trae el modulo entero (no hay S0 que separar)")
    mig_iso = _git("show", "-s", "--format=%cI", mig, cwd=gd17).strip()
    rev16 = (_git("rev-list", "-1", f"--before={mig_iso}", SRC, "--", module, cwd=gd16).strip()
             or _git("rev-parse", SRC, cwd=gd16).strip())
    m17 = manifest(gd17, mig, module)
    m16 = manifest(gd16, rev16, module)
    for version, info in ((SRC, m16), (DST, m17)):
        if not info.get("installable", True):
            raise RuntimeError(f"{module}: no instalable en {version}")
    ext = sorted(set((m17.get("external_dependencies") or {}).get("python") or [])
                 | set((m16.get("external_dependencies") or {}).get("python") or []))
    if ext:
        raise RuntimeError(f"{module}: dependencias Python externas {ext}")
    return {"repo": repo, "module": module, "gd16": gd16, "gd17": gd17, "parent": parent,
            "rev16": rev16, "mig": {"sha": mig, "date": mig_iso, "subject": row["mig_subject"],
                                    "author": row["mig_author"]},
            "depends": sorted(set(manifest(gd16, rev16, module).get("depends", []))
                              | set(m17.get("depends", [])))}


def prepare(gid: str, items: list[tuple[str, str]], force: bool = False,
            *, source: str = SRC, target: str = DST) -> dict:
    """Prepara un salto sin cambiar las versiones de otros grupos."""
    SRC, DST = validate_step(source, target)
    validate_gid(gid)
    if not items or len({m for _, m in items}) != len(items):
        raise ValueError("grupo vacio o addons duplicados")
    ed = exp_dir(gid)
    if (ed / "meta.json").exists() and not force:
        raise SystemExit(f"{ed} ya existe (usa --force para rehacerlo; borra el registro)")
    rows = _census_rows(DST)
    index = dependency_index(rows)
    srcs = [_module_source(repo, mod, rows, source=SRC, target=DST) for repo, mod in items]
    group = {s["module"] for s in srcs}
    for s in srcs:
        inside = group & set(s["depends"])
        if inside:
            raise RuntimeError(f"{s['module']} depende de otro modulo del grupo: {inside}")

    # Resolve all dependencies BEFORE deleting/recreating work directories.
    deps_all = sorted({d for s in srcs for d in s["depends"]})
    oca_deps = _resolve_oca_deps(deps_all, index, set(group), source=SRC, target=DST)
    prepared_deps = []
    for dep in oca_deps:
        drepo = index[dep]
        origins = []
        for version in (SRC, DST):
            gd = census.sync_repo(drepo, version, cache_dir())
            if gd is None or not _git_ok("cat-file", "-e", f"{version}:{dep}", cwd=gd):
                raise RuntimeError(f"la dependencia OCA {dep} no existe en {version}")
            info = manifest(gd, version, dep)
            if not info.get("installable", True):
                raise RuntimeError(f"dependencia {dep}: no instalable en {version}")
            origins.append(gd)
        prepared_deps.append((dep, drepo, *origins))

    # La linea base no puede tener los modulos en el addons-path: Odoo lee todos los
    # manifests al inicializar una BD, y uno invalido tumba el arranque entero.
    w16, w17, w17b = work_dir(gid, SRC), work_dir(gid, DST), work_dir(gid, f"{DST}-base")
    for w in (w16, w17, w17b):
        if w.exists():
            shutil.rmtree(w)
        w.mkdir(parents=True)

    dep_info = []
    for dep, drepo, g16, g17 in prepared_deps:
        _export(g16, SRC, dep, w16)
        _export(g17, DST, dep, w17)
        _export(g17, DST, dep, w17b)
        entry = {"module": dep, "repo": drepo,
                 "source_version": SRC, "target_version": DST,
                 "source_sha": _git("rev-parse", SRC, cwd=g16).strip(),
                 "target_sha": _git("rev-parse", DST, cwd=g17).strip()}
        if (SRC, DST) == ("16.0", "17.0"):
            entry.update(sha16=entry["source_sha"][:12], sha17=entry["target_sha"][:12])
        dep_info.append(entry)
    core_deps = [d for d in deps_all if d not in index and d not in group]

    hunks: list[dict] = []
    (ed / "hunks").mkdir(parents=True, exist_ok=True)
    for old in (ed / "hunks").glob("*.patch"):
        old.unlink()
    mods = []
    for s in srcs:
        mod = s["module"]
        _export(s["gd16"], s["rev16"], mod, w16)
        _export(s["gd17"], s["parent"], mod, w17)
        diff = _git("diff", "--no-renames", "--binary", s["parent"], s["mig"]["sha"], "--", mod,
                    cwd=s["gd17"])
        first = len(hunks) + 1
        for h in cz.split_diff(diff):
            h.id = len(hunks) + 1
            (ed / "hunks" / f"{h.id:03d}.patch").write_text(h.patch, encoding="utf-8", newline="\n")
            d = h.summary()
            if DST != "17.0":
                d["tags"] = [t for t in d["tags"] if not t.startswith("G17-")]
                if not d["tags"] or d["tags"] == ["SIN_GUIA"]:
                    d["tags"] = ["GUIA_PENDIENTE"]
            d["module"] = mod
            hunks.append(d)
        cmp = filecmp.dircmp(w16 / mod, w17 / mod)

        def _ndiff(c, rel=""):
            names = c.diff_files + c.left_only + c.right_only
            n = sum(1 for x in names if not cz.ADMIN_FILES.search(f"{rel}{x}"))
            return n + sum(_ndiff(sub, f"{rel}{k}/") for k, sub in c.subdirs.items())

        post = []
        pp = census_dir() / f"post_mig_commits_{DST.replace('.', '')}.csv"
        if pp.exists():
            with pp.open(encoding="utf-8") as f:
                post = [r for r in csv.DictReader(f) if r["repo"] == s["repo"] and r["module"] == mod]
        mods.append({"repo": s["repo"], "module": mod, "mig": s["mig"],
                     "s0": {"sha": s["parent"], "source": "padre del [MIG]"},
                     "source_revision": s["rev16"], "source_vs_s0_files_differ": _ndiff(cmp),
                     **({"rev16": s["rev16"], "s0_vs_16_files_differ": _ndiff(cmp)}
                        if SRC == "16.0" else {}),
                     "depends": s["depends"], "hunks": [first, len(hunks)],
                     "post_mig": {"commits": len(post),
                                  "fix": [r["subject"] for r in post if r["tag"] == "FIX"]}})
    _jdump(ed / "hunks.json", hunks)
    _jdump(ed / "post_mig.json", {m["module"]: m["post_mig"] for m in mods})

    _git("init", "-q", cwd=w17)
    _git("add", "-A", cwd=w17)
    _git("-c", "user.name=odolab", "-c", "user.email=odolab@local", "commit", "-q", "-m",
         "S0: modulos tras los pasos mecanicos de la guia (padres de los [MIG])", cwd=w17)

    meta_ = {"id": gid, "step": f"{SRC}->{DST}",
             "version_from": SRC, "version_to": DST,
             "guide_status": "implemented" if DST == "17.0" else "pending",
             "prepared_at": _now(),
             "modules": mods, "depends": {"core": core_deps, "oca": dep_info},
             "hunks": len(hunks), "hunk_tags": _count_tags(hunks)}
    _jdump(ed / "meta.json", meta_)
    for name in ("casuisticas.jsonl", "iterations.jsonl"):
        (ed / name).write_text("", encoding="utf-8")
    for name in ("baseline.json", "seed.json", "auto.json"):
        (ed / name).unlink(missing_ok=True)
    return meta_


def _count_tags(hunks: list[dict]) -> dict:
    c: dict[str, int] = {}
    for h in hunks:
        for t in h["tags"]:
            c[t] = c.get(t, 0) + 1
    return dict(sorted(c.items()))


def meta(gid: str) -> dict:
    m = _jload(exp_dir(gid) / "meta.json", None)
    if not m:
        raise SystemExit(f"experimento {gid} no preparado")
    if "modules" not in m:                       # formato del piloto (un modulo)
        m = {**m, "id": gid, "modules": [{**{k: m[k] for k in ("repo", "module", "mig", "s0",
                                                                "rev16", "s0_vs_16_files_differ")},
                                          "depends": m["depends"]["core"]}]}
    return m


def modules_of(gid: str) -> list[str]:
    return [x["module"] for x in meta(gid)["modules"]]


# ------------------------------------------------------------ forks / odoo
def _mounts(gid: str, version: str) -> dict:
    """version puede llevar sufijo de variante ('17.0-base')."""
    from .migrate import _mounts as base
    m = base()
    root = os.environ["ODOLAB_HOST_ROOT"].replace("\\", "/")
    m["custom"] = f"{root}/custom-addons/{gid}/{version}"
    return m


class _Fork:
    def __init__(self, gid: str, version: str, tag: str, variant: str = ""):
        self.gid, self.version, self.variant = gid, version, variant
        h = hashlib.sha1(gid.encode()).hexdigest()
        self.run_id = f"x-{h[:8]}-{tag}-{version.replace('.', '')}"
        self.port_base = int(os.environ.get("FORK_PORT_BASE", "8100")) + int(h[:4], 16) % 400

    def __enter__(self):
        from . import docker_ctl as d
        d.ensure_image(self.version)
        d.fork_down(self.run_id)                 # restos de una corrida interrumpida
        port = d.free_port(self.port_base)
        self.name = d.fork_up(self.run_id, version=self.version, port=port, arm="exp",
                              mounts=_mounts(self.gid, self.version + self.variant))
        return self

    def __exit__(self, *exc):
        from . import docker_ctl as d
        d.fork_down(self.run_id)


def _odoo(fork: _Fork, db: str, tag: str, *, init=None, update=None, extra=None,
          openupgrade=False, timeout_min=90):
    from . import oca
    from . import docker_ctl as d
    from .odoo_run import run_odoo, valid_addons_path
    ap = valid_addons_path(fork.name)
    kw = {}
    if openupgrade:
        # el cache se clona una vez; no se actualiza en cada corrida (reproducibilidad y
        # para que dos grupos en paralelo no hagan fetch a la vez sobre el mismo repo)
        if d.run(["test", "-d", f"{oca.CACHE}/{fork.version}/.git"], check=False).returncode:
            oca.ensure_branch(fork.version)
        ap = oca.addons_path(fork.version, ap)
        kw = {"upgrade_path": oca.upgrade_path(fork.version), "load": oca.SERVER_WIDE}
    return run_odoo(fork.name, db=db, addons_path=ap, init=init, update=update, extra=extra,
                    log_dir=log_dir(fork.gid), tag=tag, timeout_min=timeout_min, **kw)


def _deps_csv(m: dict) -> str:
    return ",".join(m["depends"]["core"] + [d["module"] for d in m["depends"]["oca"]]) or "base"


# -------------------------------------------------------------------- seed
_LOADING_RE = re.compile(r"Loading module (\w+) \(\d+/\d+\)")
_ADDON_PATH_RE = re.compile(r"/mnt/extra-addons/(\w+)/")


def culprit(log_text: str, candidates: list[str]) -> str | None:
    """Modulo del grupo responsable de una instalacion fallida, si se puede saber."""
    first_err = next((i for i, ln in enumerate(log_text.splitlines())
                      if re.search(r" (ERROR|CRITICAL) ", ln)), None)
    lines = log_text.splitlines()
    text = "\n".join(lines[first_err:first_err + 200]) if first_err is not None else log_text
    for m in _ADDON_PATH_RE.findall(text):
        if m in candidates:
            return m
    loading = [m for m in _LOADING_RE.findall("\n".join(lines[:first_err or len(lines)]))]
    for m in reversed(loading):
        if m in candidates:
            return m
    return None


class SeedError(RuntimeError):
    def __init__(self, msg, culprit=None, log=None):
        super().__init__(msg)
        self.culprit, self.log = culprit, log


def seed(gid: str, force: bool = False) -> dict:
    """Plantillas de produccion v16: con los modulos (prod) y sin ellos (base)."""
    SRC, DST = versions_of(gid)
    from . import pg
    m = meta(gid)
    mods = ",".join(modules_of(gid))
    out = {}
    with _Fork(gid, SRC, "seed") as f:
        for suffix, init in (("prod", f"{_deps_csv(m)},{mods}"), ("base", _deps_csv(m))):
            db = _db(gid, suffix)
            if pg.exists(db) and not force:
                out[suffix] = {"db": db, "created": False}
                continue
            pg.drop(db)
            act(gid, f"seed: instalando en {SRC} la BD {db} con {init}")
            r = _odoo(f, db, f"seed-{suffix}", init=init)
            ev = cz.parse_log(r.log_path.read_text(encoding="utf-8", errors="replace"))
            if not r.ok or any(e.level in BLOCKING for e in ev):
                pg.drop(db)
                c = culprit(r.log_path.read_text(encoding="utf-8", errors="replace"), modules_of(gid))
                raise SeedError(f"fallo la siembra {db} en {SRC}: ver {r.log_path}", c, str(r.log_path))
            out[suffix] = {"db": db, "created": True, "seconds": round(r.seconds, 1),
                           "fingerprint": _fingerprint(db)}
            act(gid, f"seed: {db} lista en {r.seconds:.0f}s, {out[suffix]['fingerprint']}")
    data = _jload(exp_dir(gid) / "seed.json", {})
    data.update(out)
    _jdump(exp_dir(gid) / "seed.json", data)
    return out


def _fingerprint(db: str) -> dict:
    from . import pg
    return {"tables": len(pg.tables(db)), "modules": len(pg.q(db, pg.MODULES_SQL)),
            "installed": len(pg.q(db, "select 1 from ir_module_module where state='installed'"))}


def _check_templates(gid: str) -> None:
    s = _jload(exp_dir(gid) / "seed.json", {})
    for k in ("prod", "base"):
        if k not in s:
            raise SystemExit(f"falta la plantilla {k}: `odoolab exp seed {gid}`")
        fp = s[k].get("fingerprint")
        if fp and _fingerprint(s[k]["db"]) != fp:
            raise SystemExit(f"PLANTILLA ALTERADA {s[k]['db']}: {fp} -> {_fingerprint(s[k]['db'])}")


# --------------------------------------------------------------- fases
def _phase(gid: str, phase: str, *, baseline: bool, fork: _Fork, tag: str):
    from . import pg
    m = meta(gid)
    mods = ",".join(modules_of(gid))
    if phase == "install":
        db = _db(gid, "ib" if baseline else "i")
        pg.drop(db)
        return db, _odoo(fork, db, tag, init=_deps_csv(m) if baseline else mods)
    if phase == "upgrade":
        _check_templates(gid)
        db = _db(gid, "ub" if baseline else "u")
        pg.clone(_db(gid, "base" if baseline else "prod"), db)
        return db, _odoo(fork, db, tag, update="all", openupgrade=True, timeout_min=150)
    if phase == "test":
        if baseline:
            return None, None
        db = _db(gid, "t")
        pg.drop(db)
        tags = ",".join(f"/{x}" for x in modules_of(gid))
        return db, _odoo(fork, db, tag, init=mods, extra=["--test-enable", f"--test-tags={tags}"],
                         timeout_min=150)
    raise SystemExit(f"fase desconocida {phase}; usa {PHASES}")


def baseline(gid: str, phases=("install", "upgrade")) -> dict:
    SRC, DST = versions_of(gid)
    from . import pg, oca
    out = {}
    if not work_dir(gid, f"{DST}-base").exists():
        raise SystemExit(f"falta {work_dir(gid, f'{DST}-base')}: rehace `exp prepare --force`")
    with _Fork(gid, DST, "base", variant="-base") as f:
        for ph in phases:
            act(gid, f"baseline: fase {ph} sin los modulos del grupo")
            db, r = _phase(gid, ph, baseline=True, fork=f, tag=f"baseline-{ph}")
            if r is None:
                continue
            ev = cz.parse_log(r.log_path.read_text(encoding="utf-8", errors="replace"))
            out[ph] = {"ok": r.ok, "returncode": r.returncode, "seconds": round(r.seconds, 1),
                       "events": len(ev), "signatures": sorted({e.signature for e in ev})}
            act(gid, f"baseline: {ph} rc={r.returncode} {r.seconds:.0f}s, {len(ev)} eventos "
                     f"(se descuentan)")
            pg.drop(db)
    data = _jload(exp_dir(gid) / "baseline.json", {})
    data.update(out)
    data["openupgrade_commit"] = oca.commit(DST)
    _jdump(exp_dir(gid) / "baseline.json", data)
    return {k: {kk: vv for kk, vv in v.items() if kk != "signatures"}
            for k, v in out.items() if isinstance(v, dict)}


def _iterations(gid: str) -> list[dict]:
    return _jsonl(exp_dir(gid) / "iterations.jsonl")


def run(gid: str, phase: str, keep_db=False) -> dict:
    SRC, DST = versions_of(gid)
    from . import pg
    base = _jload(exp_dir(gid) / "baseline.json", {})
    if phase != "test" and phase not in base:
        raise SystemExit(f"falta la linea base de {phase}: `odoolab exp baseline {gid}`")
    known = set(base.get(phase, {}).get("signatures", []))
    it = len(_iterations(gid)) + 1
    head = _git("rev-parse", "--short", "HEAD", cwd=work_dir(gid, DST)).strip()
    with _Fork(gid, DST, "run") as f:
        db, r = _phase(gid, phase, baseline=False, fork=f, tag=f"{it:02d}-{phase}")
    ev = cz.parse_log(r.log_path.read_text(encoding="utf-8", errors="replace"))
    new, seen = [], set()
    for e in ev:
        if e.signature in known or e.signature in seen:
            continue
        seen.add(e.signature)
        d = e.dict()
        if DST != "17.0":
            d["guide"] = ""
        d["sig_id"] = cz.sig_id(e.signature)
        d["module"] = _event_module(gid, d)
        d["detail"] = d["detail"][-3000:]
        new.append(d)
    rec = {"iteration": it, "phase": phase, "at": _now(), "code_head": head,
           "ok": r.ok and not any(x["level"] in BLOCKING for x in new),
           "returncode": r.returncode, "seconds": round(r.seconds, 1),
           "log": str(r.log_path.relative_to(_root())).replace("\\", "/"),
           "events_total": len(ev), "events_new": new}
    with (exp_dir(gid) / "iterations.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if not keep_db:
        pg.drop(db)
    return rec


def _event_module(gid: str, e: dict) -> str:
    SRC, DST = versions_of(gid)
    mods = modules_of(gid)
    if e.get("location"):
        top = e["location"].split("/", 1)[0]
        if top in mods:
            return top
    text = e.get("message", "") + "\n" + e.get("detail", "")
    for m in _ADDON_PATH_RE.findall(text):
        if m in mods:
            return m
    for m in mods:
        if re.search(rf"\b{re.escape(m)}\b", text):
            return m
    # hooks y callbacks que Odoo invoca sin pasar por un archivo del modulo:
    # `set_sale_price_on_variant() missing 1 required positional argument`
    for fn in re.findall(r"\b(\w+)\(\) (?:missing|takes|got)", text):
        for m in mods:
            src = work_dir(gid, DST) / m
            if any(f"def {fn}(" in p.read_text(encoding="utf-8", errors="replace")
                   for p in src.rglob("*.py")):
                return m
    return ""


# ----------------------------------------------------------------- fix
def _hunks(gid: str) -> list[dict]:
    hs = _jload(exp_dir(gid) / "hunks.json", [])
    if hs and "module" not in hs[0]:              # formato del piloto
        mod = modules_of(gid)[0]
        for h in hs:
            h["module"] = mod
    return hs


def apply_hunks(gid: str, ids: list[int]) -> str:
    SRC, DST = versions_of(gid)
    w = work_dir(gid, DST)
    ed = exp_dir(gid)
    patches = [str((ed / "hunks" / f"{i:03d}.patch").resolve()) for i in ids]
    p = subprocess.run(["git", "-c", "safe.directory=*", "apply", "--recount", "--whitespace=nowarn",
                        *patches], cwd=w, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"no aplican los hunks {ids}: {p.stderr[:800]}")
    _git("add", "-A", cwd=w)
    _git("-c", "user.name=odolab", "-c", "user.email=odolab@local", "commit", "-q", "-m",
         "hunks " + ",".join(f"{i:03d}" for i in ids), cwd=w)
    return _git("rev-parse", "--short", "HEAD", cwd=w).strip()


def _find_event(gid: str, sig_id: str) -> tuple[dict, dict]:
    for it in reversed(_iterations(gid)):
        for e in it["events_new"]:
            if e["sig_id"] == sig_id:
                return it, e
    raise SystemExit(f"no encuentro el evento {sig_id} en las iteraciones")


def _first_seen(gid: str, sig_id: str) -> int:
    for it in _iterations(gid):
        if any(e["sig_id"] == sig_id for e in it["events_new"]):
            return it["iteration"]
    return 0


def _casuistics(gid: str) -> list[dict]:
    return _jsonl(exp_dir(gid) / "casuisticas.jsonl")


def fix(gid: str, *, event: str | None, hunks: list[int], category: str | None = None,
        coverage: str | None = None, severity: str = "bloqueante", note: str = "",
        minutes: float | None = None, auto_level: int | None = None,
        resolved: bool = True) -> dict:
    """Registra una casuistica y aplica los hunks humanos que la resuelven."""
    SRC, DST = versions_of(gid)
    hs = {h["id"]: h for h in _hunks(gid)}
    for i in hunks:
        if i not in hs:
            raise SystemExit(f"hunk {i} no existe")
        if hs[i]["state"] == "applied":
            raise SystemExit(f"hunk {i} ya aplicado en {hs[i]['commit']}")
    it, ev = _find_event(gid, event) if event else ({}, {})
    commit = apply_hunks(gid, hunks) if hunks else ""
    tags = sorted({t for i in hunks for t in hs[i]["tags"]})
    guide = sorted(t for t in tags if t.startswith("G17-")) or ([ev["guide"]] if ev.get("guide") else [])
    if not coverage:
        coverage = ("L" if guide else "C" if it.get("phase") == "test" else "R") if DST == "17.0" else "?"
    mods = sorted({hs[i]["module"] for i in hunks}) or ([ev["module"]] if ev.get("module") else [])
    cas = _casuistics(gid)
    rec = {
        "id": f"C{len(cas) + 1:03d}", "group": gid, "module": ",".join(mods),
        "step": f"{SRC}->{DST}", "phase": it.get("phase", ""),
        "iteration_fixed": it.get("iteration"),
        "iteration_first_seen": _first_seen(gid, event) if event else None,
        "sig_id": event, "signature": ev.get("signature", ""), "level": ev.get("level", ""),
        "message": ev.get("message", ""), "location": ev.get("location", ""),
        "rule": ev.get("rule", ""), "category": category or ev.get("category", "?"),
        "coverage": coverage, "guide": guide, "severity": severity, "resolved": resolved,
        "hunks": hunks, "hunk_tags": tags, "commit": commit, "auto_level": auto_level,
        "lines_changed": sum(hs[i]["removed"] + hs[i]["added"] for i in hunks),
        "minutes": minutes, "note": note, "at": _now(),
    }
    with (exp_dir(gid) / "casuisticas.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    for i in hunks:
        hs[i].update(state="applied", commit=commit, casuistics=hs[i]["casuistics"] + [rec["id"]])
    _jdump(exp_dir(gid) / "hunks.json", list(hs.values()))
    return rec


# ---------------------------------------------------------------- auto
_KIND = {"A": ("__manifest__.py",), "D": (".xml",), "E": (".xml", ".csv"), "G": (".xml",), "B": (".py",), "C": (".py",),
         "H": (".py",), "F": (".js", ".xml", ".scss", ".css"), "J": ("tests/",)}


def _file_rank(path: str) -> tuple:
    """Orden del nivel 3: manifest, Python de negocio, datos/vistas, web, pruebas."""
    if path.endswith("__manifest__.py"):
        k = 0
    elif "/tests/" in path:
        k = 4
    elif path.endswith(".py"):
        k = 1
    elif path.endswith((".xml", ".csv")):
        k = 2
    else:
        k = 3
    return k, path


def _candidates(gid: str, ev: dict, level: int) -> tuple[list[int], int]:
    """Hunks humanos pendientes que pueden resolver el evento, desde `level` hacia arriba.

    1 = mismo archivo que el error; 2 = mismo modulo y mismo tipo de archivo;
    3 = lo pendiente del modulo (salvo administrativos), UN archivo por iteracion para no perder
        la atribucion hunk -> error; el nivel 3 se repite mientras el error persista.
    """
    mod = ev.get("module") or ""
    if not mod:
        return [], 0
    pend = [h for h in _hunks(gid) if h["state"] == "pending" and h["module"] == mod
            and "ADMIN" not in h["tags"]]
    loc_file = ev.get("location", "").split(":")[0]
    kinds = _KIND.get(ev.get("category", ""), ())
    for lv in range(level, 4):
        if lv == 1 and loc_file:
            ids = [h["id"] for h in pend if h["path"] == loc_file]
        elif lv == 2 and kinds:
            ids = [h["id"] for h in pend
                   if any(h["path"].endswith(k) or f"/{k}" in h["path"] for k in kinds)]
        elif lv == 3 and pend:
            path = min((h["path"] for h in pend), key=_file_rank)
            ids = [h["id"] for h in pend if h["path"] == path]
        else:
            ids = []
        if ids:
            return ids, lv
    return [], 0


def auto(gid: str, phases=PHASES, max_iter: int = 15) -> dict:
    """Bucle sin intervencion sobre las fases; cada accion queda en acciones.log."""
    summary = _jload(exp_dir(gid) / "auto.json", {})
    for phase in phases:
        act(gid, f"=== fase {phase} ===")
        level_of: dict[tuple[str, str], int] = {}   # (firma, modulo): misma firma en otro modulo es otro error
        status = "max_iter"
        for _ in range(max_iter):
            rec = run(gid, phase)
            blocking = [e for e in rec["events_new"] if e["level"] in BLOCKING]
            warns = [e for e in rec["events_new"] if e["level"] == "WARNING"]
            act(gid, f"iter {rec['iteration']:02d} {phase}: {'OK' if rec['ok'] else 'FALLA'} "
                     f"rc={rec['returncode']} {rec['seconds']:.0f}s | {len(blocking)} errores y "
                     f"{len(warns)} avisos nuevos | log {rec['log']}")
            if rec["ok"]:
                status = "ok"
                for w in warns:                      # avisos que sobreviven: posibles silenciosas
                    if not any(c["sig_id"] == w["sig_id"] for c in _casuistics(gid)):
                        c = fix(gid, event=w["sig_id"], hunks=[], severity="aviso", coverage="?",
                                note="aviso no bloqueante al final de la fase", resolved=False)
                        act(gid, f"  {c['id']} aviso [{w['category']}] {w['module'] or '-'}: "
                                 f"{w['message'][:140]}")
                break
            if not blocking:
                status = "falla_sin_evento"
                act(gid, f"  rc={rec['returncode']} sin eventos nuevos: no hay que corregir")
                break
            ev = blocking[0]
            key = (ev["sig_id"], ev.get("module") or "")
            lv0 = min(level_of.get(key, 0) + 1, 3)
            ids, lv = _candidates(gid, ev, lv0)
            if not ids:
                c = fix(gid, event=ev["sig_id"], hunks=[], coverage="R", resolved=False,
                        note="sin hunk humano pendiente que lo resuelva")
                act(gid, f"  {c['id']} SIN RESOLVER [{ev['category']}/{ev['rule'] or '?'}] "
                         f"{ev['module'] or '?'} {ev['location']}: {ev['message'][:160]}")
                status = "sin_resolver"
                break
            level_of[key] = lv
            try:
                c = fix(gid, event=ev["sig_id"], hunks=ids, auto_level=lv,
                        note=f"auto nivel {lv}")
            except RuntimeError as e:                # hunks que no aplican juntos
                act(gid, f"  no aplican {ids}: {str(e)[:200]}")
                status = "hunks_no_aplican"
                break
            act(gid, f"  {c['id']} [{c['category']}/{c['rule'] or '?'}] cob={c['coverage']} "
                     f"{c['module']} {ev['location']}: {ev['message'][:120]} -> hunks "
                     f"{','.join(f'{i:03d}' for i in ids)} (nivel {lv}, {c['lines_changed']} lineas)")
        summary[phase] = status
        act(gid, f"fase {phase}: {status}")
    _jdump(exp_dir(gid) / "auto.json", summary)
    return summary


# -------------------------------------------------------------- reporte
NON_BEHAVIOUR = {"ADMIN", "ESTILO"}


def _tbl(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    return "\n".join(out + ["| " + " | ".join(str(c).replace("|", "/").replace("\n", " ")
                                             for c in r) + " |" for r in rows])


def _count(key, items):
    c: dict = {}
    for x in items:
        vals = x[key] if isinstance(x[key], list) else [x[key]]
        for v in vals or ["-"]:
            c[v] = c.get(v, 0) + 1
    return sorted(c.items(), key=lambda kv: -kv[1])


def report(gid: str) -> Path:
    m = meta(gid)
    cas = _casuistics(gid)
    hs = _hunks(gid)
    its = _iterations(gid)
    auto_ = _jload(exp_dir(gid) / "auto.json", {})
    pending = [h for h in hs if h["state"] == "pending"]
    silent = [h for h in pending if not set(h["tags"]) <= NON_BEHAVIOUR]

    L = [f"# Experimento {gid} ({m['step']})", "",
         f"- Modulos: {', '.join(x['module'] for x in m['modules'])}",
         f"- Dependencias core: {', '.join(m['depends']['core']) or '-'} · OCA: "
         f"{', '.join(d['module'] for d in m['depends']['oca']) or '-'}",
         f"- Iteraciones: {len(its)} · casuisticas: {len(cas)} · hunks: {len(hs)} "
         f"(aplicados {len(hs) - len(pending)}, pendientes {len(pending)})",
         f"- Resultado por fase: {', '.join(f'{k}={v}' for k, v in auto_.items()) or '-'}", ""]
    L += ["## Modulos", "", _tbl(
        [[x["module"], x["repo"], x["mig"]["sha"][:10], x["mig"]["date"][:10],
          sum(1 for h in hs if h["module"] == x["module"]),
          sum(1 for h in hs if h["module"] == x["module"] and h["state"] == "applied"),
          len(x.get("post_mig", {}).get("fix", []))] for x in m["modules"]],
        ["modulo", "repo", "[MIG]", "fecha", "hunks", "aplicados", "[FIX] post"]), ""]
    L += ["## Iteraciones", "", _tbl(
        [[i["iteration"], i["phase"], "OK" if i["ok"] else "FALLA", i["returncode"], i["seconds"],
          sum(1 for e in i["events_new"] if e["level"] in BLOCKING),
          sum(1 for e in i["events_new"] if e["level"] == "WARNING"), i["log"]] for i in its],
        ["it", "fase", "res", "rc", "s", "err", "avisos", "log"]), ""]
    L += ["## Casuisticas", "", _tbl(
        [[c["id"], c.get("module", ""), c["phase"], c["iteration_first_seen"], c["severity"],
          c["category"], c["coverage"], ",".join(c["guide"]) or "-",
          ",".join(f"{i:03d}" for i in c["hunks"]) or "-", c.get("auto_level") or "-",
          (c["message"] or c["note"])[:90]] for c in cas],
        ["id", "modulo", "fase", "it", "sev", "cat", "cob", "guia", "hunks", "niv", "sintoma"]), ""]
    L += ["### Por cobertura del estandar", "",
          _tbl([[k, v, cz.COVERAGE.get(k, "por codificar")] for k, v in _count("coverage", cas)],
               ["etiqueta", "n", "significado"]), ""]
    L += ["### Por categoria", "",
          _tbl([[k, v, cz.CATEGORIES.get(k, "")] for k, v in _count("category", cas)],
               ["cat", "n", "nombre"]), ""]
    L += ["## Hunks pendientes que cambian comportamiento (candidatos a silenciosa)", "",
          "Ningun error de install/upgrade/test los pidio.", "",
          _tbl([[f"{h['id']:03d}", h["module"], h["path"].split("/", 1)[-1],
                 f"-{h['removed']}+{h['added']}", ",".join(h["tags"])] for h in silent],
               ["hunk", "modulo", "archivo", "lineas", "tags"]), ""]
    p = exp_dir(gid) / "report.md"
    p.write_text("\n".join(L), encoding="utf-8")
    return p
