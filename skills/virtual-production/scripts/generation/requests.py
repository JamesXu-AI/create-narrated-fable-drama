"""Parse Segment contracts and build exact provider request payloads."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from narrated_fable_drama.contracts.segment import (
    SCRIPT_DIR_RELATIVE,
    load_execution_plan,
    parse_segment_script as parse_local_segment_prompt,
    sha256_file,
    sha256_json,
    storyboard_segment_rows,
    token_sort_key,
)
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.providers import runtime as provider_runtime
from narrated_fable_drama.providers import seedance
from .common import (
    DEPARTMENT_DIRNAME,
    GENERATION_DIRNAME,
    PENDING_DIRNAME,
    SegmentGenerationError,
    read_json,
)
from .reset import (
    ensure_white_model_predecessor,
)
from validate_segment_scripts import validate_task as validate_segment_scripts


def _provider_audio_url(
    reference: dict[str, Any], *, task_dir: Path
) -> str:
    source_duration = reference.get("source_duration_seconds")
    provider_duration = reference.get("provider_duration_seconds")
    if (
        not isinstance(source_duration, (int, float))
        or not isinstance(provider_duration, (int, float))
        or source_duration <= 0
        or provider_duration <= 0
    ):
        raise SegmentGenerationError("Reference audio lacks duration policy")
    if abs(provider_duration - source_duration) <= 0.001:
        return str(reference["uri"])

    repository_root = task_dir.parents[2]
    source = (repository_root / str(reference.get("local_path") or "")).resolve()
    try:
        source.relative_to(repository_root)
    except ValueError as exc:
        raise SegmentGenerationError(
            "Reference audio resolves outside the repository"
        ) from exc
    if not source.is_file():
        raise SegmentGenerationError(f"Missing reference audio: {source}")
    output_root = (
        task_dir / PENDING_DIRNAME / DEPARTMENT_DIRNAME / "reference-audio"
    )
    output_root.mkdir(parents=True, exist_ok=True)
    duration_ms = int(round(float(provider_duration) * 1000.0))
    output = output_root / (
        f"{reference['asset_id']}-{duration_ms}ms-{sha256_file(source)[:12]}.wav"
    )
    if not output.is_file():
        audio_filter_args = (
            ["-af", "apad"]
            if provider_duration > source_duration
            else []
        )
        result = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(source),
                *audio_filter_args,
                "-t",
                f"{provider_duration:.3f}",
                "-ac",
                "1",
                "-ar",
                "44100",
                "-c:a",
                "pcm_s16le",
                str(output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not output.is_file():
            raise SegmentGenerationError(
                f"Cannot prepare bounded reference audio: {result.stderr.strip()}"
            )
    return provider_runtime.tos_upload_path(
        output, kind="inputs/reference-audio"
    )["public_url"]


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
    context = load_project_context(task_dir)
    return {
        "resolution": context["resolution"],
        "ratio": context["aspect_ratio"],
        "seedance_audio_mode": "native_sync",
        "dialogue_source": "seedance",
    }


def discover_segments(
    task_dir: Path, *, segment_ids: list[str] | None = None
) -> list[dict[str, Any]]:
    # No human-facing generation begins until the first complete Prompt set and
    # its full speech-rate/continuity gate have passed.
    validate_segment_scripts(task_dir, segment_ids=None)
    validation_through_segment_id = None
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
    request_timeout: int = provider_runtime.DEFAULT_TIMEOUT,
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
            # Provider result URLs can be readable by the local downloader yet
            # return 403 when Seedance tries to fetch them for a successor.
            # Re-upload the accepted local evidence to our public input bucket.
            url = None
        elif source_kind == "complete_predecessor_video":
            source = source_dir / "video.mp4"
            provider_type = "video_url"
            url = None
        elif source_kind == "white_model_predecessor_video":
            source = ensure_white_model_predecessor(
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
            url = provider_runtime.tos_upload_path(
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
    request_timeout: int = provider_runtime.DEFAULT_TIMEOUT,
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
            "audio_url": {
                "url": _provider_audio_url(reference, task_dir=task_dir)
            },
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
            f"{segment['generation_task_id']} runtime media differs from Storyboard bindings"
        )
    content: list[dict[str, Any]] = [{"type": "text", "text": segment["prompt"]}]
    for item in sorted(media_content, key=lambda value: token_sort_key(value["_provider_token"])):
        content.append({key: value for key, value in item.items() if key != "_provider_token"})
    return {**parameters, "content": content}
