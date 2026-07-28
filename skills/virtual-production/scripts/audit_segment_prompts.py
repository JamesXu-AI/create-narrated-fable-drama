#!/usr/bin/env python3
"""Run virtual-production's internal audit on compiled Segment Prompts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from narrated_fable_drama.contracts.segment import (
    SegmentRuntimeError,
    build_prompt_audit_record,
    prompt_audit_path,
    storyboard_segment_rows,
    write_json,
)


def audit_prompts(
    task_dir: Path,
    *,
    segment_id: str | None,
    audit_all: bool,
) -> dict[str, object]:
    task_root = task_dir.expanduser().resolve(strict=True)
    all_ids = [
        str(row["segment_id"])
        for row in storyboard_segment_rows(task_root)
    ]
    if audit_all:
        selected = all_ids
    elif segment_id in all_ids:
        selected = [str(segment_id)]
    else:
        raise SegmentRuntimeError(f"Unknown Segment for Prompt audit: {segment_id}")

    records = [
        build_prompt_audit_record(task_root, current)
        for current in selected
    ]
    for record in records:
        current = str(record["segment_id"])
        write_json(prompt_audit_path(task_root, current), record)
    return {
        "contract": "seedance-prompt-internal-audit-run/v3",
        "status": "PASS",
        "department": "virtual-production",
        "gate": "seedance_prompt_internal_audit",
        "language": "Arabic",
        "language_code": "ar",
        "arabic_only_no_latin": "PASS",
        "full_model_prompt_arabic_only_no_latin_except_provider_tokens": (
            "PASS"
        ),
        "segment_count": len(records),
        "segments": selected,
        "records": [
            str(prompt_audit_path(task_root, current).resolve())
            for current in selected
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--segment")
    target.add_argument("--all", action="store_true", dest="audit_all")
    args = parser.parse_args()
    try:
        result = audit_prompts(
            args.task_dir,
            segment_id=args.segment,
            audit_all=args.audit_all,
        )
    except Exception as exc:
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
