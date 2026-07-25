#!/usr/bin/env python3
"""Validate one complete model-authored finishing plan against current media."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from finishing.plan import RepairPlanError, ensure_renderable, load_repair_plan
from post_timeline import TimelineError, discover_segments


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--repair-plan", required=True, type=Path)
    parser.add_argument("--evidence-manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        records = discover_segments(args.task_dir)
        plan = load_repair_plan(
            args.repair_plan,
            args.evidence_manifest,
            records,
        )
        ensure_renderable(plan)
    except (RepairPlanError, TimelineError, OSError) as exc:
        print(
            json.dumps(
                {"status": "FAIL", "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "status": "REPAIR_PLAN_VALID",
                "segment_count": len(plan["segments"]),
                "boundary_count": len(plan["boundaries"]),
                "repair_count": sum(
                    item["decision"] == "repair"
                    for item in plan["boundaries"]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
