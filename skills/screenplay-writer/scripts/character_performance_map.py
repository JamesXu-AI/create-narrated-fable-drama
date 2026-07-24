#!/usr/bin/env python3
"""Validate screenplay performance authority and role/image scope."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.role_scope import (
    MAP_RELATIVE_PATH,
    _role_visual_type_budget,
    load_character_performance_map,
    role_asset_scope_gate,
    validate_character_performance_map,
)


def _validate_command(task_dir: Path) -> dict[str, Any]:
    value = load_character_performance_map(task_dir)
    scope = role_asset_scope_gate(task_dir)
    return {
        "status": "PASS",
        "path": str(task_dir.expanduser().resolve() / MAP_RELATIVE_PATH),
        "entity_count": len(value["performance_entities"]),
        "segment_count": len(value["scene_segment_calls"]),
        "role_asset_scope_gate": scope["status"],
        "image_asset_generation": scope["image_asset_generation"],
        "detailed_screenplay_review": scope["detailed_screenplay_review"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate screenplay performance authority and role/image scope."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "role-asset-scope"):
        child = commands.add_parser(command)
        child.add_argument("--task-dir", required=True, type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = (
            role_asset_scope_gate(args.task_dir)
            if args.command == "role-asset-scope"
            else _validate_command(args.task_dir)
        )
    except Exception as exc:
        failure = {"status": "FAIL", "error": str(exc)}
        if args.command == "role-asset-scope":
            failure.update(
                {
                    "contract": "role-asset-scope-gate/v2",
                    "image_asset_generation": "BLOCKED",
                }
            )
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
