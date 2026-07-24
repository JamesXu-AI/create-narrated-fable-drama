"""Probe generated media and execute authorized white-model quality resets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.segment import (
    WHITE_MODEL_RESET_CONTRACT_RELATIVE,
    sha256_file,
)
from narrated_fable_drama.media.ffmpeg import (
    MediaCommandError,
    require_binary,
    run as run_media_command,
)
from narrated_fable_drama.media.probe import probe_json
from narrated_fable_drama.providers import runtime as provider_runtime
from narrated_fable_drama.providers import seedance
from .common import (
    DEPARTMENT_DIRNAME,
    MAX_PROVIDER_ATTEMPTS,
    PENDING_DIRNAME,
    REPOSITORY_ROOT,
    SegmentGenerationError,
    read_json,
    write_json,
)
from .provider_tasks import (
    provider_task_id,
    wait_for_task,
)


def _probe_media(
    path: Path, *, timeout: int = 60, require_audio: bool = True
) -> dict[str, Any]:
    try:
        payload = probe_json(path, timeout=timeout)
        duration = float((payload.get("format") or {}).get("duration"))
    except (MediaCommandError, TypeError, ValueError) as exc:
        raise SegmentGenerationError(f"Could not probe generated media {path}: {exc}") from exc
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    result = {
        "duration_seconds": duration,
        "has_video_stream": any(
            isinstance(stream, dict) and stream.get("codec_type") == "video"
            for stream in streams
        ),
        "has_audio_stream": any(
            isinstance(stream, dict) and stream.get("codec_type") == "audio"
            for stream in streams
        ),
        "streams": streams,
    }
    if not result["has_video_stream"] or (
        require_audio and not result["has_audio_stream"]
    ):
        raise SegmentGenerationError(
            "Generated media lacks its required video/audio streams: " + str(path)
        )
    return result


def _white_model_reset_contract() -> tuple[Path, dict[str, Any]]:
    path = REPOSITORY_ROOT / WHITE_MODEL_RESET_CONTRACT_RELATIVE
    value = read_json(path)
    required = {
        "contract": "seedance-white-model-quality-reset-v1",
        "operation": "video_edit",
        "strategy": "white_model_video_edit",
        "duration": -1,
        "generate_audio": True,
        "watermark": False,
        "return_last_frame": False,
        "preserve_source_audio_by_remux": True,
    }
    if any(value.get(key) != expected for key, expected in required.items()):
        raise SegmentGenerationError("White-model quality-reset contract is invalid")
    prompt = value.get("prompt_zh")
    if not isinstance(prompt, str) or "严格编辑 @Video1" not in prompt or "白模" not in prompt:
        raise SegmentGenerationError(
            "White-model quality-reset contract lacks its strict edit Prompt"
        )
    return path, value


def _remux_source_audio(
    *, white_model_video: Path, source_video: Path, output_video: Path
) -> None:
    try:
        run_media_command(
            [
            require_binary("ffmpeg"),
            "-y",
            "-i",
            str(white_model_video),
            "-i",
            str(source_video),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_video),
            ],
            context="White-model source-audio remux",
            timeout=180,
        )
    except MediaCommandError as exc:
        raise SegmentGenerationError(
            "Could not preserve predecessor audio in white-model reset"
        ) from exc
    if not output_video.is_file():
        raise SegmentGenerationError(
            "Could not preserve predecessor audio in white-model reset"
        )


def ensure_white_model_predecessor(
    segment: dict[str, Any],
    *,
    task_dir: Path,
    source_dir: Path,
    source_segment_id: str,
    source_provider_attempt_id: str,
    poll_interval: float,
    wait_timeout: float,
    request_timeout: int,
) -> Path:
    quality_reset = segment["execution_plan"].get("quality_reset")
    if (
        not isinstance(quality_reset, dict)
        or quality_reset.get("required") is not True
        or quality_reset.get("strategy") != "white_model_video_edit"
        or quality_reset.get("source_segment_id") != source_segment_id
    ):
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} lacks an authorized white-model quality reset"
        )
    contract_path, contract = _white_model_reset_contract()
    if quality_reset.get("contract_sha256") != sha256_file(contract_path):
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} white-model quality-reset contract is stale"
        )
    source_video = source_dir / "video.mp4"
    source_probe = _probe_media(source_video)
    source_record = read_json(source_dir / "production-record.json")
    source_url = source_record.get("video_source_url")
    if not isinstance(source_url, str) or not source_url.startswith(("http://", "https://")):
        source_upload = provider_runtime.tos_upload_path(
            source_video, kind="inputs/white-model-quality-reset-source"
        )
        source_url = source_upload["public_url"]
    parameters = segment["seedance_parameters"]
    request = {
        "model": parameters["model"],
        "content": [
            {"type": "text", "text": contract["prompt_zh"]},
            {
                "type": "video_url",
                "video_url": {"url": source_url},
                "role": "reference_video",
            },
        ],
        "resolution": parameters["resolution"],
        "ratio": parameters["ratio"],
        "duration": contract["duration"],
        "generate_audio": contract["generate_audio"],
        "watermark": contract["watermark"],
        "return_last_frame": contract["return_last_frame"],
        "execution_expires_after": parameters["execution_expires_after"],
        "priority": parameters["priority"],
    }
    request_sha256 = hashlib.sha256(
        json.dumps(request, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    reset_root = (
        task_dir
        / PENDING_DIRNAME
        / DEPARTMENT_DIRNAME
        / "white-model-quality-resets"
        / segment["generation_task_id"]
    )
    reset_root.mkdir(parents=True, exist_ok=True)
    expected_identity = {
        "contract": "seedance-white-model-quality-reset-record-v1",
        "segment_id": segment["generation_task_id"],
        "source_segment_id": source_segment_id,
        "source_provider_attempt_id": source_provider_attempt_id,
        "source_video_sha256": sha256_file(source_video),
        "quality_reset_contract_sha256": sha256_file(contract_path),
        "request_sha256": request_sha256,
    }
    failures: list[str] = []
    for attempt_number in range(1, MAX_PROVIDER_ATTEMPTS + 1):
        attempt_dir = reset_root / f"attempt-{attempt_number:04d}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        output_video = attempt_dir / "video.mp4"
        record_path = attempt_dir / "production-record.json"
        if output_video.is_file() and record_path.is_file():
            record = read_json(record_path)
            if all(record.get(key) == value for key, value in expected_identity.items()):
                _probe_media(output_video)
                return output_video
            raise SegmentGenerationError(
                f"{segment['generation_task_id']} cached white-model output is stale"
            )

        failure_path = attempt_dir / "failure-record.json"
        if failure_path.is_file():
            failure = read_json(failure_path)
            failures.append(
                f"attempt {attempt_number}: {failure.get('provider_status', 'failed')}"
            )
            continue
        submission_path = attempt_dir / "submission.json"
        if submission_path.is_file():
            submission = read_json(submission_path)
            if any(
                submission.get(key) != value
                for key, value in expected_identity.items()
            ):
                raise SegmentGenerationError(
                    f"{segment['generation_task_id']} active white-model attempt is stale"
                )
            task_id = submission.get("provider_task_id")
            if not isinstance(task_id, str) or not task_id:
                raise SegmentGenerationError("White-model submission lacks a provider task ID")
        else:
            try:
                response = seedance.create_video_task(request, timeout=request_timeout)
                task_id = provider_task_id(response)
                submission = {
                    "contract": "seedance-white-model-quality-reset-submission-v1",
                    **expected_identity,
                    "provider_task_id": task_id,
                    "attempt_number": attempt_number,
                    "status": str(response.get("status") or "submitted"),
                }
                write_json(submission_path, submission)
            except Exception as exc:
                raise SegmentGenerationError(
                    f"{segment['generation_task_id']} white-model quality reset "
                    f"attempt {attempt_number} create failed: {exc}. Automatic retry "
                    "is disabled; obtain fresh human confirmation."
                ) from exc
        result = wait_for_task(
            task_id,
            segment_id=f"{segment['generation_task_id']}:white-model-reset",
            poll_interval=poll_interval,
            wait_timeout=wait_timeout,
            request_timeout=request_timeout,
        )
        status = str(result.get("status") or "unknown")
        submission = read_json(submission_path)
        submission["status"] = status
        write_json(submission_path, submission)
        if status != "succeeded":
            failures.append(f"attempt {attempt_number}: {status}")
            write_json(
                failure_path,
                {
                    "contract": "seedance-white-model-quality-reset-failure-v1",
                    **expected_identity,
                    "provider_task_id": task_id,
                    "attempt_number": attempt_number,
                    "provider_status": status,
                },
            )
            submission_path.unlink(missing_ok=True)
            raise SegmentGenerationError(
                f"{segment['generation_task_id']} white-model quality reset "
                f"attempt {attempt_number} ended with {status}. Automatic retry is "
                "disabled; obtain fresh human confirmation."
            )
        content = result.get("content")
        video_url = content.get("video_url") if isinstance(content, dict) else None
        if not isinstance(video_url, str) or not video_url:
            write_json(
                failure_path,
                {
                    "contract": "seedance-white-model-quality-reset-failure-v1",
                    **expected_identity,
                    "provider_task_id": task_id,
                    "attempt_number": attempt_number,
                    "provider_status": "missing_video",
                },
            )
            submission_path.unlink(missing_ok=True)
            raise SegmentGenerationError(
                f"{segment['generation_task_id']} white-model quality reset "
                f"attempt {attempt_number} returned no video. Automatic retry is "
                "disabled; obtain fresh human confirmation."
            )
        raw_video = attempt_dir / "white-model-provider.mp4"
        provider_runtime.download_url(video_url, raw_video, timeout=request_timeout)
        _probe_media(raw_video, require_audio=False)
        _remux_source_audio(
            white_model_video=raw_video,
            source_video=source_video,
            output_video=output_video,
        )
        output_probe = _probe_media(output_video)
        if abs(
            float(output_probe["duration_seconds"])
            - float(source_probe["duration_seconds"])
        ) > 0.75:
            raise SegmentGenerationError(
                f"{segment['generation_task_id']} white-model reset changed source duration"
            )
        write_json(
            record_path,
            {
                **expected_identity,
                "status": "GENERATED",
                "provider_task_id": task_id,
                "attempt_number": attempt_number,
                "visual_source": "seedance_white_model_video_edit",
                "audio_source": "remuxed_complete_predecessor",
                "media_probe": output_probe,
            },
        )
        raw_video.unlink(missing_ok=True)
        submission_path.unlink(missing_ok=True)
        return output_video
    raise SegmentGenerationError(
        f"{segment['generation_task_id']} white-model quality reset failed after "
        f"{MAX_PROVIDER_ATTEMPTS} attempts: {'; '.join(failures)}"
    )
