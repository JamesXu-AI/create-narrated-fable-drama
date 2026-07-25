#!/usr/bin/env python3
"""Prepare mandatory approved-reference voice evidence for one Segment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from review.voice_identity import (
    DEFAULT_CONFIG,
    VoiceIdentityGateError,
    prepare_segment_voice_identity_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--segment", required=True)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    try:
        result = prepare_segment_voice_identity_gate(
            args.task_dir,
            args.segment,
            video_path=args.video,
            config_path=args.config,
        )
    except VoiceIdentityGateError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
