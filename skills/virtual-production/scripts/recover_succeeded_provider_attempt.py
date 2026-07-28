#!/usr/bin/env python3
"""Publish one succeeded Seedance attempt whose local dubbing initially failed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from generation.common import write_json  # noqa: E402
from generation.requests import discover_segments, request_payload  # noqa: E402
from generation.reset import _probe_media  # noqa: E402

from narrated_fable_drama.contracts.segment import (  # noqa: E402
    sha256_file,
    sha256_json,
)
from narrated_fable_drama.core.arabic_pronunciation import (  # noqa: E402
    has_current_arabic_pronunciation_contract,
)
from narrated_fable_drama.providers import runtime as provider_runtime  # noqa: E402
from narrated_fable_drama.providers import seedance  # noqa: E402


def recover(
    *,
    task_dir: Path,
    segment_id: str,
    failed_attempt_dir: Path,
    provider_task_id: str,
    attempt_number: int,
    request_timeout: int,
) -> dict[str, object]:
    task_root = task_dir.expanduser().resolve(strict=True)
    attempt_dir = failed_attempt_dir.expanduser().resolve(strict=True)
    segment = discover_segments(task_root, segment_ids=[segment_id])[0]
    parameters = segment["seedance_parameters"]
    request = request_payload(
        segment,
        task_dir=task_root,
        resolution=str(parameters["resolution"]),
        ratio=str(parameters["ratio"]),
        request_timeout=request_timeout,
    )
    provider_result = seedance.get_video_task(
        provider_task_id,
        timeout=request_timeout,
    )
    if provider_result.get("status") != "succeeded":
        raise RuntimeError("The referenced Seedance provider task is not succeeded")
    if (
        provider_result.get("duration") != segment["duration"]
        or provider_result.get("resolution") != parameters["resolution"]
        or provider_result.get("ratio") != parameters["ratio"]
        or provider_result.get("generate_audio") is not True
    ):
        raise RuntimeError(
            "The provider result differs from the current Segment contract"
        )
    content = provider_result.get("content")
    video_url = content.get("video_url") if isinstance(content, dict) else None
    last_frame_url = (
        content.get("last_frame_url") if isinstance(content, dict) else None
    )
    if not isinstance(video_url, str) or not isinstance(last_frame_url, str):
        raise RuntimeError("The succeeded provider task lacks output URLs")

    seedance_source = attempt_dir / "seedance-source.mp4"
    video_path = attempt_dir / "video.mp4"
    last_frame_path = attempt_dir / "last-frame.png"
    embedding_path = attempt_dir / "arabic-embedding-record.json"
    for path in (seedance_source, last_frame_path):
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"Recovery input is missing or empty: {path}")
    background_probe = _probe_media(
        seedance_source,
        timeout=min(request_timeout, 60),
        require_audio=True,
    )
    has_video = video_path.is_file() and video_path.stat().st_size > 0
    has_embedding = (
        embedding_path.is_file() and embedding_path.stat().st_size > 0
    )
    if has_video != has_embedding:
        raise RuntimeError(
            "Recovery has only one of dubbed video and Arabic embedding record"
        )
    final_probe = None
    dubbing = None
    if has_video:
        final_probe = _probe_media(
            video_path,
            timeout=min(request_timeout, 60),
            require_audio=True,
        )
        dubbing = json.loads(embedding_path.read_text(encoding="utf-8"))
        if (
            dubbing.get("contract")
            != "seedance-original-audio-dialogue-replacement/v2"
            or not has_current_arabic_pronunciation_contract(dubbing)
            or dubbing.get(
                "seedance_clean_background_speech_gate", {}
            ).get("status")
            != "PASS"
            or dubbing.get("seedance_speech_in_delivery") is not False
        ):
            raise RuntimeError("Arabic embedding record is incomplete or failed")

    provider_attempt_id = f"{segment_id}__attempt-{attempt_number:04d}"
    record = {
        "contract": "generated-segment-production-record",
        "segment_id": segment_id,
        "provider_task_id": provider_task_id,
        "provider_attempt_id": provider_attempt_id,
        "segment_prompt_sha256": segment["script_sha256"],
        "seedance_execution_plan_sha256": segment["execution_plan_sha256"],
        "operation": segment["operation"],
        "quality_reset": segment["execution_plan"].get("quality_reset"),
        "attempt_number": attempt_number,
        "submission_revision": attempt_number,
        "request_sha256": sha256_json(request),
        "submitted_prompt": segment["prompt"],
        "prompt_audit": segment["prompt_audit"],
        "video_source_url": provider_runtime.persistent_tos_url(video_url),
        "seedance_source_path": "seedance-source.mp4",
        "seedance_source_bytes": seedance_source.stat().st_size,
        "seedance_source_sha256": sha256_file(seedance_source),
        "last_frame_path": "last-frame.png",
        "last_frame_source_url": provider_runtime.persistent_tos_url(last_frame_url),
        "last_frame_bytes": last_frame_path.stat().st_size,
        "seedance_background_media_probe": background_probe,
        "generate_audio": True,
        "seedance_audio_mode": segment["audio_policy"]["seedance_audio_mode"],
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
        "recovery": {
            "reason": "provider_succeeded_local_dubbing_configuration_failed",
            "provider_retried": False,
            "source_attempt_directory": attempt_dir.name,
        },
        "status": "GENERATED" if has_video else "PICTURE_GENERATED",
    }
    if has_video:
        record.update(
            {
                "video_path": "video.mp4",
                "video_bytes": video_path.stat().st_size,
                "media_probe": final_probe,
                "dubbing": dubbing,
            }
        )
    write_json(attempt_dir / "production-record.json", record)
    if not has_video:
        write_json(
            attempt_dir / "submission.json",
            {
                "contract": "seedance-submission",
                "generation_task_id": segment_id,
                "provider_task_id": provider_task_id,
                "attempt_number": attempt_number,
                "status": "succeeded",
                "segment_prompt_sha256": segment["script_sha256"],
                "seedance_execution_plan_sha256": segment[
                    "execution_plan_sha256"
                ],
                "request_sha256": sha256_json(request),
                "generate_audio": True,
                "seedance_audio_mode": segment["audio_policy"][
                    "seedance_audio_mode"
                ],
                "dialogue_source": segment["audio_policy"]["dialogue_source"],
            },
        )

    published = (
        task_root
        / ".pending"
        / "virtual-production"
        / "generation-segments"
        / segment_id
    )
    if published.exists():
        raise RuntimeError(f"Published Segment already exists: {published}")
    published.parent.mkdir(parents=True, exist_ok=True)
    attempt_dir.replace(published)
    return {
        "status": "PASS",
        "segment_id": segment_id,
        "provider_task_id": provider_task_id,
        "provider_attempt_id": provider_attempt_id,
        "provider_retried": False,
        "publication_status": record["status"],
        "video_path": (
            str((published / "video.mp4").resolve()) if has_video else None
        ),
        "seedance_source_path": str(
            (published / "seedance-source.mp4").resolve()
        ),
        "production_record": str((published / "production-record.json").resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--segment-id", required=True)
    parser.add_argument("--failed-attempt-dir", required=True, type=Path)
    parser.add_argument("--provider-task-id", required=True)
    parser.add_argument("--attempt-number", required=True, type=int)
    parser.add_argument("--request-timeout", type=int, default=300)
    args = parser.parse_args()
    try:
        result = recover(
            task_dir=args.task_dir,
            segment_id=args.segment_id,
            failed_attempt_dir=args.failed_attempt_dir,
            provider_task_id=args.provider_task_id,
            attempt_number=args.attempt_number,
            request_timeout=args.request_timeout,
        )
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
