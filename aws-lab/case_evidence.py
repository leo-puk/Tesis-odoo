"""Browse a case and measure its archived results after removing downloads."""
from collections import defaultdict
from html import escape
import os
from pathlib import Path
import re
import shutil

from experimentos import ENGINES, digest, read, save, table


def archive_acquisition(work, attempt):
    """Retain the plan, inventories and logs from the disposable capture tree."""
    for stage in ("local-source", "oca-sources", "acquisition"):
        source = work / stage
        for path in source.rglob("*"):
            if path.is_file() and path.name in {
                "inventory.json", "acquisition.jsonl", "plan.json", "planning.json",
                "local-source.json", "catalog.json", "bindings.json", "merged-bindings.json",
            }:
                destination = attempt / "adquisicion" / stage / path.relative_to(source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)


def recover_case_cache(cache_root, output, case, state):
    """Remove the owned work area of an attempt interrupted before cleanup."""
    name = state.get("temporary_cache")
    if not name:
        return
    root = cache_root.resolve()
    path = root / name
    attempt = (output / state["attempt"]).resolve()
    case_root = (output / "cases" / case["id"]).resolve()
    if (not re.fullmatch(re.escape(case["id"]) + r"-[a-z0-9_]{8}", name)
            or path.resolve().parent != root or path.is_symlink() or path.is_junction()
            or attempt.parent != case_root):
        raise ValueError("Invalid temporary case cache recorded in attempt state")
    if path.is_dir():
        archive_acquisition(path / "captures", attempt)
        shutil.rmtree(path)


def publish_case_index(output, case, attempt):
    jump = f"{case['version_from']}-a-{case['version_to']}"
    folder = output / "logs" / jump / case["id"]
    folder.mkdir(parents=True, exist_ok=True)
    relative = Path(os.path.relpath(attempt, folder)).as_posix()
    links = {
        "Resultados, unidades, aristas, fuentes y MIG/FIX": "review/README.md",
        "Log de ejecución": "execution.log",
        "Log de Git y adquisición": "sources.log",
        "Inventarios y planes de adquisición": "adquisicion/",
        "Exclusiones de adquisición": "reference-exclusions.json",
        "Estado del intento": "result.json",
    }
    lines = [f"# Odoo {case['version_from']} → {case['version_to']} · {case['id']}", "",
             f"Intento más reciente · `{attempt.name}`", ""]
    for title, path in links.items():
        if (attempt / path).exists():
            lines.append(f"- [{title}]({relative}/{path})")
    (folder / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_views(attempt, packet, units):
    folder = attempt / "review"
    by_id = {unit["id"]: unit for unit in units}
    unit_ids, graph_files = set(), []
    nodes, ranks = [], []
    for query in packet["queries"]:
        name = query["module_name"]
        graph_path = attempt / "addons" / name / "graph" / "relations.json"
        graph_files.append(f"../addons/{name}/graph/relations.json")
        graph = read(graph_path)
        incident = defaultdict(list)
        for edge in graph["edges"]:
            for uid in (edge["left"], edge["right"]):
                incident[uid].append(edge["id"])
        for node in graph["nodes"]:
            uid = node["unit_id"]
            unit_ids.add(uid)
            nodes.append(dict(addon=name, unit_id=uid, seed=node["is_seed"], depth=node["minimum_hops"],
                              edges=" ".join(incident[uid]), relations=graph_files[-1],
                              evidence=f"unidades.html#{uid}", source_url=by_id[uid]["source_url"]))
        for engine, report in query["reports"].items():
            for rank, row in enumerate(report["results"], 1):
                uid = row["source"]["unit_id"]
                unit_ids.add(uid)
                ranks.append(dict(addon=name, engine=engine, rank=rank, unit_id=uid, change_id=row["change_id"],
                                  title=row["title"], evidence=f"unidades.html#{uid}", source_url=row["source"]["url"]))
    table(folder / "nodos.csv", nodes, ["addon", "unit_id", "seed", "depth", "edges", "relations",
                                        "evidence", "source_url"])
    table(folder / "primeras-unidades.csv", ranks, ["addon", "engine", "rank", "unit_id", "change_id",
                                                    "title", "evidence", "source_url"])
    with (folder / "unidades.html").open("w", encoding="utf-8") as stream:
        stream.write('<!doctype html><html lang="es"><meta charset="utf-8"><title>Unidades de evidencia</title>'
                     '<h1>Unidades de evidencia</h1>\n')
        for uid in sorted(unit_ids):
            unit = by_id[uid]
            url = unit["source_url"] or ""
            data = unit["data"]
            content = unit["text"]
            if unit["kind"] == "diff_hunk":
                content = f"{data['file_path']}\n{data['diff_header']}\n{data['diff_body']}"
            stream.write(f'<section id="{escape(uid)}"><h2>{escape(uid)}</h2>\n')
            if url.startswith("https://"):
                stream.write(f'<p><a href="{escape(url)}">Abrir la fuente original</a></p>\n')
            stream.write(f"<p>{escape(str(unit['source_locator']))}</p><pre>{escape(content)}</pre></section>\n")
        stream.write("</html>\n")
    candidates = packet["mig_candidates"]
    save(folder / "mig-fix-candidatos.json", dict(scope=packet["reference_scope"], candidates=candidates))
    lines = [f"# Evidencia de {packet['case']['id']}", "",
             "- [Ranking de unidades por addon y motor](primeras-unidades.csv)",
             "- [Todos los nodos alcanzados y sus aristas](nodos.csv)",
             "- [Fragmentos originales de las unidades con enlaces y localizadores](unidades.html)",
             "- [Recomendaciones y candidatos MIG/FIX con enlaces](RECOMENDACIONES_MIG.md)",
             "- [Lista de MIG/FIX candidatos en JSON](mig-fix-candidatos.json)",
             "- [Colección normalizada para revisar C1](corpus-units.json)",
             "- [Dossier con sugerencias de coincidencias para revisar](packet.json)",
             "- [Instrucciones de revisión](REVIEW_PROMPT.md) y [plantilla JSON](review-template.json)",
             "", "Después de aplicar los juicios", "",
             "- [MIG/FIX admitidos como referencias](mig-fix-admitidos.json)",
             "- [Matriz de evidencia, pertinencia y cobertura](matriz-unidad-mig.csv)",
             "", "Aristas por addon. Cada arista conserva las identidades compartidas, las reglas y sus localizadores.", ""]
    if (attempt / "recommended-sources.json").is_file():
        lines.insert(3, "- [URLs recomendadas del caso por motor](../recommended-sources.json)")
    lines.extend(f"- [{query['module_name']}]({path})" for query, path in zip(packet["queries"], graph_files))
    (folder / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_judgments(folder, packet, specification, units, decisions):
    references = specification["references"]
    case = packet["case"]
    commits = {f"{entry['repository']}@{entry['sha']}": entry for entry in specification["admitted_commits"]}
    save(folder / "mig-fix-admitidos.json", dict(reviewer=specification["reviewer"],
        mig=specification["admitted_migrations"],
        fix=[entry for entry in commits.values() if "FIX" in entry["tags"]],
        corrections={rid: dict(reference, description=decisions[rid]["description"],
                               coverage_reason=decisions[rid]["coverage_reason"])
                     for rid, reference in references.items()}))

    def reference_fields(rid):
        if not rid:
            return {}
        reference = references[rid]
        return dict(correction_id=rid, commits=" ".join(reference["commit_ids"]),
                    commit_urls=" ".join(commits[key]["url"] for key in reference["commit_ids"]),
                    patch_hunks=" ".join(reference["hunk_ids"]))

    def rows():
        for rid, reference in references.items():
            for uid in reference["available_unit_ids"] or [""]:
                yield dict(scope="collection", unit_id=uid, source_url=units[uid]["source_url"] if uid else "",
                           covers_correction=bool(uid), **reference_fields(rid),
                           affected_layer=reference.get("affected_layer"),
                           affected_component=reference.get("affected_component"),
                           reason=reference["unit_explanations"].get(uid) or decisions[rid]["coverage_reason"])
        by_query = {query["id"]: query for query in packet["queries"]}
        for query in specification["queries"]:
            for engine, report in by_query[query["id"]]["reports"].items():
                for rank, row in enumerate(report["results"], 1):
                    uid = row["change_id"]
                    judgment = query["judgments"][uid]
                    for rid in query["reference_ids"] or [""]:
                        covered = rid in judgment["reference_ids"]
                        yield dict(scope="first_view", addon=query["module_name"], engine=engine, rank=rank,
                                   unit_id=uid, shown_unit_id=row["source"]["unit_id"],
                                   evidence=f"unidades.html#{row['source']['unit_id']}",
                                   source_url=row["source"]["url"], relevant=judgment["relevant"],
                                   covers_correction=covered if rid else "", **reference_fields(rid),
                                   affected_layer=judgment.get("affected_layer"),
                                   affected_component=judgment.get("affected_component"),
                                   reason=judgment["reason"], uncertainty=judgment["uncertainty"],
                                   link_explanation=(references[rid]["unit_explanations"].get(uid, "") if covered else ""))

    scoped_rows = (dict(case=case["id"], version_from=case["version_from"], version_to=case["version_to"], **row)
                   for row in rows())
    table(folder / "matriz-unidad-mig.csv", scoped_rows, ["case", "version_from", "version_to",
          "scope", "addon", "engine", "rank", "unit_id",
          "shown_unit_id", "evidence", "source_url", "correction_id", "commits", "commit_urls", "patch_hunks", "relevant",
          "covers_correction", "affected_layer", "affected_component", "reason", "link_explanation", "uncertainty"])


def verified_archive(attempt, result):
    from review_dossier import verify_dossier

    folder = attempt / "review"
    if digest(folder / "packet.json") != result["review_packet_sha256"]:
        raise ValueError("Archived review packet changed")
    packet = read(folder / "packet.json")
    if packet["database_sha256"] != result["database_sha256"]:
        raise ValueError("Archived collection fingerprint differs")
    verify_dossier(folder, packet)
    return packet


def evaluate_archive(attempt, result, specification, manifest):
    from r2.evaluation.normalized import evaluate_reports

    packet = verified_archive(attempt, result)
    if specification.get("review_packet_sha256") != result["review_packet_sha256"]:
        raise ValueError("Judgments must refer to the archived review packet")
    matrix_hash = digest(attempt / "review" / "matriz-unidad-mig.csv")
    if specification.get("judgment_matrix_sha256") != matrix_hash:
        raise ValueError("The judgment matrix differs from the applied review")
    units = {row["id"]: row for row in read(attempt / "review" / "corpus-units.json")["units"]}
    repeats = manifest["protocol"]["repeats"]

    def report_for(query):
        folder = attempt / "addons" / query["module_name"]
        timings = read(folder / "timing.json")
        samples = {engine: [row["seconds"] for row in timings if row["engine"] == engine] for engine in ENGINES}
        if any(len(values) != repeats for values in samples.values()):
            raise ValueError("Archived timings do not match the frozen repetitions")
        reports = {engine: read(folder / engine / "report.json") for engine in ENGINES}
        return reports, samples

    value = evaluate_reports(specification, units, packet["collection_revision"], report_for,
        timing=dict(repeats=repeats, environment=manifest.get("platform"), order="Alternated per repetition",
                    cache=manifest["cache_policy"], boundary="Archived query through rendering and serialization"))
    return dict(value, judgment_matrix_sha256=matrix_hash)
