#!/usr/bin/env python3
"""Validate local Segment Prompts and their materialized execution plans."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = REPOSITORY_ROOT / "virtual-production" / "scripts"
DESIGN_SCRIPT_ROOT = REPOSITORY_ROOT / "direct-production-design" / "scripts"
PROJECT_SCRIPT_ROOT = REPOSITORY_ROOT / "scripts"
for script_root in (SCRIPT_ROOT, DESIGN_SCRIPT_ROOT, PROJECT_SCRIPT_ROOT):
    if str(script_root) not in sys.path:
        sys.path.insert(0, str(script_root))

from asset_catalog import load_asset_catalog  # noqa: E402
from project_domain import ProjectDomainError, validate_project_profiles  # noqa: E402
from segment_runtime import (  # noqa: E402
    CAPABILITY_PROFILE_RELATIVE,
    SCRIPT_DIR_RELATIVE,
    SegmentRuntimeError,
    load_execution_plan,
    parse_segment_script,
    read_json,
    storyboard_segment_rows,
    token_sort_key,
    validate_source_identity,
)
from segment_handoff import load_segment_handoff  # noqa: E402


def _validate_execution_plan(
    task_dir: Path, parsed: dict[str, Any], plan: dict[str, Any]
) -> None:
    segment_id = parsed["segment_id"]
    if (
        plan.get("source_script_sha256") != parsed["script_sha256"]
        or plan.get("source_private_plan_sha256") != parsed["private_plan_sha256"]
        or plan.get("source_storyboard_sha256")
        != parsed["metadata"]["source_storyboard_sha256"]
    ):
        raise SegmentRuntimeError(f"{segment_id} execution plan is stale")
    shooting = plan.get("shooting_plan")
    if not isinstance(shooting, dict):
        raise SegmentRuntimeError(f"{segment_id} execution plan lacks shooting_plan")
    for field in (
        "shooting_plan_status",
        "schedule_mode",
        "planned_wave",
        "depends_on_segment_ids",
        "required_predecessor_evidence",
        "operation",
        "seam_class",
        "editorial_intent",
        "reference_video_scope",
        "reference_video_audio",
    ):
        if shooting.get(field) != parsed["metadata"].get(field):
            raise SegmentRuntimeError(
                f"{segment_id} execution plan changes shooting-plan field {field}"
            )
    parameters = plan.get("seedance_parameters")
    if not isinstance(parameters, dict) or parameters.get("duration") != parsed["duration"]:
        raise SegmentRuntimeError(f"{segment_id} execution parameters are invalid")
    fixed = {
        "generate_audio": True,
        "watermark": False,
        "return_last_frame": True,
        "execution_expires_after": 172800,
        "priority": 0,
    }
    if any(parameters.get(key) != value for key, value in fixed.items()):
        raise SegmentRuntimeError(f"{segment_id} changes fixed Seedance values")
    media = plan.get("media_bindings")
    if not isinstance(media, list):
        raise SegmentRuntimeError(f"{segment_id} media_bindings must be an array")
    tokens = [item.get("provider_token") for item in media if isinstance(item, dict)]
    expected_tokens = sorted(
        set(item["provider_token"] for item in parsed["bindings"]),
        key=token_sort_key,
    )
    if tokens != expected_tokens:
        raise SegmentRuntimeError(
            f"{segment_id} execution media does not exactly replace Prompt tokens"
        )
    if any(
        item.get("source_kind") == "asset_catalog"
        and not str(item.get("uri") or "").startswith(("https://", "http://"))
        for item in media
    ):
        raise SegmentRuntimeError(f"{segment_id} has an unresolved asset URL")
    source_attempts = {
        item.get("source_provider_attempt_id")
        for item in media
        if isinstance(item, dict) and item.get("source_kind") != "asset_catalog"
    }
    if len(source_attempts) > 1:
        raise SegmentRuntimeError(f"{segment_id} mixes predecessor provider attempts")
    if source_attempts:
        dependency = parsed["metadata"]["depends_on_segment_ids"][0]
        record = read_json(
            task_dir
            / ".pending/virtual-production/generation-segments"
            / dependency
            / "production-record.json",
            label="predecessor production record",
        )
        if record.get("provider_attempt_id") not in source_attempts:
            raise SegmentRuntimeError(
                f"{segment_id} is not locked to the current predecessor attempt"
            )


def validate_task(
    task_dir: Path, *, segment_ids: list[str] | None = None
) -> dict[str, Any]:
    task_dir = task_dir.expanduser().resolve(strict=True)
    validation_through_segment_id = max(segment_ids) if segment_ids else None
    plan_rows = storyboard_segment_rows(
        task_dir,
        validation_through_segment_id=validation_through_segment_id,
    )
    all_ids = [str(item["segment_id"]) for item in plan_rows]
    if segment_ids is None:
        selected = all_ids
    else:
        if not segment_ids or len(segment_ids) != len(set(segment_ids)):
            raise SegmentRuntimeError("Selected Segment IDs must be unique")
        if any(item not in all_ids for item in segment_ids):
            raise SegmentRuntimeError("Selected Segment IDs are not in the private Storyboard-derived plans")
        selected = segment_ids
    script_root = task_dir / SCRIPT_DIR_RELATIVE
    catalog = load_asset_catalog(task_dir)
    task = read_json(task_dir / "task.json", label="task.json")
    try:
        validate_project_profiles(
            task, context=str(task_dir / "task.json")
        )
    except ProjectDomainError as exc:
        raise SegmentRuntimeError(str(exc)) from exc
    capability_profile = read_json(
        task_dir / CAPABILITY_PROFILE_RELATIVE,
        label="Seedance capability profile",
    )
    if segment_ids is None:
        actual_scripts = sorted(path.stem for path in script_root.glob("segment-*.md"))
        if actual_scripts != all_ids:
            raise SegmentRuntimeError(
                "Complete Prompt coverage differs from the private Segment plans"
            )
    total_duration = 0
    parsed_by_id: dict[str, dict[str, Any]] = {}
    for segment_id in selected:
        parsed = parse_segment_script(script_root / f"{segment_id}.md")
        validate_source_identity(task_dir, parsed)
        plan = load_execution_plan(task_dir, segment_id)
        _validate_execution_plan(task_dir, parsed, plan)
        parsed_by_id[segment_id] = parsed
        total_duration += parsed["duration"]
    if segment_ids is None and total_duration > 240:
        raise SegmentRuntimeError("Complete Seedance source-video duration exceeds 240s")
    if segment_ids is None:
        wave_by_id: dict[str, int] = {}
        for index, segment_id in enumerate(all_ids):
            metadata = parsed_by_id[segment_id]["metadata"]
            dependencies = metadata["depends_on_segment_ids"]
            if any(
                dependency not in wave_by_id
                or all_ids.index(dependency) >= index
                for dependency in dependencies
            ):
                raise SegmentRuntimeError(
                    f"{segment_id} has a forward, missing, or cyclic shooting-plan dependency"
                )
            expected_wave = (
                0
                if not dependencies
                else 1 + max(wave_by_id[item] for item in dependencies)
            )
            if metadata["planned_wave"] != expected_wave:
                raise SegmentRuntimeError(
                    f"{segment_id} planned_wave differs from the dependency DAG"
                )
            wave_by_id[segment_id] = expected_wave
        handoff = load_segment_handoff(task_dir)
        if list(handoff) != all_ids:
            raise SegmentRuntimeError(
                "Dialogue/boundary handoff differs from the private Segment plans"
            )
    return {
        "status": "PASS",
        "segment_count": len(selected),
        "segments": selected,
        "generate_audio": True,
        "script_root": str(script_root),
        "execution_plan_storage": "in_memory_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--segments", nargs="+", metavar="SEGMENT_ID")
    args = parser.parse_args()
    try:
        result = validate_task(args.task_dir, segment_ids=args.segments)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
