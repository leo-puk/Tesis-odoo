"""Archive GitHub OCA MIG/FIX evidence separately from retrieval."""
import re
from subprocess import TimeoutExpired

from experimentos import now, read, save


def reference_repositories(case, catalog=None):
    repositories = {item["repo"] for item in case["modules"]}
    if catalog:
        data = read(catalog)
        for entry in data["repositories"]:
            if not entry.get("cases") or case["id"] in entry["cases"]:
                repositories.add(entry["repository"])
    if any(not re.fullmatch(r"[a-z0-9_-]+", repository) for repository in repositories):
        raise ValueError("Invalid extra OCA repository")
    return repositories


def collect_migs(sources, case, destination, catalog=None):
    """Archive all tagged candidates in the target history relative to the origin."""
    destination.mkdir(parents=True, exist_ok=True)
    repositories = reference_repositories(case, catalog)
    candidates, failures, searched = [], {}, []
    origin, target = case["version_from"], case["version_to"]
    for repository in sorted(repositories):
        try:
            bare, first = sources.pin("OCA", repository, origin)
            _, revision = sources.pin("OCA", repository, target)
            history = sources.git(bare, "log", "--full-history", "--format=%H%x09%s",
                                  r"--grep=\[(MIG|FIX)\]", "--extended-regexp", "--regexp-ignore-case",
                                  f"{first}..{revision}")
            for line in history.splitlines():
                sha, _, subject = line.partition("\t")
                versions = re.findall(r"(?<![\d.])\d+\.0(?![\d.])", subject)
                if versions and target not in versions:
                    continue
                tags = sorted({tag.upper() for tag in re.findall(r"\[(MIG|FIX)\]", subject, re.I)})
                if not tags:
                    continue
                # Archive the complete commit: another addon's correction may
                # demonstrate an incompatibility also affecting a tested addon.
                patch = sources.git(bare, "show", "--diff-merges=first-parent", "--format=fuller",
                                    "--no-ext-diff", "--no-textconv", sha)
                patch_file = f"{repository}-{sha}.diff"
                (destination / patch_file).write_text(patch + "\n", encoding="utf-8")
                candidates.append(dict(repository=f"OCA/{repository}", sha=sha, subject=subject,
                    tags=tags,
                    url=f"https://github.com/OCA/{repository}/commit/{sha}", patch_file=patch_file,
                    target_in_subject=target in versions,
                    admission="requires_technical_decision"))
            searched.append(dict(repository=f"OCA/{repository}", origin_revision=first, revision=revision, target=target))
        except (RuntimeError, OSError, ValueError, TimeoutExpired) as error:
            failures[repository] = str(error)
    result = dict(schema_version=2, collected_at=now(), status="partial" if failures else "collected",
        scope=dict(repositories=searched, requested_repositories=sorted(repositories),
                   rule="All [MIG]/[FIX] commits reachable from target but not origin, naming target "
                        "or no explicit version; all addon paths",
                   limitation="Frozen selected OCA repositories, not an exhaustive search of the entire Internet. "
                              "Unmerged PRs and other repositories are outside this scope unless added separately."),
        candidates=candidates, failures=failures)
    save(destination / "candidates.json", result)
    return result
