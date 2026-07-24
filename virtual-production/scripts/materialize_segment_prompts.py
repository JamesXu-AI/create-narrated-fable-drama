#!/usr/bin/env python3
"""Resolve repository-authored Segment Prompt tokens to Seedance values."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
for script_root in (
    REPOSITORY_ROOT / "screenplay-writer" / "scripts",
    REPOSITORY_ROOT / "direct-production-design" / "scripts",
    REPOSITORY_ROOT / "virtual-production" / "scripts",
):
    if str(script_root) not in sys.path:
        sys.path.insert(0, str(script_root))

from segment_runtime import (  # noqa: E402
    SCRIPT_DIR_RELATIVE,
    SegmentRuntimeError,
    load_execution_plan,
    parse_segment_script,
    sha256_json,
    storyboard_segment_rows,
    validate_source_identity,
)


def materialize(
    task_dir: Path, *, segment_ids: list[str] | None = None
) -> dict[str, Any]:
    task_dir = task_dir.expanduser().resolve(strict=True)
    validation_through_segment_id = max(segment_ids) if segment_ids else None
    plan_rows = storyboard_segment_rows(
        task_dir,
        validation_through_segment_id=validation_through_segment_id,
    )
    planned_ids = [str(item["segment_id"]) for item in plan_rows]
    if segment_ids is None:
        selected_ids = [
            segment_id
            for segment_id in planned_ids
            if (task_dir / SCRIPT_DIR_RELATIVE / f"{segment_id}.md").is_file()
        ]
        if not selected_ids:
            raise SegmentRuntimeError(
                "Virtual production has not authored any segment-NNN.md Prompts"
            )
    else:
        if len(segment_ids) != len(set(segment_ids)):
            raise SegmentRuntimeError("--segments values must be unique")
        unknown = [item for item in segment_ids if item not in planned_ids]
        if unknown:
            raise SegmentRuntimeError(
                "Unknown --segments values: " + ", ".join(unknown)
            )
        selected_ids = segment_ids

    hashes: dict[str, str] = {}
    for segment_id in selected_ids:
        script_path = task_dir / SCRIPT_DIR_RELATIVE / f"{segment_id}.md"
        parsed = parse_segment_script(script_path)
        validate_source_identity(task_dir, parsed)
        hashes[segment_id] = sha256_json(load_execution_plan(task_dir, segment_id))
    return {
        "status": "PASS",
        "segment_count": len(selected_ids),
        "segments": selected_ids,
        "execution_plan_storage": "in_memory_only",
        "execution_plan_sha256": hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--segments", nargs="+", metavar="SEGMENT_ID")
    args = parser.parse_args()
    try:
        result = materialize(args.task_dir, segment_ids=args.segments)
    except Exception as exc:
        print(
            json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2)
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
