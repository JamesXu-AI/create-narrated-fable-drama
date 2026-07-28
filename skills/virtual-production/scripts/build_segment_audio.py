#!/usr/bin/env python3
"""Replace one Seedance Segment's character speech with exact ElevenLabs Arabic."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from narrated_fable_drama.core.json_io import (  # noqa: E402
    load_json_object,
    write_json_atomic,
)
from narrated_fable_drama.dubbing import (  # noqa: E402
    ArabicSegmentEmbeddingError,
    embed_arabic_segment,
)


def _parse_reviewed_cue_windows(
    values: list[str],
) -> dict[str, tuple[float, float]]:
    result: dict[str, tuple[float, float]] = {}
    for value in values:
        line_id, separator, raw_window = value.partition("=")
        start_text, comma, end_text = raw_window.partition(",")
        if (
            separator != "="
            or comma != ","
            or not line_id.strip()
            or line_id.strip() in result
        ):
            raise ValueError(
                "Each --reviewed-cue-window must be unique and use "
                "LINE_ID=START_SECONDS,END_SECONDS."
            )
        try:
            start = float(start_text)
            end = float(end_text)
        except ValueError as exc:
            raise ValueError(
                "Reviewed cue window bounds must be numeric seconds."
            ) from exc
        result[line_id.strip()] = (start, end)
    return result


def _parse_reviewed_cue_speeds(values: list[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for value in values:
        line_id, separator, speed_text = value.partition("=")
        if (
            separator != "="
            or not line_id.strip()
            or line_id.strip() in result
        ):
            raise ValueError(
                "Each --reviewed-cue-speed must be unique and use "
                "LINE_ID=SPEED."
            )
        try:
            speed = float(speed_text)
        except ValueError as exc:
            raise ValueError(
                "Reviewed cue speed must be a numeric ElevenLabs speed."
            ) from exc
        if speed < 0.7 or speed > 1.2:
            raise ValueError(
                "Reviewed cue speed must stay between 0.7 and 1.2."
            )
        result[line_id.strip()] = speed
    return result


def _parse_reviewed_cue_seeds(values: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        line_id, separator, seed_text = value.partition("=")
        if (
            separator != "="
            or not line_id.strip()
            or line_id.strip() in result
        ):
            raise ValueError(
                "Each --reviewed-cue-seed must be unique and use "
                "LINE_ID=SEED."
            )
        try:
            seed = int(seed_text)
        except ValueError as exc:
            raise ValueError(
                "Reviewed cue seed must be an integer."
            ) from exc
        if seed < 0 or seed > 4294967295:
            raise ValueError(
                "Reviewed cue seed must stay between 0 and 4294967295."
            )
        result[line_id.strip()] = seed
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--segment-id", required=True)
    parser.add_argument("--seedance-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--record-out", type=Path)
    parser.add_argument("--production-record", type=Path)
    parser.add_argument("--request-timeout", type=int, default=300)
    parser.add_argument(
        "--reviewed-cue-window",
        action="append",
        default=[],
        metavar="LINE_ID=START_SECONDS,END_SECONDS",
        help=(
            "Use one frame-reviewed mouth-performance window; repeat for "
            "additional cues."
        ),
    )
    parser.add_argument(
        "--reviewed-cue-speed",
        action="append",
        default=[],
        metavar="LINE_ID=SPEED",
        help=(
            "Use one frame-reviewed ElevenLabs speaking speed for a cue; "
            "repeat for additional cues."
        ),
    )
    parser.add_argument(
        "--reviewed-cue-seed",
        action="append",
        default=[],
        metavar="LINE_ID=SEED",
        help=(
            "Replay one previously recorded ElevenLabs seed for a cue; "
            "repeat for additional cues. Omit to create a fresh seed."
        ),
    )
    args = parser.parse_args()
    try:
        reviewed_cue_windows = _parse_reviewed_cue_windows(
            args.reviewed_cue_window
        )
        reviewed_cue_speeds = _parse_reviewed_cue_speeds(
            args.reviewed_cue_speed
        )
        reviewed_cue_seeds = _parse_reviewed_cue_seeds(
            args.reviewed_cue_seed
        )
        record = embed_arabic_segment(
            task_dir=args.task_dir.expanduser().resolve(strict=True),
            segment_id=args.segment_id,
            seedance_background_video=args.seedance_source.expanduser().resolve(
                strict=True
            ),
            output_video=args.output.expanduser().resolve(),
            request_timeout=args.request_timeout,
            reviewed_cue_windows=reviewed_cue_windows,
            reviewed_cue_speeds=reviewed_cue_speeds,
            reviewed_cue_seeds=reviewed_cue_seeds,
        )
    except (ArabicSegmentEmbeddingError, OSError, ValueError) as exc:
        parser.error(str(exc))
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.record_out:
        record_path = args.record_out.expanduser().resolve()
        write_json_atomic(record_path, record)
    if args.production_record:
        production_record_path = args.production_record.expanduser().resolve(
            strict=True
        )
        production_record = load_json_object(
            production_record_path,
            label="generated Segment production record",
            error_type=ArabicSegmentEmbeddingError,
        )
        if (
            production_record.get("segment_id") != args.segment_id
            or production_record.get("status") != "GENERATED"
        ):
            parser.error(
                "Production record does not identify the generated Segment"
            )
        production_record["dubbing"] = record
        production_record["media_probe"] = record["final_media_probe"]
        production_record["video_bytes"] = args.output.expanduser().resolve(
            strict=True
        ).stat().st_size
        production_record["voice_identity_gate"] = {
            "contract": "video-review-voice-identity-gate/v2",
            "segment_id": args.segment_id,
            "language": "Arabic",
            "language_code": "ar",
            "status": "PENDING",
            "blocks_acceptance": True,
            "human_listening_review_required": True,
        }
        recovery = production_record.get("recovery")
        if not isinstance(recovery, dict):
            recovery = {}
        recovery["audio_alignment_rebuilt"] = True
        recovery["provider_retried_for_audio_alignment"] = False
        production_record["recovery"] = recovery
        write_json_atomic(
            production_record_path,
            production_record,
            sort_keys=True,
        )
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
