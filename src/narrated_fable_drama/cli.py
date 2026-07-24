"""Project-level validation entry point."""

from __future__ import annotations

import argparse
import subprocess
import sys

from narrated_fable_drama.core.paths import ProjectPaths


def _validate_repository() -> int:
    paths = ProjectPaths.resolve()
    command = [
        sys.executable,
        str(paths.repository_root / "scripts" / "validate_repository.py"),
    ]
    return subprocess.run(command, cwd=paths.repository_root, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="narrated-fable-drama",
        description="Operate the narrated fable drama Skill monorepo.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-repository")
    args = parser.parse_args(argv)
    if args.command == "validate-repository":
        return _validate_repository()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
