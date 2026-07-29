#!/usr/bin/env python3
"""Run local structural checks without writing bytecode beside source files."""

from __future__ import annotations

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


def python_syntax_errors(source_root: Path) -> list[str]:
    """Return syntax failures while keeping the source tree free of ``.pyc`` files."""

    failures: list[str] = []
    for source_path in sorted(source_root.rglob("*.py")):
        try:
            source = source_path.read_bytes()
            compile(source, str(source_path), "exec")
        except (OSError, SyntaxError, ValueError) as exc:
            failures.append(f"{source_path}: {exc}")
    return failures


def main() -> int:
    paths = ProjectPaths.resolve(Path(__file__))
    missing = [
        str(paths.skills_root / name / "SKILL.md")
        for name in DEPARTMENTS
        if not (paths.skills_root / name / "SKILL.md").is_file()
    ]
    if missing:
        raise SystemExit("Missing department Skills: " + ", ".join(missing))
    syntax_errors = python_syntax_errors(paths.repository_root / "src")
    if syntax_errors:
        raise SystemExit(
            "Shared Python package syntax check failed:\n" + "\n".join(syntax_errors)
        )
    print("repository structure: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
