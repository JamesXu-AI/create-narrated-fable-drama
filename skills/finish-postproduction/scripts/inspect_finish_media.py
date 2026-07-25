#!/usr/bin/env python3
"""Generate fixed ±3s real-media evidence for model-authored finishing decisions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from finishing.evidence import FinishEvidenceError, generate_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument(
        "--preview-through-segment",
        help=(
            "Generate explicitly non-final prefix evidence through SEGMENT-NNN "
            "when the complete task has not been generated."
        ),
    )
    args = parser.parse_args()
    try:
        path = generate_evidence(
            args.task_dir,
            validation_through_segment_id=args.preview_through_segment,
        )
    except (FinishEvidenceError, OSError) as exc:
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
                "status": "EVIDENCE_READY",
                "manifest": str(path.resolve()),
                "decision_authority": "editor-restoration-master-model",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
