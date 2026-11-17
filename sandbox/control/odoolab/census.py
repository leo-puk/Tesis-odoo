"""Censo de migraciones OCA: que modulos se migraron a una version y que paso despues.

Poblacion del experimento. Por cada repo de la OCA con rama <version> se busca, por
modulo, el commit humano `[MIG] <modulo>: Migration to <version>` (la verdad de
referencia) y los commits posteriores que tocan el modulo, en particular los
`[FIX]`: defectos que pasaron la CI y la revision del PR.

Solo usa git y la API publica de GitHub (sin token, 1 request por cada 100 repos).
Los clones son parciales (--filter=blob:none): historia y arboles, sin contenido de
archivos, asi que todo lo que se calcula aqui sale de nombres de archivo y mensajes.
Stdlib solamente: corre igual en el host que en sbx-control.

    python -m odoolab.census --version 17.0 --out research/census
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ORG = "OCA"
GH_REPOS = "https://api.github.com/orgs/{org}/repos?per_page=100&page={page}&type=public"
# Repos de la OCA que no son repos de addons.
NOT_ADDONS = {"OpenUpgrade", "maintainer-tools", "oca-github-bot", "oca-ci", "openupgradelib",
              "odoo-module-migrator", "oca-addons-repo-template", "oca-port", "repo-maintainer",
              "repo-maintainer-conf", "oca-custom", "OCB", "odoo-community.org", "pylint-odoo",
              "oca-weblate-deployment", "mis-builder-docs", "contribute-md-template"}

# Commits de bots y de traduccion: no son trabajo de migracion ni defectos.
BOT_RE = re.compile(r"translated using weblate|^\[UPD\] |^\[BOT\]|update translation|"
                    r"added translation|^oca-git-bot|^\[ADD\] icon|readme\.rst|"
                    r"update .*\.pot|^Merge pull request|bot\b.*bump", re.I)
SEP = "\x1f"


def git(*args: str, cwd: Path | None = None, check=True) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()[:300]}")
    return p.stdout


def list_repos(org: str = ORG) -> list[str]:
    names, page = [], 1
    while True:
        req = urllib.request.Request(GH_REPOS.format(org=org, page=page),
                                     headers={"Accept": "application/vnd.github+json",
                                              "User-Agent": "odolab-census"})
        with urllib.request.urlopen(req, timeout=60) as r:
            batch = json.load(r)
        if not batch:
            break
        names += [b["name"] for b in batch if not b.get("archived") and not b.get("fork")]
        page += 1
    return sorted(n for n in names if n not in NOT_ADDONS)


def has_branch(repo: str, version: str) -> bool:
    out = git("ls-remote", "--heads", f"https://github.com/{ORG}/{repo}.git", version, check=False)
    return bool(out.strip())


def sync_repo(repo: str, version: str, cache: Path) -> Path | None:
    """Clon bare parcial de la rama <version>; si ya existe, fetch."""
    dest = cache / f"{repo}@{version}.git"
    if dest.exists():
        git("fetch", "-q", "--filter=blob:none", "origin", f"+{version}:{version}", cwd=dest,
            check=False)
        return dest
    if not has_branch(repo, version):
        return None
    git("clone", "-q", "--bare", "--filter=blob:none", "--single-branch", "-b", version,
        f"https://github.com/{ORG}/{repo}.git", str(dest))
    return dest


def _version_re(version: str) -> re.Pattern:
    # "Migration to 17.0", "[17.0][MIG] m", "migrate to v17"
    return re.compile(rf"(?<![\d.]){re.escape(version.split('.')[0])}(\.0)?(?![\d])")


def _find_mig(hist: list[dict], module: str, version: str) -> tuple[dict | None, str]:
    """Commit [MIG] a <version> del modulo, el mas reciente.

    Primero uno que nombre al modulo; si no, cualquier [MIG] a la version que lo
    toque (hay quien escribe el nombre funcional: "[MIG] Sale Discount Display Amount").
    """
    vrx = _version_re(version)
    migs = [c for c in hist if re.search(r"\[MIG\]", c["subject"], re.I) and vrx.search(c["subject"])]
    named = re.compile(rf"\[MIG\]\s*{re.escape(module)}\b|\b{re.escape(module)}\s*:", re.I)
    for c in migs:
        if named.search(c["subject"]):
            return c, "name"
    return (migs[0], "fallback") if migs else (None, "")


def _module_files(gitdir: Path, version: str) -> dict[str, list[str]]:
    """modulo -> archivos (rutas relativas al modulo) en la punta de la rama."""
    out = git("ls-tree", "-r", "--name-only", version, cwd=gitdir)
    mods: dict[str, list[str]] = {}
    paths = out.splitlines()
    manifests = {p.split("/")[0] for p in paths
                 if p.count("/") == 1 and p.endswith(("/__manifest__.py", "/__openerp__.py"))}
    for p in paths:
        top, _, rest = p.partition("/")
        if top in manifests:
            mods.setdefault(top, []).append(rest)
    return mods


def _profile(files: list[str]) -> dict:
    ext = Counter(Path(f).suffix.lower() for f in files)
    return {
        "n_files": len(files),
        "n_py": ext[".py"],
        "n_xml": ext[".xml"],
        "n_js": ext[".js"],
        "n_scss_css": ext[".scss"] + ext[".css"],
        "n_csv": ext[".csv"],
        "has_tests": any(f.startswith("tests/") for f in files),
        "n_test_files": sum(1 for f in files if f.startswith("tests/test") and f.endswith(".py")),
        "has_report": any(f.startswith(("report/", "reports/")) for f in files),
        "has_wizard": any(f.startswith("wizard") for f in files),
        "has_static_src": any(f.startswith("static/src/") for f in files),
        "has_migrations": any(f.startswith("migrations/") for f in files),
        "has_hooks": "hooks.py" in files,
        "has_security_csv": "security/ir.model.access.csv" in files,
    }


def _commits(gitdir: Path, rev: str, path: str) -> list[dict]:
    fmt = SEP.join(["%H", "%cI", "%aI", "%an", "%s"])
    out = git("log", f"--format={fmt}", rev, "--", path, cwd=gitdir)
    rows = []
    for ln in out.splitlines():
        h, cd, ad, an, s = ln.split(SEP, 4)
        rows.append({"sha": h, "committed": cd, "authored": ad, "author": an, "subject": s})
    return rows


def _tag(subject: str) -> str:
    m = re.search(r"\[(FIX|IMP|REF|MIG|ADD|REM|UPD|MOV|PERF|CHG|I18N|DOC|SEC)\]", subject, re.I)
    return m.group(1).upper() if m else "OTHER"


def _days(a: str, b: str) -> float:
    return round((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 86400, 1)


def census_repo(repo: str, gitdir: Path, version: str) -> tuple[list[dict], list[dict]]:
    modules, post = [], []
    for mod, files in sorted(_module_files(gitdir, version).items()):
        hist = _commits(gitdir, version, mod)           # mas reciente primero
        mig, how = _find_mig(hist, mod, version)
        origin = "migrado" if mig else (
            "nuevo" if hist and _tag(hist[-1]["subject"]) == "ADD" else "sin_mig")
        row = {"repo": repo, "module": mod, "migrated": bool(mig), "origin": origin,
               "mig_match": how, **_profile(files)}
        if mig:
            files_mig = git("show", "--name-status", "--format=", mig["sha"], "--", mod,
                            cwd=gitdir).splitlines()
            after = [c for c in hist[:hist.index(mig)] if not BOT_RE.search(c["subject"])]
            fixes = [c for c in after if _tag(c["subject"]) == "FIX"]
            row.update({
                "mig_sha": mig["sha"], "mig_date": mig["committed"][:10],
                "mig_author": mig["author"], "mig_subject": mig["subject"],
                "mig_files_changed": len(files_mig),
                "post_commits": len(after),
                "post_fix": len(fixes),
                "post_fix_180d": sum(1 for c in fixes
                                     if _days(mig["committed"], c["committed"]) <= 180),
                "days_to_first_fix": (_days(mig["committed"], fixes[-1]["committed"])
                                      if fixes else ""),
                "post_tags": " ".join(f"{k}:{v}" for k, v in
                                      sorted(Counter(_tag(c["subject"]) for c in after).items())),
            })
            for c in after:
                post.append({"repo": repo, "module": mod, "tag": _tag(c["subject"]),
                             "days_after_mig": _days(mig["committed"], c["committed"]), **c})
        modules.append(row)
    return modules, post


def _manifest_depends(gitdir: Path, rev: str, module: str) -> list[str]:
    import ast
    for name in ("__manifest__.py", "__openerp__.py"):
        p = subprocess.run(["git", "show", f"{rev}:{module}/{name}"], cwd=gitdir,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode == 0:
            try:
                return list(ast.literal_eval(p.stdout[p.stdout.index("{"):]).get("depends", []))
            except (ValueError, SyntaxError):
                return []
    return []


def enrich_module(row: dict, gitdir: Path, oca_modules: set[str]) -> tuple[dict, list[dict]]:
    """Segunda pasada (necesita blobs): dependencias y hunks del [MIG] humano."""
    from .casuistics import split_diff
    mod, mig = row["module"], row["mig_sha"]
    deps = _manifest_depends(gitdir, mig, mod)
    diff = git("diff", "--no-renames", f"{mig}^", mig, "--", mod, cwd=gitdir, check=False)
    hunks = split_diff(diff)
    tags = Counter(t for h in hunks for t in h.tags)
    behav = [h for h in hunks if not set(h.tags) <= {"ADMIN", "ESTILO"}]
    out = {
        "repo": row["repo"], "module": mod,
        "depends": " ".join(deps),
        "n_oca_deps": sum(1 for d in deps if d in oca_modules),
        "core_deps": " ".join(d for d in deps if d not in oca_modules),
        "mig_added": sum(h.added for h in hunks), "mig_removed": sum(h.removed for h in hunks),
        "n_hunks": len(hunks),
        "n_hunks_behaviour": len(behav),
        "n_hunks_guide": sum(1 for h in hunks if any(t.startswith("G17-") for t in h.tags)),
        "n_hunks_sin_guia": tags.get("SIN_GUIA", 0),
        "n_hunks_admin": tags.get("ADMIN", 0), "n_hunks_estilo": tags.get("ESTILO", 0),
        "guide_tasks": " ".join(sorted(t for t in tags if t.startswith("G17-"))),
        "mig_touches_module_whole": any(h.status == "A" and h.path.endswith("__manifest__.py")
                                        for h in hunks),
    }
    hrows = [{"repo": row["repo"], "module": mod, "hunk": h.id, "path": h.path, "status": h.status,
              "removed": h.removed, "added": h.added, "tags": " ".join(h.tags),
              "header": h.header[:120]} for h in hunks]
    return out, hrows


def enrich(out: Path, cache: Path, version: str, jobs: int) -> None:
    v = version.replace(".", "")
    with (out / f"modules_{v}.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    oca = {r["module"] for r in rows}
    todo = [r for r in rows if r["migrated"] == "True"]
    res, hunks = [], []
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(enrich_module, r, cache / f"{r['repo']}@{version}.git", oca): r
                for r in todo}
        for i, f in enumerate(as_completed(futs), 1):
            r = futs[f]
            try:
                e, h = f.result()
                res.append(e)
                hunks += h
            except Exception as e:                       # noqa: BLE001
                res.append({"repo": r["repo"], "module": r["module"], "error": str(e)[:300]})
            if i % 50 == 0:
                print(f"  [{i}/{len(todo)}]", file=sys.stderr)
    res.sort(key=lambda r: (r["repo"], r["module"]))
    hunks.sort(key=lambda r: (r["repo"], r["module"], r["hunk"]))
    write_csv(out / f"mig_enriched_{v}.csv", res)
    write_csv(out / f"mig_hunks_{v}.csv", hunks)
    print(f"{len(res)} modulos, {len(hunks)} hunks", file=sys.stderr)


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", default="17.0")
    ap.add_argument("--out", default="research/census")
    ap.add_argument("--cache", default=".cache/oca-git")
    ap.add_argument("--repos", help="csv de repos (por defecto: todos los de la OCA)")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--enrich", action="store_true",
                    help="segunda pasada sobre un censo ya hecho: dependencias y hunks del [MIG]")
    a = ap.parse_args(argv)

    out, cache = Path(a.out), Path(a.cache)
    out.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    if a.enrich:
        enrich(out, cache, a.version, a.jobs)
        return 0
    repos = a.repos.split(",") if a.repos else list_repos()
    print(f"{len(repos)} repos candidatos", file=sys.stderr)

    modules, post, skipped = [], [], {}
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(sync_repo, r, a.version, cache): r for r in repos}
        for i, f in enumerate(as_completed(futs), 1):
            r = futs[f]
            try:
                gd = f.result()
                if gd is None:
                    skipped[r] = f"sin rama {a.version}"
                    continue
                m, p = census_repo(r, gd, a.version)
                modules += m
                post += p
            except Exception as e:                       # noqa: BLE001 - se reporta y sigue
                skipped[r] = f"{type(e).__name__}: {e}"[:300]
            print(f"  [{i}/{len(repos)}] {r}", file=sys.stderr)

    modules.sort(key=lambda r: (r["repo"], r["module"]))
    post.sort(key=lambda r: (r["repo"], r["module"], r["committed"]))
    v = a.version.replace(".", "")
    write_csv(out / f"modules_{v}.csv", modules)
    write_csv(out / f"post_mig_commits_{v}.csv", post)

    mig = [m for m in modules if m["migrated"]]
    summary = {
        "version": a.version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repos_considered": len(repos),
        "repos_with_branch": len(repos) - sum(1 for s in skipped.values() if s.startswith("sin rama")),
        "skipped": skipped,
        "modules_in_branch": len(modules),
        "modules_with_mig_commit": len(mig),
        "with_fix_after_mig": sum(1 for m in mig if m["post_fix"]),
        "with_fix_within_180d": sum(1 for m in mig if m["post_fix_180d"]),
        "note": "[FIX] es cota superior de defectos: falta codificar a mano cuales "
                "son defectos introducidos por la migracion (ver post_mig_commits).",
    }
    (out / f"summary_{v}.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                           encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "skipped"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
