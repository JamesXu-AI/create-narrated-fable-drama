#!/usr/bin/env python3
"""Render one model-planned picture-and-sound seam candidate from source Segments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from assemble_segment_videos import render_picture_lock
from finishing.plan import RepairPlanError, ensure_renderable, load_repair_plan
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.media.ffmpeg import MediaCommandError
from post_timeline import TimelineError, compile_timelines, discover_segments


def render_candidate(
    task_dir: Path,
    *,
    repair_plan_path: Path,
    evidence_manifest_path: Path,
    boundary_id: str,
    output: Path,
) -> dict[str, object]:
    task_dir = task_dir.expanduser().resolve()
    records = discover_segments(task_dir)
    plan = load_repair_plan(repair_plan_path, evidence_manifest_path, records)
    ensure_renderable(plan)
    picture_edl, audio_timeline = compile_timelines(task_dir, plan, records)
    boundary = next(
        (
            item
            for item in picture_edl["boundaries"]
            if item["boundary_id"] == boundary_id
        ),
        None,
    )
    if boundary is None:
        raise TimelineError(f"Unknown candidate boundary: {boundary_id}")
    if boundary["picture_edit"] in {"dissolve", "fade"}:
        center = (
            float(boundary["transition_start_seconds"])
            + float(boundary["transition_end_seconds"])
        ) / 2.0
    else:
        center = float(boundary["timeline_seconds"])
    start = max(0.0, center - 3.0)
    end = min(float(picture_edl["duration_seconds"]), center + 3.0)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    render_picture_lock(
        records,
        output,
        load_project_context(task_dir),
        picture_edl,
        audio_timeline,
        plan,
        timeline_window=(start, end),
    )
    return {
        "status": "CANDIDATE_READY_FOR_MODEL_REVIEW",
        "boundary_id": boundary_id,
        "output": str(output),
        "timeline_start_seconds": round(start, 6),
        "timeline_end_seconds": round(end, 6),
        "decision_authority": "editor-restoration-master-model",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--repair-plan", required=True, type=Path)
    parser.add_argument("--evidence-manifest", required=True, type=Path)
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = render_candidate(
            args.task_dir,
            repair_plan_path=args.repair_plan,
            evidence_manifest_path=args.evidence_manifest,
            boundary_id=args.boundary,
            output=args.output,
        )
    except (RepairPlanError, TimelineError, MediaCommandError, OSError) as exc:
        print(
            json.dumps(
                {"status": "FAIL", "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
