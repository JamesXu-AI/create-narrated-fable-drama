"""Own provider attempt state, resumability, retries, and publication."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from preflight_segment import preflight_segment

from narrated_fable_drama.contracts.segment import sha256_file, sha256_json
from narrated_fable_drama.core.arabic_pronunciation import (
    has_current_arabic_pronunciation_contract,
)
from narrated_fable_drama.dubbing import embed_arabic_segment
from narrated_fable_drama.providers import runtime as provider_runtime
from narrated_fable_drama.providers import seedance

from .common import (
    ACTIVE_ATTEMPT_DIRNAME,
    DEPARTMENT_DIRNAME,
    FAILED_ATTEMPT_RE,
    GENERATION_DIRNAME,
    PENDING_DIRNAME,
    PROVIDER_ATTEMPTS_DIRNAME,
    TERMINAL_STATES,
    SegmentGenerationError,
    announce,
    read_json,
    write_json,
)
from .provider_tasks import (
    provider_task_id,
    wait_for_task,
)
from .requests import request_payload
from .reset import _probe_media


def _archive_failed_attempt(
    *, active_dir: Path, segment_id: str, attempt_number: int
) -> Path:
    if not active_dir.is_dir():
        raise SegmentGenerationError(f"{segment_id} has no active attempt to archive.")
    archive_dir = active_dir.parent / f"attempt-{attempt_number:04d}-failed"
    if archive_dir.exists():
        raise SegmentGenerationError(
            f"{segment_id} failed-attempt archive already exists: {archive_dir.name}"
        )
    (active_dir / "submission.json").unlink(missing_ok=True)
    (active_dir / "production-record.json").unlink(missing_ok=True)
    active_dir.replace(archive_dir)
    return archive_dir


def _next_attempt_number(attempt_parent: Path) -> int:
    attempted = [
        int(match.group(1))
        for path in attempt_parent.iterdir()
        if (match := FAILED_ATTEMPT_RE.fullmatch(path.name))
    ]
    return max(attempted, default=0) + 1


def _load_resumable_attempt(
    segment: dict[str, Any], active_dir: Path, request: dict[str, Any]
) -> dict[str, Any] | None:
    if not active_dir.exists():
        return None
    compact_record_path = active_dir / "production-record.json"
    if compact_record_path.is_file():
        compact_record = read_json(compact_record_path)
        if (
            compact_record.get("status") == "GENERATED"
            and compact_record.get("request_sha256") == sha256_json(request)
            and (active_dir / "video.mp4").is_file()
            and (active_dir / "seedance-source.mp4").is_file()
            and (active_dir / "last-frame.png").is_file()
        ):
            return {
                "generation_task_id": segment["generation_task_id"],
                "provider_task_id": compact_record.get("provider_task_id"),
                "attempt_number": compact_record.get("attempt_number"),
                "status": "succeeded",
            }
    submission_path = active_dir / "submission.json"
    if not submission_path.is_file():
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} active attempt is incomplete."
        )
    submission = read_json(submission_path)
    if submission.get("generation_task_id") != segment["generation_task_id"]:
        raise SegmentGenerationError("Active provider task belongs to another Segment.")
    if (
        submission.get("request_sha256") != sha256_json(request)
        or submission.get("segment_prompt_sha256") != segment["script_sha256"]
        or submission.get("seedance_execution_plan_sha256")
        != segment["execution_plan_sha256"]
    ):
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} active attempt uses stale authority."
        )
    return submission


def _completed_result(
    segment: dict[str, Any], directory: Path, submission: dict[str, Any]
) -> dict[str, Any] | None:
    if submission.get("status") != "succeeded":
        return None
    video_path = directory / "video.mp4"
    seedance_source_path = directory / "seedance-source.mp4"
    record_path = directory / "production-record.json"
    embedding_record_path = directory / "arabic-embedding-record.json"
    last_frame_path = directory / "last-frame.png"
    if (
        not video_path.is_file()
        or not seedance_source_path.is_file()
        or not last_frame_path.is_file()
        or not record_path.is_file()
        or not embedding_record_path.is_file()
    ):
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} succeeded attempt lacks dubbed video, "
            "Seedance source video, final frame, production record, or Arabic "
            "embedding record."
        )
    record = read_json(record_path)
    dubbing = record.get("dubbing")
    embedding_record = read_json(embedding_record_path)
    prompt_audit = record.get("prompt_audit")
    attempt_number = submission.get("attempt_number")
    expected_attempt_id = (
        f"{segment['generation_task_id']}__attempt-{int(attempt_number):04d}"
        if isinstance(attempt_number, int) and attempt_number > 0
        else None
    )
    expected_dubbing_contract = (
        "seedance-original-audio-dialogue-replacement/v2"
    )
    expected_alignment_method = (
        "seedance_detected_or_storyboard_window_natural_phrase_atempo"
    )
    cleaned_background_gate = (
        dubbing.get("seedance_clean_background_speech_gate")
        if isinstance(dubbing, dict)
        else None
    )
    seedance_audio_edit = (
        dubbing.get("seedance_audio_edit")
        if isinstance(dubbing, dict)
        else None
    )
    if (
        record.get("status") != "GENERATED"
        or record.get("segment_id") != segment["generation_task_id"]
        or record.get("provider_attempt_id") != expected_attempt_id
        or record.get("segment_prompt_sha256") != segment["script_sha256"]
        or record.get("seedance_execution_plan_sha256")
        != segment["execution_plan_sha256"]
        or record.get("operation") != segment["operation"]
        or not isinstance(prompt_audit, dict)
        or prompt_audit.get("contract")
        != "seedance-prompt-internal-audit/v3"
        or prompt_audit.get("status") != "PASS"
        or prompt_audit.get("prompt_sha256") != segment["script_sha256"]
        or record.get("quality_reset")
        != segment["execution_plan"].get("quality_reset")
        or record.get("seedance_source_path") != "seedance-source.mp4"
        or record.get("seedance_source_bytes") != seedance_source_path.stat().st_size
        or record.get("seedance_source_sha256") != sha256_file(seedance_source_path)
        or not isinstance(dubbing, dict)
        or not has_current_arabic_pronunciation_contract(dubbing)
        or embedding_record != dubbing
        or dubbing.get("contract") != expected_dubbing_contract
        or dubbing.get("alignment_method") != expected_alignment_method
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
        or dubbing.get("seedance_speech_forbidden") is not True
        or dubbing.get("seedance_speech_in_delivery") is not False
        or not isinstance(cleaned_background_gate, dict)
        or cleaned_background_gate.get("status") != "PASS"
        or not isinstance(seedance_audio_edit, dict)
        or seedance_audio_edit.get("status") not in {"APPLIED", "NOT_REQUIRED"}
        or dubbing.get("picture_frames_retimed") is not False
        or (directory / "seedance-picture.mp4").exists()
    ):
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} production record is invalid."
        )
    return {
        "segment_id": segment["generation_task_id"],
        "provider_task_id": submission["provider_task_id"],
        "status": "succeeded",
        "video_path": str(video_path.resolve()),
        "seedance_source_path": str(seedance_source_path.resolve()),
        "last_frame_path": str(last_frame_path.resolve()),
        "provider_attempt_id": expected_attempt_id,
        "segment_prompt_sha256": segment["script_sha256"],
        "seedance_execution_plan_sha256": segment["execution_plan_sha256"],
        "operation": segment["operation"],
        "quality_reset": segment["execution_plan"].get("quality_reset"),
    }


def _finish_picture_generated_attempt(
    segment: dict[str, Any],
    *,
    task_dir: Path,
    directory: Path,
    submission: dict[str, Any],
    request_timeout: int,
) -> dict[str, Any]:
    """Build Arabic audio without hiding the already usable Seedance picture."""

    segment_id = segment["generation_task_id"]
    record_path = directory / "production-record.json"
    record = read_json(record_path)
    if (
        record.get("status") != "PICTURE_GENERATED"
        or record.get("segment_id") != segment_id
        or record.get("request_sha256") != submission.get("request_sha256")
        or not (directory / "seedance-source.mp4").is_file()
        or not (directory / "last-frame.png").is_file()
    ):
        raise SegmentGenerationError(
            f"{segment_id} picture-ready attempt is incomplete or stale."
        )
    video_path = directory / "video.mp4"
    embedding_path = directory / "arabic-embedding-record.json"
    try:
        dubbing_record = embed_arabic_segment(
            task_dir=task_dir,
            segment_id=segment_id,
            seedance_background_video=directory / "seedance-source.mp4",
            output_video=video_path,
            request_timeout=request_timeout,
        )
        write_json(embedding_path, dubbing_record)
        media_probe = _probe_media(
            video_path,
            timeout=min(request_timeout, 60),
            require_audio=True,
        )
    except Exception as exc:
        video_path.unlink(missing_ok=True)
        embedding_path.unlink(missing_ok=True)
        raise SegmentGenerationError(
            f"{segment_id} Arabic audio build failed while its Seedance picture "
            f"remains reusable: {exc}"
        ) from exc
    record.update(
        {
            "video_path": "video.mp4",
            "video_bytes": video_path.stat().st_size,
            "media_probe": media_probe,
            "dubbing": dubbing_record,
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
    )
    write_json(record_path, record)
    (directory / "submission.json").unlink(missing_ok=True)
    completed = _completed_result(segment, directory, submission)
    if completed is None:
        raise SegmentGenerationError(
            f"{segment_id} Arabic audio build did not complete publication."
        )
    completed.update(
        {
            "seedance_audio_mode": segment["audio_policy"][
                "seedance_audio_mode"
            ],
            "dialogue_source": segment["audio_policy"]["dialogue_source"],
        }
    )
    announce(
        f"DOWNLOADED {segment_id} task={submission['provider_task_id']} "
        f"bytes={video_path.stat().st_size}"
    )
    return completed


def generate_one(
    segment: dict[str, Any],
    *,
    task_dir: Path,
    resolution: str,
    ratio: str,
    poll_interval: float,
    wait_timeout: float,
    request_timeout: int,
    predecessor_observations: dict[str, str] | None = None,
) -> dict[str, Any]:
    segment_id = segment["generation_task_id"]
    published_dir = (
        task_dir
        / PENDING_DIRNAME
        / DEPARTMENT_DIRNAME
        / GENERATION_DIRNAME
        / segment_id
    )
    if (published_dir / "production-record.json").is_file():
        published_record = read_json(published_dir / "production-record.json")
        if published_record.get("status") == "PICTURE_GENERATED":
            submission_path = published_dir / "submission.json"
            if not submission_path.is_file():
                raise SegmentGenerationError(
                    f"{segment_id} picture-ready attempt lacks submission identity."
                )
            submission = read_json(submission_path)
            if (
                submission.get("status") != "succeeded"
                or submission.get("generation_task_id") != segment_id
                or submission.get("segment_prompt_sha256")
                != segment["script_sha256"]
                or submission.get("seedance_execution_plan_sha256")
                != segment["execution_plan_sha256"]
                or published_record.get("request_sha256")
                != submission.get("request_sha256")
            ):
                raise SegmentGenerationError(
                    f"{segment_id} picture-ready attempt uses stale authority."
                )
            announce(
                f"RESUME_AUDIO {segment_id} "
                f"task={submission.get('provider_task_id')}"
            )
            return _finish_picture_generated_attempt(
                segment,
                task_dir=task_dir,
                directory=published_dir,
                submission=submission,
                request_timeout=request_timeout,
            )
    preflight_segment(
        task_dir=task_dir,
        segment_script_path=segment["script_path"],
        predecessor_observations=predecessor_observations,
    )
    request = request_payload(
        segment,
        task_dir=task_dir,
        resolution=resolution,
        ratio=ratio,
        poll_interval=poll_interval,
        wait_timeout=wait_timeout,
        request_timeout=request_timeout,
    )
    if published_dir.is_dir():
        submission = _load_resumable_attempt(segment, published_dir, request)
        if submission is None:
            raise SegmentGenerationError(
                f"{segment_id} published directory is incomplete."
            )
        completed = _completed_result(segment, published_dir, submission)
        if completed is None:
            raise SegmentGenerationError(
                f"{segment_id} published directory is not successful."
            )
        announce(f"SKIP {segment_id} generated video already exists")
        return completed

    attempt_parent = (
        task_dir
        / PENDING_DIRNAME
        / DEPARTMENT_DIRNAME
        / PROVIDER_ATTEMPTS_DIRNAME
        / segment_id
    )
    attempt_parent.mkdir(parents=True, exist_ok=True)
    active_dir = attempt_parent / ACTIVE_ATTEMPT_DIRNAME
    attempt_number = _next_attempt_number(attempt_parent)
    submission = _load_resumable_attempt(segment, active_dir, request)
    if submission is not None:
        status = str(submission.get("status") or "")
        if status == "succeeded":
            try:
                completed = _completed_result(segment, active_dir, submission)
            except SegmentGenerationError as exc:
                current_attempt = int(
                    submission.get("attempt_number") or attempt_number
                )
                _archive_failed_attempt(
                    active_dir=active_dir,
                    segment_id=segment_id,
                    attempt_number=current_attempt,
                )
                raise SegmentGenerationError(
                    f"{segment_id} provider attempt {current_attempt} produced an "
                    f"unusable result: {exc}. Automatic retry is disabled; obtain "
                    "fresh human confirmation."
                ) from exc
            if completed is None:
                raise SegmentGenerationError(
                    f"{segment_id} succeeded attempt is incomplete."
                )
            published_dir.parent.mkdir(parents=True, exist_ok=True)
            active_dir.replace(published_dir)
            completed["video_path"] = str((published_dir / "video.mp4").resolve())
            completed["last_frame_path"] = str(
                (published_dir / "last-frame.png").resolve()
            )
            return completed
        if status in TERMINAL_STATES:
            current_attempt = int(submission.get("attempt_number") or attempt_number)
            _archive_failed_attempt(
                active_dir=active_dir,
                segment_id=segment_id,
                attempt_number=current_attempt,
            )
            attempt_number = _next_attempt_number(attempt_parent)
            submission = None
        else:
            task_id = str(submission.get("provider_task_id") or "")
            if not task_id:
                raise SegmentGenerationError(
                    f"{segment_id} active attempt has no provider task ID."
                )
            announce(f"RESUME {segment_id} task={task_id}")
    if submission is None:
        active_dir.mkdir(parents=False, exist_ok=False)
        try:
            response = seedance.create_video_task(request, timeout=request_timeout)
            task_id = provider_task_id(response)
        except Exception as exc:
            _archive_failed_attempt(
                active_dir=active_dir,
                segment_id=segment_id,
                attempt_number=attempt_number,
            )
            raise SegmentGenerationError(
                f"{segment_id} provider attempt {attempt_number} create failed: "
                f"{exc}. Automatic retry is disabled; obtain fresh human confirmation."
            ) from exc
        submission = {
            "contract": "seedance-submission",
            "generation_task_id": segment_id,
            "provider_task_id": task_id,
            "attempt_number": attempt_number,
            "status": str(response.get("status") or "submitted"),
            "segment_prompt_sha256": segment["script_sha256"],
            "seedance_execution_plan_sha256": segment[
                "execution_plan_sha256"
            ],
            "request_sha256": sha256_json(request),
            "generate_audio": segment["seedance_parameters"]["generate_audio"],
            "seedance_audio_mode": segment["audio_policy"]["seedance_audio_mode"],
            "dialogue_source": segment["audio_policy"]["dialogue_source"],
        }
        write_json(active_dir / "submission.json", submission)
        announce(f"SUBMITTED {segment_id} task={task_id}")

    result = wait_for_task(
        task_id,
        segment_id=segment_id,
        poll_interval=poll_interval,
        wait_timeout=wait_timeout,
        request_timeout=request_timeout,
    )
    status = str(result.get("status") or "unknown")
    submission = read_json(active_dir / "submission.json")
    submission["status"] = status
    write_json(active_dir / "submission.json", submission)
    if status != "succeeded":
        current_attempt = int(submission["attempt_number"])
        _archive_failed_attempt(
            active_dir=active_dir,
            segment_id=segment_id,
            attempt_number=current_attempt,
        )
        raise SegmentGenerationError(
            f"{segment_id} provider attempt {current_attempt} ended with {status}. "
            "Automatic retry is disabled; obtain fresh human confirmation."
        )

    try:
        content = result.get("content")
        video_url = content.get("video_url") if isinstance(content, dict) else None
        last_frame_url = (
            content.get("last_frame_url") if isinstance(content, dict) else None
        )
        if not isinstance(video_url, str) or not video_url:
            raise SegmentGenerationError(
                f"{segment_id} provider returned no video URL."
            )
        if not isinstance(last_frame_url, str) or not last_frame_url:
            raise SegmentGenerationError(
                f"{segment_id} provider returned no final frame despite "
                "return_last_frame=true."
            )
        background_video_path = active_dir / "seedance-source.mp4"
        provider_runtime.download_url(
            video_url,
            background_video_path,
            timeout=request_timeout,
        )
        last_frame_path = active_dir / "last-frame.png"
        provider_runtime.download_url(
            last_frame_url, last_frame_path, timeout=request_timeout
        )
        if (
            not background_video_path.is_file()
            or background_video_path.stat().st_size <= 0
        ):
            raise SegmentGenerationError(
                f"Downloaded video is empty: {background_video_path}"
            )
        if not last_frame_path.is_file() or last_frame_path.stat().st_size <= 0:
            raise SegmentGenerationError(
                f"Downloaded final frame is empty: {last_frame_path}"
            )
        seedance_background_media_probe = _probe_media(
            background_video_path,
            timeout=min(request_timeout, 60),
            require_audio=True,
        )
    except Exception as exc:
        current_attempt = int(submission["attempt_number"])
        _archive_failed_attempt(
            active_dir=active_dir,
            segment_id=segment_id,
            attempt_number=current_attempt,
        )
        raise SegmentGenerationError(
            f"{segment_id} provider attempt {current_attempt} could not produce a "
            f"usable local video: {exc}. Automatic retry is disabled; obtain fresh "
            "human confirmation."
        ) from exc

    attempt_number = int(submission["attempt_number"])
    provider_attempt_id = f"{segment_id}__attempt-{attempt_number:04d}"
    write_json(
        active_dir / "production-record.json",
        {
            "contract": "generated-segment-production-record",
            "segment_id": segment_id,
            "provider_task_id": task_id,
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
            "seedance_source_bytes": background_video_path.stat().st_size,
            "seedance_source_sha256": sha256_file(background_video_path),
            "last_frame_path": "last-frame.png",
            "last_frame_source_url": provider_runtime.persistent_tos_url(
                last_frame_url
            ),
            "last_frame_bytes": last_frame_path.stat().st_size,
            "seedance_background_media_probe": seedance_background_media_probe,
            "generate_audio": segment["seedance_parameters"]["generate_audio"],
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
            "status": "PICTURE_GENERATED",
        },
    )
    published_dir.parent.mkdir(parents=True, exist_ok=True)
    active_dir.replace(published_dir)
    announce(
        f"PICTURE_READY {segment_id} task={task_id} "
        f"bytes={(published_dir / 'seedance-source.mp4').stat().st_size}"
    )
    return _finish_picture_generated_attempt(
        segment,
        task_dir=task_dir,
        directory=published_dir,
        submission=submission,
        request_timeout=request_timeout,
    )
