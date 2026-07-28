#!/usr/bin/env python3
"""Publish a succeeded Seedance task after its ElevenLabs audio build passes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generation.attempts import _completed_result
from generation.common import SegmentGenerationError, read_json, write_json
from generation.requests import discover_segments, request_payload
from generation.reset import _probe_media

from narrated_fable_drama.contracts.segment import sha256_file, sha256_json
from narrated_fable_drama.core.arabic_pronunciation import (
    has_current_arabic_pronunciation_contract,
)
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.core.project_domain import SPEECH_AUDIO_SOURCE
from narrated_fable_drama.dubbing import embed_arabic_segment
from narrated_fable_drama.providers import runtime as provider_runtime
from narrated_fable_drama.providers import seedance


def recover(
    *,
    task_dir: Path,
    segment_id: str,
    provider_task_id: str,
    attempt_number: int,
    request_timeout: int,
) -> dict[str, object]:
    task_root = task_dir.expanduser().resolve(strict=True)
    if attempt_number < 1:
        raise SegmentGenerationError("Attempt number must be positive.")
    segments = discover_segments(task_root, segment_ids=[segment_id])
    if len(segments) != 1:
        raise SegmentGenerationError(f"Unknown Segment: {segment_id}")
    segment = segments[0]
    project = load_project_context(task_root)
    request = request_payload(
        segment,
        task_dir=task_root,
        resolution=str(project["resolution"]),
        ratio=str(project["aspect_ratio"]),
        request_timeout=request_timeout,
    )
    result = seedance.get_video_task(
        provider_task_id,
        timeout=request_timeout,
    )
    if (
        result.get("status") != "succeeded"
        or result.get("id") != provider_task_id
        or result.get("model") != request.get("model")
        or result.get("duration") != request.get("duration")
        or result.get("resolution") != request.get("resolution")
        or result.get("ratio") != request.get("ratio")
        or result.get("generate_audio") != request.get("generate_audio")
    ):
        raise SegmentGenerationError(
            f"{segment_id} provider task is not the succeeded authored request."
        )
    content = result.get("content")
    video_url = content.get("video_url") if isinstance(content, dict) else None
    last_frame_url = (
        content.get("last_frame_url") if isinstance(content, dict) else None
    )
    if not isinstance(video_url, str) or not isinstance(last_frame_url, str):
        raise SegmentGenerationError(
            f"{segment_id} provider task lacks video or final-frame URLs."
        )

    attempt_dir = (
        task_root
        / ".pending"
        / "virtual-production"
        / "provider-attempts"
        / segment_id
        / f"attempt-{attempt_number:04d}-failed"
    )
    published_dir = (
        task_root
        / ".pending"
        / "virtual-production"
        / "generation-segments"
        / segment_id
    )
    if published_dir.exists():
        raise SegmentGenerationError(
            f"{segment_id} already has a published generation directory."
        )
    picture_path = attempt_dir / "seedance-source.mp4"
    video_path = attempt_dir / "video.mp4"
    last_frame_path = attempt_dir / "last-frame.png"
    embedding_path = attempt_dir / "arabic-embedding-record.json"
    for path in (picture_path, last_frame_path):
        if not path.is_file() or path.stat().st_size <= 0:
            raise SegmentGenerationError(
                f"{segment_id} recovery input is missing: {path.name}"
            )
    picture_probe = _probe_media(
        picture_path,
        timeout=min(request_timeout, 60),
        require_audio=True,
    )
    if (
        video_path.is_file()
        and video_path.stat().st_size > 0
        and embedding_path.is_file()
        and embedding_path.stat().st_size > 0
    ):
        dubbing = read_json(embedding_path)
    else:
        dubbing = embed_arabic_segment(
            task_dir=task_root,
            segment_id=segment_id,
            seedance_background_video=picture_path,
            output_video=video_path,
            request_timeout=request_timeout,
        )
        write_json(embedding_path, dubbing)
    expected_contract = "seedance-original-audio-dialogue-replacement/v2"
    cleaned_gate = dubbing.get("seedance_clean_background_speech_gate")
    audio_edit = dubbing.get("seedance_audio_edit")
    if (
        dubbing.get("contract") != expected_contract
        or not has_current_arabic_pronunciation_contract(dubbing)
        or dubbing.get("language") != "Arabic"
        or dubbing.get("language_code") != "ar"
        or dubbing.get("speech_audio_source") != SPEECH_AUDIO_SOURCE
        or dubbing.get("sound_effects_audio_source")
        != "seedance_native"
        or dubbing.get("native_audio_full_duration") is not True
        or dubbing.get("elevenlabs_usage_scope") != "arabic_dialogue_only"
        or dubbing.get("elevenlabs_non_dialogue_request_count") != 0
        or dubbing.get("dialogue_gap_fill_source")
        not in {
            "digital_silence",
            "not_required",
        }
        or dubbing.get("seedance_generate_audio") is not True
        or dubbing.get("seedance_audio_in_delivery") is not True
        or dubbing.get("seedance_background_audio_retained") is not True
        or not isinstance(cleaned_gate, dict)
        or cleaned_gate.get("status") != "PASS"
        or not isinstance(audio_edit, dict)
        or audio_edit.get("status") not in {"APPLIED", "NOT_REQUIRED"}
    ):
        raise SegmentGenerationError(
            f"{segment_id} recovery requires a valid Seedance-native plus "
            "ElevenLabs-dialogue audio build record."
        )
    media_probe = _probe_media(
        video_path,
        timeout=min(request_timeout, 60),
        require_audio=True,
    )
    provider_attempt_id = (
        f"{segment_id}__attempt-{attempt_number:04d}"
    )
    record = {
        "contract": "generated-segment-production-record",
        "segment_id": segment_id,
        "provider_task_id": provider_task_id,
        "provider_attempt_id": provider_attempt_id,
        "segment_prompt_sha256": segment["script_sha256"],
        "seedance_execution_plan_sha256": segment[
            "execution_plan_sha256"
        ],
        "operation": segment["operation"],
        "quality_reset": segment["execution_plan"].get("quality_reset"),
        "attempt_number": attempt_number,
        "submission_revision": attempt_number,
        "request_sha256": sha256_json(request),
        "submitted_prompt": segment["prompt"],
        "prompt_audit": segment["prompt_audit"],
        "video_path": "video.mp4",
        "video_source_url": provider_runtime.persistent_tos_url(video_url),
        "video_bytes": video_path.stat().st_size,
        "seedance_source_path": "seedance-source.mp4",
        "seedance_source_bytes": picture_path.stat().st_size,
        "seedance_source_sha256": sha256_file(picture_path),
        "last_frame_path": "last-frame.png",
        "last_frame_source_url": provider_runtime.persistent_tos_url(
            last_frame_url
        ),
        "last_frame_bytes": last_frame_path.stat().st_size,
        "media_probe": media_probe,
        "seedance_background_media_probe": picture_probe,
        "dubbing": dubbing,
        "generate_audio": segment["seedance_parameters"]["generate_audio"],
        "seedance_audio_mode": segment["audio_policy"][
            "seedance_audio_mode"
        ],
        "dialogue_source": segment["audio_policy"]["dialogue_source"],
        "voice_identity_gate": {
            "contract": "video-review-voice-identity-gate/v2",
            "segment_id": segment_id,
            "language": "Arabic",
            "language_code": "ar",
            "status": "PENDING",
            "blocks_acceptance": True,
            "human_listening_review_required": True,
        },
        "status": "GENERATED",
    }
    record_path = attempt_dir / "production-record.json"
    write_json(record_path, record)
    submission = {
        "provider_task_id": provider_task_id,
        "attempt_number": attempt_number,
        "status": "succeeded",
    }
    try:
        completed = _completed_result(segment, attempt_dir, submission)
        if completed is None:
            raise SegmentGenerationError(
                f"{segment_id} recovered result did not complete validation."
            )
        published_dir.parent.mkdir(parents=True, exist_ok=True)
        attempt_dir.replace(published_dir)
    except Exception:
        record_path.unlink(missing_ok=True)
        raise
    return {
        **completed,
        "video_path": str((published_dir / "video.mp4").resolve()),
        "seedance_source_path": str(
            (published_dir / "seedance-source.mp4").resolve()
        ),
        "last_frame_path": str((published_dir / "last-frame.png").resolve()),
        "recovered_existing_provider_task": True,
        "provider_resubmitted": False,
        "audio_only_recovery": True,
        "arabic_embedding_record": str(
            (published_dir / "arabic-embedding-record.json").resolve()
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--segment", required=True)
    parser.add_argument("--provider-task-id", required=True)
    parser.add_argument("--attempt-number", type=int, required=True)
    parser.add_argument("--request-timeout", type=int, default=120)
    args = parser.parse_args()
    try:
        result = recover(
            task_dir=args.task_dir,
            segment_id=args.segment,
            provider_task_id=args.provider_task_id,
            attempt_number=args.attempt_number,
            request_timeout=args.request_timeout,
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
