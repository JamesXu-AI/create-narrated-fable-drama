#!/usr/bin/env python3
"""Generate audiovisual clips from repository-authored Seedance Segment Prompts."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = REPOSITORY_ROOT / "virtual-production" / "scripts"
PRODUCTION_DESIGN_SCRIPT_ROOT = REPOSITORY_ROOT / "direct-production-design" / "scripts"
SCREENPLAY_SCRIPT_ROOT = REPOSITORY_ROOT / "screenplay-writer" / "scripts"
for script_root in (SCRIPT_ROOT, PRODUCTION_DESIGN_SCRIPT_ROOT, SCREENPLAY_SCRIPT_ROOT):
    if str(script_root) not in sys.path:
        sys.path.insert(0, str(script_root))

from segment_runtime import (  # noqa: E402
    SCRIPT_DIR_RELATIVE,
    WHITE_MODEL_RESET_CONTRACT_RELATIVE,
    load_execution_plan,
    storyboard_segment_rows,
    parse_segment_script as parse_local_segment_prompt,
    sha256_json,
    sha256_file,
    token_sort_key,
)
from preflight_segment import (  # noqa: E402
    parse_predecessor_observations,
    predecessor_observation_requirement,
    preflight_segment,
)
import seedance  # noqa: E402
from validate_segment_scripts import validate_task as validate_segment_scripts  # noqa: E402
from incremental_boundary_precheck import (  # noqa: E402
    prepare_adjacent_boundary_prechecks,
)


PENDING_DIRNAME = ".pending"
DEPARTMENT_DIRNAME = "virtual-production"
SCRIPTS_DIRNAME = "seedance-segment-scripts"
GENERATION_DIRNAME = "generation-segments"
PROVIDER_ATTEMPTS_DIRNAME = "provider-attempts"
ACTIVE_ATTEMPT_DIRNAME = "active"
EXECUTION_LOCK_FILENAME = "generation.lock"
SCRIPT_RE = re.compile(r"^segment-([0-9]{3,})\.md$")
TERMINAL_STATES = {"succeeded", "failed", "cancelled", "expired"}
MAX_PROVIDER_ATTEMPTS = 3
FAILED_ATTEMPT_RE = re.compile(r"^attempt-([0-9]{4})-failed$")
PRINT_LOCK = threading.Lock()


class SegmentGenerationError(RuntimeError):
    pass


def announce(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SegmentGenerationError(f"Missing or invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise SegmentGenerationError(f"Expected one JSON object: {path}")
    return value


def parse_segment_script(path: Path, *, task_dir: Path | None = None) -> dict[str, Any]:
    path = path.expanduser().resolve()
    task_root = task_dir.expanduser().resolve() if task_dir else path.parents[3]
    parsed = parse_local_segment_prompt(path)
    plan = load_execution_plan(task_root, parsed["segment_id"])
    if plan.get("source_script_sha256") != parsed["script_sha256"]:
        raise SegmentGenerationError(f"{path.name} execution plan is stale")
    media = plan.get("media_bindings")
    if not isinstance(media, list):
        raise SegmentGenerationError(f"{path.name} execution plan has no media bindings")
    static_images = [
        item
        for item in media
        if item.get("source_kind") == "asset_catalog"
        and item.get("provider_role") == "reference_image"
    ]
    static_audio = [
        item
        for item in media
        if item.get("source_kind") == "asset_catalog"
        and item.get("provider_role") == "reference_audio"
    ]
    runtime_media = [item for item in media if item.get("source_kind") != "asset_catalog"]
    shooting = plan["shooting_plan"]
    return {
        "number": parsed["number"],
        "generation_task_id": parsed["segment_id"],
        "duration": parsed["duration"],
        "prompt": parsed["prompt"],
        "script_path": path,
        "script_sha256": parsed["script_sha256"],
        "execution_plan": plan,
        "execution_plan_sha256": sha256_json(plan),
        "references": static_images,
        "audio_references": static_audio,
        "runtime_media": runtime_media,
        "shooting_schedule_mode": shooting["schedule_mode"],
        "planned_wave": shooting["planned_wave"],
        "depends_on_segment_ids": shooting["depends_on_segment_ids"],
        "operation": shooting["operation"],
        "required_predecessor_evidence": shooting["required_predecessor_evidence"],
        "seedance_parameters": plan["seedance_parameters"],
        "audio_policy": plan.get(
            "audio_policy",
            {
                "seedance_audio_mode": "native_sync",
                "dialogue_source": "seedance",
                "silent_mouth_performance": False,
                "native_background_audio": True,
                "seedance_background_music": True,
                "background_music_source": "seedance_native",
            },
        ),
    }


def _task_contract(task_dir: Path) -> dict[str, str]:
    task = read_json(task_dir / "task.json")
    audio_mode = str(task.get("seedance_audio_mode") or "native_sync")
    expected_audio_sources = (
        {
            "voice_audio_source": "speaker_reference_audio",
            "dialogue_source": "seedance",
        }
        if audio_mode == "native_sync"
        else {
            "voice_audio_source": "external_tts",
            "dialogue_source": "external_tts",
        }
        if audio_mode == "background_only"
        else None
    )
    if expected_audio_sources is None:
        raise SegmentGenerationError(
            f"task.json seedance_audio_mode is unsupported: {audio_mode!r}."
        )
    for field, expected in expected_audio_sources.items():
        if task.get(field) != expected:
            raise SegmentGenerationError(f"task.json {field} must be {expected}.")
    task_input = task.get("input")
    if not isinstance(task_input, dict):
        raise SegmentGenerationError("task.json input must be an object.")
    supported_resolutions = {"480p", "720p", "1080p", "4k"}
    resolution = str(task_input.get("resolution") or "").strip().lower()
    ratio = task_input.get("aspect_ratio")
    if resolution not in supported_resolutions:
        raise SegmentGenerationError("task.json input.resolution is unsupported.")
    if ratio not in {"16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"}:
        raise SegmentGenerationError("task.json input.aspect_ratio is unsupported.")
    return {
        "resolution": resolution,
        "ratio": str(ratio),
        "seedance_audio_mode": audio_mode,
        "dialogue_source": str(task["dialogue_source"]),
    }


def discover_segments(
    task_dir: Path, *, segment_ids: list[str] | None = None
) -> list[dict[str, Any]]:
    validate_segment_scripts(task_dir, segment_ids=segment_ids)
    validation_through_segment_id = max(segment_ids) if segment_ids else None
    all_ids = [
        str(item["segment_id"])
        for item in storyboard_segment_rows(
            task_dir,
            validation_through_segment_id=validation_through_segment_id,
        )
    ]
    selected_ids = all_ids if segment_ids is None else segment_ids
    script_dir = task_dir / SCRIPT_DIR_RELATIVE
    paths = [script_dir / f"{segment_id}.md" for segment_id in selected_ids]
    segments = [parse_segment_script(path, task_dir=task_dir) for path in paths]
    if [segment["generation_task_id"] for segment in segments] != selected_ids:
        raise SegmentGenerationError("Seed Master Segment Script order is not authoritative")
    if segment_ids is None and sum(segment["duration"] for segment in segments) > 240:
        raise SegmentGenerationError("Complete Seedance picture exceeds 240 seconds.")
    return segments


def _runtime_reference_media_content(
    segment: dict[str, Any],
    *,
    task_dir: Path,
    poll_interval: float = seedance.DEFAULT_POLL_INTERVAL,
    wait_timeout: float = seedance.DEFAULT_WAIT_TIMEOUT,
    request_timeout: int = seedance.core.DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    bindings = segment["runtime_media"]
    if not bindings:
        return []
    source_ids = {item["source_segment_id"] for item in bindings}
    attempt_ids = {item["source_provider_attempt_id"] for item in bindings}
    if len(source_ids) != 1 or len(attempt_ids) != 1:
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} runtime bindings must use one predecessor attempt"
        )
    source_id = next(iter(source_ids))
    source_attempt_id = next(iter(attempt_ids))
    source_dir = (
        task_dir / PENDING_DIRNAME / DEPARTMENT_DIRNAME / GENERATION_DIRNAME / source_id
    )
    source_record = read_json(source_dir / "production-record.json")
    if (
        source_record.get("status") != "GENERATED"
        or source_record.get("provider_attempt_id") != source_attempt_id
    ):
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} is not locked to the current {source_id} attempt"
        )
    content: list[dict[str, Any]] = []
    for binding in sorted(
        bindings, key=lambda item: token_sort_key(item["provider_token"])
    ):
        source_kind = binding["source_kind"]
        token = binding["provider_token"]
        if source_kind == "provider_last_frame":
            source = source_dir / "last-frame.png"
            provider_type = "image_url"
            url = source_record.get("last_frame_source_url")
        elif source_kind == "complete_predecessor_video":
            source = source_dir / "video.mp4"
            provider_type = "video_url"
            url = source_record.get("video_source_url")
        elif source_kind == "white_model_predecessor_video":
            source = _ensure_white_model_predecessor(
                segment,
                task_dir=task_dir,
                source_dir=source_dir,
                source_segment_id=source_id,
                source_provider_attempt_id=source_attempt_id,
                poll_interval=poll_interval,
                wait_timeout=wait_timeout,
                request_timeout=request_timeout,
            )
            provider_type = "video_url"
            url = None
        else:
            raise SegmentGenerationError(
                f"Unsupported runtime source kind: {source_kind}"
            )
        if not source.is_file():
            raise SegmentGenerationError(f"Missing runtime evidence for {token}")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            url = seedance.core.tos_upload_path(
                source, kind=f"inputs/{source_kind.replace('_', '-')}"
            )["public_url"]
        if provider_type == "image_url":
            payload = {
                "type": "image_url",
                "image_url": {"url": url},
                "role": "reference_image",
            }
        else:
            payload = {
                "type": "video_url",
                "video_url": {"url": url},
                "role": "reference_video",
            }
        payload["_provider_token"] = token
        content.append(payload)
    return content


def request_payload(
    segment: dict[str, Any],
    *,
    task_dir: Path,
    resolution: str,
    ratio: str,
    poll_interval: float = seedance.DEFAULT_POLL_INTERVAL,
    wait_timeout: float = seedance.DEFAULT_WAIT_TIMEOUT,
    request_timeout: int = seedance.core.DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    parameters = segment["seedance_parameters"]
    if parameters["resolution"] != resolution or parameters["ratio"] != ratio:
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} task output settings changed after materialization"
        )
    media_content: list[dict[str, Any]] = []
    media_content.extend(
        {
            "type": "image_url",
            "image_url": {"url": reference["uri"]},
            "role": "reference_image",
            "_provider_token": reference["provider_token"],
        }
        for reference in segment["references"]
    )
    media_content.extend(
        {
            "type": "audio_url",
            "audio_url": {"url": reference["uri"]},
            "role": "reference_audio",
            "_provider_token": reference["provider_token"],
        }
        for reference in segment["audio_references"]
    )
    media_content.extend(
        _runtime_reference_media_content(
            segment,
            task_dir=task_dir,
            poll_interval=poll_interval,
            wait_timeout=wait_timeout,
            request_timeout=request_timeout,
        )
    )
    expected_tokens = [
        item["provider_token"]
        for item in segment["execution_plan"]["media_bindings"]
    ]
    actual_tokens = sorted(
        [item["_provider_token"] for item in media_content], key=token_sort_key
    )
    if actual_tokens != expected_tokens or len(actual_tokens) != len(set(actual_tokens)):
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} runtime media differs from the private plan"
        )
    content: list[dict[str, Any]] = [{"type": "text", "text": segment["prompt"]}]
    for item in sorted(media_content, key=lambda value: token_sort_key(value["_provider_token"])):
        content.append({key: value for key, value in item.items() if key != "_provider_token"})
    return {**parameters, "content": content}


def _probe_media(
    path: Path, *, timeout: int = 60, require_audio: bool = True
) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SegmentGenerationError("ffprobe is required to verify generated media.")
    try:
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        payload = json.loads(completed.stdout)
        duration = float((payload.get("format") or {}).get("duration"))
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
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
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SegmentGenerationError(
            "ffmpeg is required to preserve predecessor audio in a white-model reset"
        )
    completed = subprocess.run(
        [
            ffmpeg,
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
    )
    if completed.returncode != 0 or not output_video.is_file():
        raise SegmentGenerationError(
            "Could not preserve predecessor audio in white-model reset: "
            + completed.stderr[-1200:]
        )


def _ensure_white_model_predecessor(
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
        source_upload = seedance.core.tos_upload_path(
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
                task_id = _provider_task_id(response)
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
        result = _wait_for_task(
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
        seedance.core.download_url(video_url, raw_video, timeout=request_timeout)
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


def _provider_task_id(response: dict[str, Any]) -> str:
    task_id = response.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise SegmentGenerationError("Seedance create response has no task ID.")
    return task_id


def _wait_for_task(
    task_id: str,
    *,
    segment_id: str,
    poll_interval: float,
    wait_timeout: float,
    request_timeout: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + wait_timeout
    while True:
        result = seedance.get_video_task(task_id, timeout=request_timeout)
        status = str(result.get("status") or "unknown")
        announce(f"STATUS {segment_id} task={task_id} status={status}")
        if status in TERMINAL_STATES:
            return result
        if time.monotonic() >= deadline:
            raise SegmentGenerationError(
                f"Timed out waiting for {segment_id} provider task {task_id}."
            )
        time.sleep(poll_interval)


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
    submission_path = active_dir / "submission.json"
    submission = read_json(submission_path) if submission_path.is_file() else {}
    write_json(
        active_dir / "failure-record.json",
        {
            "contract": "seedance-failed-attempt",
            "segment_id": segment_id,
            "attempt_number": attempt_number,
            "provider_task_id": submission.get("provider_task_id"),
            "provider_status": submission.get("status"),
            "request_sha256": submission.get("request_sha256"),
        },
    )
    submission_path.unlink(missing_ok=True)
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
    record_path = directory / "production-record.json"
    last_frame_path = directory / "last-frame.png"
    if not video_path.is_file() or not last_frame_path.is_file() or not record_path.is_file():
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} succeeded attempt lacks video, final frame, or record."
        )
    record = read_json(record_path)
    attempt_number = submission.get("attempt_number")
    expected_attempt_id = (
        f"{segment['generation_task_id']}__attempt-{int(attempt_number):04d}"
        if isinstance(attempt_number, int) and attempt_number > 0
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
        or record.get("quality_reset")
        != segment["execution_plan"].get("quality_reset")
    ):
        raise SegmentGenerationError(
            f"{segment['generation_task_id']} production record is invalid."
        )
    return {
        "segment_id": segment["generation_task_id"],
        "provider_task_id": submission["provider_task_id"],
        "status": "succeeded",
        "video_path": str(video_path.resolve()),
        "last_frame_path": str(last_frame_path.resolve()),
        "provider_attempt_id": expected_attempt_id,
        "segment_prompt_sha256": segment["script_sha256"],
        "seedance_execution_plan_sha256": segment["execution_plan_sha256"],
        "operation": segment["operation"],
        "quality_reset": segment["execution_plan"].get("quality_reset"),
    }


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
        task_dir / PENDING_DIRNAME / DEPARTMENT_DIRNAME / GENERATION_DIRNAME / segment_id
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
            raise SegmentGenerationError(f"{segment_id} published directory is incomplete.")
        completed = _completed_result(segment, published_dir, submission)
        if completed is None:
            raise SegmentGenerationError(f"{segment_id} published directory is not successful.")
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
                raise SegmentGenerationError(f"{segment_id} succeeded attempt is incomplete.")
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
        if not 1 <= attempt_number <= MAX_PROVIDER_ATTEMPTS:
            raise SegmentGenerationError(
                f"{segment_id} reached the maximum of "
                f"{MAX_PROVIDER_ATTEMPTS} human-confirmed attempts."
            )
        active_dir.mkdir(parents=False, exist_ok=False)
        try:
            response = seedance.create_video_task(request, timeout=request_timeout)
            task_id = _provider_task_id(response)
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
            "generate_audio": True,
            "seedance_audio_mode": segment["audio_policy"]["seedance_audio_mode"],
            "dialogue_source": segment["audio_policy"]["dialogue_source"],
        }
        write_json(active_dir / "submission.json", submission)
        announce(f"SUBMITTED {segment_id} task={task_id}")

    result = _wait_for_task(
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
            raise SegmentGenerationError(f"{segment_id} provider returned no video URL.")
        if not isinstance(last_frame_url, str) or not last_frame_url:
            raise SegmentGenerationError(
                f"{segment_id} provider returned no final frame despite "
                "return_last_frame=true."
            )
        video_path = active_dir / "video.mp4"
        seedance.core.download_url(video_url, video_path, timeout=request_timeout)
        last_frame_path = active_dir / "last-frame.png"
        seedance.core.download_url(
            last_frame_url, last_frame_path, timeout=request_timeout
        )
        if not video_path.is_file() or video_path.stat().st_size <= 0:
            raise SegmentGenerationError(f"Downloaded video is empty: {video_path}")
        if not last_frame_path.is_file() or last_frame_path.stat().st_size <= 0:
            raise SegmentGenerationError(
                f"Downloaded final frame is empty: {last_frame_path}"
            )
        media_probe = _probe_media(video_path, timeout=min(request_timeout, 60))
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
            "video_path": "video.mp4",
            "video_source_url": seedance.core.persistent_tos_url(video_url),
            "video_bytes": video_path.stat().st_size,
            "last_frame_path": "last-frame.png",
            "last_frame_source_url": seedance.core.persistent_tos_url(last_frame_url),
            "last_frame_bytes": last_frame_path.stat().st_size,
            "media_probe": media_probe,
            "generate_audio": True,
            "seedance_audio_mode": segment["audio_policy"]["seedance_audio_mode"],
            "dialogue_source": segment["audio_policy"]["dialogue_source"],
            "status": "GENERATED",
        },
    )
    (active_dir / "submission.json").unlink(missing_ok=True)
    published_dir.parent.mkdir(parents=True, exist_ok=True)
    active_dir.replace(published_dir)
    announce(
        f"DOWNLOADED {segment_id} task={task_id} "
        f"bytes={(published_dir / 'video.mp4').stat().st_size}"
    )
    return {
        "segment_id": segment_id,
        "provider_task_id": task_id,
        "status": "succeeded",
        "video_path": str((published_dir / "video.mp4").resolve()),
        "last_frame_path": str((published_dir / "last-frame.png").resolve()),
        "provider_attempt_id": provider_attempt_id,
        "segment_prompt_sha256": segment["script_sha256"],
        "seedance_execution_plan_sha256": segment["execution_plan_sha256"],
        "operation": segment["operation"],
        "quality_reset": segment["execution_plan"].get("quality_reset"),
        "seedance_audio_mode": segment["audio_policy"]["seedance_audio_mode"],
        "dialogue_source": segment["audio_policy"]["dialogue_source"],
    }


def _published_segment_ready(task_dir: Path, segment_id: str) -> bool:
    directory = (
        task_dir / PENDING_DIRNAME / DEPARTMENT_DIRNAME / GENERATION_DIRNAME / segment_id
    )
    record_path = directory / "production-record.json"
    if not record_path.is_file():
        return False
    try:
        record = read_json(record_path)
    except SegmentGenerationError:
        return False
    return (
        record.get("status") == "GENERATED"
        and record.get("segment_id") == segment_id
        and (directory / "video.mp4").is_file()
        and (directory / "last-frame.png").is_file()
    )


def _enforce_human_confirmation(
    *,
    task_dir: Path,
    selected_segment_ids: list[str],
    human_confirmed_segment: str | None,
) -> list[str]:
    new_segment_ids = [
        segment_id
        for segment_id in selected_segment_ids
        if not _published_segment_ready(task_dir, segment_id)
    ]
    if len(new_segment_ids) > 1:
        raise SegmentGenerationError(
            "Human-in-the-loop generation permits only one not-yet-generated "
            "Segment per run; select and confirm exactly one."
        )
    if not new_segment_ids:
        if human_confirmed_segment is not None:
            raise SegmentGenerationError(
                "--human-confirmed-segment names no not-yet-generated Segment in "
                "this run."
            )
        return new_segment_ids
    expected = new_segment_ids[0]
    if human_confirmed_segment != expected:
        raise SegmentGenerationError(
            f"{expected} requires a fresh conversational before-video confirmation "
            f"and --human-confirmed-segment {expected}."
        )
    return new_segment_ids


def _storyboard_topological_waves(
    segments: list[dict[str, Any]], *, task_dir: Path
) -> list[list[str]]:
    """Execute the exact Seed Master planned waves and dependency edges."""

    order = [segment["generation_task_id"] for segment in segments]
    segment_by_id = {
        segment["generation_task_id"]: segment for segment in segments
    }
    selected = set(order)
    dependencies = {
        segment["generation_task_id"]: set(segment["depends_on_segment_ids"])
        for segment in segments
    }
    external = {
        dependency
        for values in dependencies.values()
        for dependency in values
        if dependency not in selected
    }
    missing_external = sorted(
        dependency
        for dependency in external
        if not _published_segment_ready(task_dir, dependency)
    )
    if missing_external:
        raise SegmentGenerationError(
            "Selected serial Segments require generated continuity sources: "
            + ", ".join(missing_external)
        )
    completed = set(external)
    if any(
        isinstance(segment.get("planned_wave"), bool)
        or not isinstance(segment.get("planned_wave"), int)
        or segment["planned_wave"] < 0
        for segment in segments
    ):
        raise SegmentGenerationError("Every Segment requires one non-negative planned_wave")
    waves: list[list[str]] = []
    for planned_wave in sorted({segment["planned_wave"] for segment in segments}):
        ready = [
            segment_id
            for segment_id in order
            if segment_by_id[segment_id]["planned_wave"] == planned_wave
        ]
        blocked = [
            segment_id
            for segment_id in ready
            if not dependencies[segment_id] <= completed
        ]
        if blocked:
            raise SegmentGenerationError(
                f"Seed Master planned wave {planned_wave} has unresolved dependencies: "
                + ", ".join(blocked)
            )
        waves.append(ready)
        completed.update(ready)
    return waves


def run(args: argparse.Namespace) -> int:
    if args.max_concurrency != 1:
        raise SegmentGenerationError(
            "Guided human-in-the-loop generation requires --max-concurrency 1."
        )
    if args.poll_interval <= 0 or args.wait_timeout <= 0 or args.timeout <= 0:
        raise SegmentGenerationError("Provider timing values must be positive.")
    task_dir = args.task_dir.expanduser().resolve()
    if not task_dir.is_dir():
        raise SegmentGenerationError(f"Task directory does not exist: {task_dir}")
    task = _task_contract(task_dir)
    predecessor_observations = parse_predecessor_observations(
        getattr(args, "observed_predecessor", None)
    )
    validation_through_segment_id = max(args.segments) if args.segments else None
    all_segment_ids = [
        str(item["segment_id"])
        for item in storyboard_segment_rows(
            task_dir,
            validation_through_segment_id=validation_through_segment_id,
        )
    ]
    if args.segments:
        unknown = sorted(set(args.segments) - set(all_segment_ids))
        if unknown:
            raise SegmentGenerationError(
                f"Unknown --segments values: {', '.join(unknown)}"
            )
    segments = discover_segments(task_dir, segment_ids=args.segments)
    selected_order = [
        segment["generation_task_id"] for segment in segments
    ]
    selected_ids = set(selected_order)
    _enforce_human_confirmation(
        task_dir=task_dir,
        selected_segment_ids=selected_order,
        human_confirmed_segment=getattr(args, "human_confirmed_segment", None),
    )
    unexpected_observations = sorted(
        set(predecessor_observations) - selected_ids
    )
    if unexpected_observations:
        raise SegmentGenerationError(
            "Predecessor observations name unselected Segments: "
            + ", ".join(unexpected_observations)
        )
    unnecessary_observations = sorted(
        segment["generation_task_id"]
        for segment in segments
        if segment["generation_task_id"] in predecessor_observations
        and segment["execution_plan"]["shooting_plan"].get(
            "predecessor_review_required"
        )
        is not True
    )
    if unnecessary_observations:
        raise SegmentGenerationError(
            "Predecessor observations are valid only for serial reviewed Segments: "
            + ", ".join(unnecessary_observations)
        )
    pending_root = task_dir / PENDING_DIRNAME / DEPARTMENT_DIRNAME
    waves = _storyboard_topological_waves(segments, task_dir=task_dir)
    announce(
        f"START segments={len(segments)} resolution={task['resolution']} "
        f"ratio={task['ratio']} audio_mode={task.get('seedance_audio_mode', 'native_sync')} "
        "scheduler=storyboard_shooting_plan_waves"
    )
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    boundary_precheck_failures: list[dict[str, str]] = []
    boundary_prechecks: dict[str, dict[str, Any]] = {}
    boundary_review_holds: dict[str, dict[str, Any]] = {}
    predecessor_observation_holds: dict[str, dict[str, Any]] = {}
    segment_by_id = {
        segment["generation_task_id"]: segment for segment in segments
    }
    for wave_number, wave_ids in enumerate(waves, start=1):
        for segment_id in wave_ids:
            requirement = predecessor_observation_requirement(
                task_dir=task_dir,
                segment_id=segment_id,
                plan=segment_by_id[segment_id]["execution_plan"],
            )
            if (
                requirement is not None
                and predecessor_observations.get(segment_id)
                != requirement["source_provider_attempt_id"]
            ):
                predecessor_observation_holds[segment_id] = requirement
        if predecessor_observation_holds:
            announce(
                "STOP before Seedance submission: virtual production must review "
                "the actual predecessor, current Segment, and resolved character/"
                "location bindings, adapt and rematerialize if needed, then receive "
                "seedance-video-review NO_ISSUES"
            )
            for segment_id in sorted(predecessor_observation_holds):
                requirement = predecessor_observation_holds[segment_id]
                announce(
                    "PREDECESSOR_OBSERVATION_REQUIRED "
                    f"segment={segment_id} "
                    f"attempt={requirement['source_provider_attempt_id']} "
                    f"segment_script={requirement['segment_script_path']} "
                    f"predecessor_video={requirement['predecessor_video_path']}"
                )
            break
        announce(f"WAVE {wave_number} segments={','.join(wave_ids)}")
        with ThreadPoolExecutor(max_workers=args.max_concurrency) as executor:
            futures = {
                executor.submit(
                    generate_one,
                    segment_by_id[segment_id],
                    task_dir=task_dir,
                    resolution=task["resolution"],
                    ratio=task["ratio"],
                    poll_interval=args.poll_interval,
                    wait_timeout=args.wait_timeout,
                    request_timeout=args.timeout,
                    predecessor_observations=predecessor_observations,
                ): segment_id
                for segment_id in wave_ids
            }
            for future in as_completed(futures):
                segment_id = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    failures.append({"segment_id": segment_id, "error": str(exc)})
                    announce(f"FAIL {segment_id} error={exc}")
                    continue
                results.append(result)
                try:
                    checks = prepare_adjacent_boundary_prechecks(
                        task_dir,
                        segment_id,
                        all_segment_ids,
                    )
                    for check in checks:
                        boundary_id = str(check["boundary_id"])
                        boundary_prechecks[boundary_id] = check
                        announce(
                            "BOUNDARY_REVIEW_READY "
                            f"boundary={boundary_id} "
                            f"technical_status={check['technical_status']}"
                        )
                        if check.get("blocks_downstream") is True:
                            boundary_review_holds[boundary_id] = {
                                "boundary_id": boundary_id,
                                "segment_id": str(check["to"]),
                                "technical_status": str(check["technical_status"]),
                                "reason": str(check.get("technical_reason") or ""),
                                "recommended_owner": str(
                                    check.get("recommended_owner") or "virtual-production"
                                ),
                            }
                except Exception as exc:
                    boundary_precheck_failures.append(
                        {"segment_id": segment_id, "error": str(exc)}
                    )
                    announce(f"BOUNDARY_PRECHECK_FAIL {segment_id} error={exc}")
        if failures or boundary_precheck_failures or boundary_review_holds:
            if failures or boundary_precheck_failures:
                announce("STOP downstream waves because an upstream wave failed")
            else:
                announce(
                    "STOP downstream waves because an incremental boundary needs "
                    "direct picture-and-sound review"
                )
            break
    results.sort(key=lambda item: item["segment_id"])
    failures.sort(key=lambda item: item["segment_id"])
    boundary_precheck_failures.sort(key=lambda item: item["segment_id"])
    summary_status = (
        "failed"
        if failures or boundary_precheck_failures
        else "boundary_review_required"
        if boundary_review_holds
        else "predecessor_observation_required"
        if predecessor_observation_holds
        else "succeeded"
    )
    summary = {
        "status": summary_status,
        "segment_count": len(segments),
        "project_segment_count": len(all_segment_ids),
        "succeeded_count": len(results),
        "failed_count": len(failures),
        "generate_audio": True,
        "seedance_audio_mode": task.get("seedance_audio_mode", "native_sync"),
        "dialogue_source": task.get("dialogue_source", "seedance"),
        "results": results,
        "failures": failures,
        "boundary_precheck_failed_count": len(boundary_precheck_failures),
        "boundary_precheck_failures": boundary_precheck_failures,
        "incremental_boundary_precheck_count": len(boundary_prechecks),
        "incremental_boundary_prechecks": [
            {
                "boundary_id": boundary_id,
                "from": check.get("from"),
                "to": check.get("to"),
                "technical_status": check.get("technical_status"),
                "blocks_downstream": check.get("blocks_downstream"),
                "recommended_owner": check.get("recommended_owner"),
                "evidence_storage": check.get("evidence_storage"),
            }
            for boundary_id, check in sorted(boundary_prechecks.items())
        ],
        "boundary_review_hold_count": len(boundary_review_holds),
        "boundary_review_holds": [
            boundary_review_holds[key] for key in sorted(boundary_review_holds)
        ],
        "predecessor_observation_hold_count": len(predecessor_observation_holds),
        "predecessor_observation_holds": [
            predecessor_observation_holds[key]
            for key in sorted(predecessor_observation_holds)
        ],
    }
    if (
        not failures
        and not boundary_precheck_failures
        and not boundary_review_holds
        and not predecessor_observation_holds
    ):
        full_generation = all(
            _published_segment_ready(task_dir, segment_id)
            for segment_id in all_segment_ids
        )
        summary["state"] = "GENERATED" if full_generation else "CANARY_GENERATED"
    announce(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return (
        0
        if not failures
        and not boundary_precheck_failures
        and not boundary_review_holds
        and not predecessor_observation_holds
        else 1
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--wait-timeout", type=float, default=3600.0)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument(
        "--observed-predecessor",
        action="append",
        metavar="SEGMENT_ID=PROVIDER_ATTEMPT_ID",
        help=(
            "Transient exact-attempt acknowledgement; pass only after virtual "
            "production reviews the predecessor video, current Segment and resolved "
            "character/location inputs, seedance-video-review returns NO_ISSUES, and "
            "the successor has been adjusted/rematerialized when needed."
        ),
    )
    parser.add_argument(
        "--human-confirmed-segment",
        metavar="SEGMENT_ID",
        help=(
            "Ephemeral assertion for the one Segment explicitly confirmed in the "
            "current conversation. It is not persisted and never authorizes a retry "
            "or another Segment."
        ),
    )
    parser.add_argument(
        "--segments",
        nargs="+",
        metavar="SEGMENT_ID",
        help=(
            "Generate only these Segment IDs in current plan order. Partial runs "
            "write CANARY_GENERATED and cannot enter postproduction."
        ),
    )
    return parser


@contextmanager
def task_execution_lock(task_dir: Path):
    pending_root = task_dir / PENDING_DIRNAME / DEPARTMENT_DIRNAME
    pending_root.mkdir(parents=True, exist_ok=True)
    lock_path = pending_root / EXECUTION_LOCK_FILENAME
    handle = lock_path.open("a+", encoding="utf-8")
    acquired = False
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError as exc:
            raise SegmentGenerationError(
                f"Another Seedance generation process already owns this task: {task_dir}"
            ) from exc
        yield
    finally:
        try:
            if acquired:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            if acquired:
                lock_path.unlink(missing_ok=True)


def main() -> int:
    try:
        args = build_parser().parse_args()
        task_dir = args.task_dir.expanduser().resolve()
        with task_execution_lock(task_dir):
            return run(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
