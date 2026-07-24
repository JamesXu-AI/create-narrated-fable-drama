#!/usr/bin/env python3
"""Read and validate screenplay.md without authoring or rewriting any content."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.role_scope import (
    load_character_performance_map,
)
from narrated_fable_drama.contracts.screenplay import (
    load_screenplay_file,
    screenplay_speech_rate_gate,
)
from narrated_fable_drama.core.validation import StoryVideoError


ROOT_AUTHORITY_FILES = frozenset({"story.md"})
IGNORED_ROOT_METADATA_FILES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})


def task_root(task_dir: str | Path) -> Path:
    root = Path(task_dir).expanduser().resolve()
    if not root.is_dir():
        raise StoryVideoError(f"Task directory does not exist: {root}")
    return root


def validate_root_files(task_dir: str | Path) -> None:
    root = task_root(task_dir)
    unexpected = sorted(
        path.name
        for path in root.iterdir()
        if path.is_file()
        and path.name not in ROOT_AUTHORITY_FILES
        and path.name not in IGNORED_ROOT_METADATA_FILES
        and not path.name.startswith("._")
    )
    if unexpected:
        raise StoryVideoError(
            "Only story.md may be a task-root creative authority; found: "
            + ", ".join(unexpected)
        )


def _require_nonempty_text(path: Path, label: str) -> None:
    try:
        value = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StoryVideoError(f"Missing {label}: {path}") from exc
    except UnicodeDecodeError as exc:
        raise StoryVideoError(f"{label} must be valid UTF-8: {path}") from exc
    if not value.strip():
        raise StoryVideoError(f"{label} must not be empty: {path}")


def _require_single_release_file(output_dir: Path) -> None:
    actual = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    if actual != ["screenplay.md"]:
        raise StoryVideoError(
            "screenplay-writer release directory must contain only screenplay.md; "
            f"found={actual}"
        )


def _authorities(task_dir: Path) -> tuple[Path, dict[str, Any]]:
    root = task_root(task_dir)
    validate_root_files(root)
    _require_nonempty_text(root / "story.md", "story.md")
    screenplay_path = root / "screenplay-writer/screenplay.md"
    screenplay = load_screenplay_file(screenplay_path)
    return screenplay_path, screenplay


def build_or_check(task_dir: Path, *, check_only: bool) -> dict[str, Any]:
    root = task_root(task_dir)
    screenplay_path, screenplay = _authorities(root)
    _require_single_release_file(screenplay_path.parent)
    performance = load_character_performance_map(root)
    dialogue_count = sum(
        1
        for segment in screenplay["segments"]
        for shot in segment["shots"]
        if shot["dialogue"] is not None
    )
    runtime_seconds = sum(
        segment["story_plan"]["estimated_duration_seconds"]
        for segment in screenplay["segments"]
    )
    return {
        "status": "PASS",
        "mode": "check" if check_only else "build",
        "screenplay": str(screenplay_path),
        "release_files": ["screenplay.md"],
        "segment_count": len(screenplay["segments"]),
        "planned_runtime_seconds": runtime_seconds,
        "dialogue_cue_count": dialogue_count,
        "speech_rate_gate": screenplay_speech_rate_gate(screenplay),
        "performance_entity_count": len(performance["performance_entities"]),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "check"):
        child = commands.add_parser(command)
        child.add_argument("--task-dir", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = build_or_check(args.task_dir, check_only=args.command == "check")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
