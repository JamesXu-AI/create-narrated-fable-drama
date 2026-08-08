"""Build provider-ready execution plans from validated Segment contracts."""

from __future__ import annotations

from pathlib import Path
import math
from typing import Any
import wave

from narrated_fable_drama.contracts.segment.common import (
    CAPABILITY_PROFILE_RELATIVE,
    REPOSITORY_ROOT,
    SCRIPT_DIR_RELATIVE,
    SEGMENT_RE,
    WHITE_MODEL_RESET_CONTRACT_RELATIVE,
    SegmentRuntimeError,
    read_json,
    sha256_file,
    token_sort_key,
)
from narrated_fable_drama.contracts.segment.media import (
    extension_quality_reset_schedule,
    resolve_catalog_media,
)
from narrated_fable_drama.contracts.segment.prompt import parse_segment_script
from narrated_fable_drama.contracts.segment.storyboard import (
    storyboard_segment_rows,
)
from narrated_fable_drama.contracts.storyboard import STORYBOARD_RELATIVE
from narrated_fable_drama.core.project_context import load_project_context


REFERENCE_AUDIO_SAFETY_MARGIN_SECONDS = 0.2
REFERENCE_AUDIO_MINIMUM_SECONDS = 1.8


def audio_reference_duration_policy(
    source_durations: list[float], maximum_total_seconds: float
) -> list[float]:
    """Return provider durations that fit the model's per-file and total limits."""

    if (
        not source_durations
        or isinstance(maximum_total_seconds, bool)
        or maximum_total_seconds <= REFERENCE_AUDIO_SAFETY_MARGIN_SECONDS
        or any(duration <= 0 for duration in source_durations)
    ):
        raise SegmentRuntimeError("Invalid reference-audio duration capability")
    provider_durations = [
        max(duration, REFERENCE_AUDIO_MINIMUM_SECONDS)
        for duration in source_durations
    ]
    if sum(provider_durations) <= maximum_total_seconds:
        return provider_durations
    usable = maximum_total_seconds - REFERENCE_AUDIO_SAFETY_MARGIN_SECONDS
    per_reference = math.floor(usable / len(source_durations) * 1000.0) / 1000.0
    if per_reference < REFERENCE_AUDIO_MINIMUM_SECONDS:
        raise SegmentRuntimeError("Reference-audio aggregate limit is too small")
    return [min(duration, per_reference) for duration in provider_durations]


def _wav_duration_seconds(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as source:
            return source.getnframes() / float(source.getframerate())
    except (OSError, EOFError, wave.Error, ZeroDivisionError) as exc:
        raise SegmentRuntimeError(f"Cannot probe reference audio: {path}") from exc


def provider_identity_roles(
    states: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Split character states into submitted and internal-only identity roles.

    A character can remain physically present in story continuity while every
    authored shot deliberately keeps that character outside the crop. Sending
    that character's positive identity image makes the image model render them
    despite the negative prompt. Only roles with at least one required visible
    shot therefore receive positive identity media.
    """

    submitted: list[str] = []
    internal_only: list[str] = []
    for item in states:
        asset_id = item["character_asset_id"]
        required_visible_shots = item.get("required_visible_shots")
        if (
            item.get("segment_presence_rule") != "remain_absent"
            and isinstance(required_visible_shots, list)
            and required_visible_shots
        ):
            submitted.append(asset_id)
        else:
            internal_only.append(asset_id)
    return submitted, internal_only


def _source_attempt(task_dir: Path, source_segment_id: str) -> str:
    source_root = (
        task_dir
        / ".pending/virtual-production/generation-segments"
        / source_segment_id
    )
    record = read_json(
        source_root / "production-record.json",
        label="predecessor production record",
    )
    attempt_id = record.get("provider_attempt_id")
    if (
        record.get("status") != "GENERATED"
        or record.get("segment_id") != source_segment_id
        or not isinstance(attempt_id, str)
        or not (source_root / "video.mp4").is_file()
        or not (source_root / "last-frame.png").is_file()
    ):
        raise SegmentRuntimeError(
            f"Dependent Prompt requires the current generated attempt for {source_segment_id}"
        )
    return attempt_id


def _capability_profile_path(task_dir: Path) -> Path:
    task_local = task_dir / CAPABILITY_PROFILE_RELATIVE
    if task_local.is_file():
        return task_local
    repository_default = (
        REPOSITORY_ROOT
        / "skills/virtual-production/assets/seedance-capability-profile.json"
    )
    return repository_default


def load_execution_plan(task_dir: Path, segment_id: str) -> dict[str, Any]:
    if not SEGMENT_RE.fullmatch(segment_id):
        raise SegmentRuntimeError(f"Invalid Segment ID: {segment_id}")
    root = task_dir.expanduser().resolve(strict=True)
    parsed = parse_segment_script(
        root / SCRIPT_DIR_RELATIVE / f"{segment_id}.md"
    )
    row = parsed["metadata"]
    context = load_project_context(root)
    capability_profile = read_json(
        _capability_profile_path(root), label="Seedance capability profile"
    )
    if capability_profile.get("profile_status") != "VERIFIED":
        raise SegmentRuntimeError("Seedance capability profile is not verified")
    project_policy = capability_profile.get("project_generation_policy")
    capabilities = capability_profile.get("provider_capabilities")
    if not isinstance(project_policy, dict) or not isinstance(capabilities, dict):
        raise SegmentRuntimeError("Seedance capability profile is incomplete")
    maximum_hops = project_policy.get(
        "maximum_direct_extension_hops_without_quality_reset"
    )
    if maximum_hops != 0:
        raise SegmentRuntimeError("Every extension must use white-model quality reset")
    quality_reset = extension_quality_reset_schedule(
        storyboard_segment_rows(
            root, validation_through_segment_id=segment_id
        ),
        maximum_hops,
    )[segment_id]
    if quality_reset["required"]:
        reset_path = REPOSITORY_ROOT / WHITE_MODEL_RESET_CONTRACT_RELATIVE
        quality_reset = {
            **quality_reset,
            "contract_path": WHITE_MODEL_RESET_CONTRACT_RELATIVE.as_posix(),
            "contract_sha256": sha256_file(reset_path),
        }
    else:
        quality_reset = {
            **quality_reset,
            "contract_path": "none",
            "contract_sha256": "none",
        }
    catalog_path = REPOSITORY_ROOT / "workspace/assets/assets.json"
    catalog = read_json(catalog_path, label="repository asset catalog")
    media_bindings: list[dict[str, Any]] = []
    for binding in sorted(row["bindings"], key=lambda item: token_sort_key(item["provider_token"])):
        token = binding["provider_token"]
        role = binding["provider_role"]
        namespace = binding["asset_namespace"]
        if namespace == "continuity" or role == "reference_video":
            dependencies = row["depends_on_segment_ids"]
            if len(dependencies) != 1:
                raise SegmentRuntimeError(
                    f"{segment_id} continuity media needs one predecessor"
                )
            source = dependencies[0]
            attempt = _source_attempt(root, source)
            if role == "reference_video":
                source_kind = (
                    "white_model_predecessor_video"
                    if quality_reset["required"]
                    else "complete_predecessor_video"
                )
                audio_policy = "preserved"
            else:
                source_kind = "provider_last_frame"
                audio_policy = "none"
            media = {
                "provider_token": token,
                "provider_role": role,
                "source_kind": source_kind,
                "source_segment_id": source,
                "source_provider_attempt_id": attempt,
                "namespace": namespace,
                "audio_policy": audio_policy,
            }
        else:
            resolved = resolve_catalog_media(
                namespace=namespace,
                provider_role=role,
                catalog=catalog,
            )
            media = {
                "provider_token": token,
                "provider_role": role,
                "source_kind": "asset_catalog",
                "namespace": namespace,
                **resolved,
            }
        media["binding_ids"] = [binding["binding_id"]]
        media_bindings.append(media)
    counts = {
        role: sum(item["provider_role"] == role for item in media_bindings)
        for role in ("reference_image", "reference_video", "reference_audio")
    }
    limits = {
        "reference_image": capabilities.get("maximum_reference_images"),
        "reference_video": capabilities.get("maximum_reference_videos"),
        "reference_audio": capabilities.get("maximum_reference_audios"),
    }
    for role, count in counts.items():
        limit = limits[role]
        if isinstance(limit, bool) or not isinstance(limit, int) or count > limit:
            raise SegmentRuntimeError(f"{segment_id} exceeds verified {role} limit")
    audio_media = [
        item for item in media_bindings
        if item.get("provider_role") == "reference_audio"
        and item.get("source_kind") == "asset_catalog"
    ]
    maximum_audio_seconds = capabilities.get(
        "maximum_reference_audio_total_seconds"
    )
    audio_duration_policy = {
        "maximum_total_seconds": maximum_audio_seconds,
        "source_total_seconds": 0.0,
        "provider_total_seconds": 0.0,
        "trimmed": False,
    }
    if audio_media:
        if (
            isinstance(maximum_audio_seconds, bool)
            or not isinstance(maximum_audio_seconds, (int, float))
            or maximum_audio_seconds <= 0
        ):
            raise SegmentRuntimeError(
                "Seedance capability profile lacks reference-audio duration limit"
            )
        source_durations = [
            _wav_duration_seconds(REPOSITORY_ROOT / item["local_path"])
            for item in audio_media
        ]
        provider_durations = audio_reference_duration_policy(
            source_durations, float(maximum_audio_seconds)
        )
        for item, source_duration, provider_duration in zip(
            audio_media, source_durations, provider_durations, strict=True
        ):
            item["source_duration_seconds"] = round(source_duration, 6)
            item["provider_duration_seconds"] = round(provider_duration, 6)
        audio_duration_policy = {
            "maximum_total_seconds": float(maximum_audio_seconds),
            "source_total_seconds": round(sum(source_durations), 6),
            "provider_total_seconds": round(sum(provider_durations), 6),
            "trimmed": any(
                provider + 0.001 < source
                for source, provider in zip(
                    source_durations, provider_durations, strict=True
                )
            ),
        }
    assets = catalog.get("assets")
    if not isinstance(assets, dict):
        raise SegmentRuntimeError("Asset catalog has no assets object")
    states = row["continuity"]["character_segment_states"]
    renderable, non_submission = provider_identity_roles(states)
    bound_images = {
        str(item.get("namespace"))
        for item in media_bindings
        if item.get("source_kind") == "asset_catalog"
        and item.get("provider_role") == "reference_image"
    }

    def covers(namespace: str, performer: str) -> bool:
        if namespace == performer or namespace.startswith(f"{performer}--"):
            return True
        asset = assets.get(namespace)
        return (
            isinstance(asset, dict)
            and asset.get("type") == "costume"
            and asset.get("character_id") == performer
        )

    identity_coverage = {
        performer: [
            {
                "provider_token": item["provider_token"],
                "asset_namespace": item["namespace"],
                "source_kind": item["source_kind"],
            }
            for item in media_bindings
            if item.get("provider_role") == "reference_image"
            and item.get("source_kind") == "asset_catalog"
            and covers(str(item.get("namespace")), performer)
        ]
        for performer in renderable
    }
    missing = [performer for performer, evidence in identity_coverage.items() if not evidence]
    if missing:
        raise SegmentRuntimeError(
            f"{segment_id} lacks identity image bindings for visible/present roles: {missing}"
        )
    wrongly_bound_internal = [
        performer
        for performer in non_submission
        if any(covers(namespace, performer) for namespace in bound_images)
    ]
    if wrongly_bound_internal:
        raise SegmentRuntimeError(
            f"{segment_id} submits positive images for roles with no required "
            f"visible shots: {wrongly_bound_internal}"
        )
    result = {
        "contract": "seedance-storyboard-derived-execution-plan-v1",
        "segment_id": segment_id,
        "source_segment_script": parsed["path"].relative_to(root).as_posix(),
        "source_script_sha256": parsed["script_sha256"],
        "source_storyboard_sha256": row["source_storyboard_sha256"],
        "shot_count": row["shot_count"],
        "authored_bindings": row["bindings"],
        "continuity": row["continuity"],
        "prompt_contract": row["prompt_contract"],
        "quality_reset": quality_reset,
        "shooting_plan": {
            field: row[field]
            for field in (
                "shooting_plan_status",
                "schedule_mode",
                "planned_wave",
                "depends_on_segment_ids",
                "dependency_reason",
                "predecessor_review_required",
                "required_predecessor_evidence",
                "successor_recompile_required",
                "fallback_operation_and_story_cost",
                "operation",
                "seam_class",
                "seam_resynthesis_allowed",
                "seam_story_reason",
                "editorial_intent",
                "reference_video_scope",
                "reference_video_audio",
                "camera_ensemble_color_resynthesis_allowed",
            )
        },
        "seedance_parameters": {
            "model": capability_profile["model_id"],
            "duration": parsed["duration"],
            "resolution": context["resolution"],
            "ratio": context["aspect_ratio"],
            "generate_audio": True,
            "watermark": False,
            "return_last_frame": True,
            "execution_expires_after": 172800,
            "priority": 0,
        },
        "media_bindings": media_bindings,
        "media_counts": counts,
        "reference_audio_duration_policy": audio_duration_policy,
        "identity_reference_coverage": identity_coverage,
        "identity_non_submission_roles": non_submission,
        "dialogue_cues": row["dialogue_cues"],
        "final_visible_state": row["final_visible_state"],
        "final_sound_state": row["final_sound_state"],
        "audio_policy": {
            "seedance_audio_mode": "native_sync",
            "dialogue_source": "seedance",
            "voice_audio_source": "speaker_reference_audio",
            "silent_mouth_performance": False,
            "native_background_audio": True,
            "seedance_background_music": True,
            "background_music_source": "seedance_native",
        },
    }
    return result


def validate_source_identity(task_dir: Path, parsed: dict[str, Any]) -> None:
    current = sha256_file(task_dir / STORYBOARD_RELATIVE)
    if current != parsed["metadata"]["source_storyboard_sha256"]:
        raise SegmentRuntimeError(f"{parsed['segment_id']} Storyboard source is stale")
