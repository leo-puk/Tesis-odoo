"""Strict textual unified-diff parsing. Hunks are not complete source files."""
import json
import re
from pathlib import PurePosixPath

HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:.*)$")


def filename(value):
    value = value.split("\t", 1)[0]
    if value.startswith('"'):
        try:
            value = json.loads(value)
        except ValueError:
            raise ValueError("Unsupported quoted diff path") from None
    if value == "/dev/null":
        return None
    if value.startswith(("a/", "b/")):
        value = value[2:]
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value or not value:
        raise ValueError("Unsafe diff path")
    return value


def parse_diff(text):
    lines = text.splitlines()
    hunks, warnings = [], []
    old_path = new_path = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git "):
            old_path = new_path = None
        elif line.startswith("--- "):
            old_path = filename(line[4:])
            if i + 1 >= len(lines) or not lines[i + 1].startswith("+++ "):
                raise ValueError("Missing new-file header")
            new_path = filename(lines[i + 1][4:])
            i += 1
        elif line.startswith("@@"):
            artifact_start = i + 1
            match = HEADER.fullmatch(line)
            if not match or not (old_path or new_path):
                raise ValueError("Malformed or combined diff hunk")
            old_start, old_count, new_start, new_count = match.groups()
            old_start, new_start = int(old_start), int(new_start)
            old_count, new_count = int(old_count or 1), int(new_count or 1)
            before, after, removed, added, body = [], [], [], [], []
            i += 1
            while i < len(lines):
                content = lines[i]
                if len(before) == old_count and len(after) == new_count:
                    if content == "\\ No newline at end of file":
                        i += 1
                    break
                if content == "\\ No newline at end of file":
                    i += 1
                    continue
                if not content or content[0] not in " +-":
                    raise ValueError("Truncated unified diff hunk")
                body.append(content)
                if content[0] in " -":
                    before.append(content[1:])
                if content[0] in " +":
                    after.append(content[1:])
                if content[0] == "-":
                    removed.append(content[1:])
                if content[0] == "+":
                    added.append(content[1:])
                if len(before) > old_count or len(after) > new_count:
                    raise ValueError("Unified diff line counts exceeded")
                i += 1
            if len(before) != old_count or len(after) != new_count:
                raise ValueError("Truncated unified diff hunk")
            hunks.append(dict(file_path=new_path or old_path, old_path=old_path, new_path=new_path,
                              before_start=old_start, before_end=old_start + old_count - 1,
                              after_start=new_start, after_end=new_start + new_count - 1,
                              before="\n".join(before), after="\n".join(after),
                              removed="\n".join(removed), added="\n".join(added),
                              diff_header=line, diff_body="\n".join(body),
                              artifact_start=artifact_start, artifact_end=i))
            continue
        elif line.startswith(("Binary files ", "GIT binary patch", "rename from ", "rename to ")):
            warnings.append("Non-textual/rename metadata retained as artifact; no semantic change inferred")
        elif line.startswith(("+", "-", " ")) and (old_path or new_path):
            raise ValueError("Unexpected content outside unified diff hunk")
        i += 1
    if not hunks:
        warnings.append("No textual hunks; artifact retained without candidate changes")
    return hunks, warnings
