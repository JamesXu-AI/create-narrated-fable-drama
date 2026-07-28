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

from narrated_fable_drama.core.json_io import (
    load_json_object,
    write_json_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--segment", required=True)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--record-out", type=Path)
    parser.add_argument("--production-record", type=Path)
    args = parser.parse_args()
    try:
        result = prepare_segment_voice_identity_gate(
            args.task_dir,
            args.segment,
            video_path=args.video,
            config_path=args.config,
        )
        if args.record_out:
            write_json_atomic(
                args.record_out.expanduser().resolve(),
                result,
                sort_keys=True,
            )
        if args.production_record:
            production_record_path = (
                args.production_record.expanduser().resolve(strict=True)
            )
            production_record = load_json_object(
                production_record_path,
                label="generated Segment production record",
                error_type=VoiceIdentityGateError,
            )
            if production_record.get("segment_id") != args.segment:
                raise VoiceIdentityGateError(
                    "Production record does not identify the reviewed Segment"
                )
            production_record["voice_identity_gate"] = result
            write_json_atomic(
                production_record_path,
                production_record,
                sort_keys=True,
            )
    except VoiceIdentityGateError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
