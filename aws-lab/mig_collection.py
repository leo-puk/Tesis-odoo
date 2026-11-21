"""Archive GitHub OCA MIG evidence separately from the retrieval collection."""
import re

from experimentos import now, read, save


def collect_migs(sources, case, destination, catalog=None):
    """Include other addons in the selected repositories, with a frozen search scope.

    Reachable MIG commits are candidates, not automatically admitted corrections.
    A reviewed catalogue can extend the search beyond the five addons' repos.
    """
    destination.mkdir(parents=True, exist_ok=True)
    repositories = {item["repo"] for item in case["modules"]}
    if catalog:
        data = read(catalog)
        for entry in data["repositories"]:
            if not entry.get("cases") or case["id"] in entry["cases"]:
                repositories.add(entry["repository"])
    if any(not re.fullmatch(r"[a-z0-9_-]+", repository) for repository in repositories):
        raise ValueError("Invalid extra OCA repository")
    candidates, failures, searched = [], {}, []
    target = case["version_to"]
    for repository in sorted(repositories):
        try:
            identity = f"OCA/{repository}@{target}"
            if identity not in sources.pins:
                sources.snapshot("OCA", repository, target)
            revision = sources.pins[identity]
            bare = sources.cache / "git" / f"OCA-{repository}.git"
            history = sources.git(bare, "log", "--full-history", "--format=%H%x09%s",
                                  r"--grep=\[MIG\]", "--regexp-ignore-case", revision)
            for line in history.splitlines():
                sha, _, subject = line.partition("\t")
                versions = re.findall(r"(?<![\d.])\d+\.0(?![\d.])", subject)
                if versions and target not in versions:
                    continue
                # Archive the complete commit: another addon's correction may
                # demonstrate an incompatibility also affecting a tested addon.
                patch = sources.git(bare, "show", "--diff-merges=first-parent", "--format=fuller",
                                    "--no-ext-diff", "--no-textconv", sha)
                patch_file = f"{repository}-{sha}.diff"
                (destination / patch_file).write_text(patch + "\n", encoding="utf-8")
                candidates.append(dict(repository=f"OCA/{repository}", sha=sha, subject=subject,
                    url=f"https://github.com/OCA/{repository}/commit/{sha}", patch_file=patch_file,
                    target_in_subject=target in versions,
                    admission="requires_technical_decision"))
            searched.append(dict(repository=f"OCA/{repository}", revision=revision, target=target))
        except (RuntimeError, OSError, ValueError) as error:
            failures[repository] = str(error)
    result = dict(schema_version=1, collected_at=now(), status="partial" if failures else "collected",
        scope=dict(repositories=searched, requested_repositories=sorted(repositories),
                   rule="All reachable [MIG] commits naming the target version, or no explicit version; all addon paths",
                   limitation="Frozen selected OCA repositories, not an exhaustive search of the entire Internet. "
                              "Unmerged PRs and other repositories are outside this scope unless added separately."),
        candidates=candidates, failures=failures)
    save(destination / "candidates.json", result)
    return result
