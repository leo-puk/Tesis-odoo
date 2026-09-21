"""Reporte de esfuerzo y desempeno: lo que veria el partner de Odoo."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# Modelo de esfuerzo (horas-persona). Ajustable por escenario en report.weights.
DEFAULT_WEIGHTS = {
    "per_module": 0.5,              # revision minima por modulo integrado
    "per_version_jump": 2.0,        # coordinacion por salto de version
    "per_error_log": 0.25,          # cada ERROR/CRITICAL en el log
    "per_traceback": 0.75,
    "per_manual_intervention": 1.0,
    "per_schema_diff": 0.5,         # cada diferencia de esquema vs OCA
    "per_data_diff": 1.0,           # cada tabla con datos divergentes
}


def estimate_effort(scenario, arm, cmp_result, weights=None) -> dict:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    errs = sum(s["errors"] for s in arm["steps"])
    tbs = sum(s["tracebacks"] for s in arm["steps"])
    manual = sum(s["manual_interventions"] for s in arm["steps"])
    schema_d = len([d for d in cmp_result["diffs"] if d["kind"].startswith("schema.")]) if cmp_result else 0
    data_d = len([d for d in cmp_result["diffs"] if d["kind"].startswith("data.")]) if cmp_result else 0

    items = {
        "modulos": len(scenario["modules"]) * w["per_module"],
        "saltos_version": (len(scenario["path"]) - 1) * w["per_version_jump"],
        "errores_log": errs * w["per_error_log"],
        "tracebacks": tbs * w["per_traceback"],
        "intervenciones_manuales": manual * w["per_manual_intervention"],
        "correccion_esquema": schema_d * w["per_schema_diff"],
        "correccion_datos": data_d * w["per_data_diff"],
    }
    total = round(sum(items.values()), 2)
    return {"weights": w, "breakdown": {k: round(v, 2) for k, v in items.items()},
            "total_hours": total, "total_days_8h": round(total / 8, 2),
            "counts": {"errors": errs, "tracebacks": tbs, "manual": manual,
                       "schema_diffs": schema_d, "data_diffs": data_d}}


def build(run_dir: Path, scenario: dict, arms: dict, cmp_result: dict | None,
          prod_fingerprint: dict, weights=None) -> dict:
    ours = arms.get("ours")
    effort = estimate_effort(scenario, ours, cmp_result, weights) if ours else None
    data = {
        "run_id": run_dir.name,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scenario": scenario,
        "production": {"untouched": True, "fingerprint": prod_fingerprint},
        "arms": arms,
        "comparison": cmp_result,
        "effort": effort,
    }
    (run_dir / "report.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "report.md").write_text(_markdown(data), encoding="utf-8")
    return data


def _tbl(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _markdown(d: dict) -> str:
    sc, cmpr, eff = d["scenario"], d["comparison"], d["effort"]
    L = [f"# Reporte de migracion — {sc['name']}", "",
         f"- **Ruta de versiones:** {' -> '.join(sc['path'])}",
         f"- **Modulos integrados:** {', '.join(sc['modules']) or '(solo base)'}",
         f"- **Generado:** {d['generated_at']}",
         f"- **Produccion intacta:** {'si' if d['production']['untouched'] else 'NO'} "
         f"({d['production']['fingerprint']})", ""]

    L += ["## 1. Ejecucion por rama", ""]
    rows = []
    for arm, a in d["arms"].items():
        rows.append([arm, a["db"], "OK" if a["ok"] else "FALLO", f"{a['seconds']:.1f}s",
                     len(a["steps"])])
    L += [_tbl(rows, ["rama", "base de datos", "resultado", "duracion", "saltos"]), ""]

    L += ["### Detalle por salto de version", ""]
    rows = []
    for arm, a in d["arms"].items():
        for s in a["steps"]:
            rows.append([arm, s["step"], "OK" if s["ok"] else "FALLO", f"{s['seconds']:.1f}s",
                         s["errors"], s["warnings"], s["tracebacks"], s["note"][:60]])
    L += [_tbl(rows, ["rama", "salto", "res.", "dur.", "err", "warn", "tb", "nota"]), ""]

    if cmpr:
        L += ["## 2. Comparacion contra OCA (referencia sin errores)", "",
              f"- **Fidelidad:** **{cmpr['fidelity_pct']} %**",
              f"- Objetos comparados: {cmpr['stats'].get('objects_compared')}",
              f"- Filas verificadas por hash: {cmpr['stats'].get('rows_digested')}",
              f"- Divergencias criticas: {cmpr['stats'].get('errors')} | "
              f"advertencias: {cmpr['stats'].get('warnings')}", ""]
        by_kind = {}
        for x in cmpr["diffs"]:
            by_kind.setdefault(x["kind"], []).append(x)
        L += [_tbl([[k, len(v), v[0]["ref"]] for k, v in sorted(by_kind.items())],
                   ["tipo de divergencia", "n", "ejemplo"]), ""]
        crit = [x for x in cmpr["diffs"] if x["severity"] == "error"][:40]
        if crit:
            L += ["### Casuisticas criticas (top 40)", "",
                  _tbl([[x["kind"], x["ref"], x["detail"][:90]] for x in crit],
                       ["tipo", "referencia", "detalle"]), ""]

    if eff:
        L += ["## 3. Estimacion de esfuerzo (rama propia)", "",
              f"**Total: {eff['total_hours']} h ({eff['total_days_8h']} dias-persona de 8h)**", "",
              _tbl([[k, v] for k, v in eff["breakdown"].items()], ["concepto", "horas"]), "",
              "> Modelo lineal con pesos en `report.weights`; calibrar con datos reales "
              "de proyectos del partner antes de citar en la tesis.", ""]

    L += ["## 4. Artefactos", "",
          "- `report.json` — mismos datos en crudo",
          "- `logs/` — salida completa de odoo-bin y de la herramienta por salto",
          "- `comparison.json` — diff completo ours vs oca", ""]
    return "\n".join(L)
