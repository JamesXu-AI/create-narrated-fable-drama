#!/usr/bin/env python3
"""Run local structural checks for the narrated fable drama monorepo."""

from __future__ import annotations

import compileall
from pathlib import Path

from narrated_fable_drama.core.paths import ProjectPaths

DEPARTMENTS = (
    "screenplay-writer",
    "direct-production-design",
    "previsualize-cinematography",
    "virtual-production",
    "video-review",
    "finish-postproduction",
)


def main() -> int:
    paths = ProjectPaths.resolve(Path(__file__))
    missing = [
        str(paths.skills_root / name / "SKILL.md")
        for name in DEPARTMENTS
        if not (paths.skills_root / name / "SKILL.md").is_file()
    ]
    if missing:
        raise SystemExit("Missing department Skills: " + ", ".join(missing))
    if not compileall.compile_dir(
        paths.repository_root / "src", quiet=1, force=False
    ):
        raise SystemExit("Shared Python package compilation failed.")
    print("repository structure: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
