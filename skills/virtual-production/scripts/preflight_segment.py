#!/usr/bin/env python3
"""Run the immediate Seedance preflight for one local Segment Prompt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.contracts.segment import (
    CAPABILITY_PROFILE_RELATIVE,
    SCRIPT_DIR_RELATIVE,
    WHITE_MODEL_RESET_CONTRACT_RELATIVE,
    SegmentRuntimeError,
    extension_quality_reset_schedule,
    load_execution_plan,
    parse_segment_script,
    read_json,
    sha256_file,
    storyboard_segment_rows,
)
from validate_segment_scripts import validate_task as validate_segment_scripts


def _is_npc_ensemble_asset_id(asset_id: object) -> bool:
    return isinstance(asset_id, str) and asset_id.startswith("group-")


OBSERVATION_ARGUMENT_RE = re.compile(
    r"^(segment-[0-9]{3,})=(segment-[0-9]{3,}__attempt-[0-9]{4,})$"
)


def parse_predecessor_observations(values: list[str] | None) -> dict[str, str]:
    """Parse transient successor=predecessor-attempt review acknowledgements."""

    observations: dict[str, str] = {}
    for value in values or []:
        match = OBSERVATION_ARGUMENT_RE.fullmatch(value.strip())
        if match is None:
            raise SegmentRuntimeError(
                "--observed-predecessor must use "
                "segment-NNN=segment-MMM__attempt-NNNN"
            )
        segment_id, attempt_id = match.groups()
        if segment_id in observations:
            raise SegmentRuntimeError(
                f"Duplicate predecessor observation for {segment_id}"
            )
        observations[segment_id] = attempt_id
    return observations


def identity_reference_audit(
    *, task_dir: Path, segment_id: str, plan: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Resolve role coverage to the exact image URLs Seedance will receive."""

    continuity = plan.get("continuity")
    states = (
        continuity.get("character_segment_states", [])
        if isinstance(continuity, dict)
        else []
    )
    renderable_ids = [
        item.get("character_asset_id")
        for item in states
        if isinstance(item, dict)
        and item.get("segment_presence_rule") != "remain_absent"
    ]
    absent_ids = [
        item.get("character_asset_id")
        for item in states
        if isinstance(item, dict)
        and item.get("segment_presence_rule") == "remain_absent"
    ]
    coverage = plan.get("identity_reference_coverage")
    non_submission = plan.get("identity_non_submission_roles")
    if (
        not isinstance(coverage, dict)
        or set(coverage) != set(renderable_ids)
        or non_submission != absent_ids
    ):
        raise SegmentRuntimeError(
            f"{segment_id} identity-image coverage is stale: every "
            "provider-renderable role must have an image and remain_absent roles "
            "must be internal-only"
        )

    binding_by_id = {
        item.get("binding_id"): item
        for item in plan.get("authored_bindings", [])
        if isinstance(item, dict) and isinstance(item.get("binding_id"), str)
    }
    media_by_token = {
        item.get("provider_token"): item
        for item in plan.get("media_bindings", [])
        if isinstance(item, dict)
    }
    complete_predecessor_media = [
        item
        for item in media_by_token.values()
        if item.get("provider_role") == "reference_video"
        and item.get("source_kind")
        in {"complete_predecessor_video", "white_model_predecessor_video"}
    ]
    sole_predecessor_visual_authority = (
        isinstance(plan.get("shooting_plan"), dict)
        and plan["shooting_plan"].get("operation") == "video_extension"
        and len(complete_predecessor_media) == 1
        and not any(
            item.get("provider_role") == "reference_image"
            for item in media_by_token.values()
        )
    )
    if sole_predecessor_visual_authority:
        media = complete_predecessor_media[0]
        readable_subjects = list(
            dict.fromkeys(
                str(binding_by_id[binding_id].get("readable_subject") or "").strip()
                for binding_id in media.get("binding_ids", [])
                if binding_id in binding_by_id
                and str(
                    binding_by_id[binding_id].get("readable_subject") or ""
                ).strip()
            )
        )
        if not readable_subjects:
            raise SegmentRuntimeError(
                f"{segment_id} complete predecessor lacks a model-facing readable name"
            )
        return {
            str(role_id): [
                {
                    "provider_token": media.get("provider_token"),
                    "readable_subjects": readable_subjects,
                    "video_source_kind": media.get("source_kind"),
                    "source_provider_attempt_id": media.get(
                        "source_provider_attempt_id"
                    ),
                }
            ]
            for role_id in renderable_ids
        }
    provider_last_frame_media = [
        item
        for item in media_by_token.values()
        if item.get("provider_role") == "reference_image"
        and item.get("source_kind") == "provider_last_frame"
        and item.get("namespace") == "continuity"
    ]
    last_frame_visual_authority = (
        isinstance(plan.get("shooting_plan"), dict)
        and plan["shooting_plan"].get("operation") == "multimodal_reference"
        and plan["shooting_plan"].get("required_predecessor_evidence")
        == "approved_provider_last_frame"
        and len(provider_last_frame_media) == 1
        and all(
            isinstance(item, dict)
            and item.get("incoming_presence") == "visible"
            and item.get("segment_presence_rule") == "must_remain_visible"
            for item in states
            if item.get("character_asset_id") in renderable_ids
        )
    )
    if last_frame_visual_authority:
        media = provider_last_frame_media[0]
        readable_subjects = list(
            dict.fromkeys(
                str(binding_by_id[binding_id].get("readable_subject") or "").strip()
                for binding_id in media.get("binding_ids", [])
                if binding_id in binding_by_id
                and str(
                    binding_by_id[binding_id].get("readable_subject") or ""
                ).strip()
            )
        )
        if not readable_subjects:
            raise SegmentRuntimeError(
                f"{segment_id} provider last frame lacks a model-facing readable name"
            )
        return {
            str(role_id): [
                {
                    "provider_token": media.get("provider_token"),
                    "readable_subjects": readable_subjects,
                    "image_source_kind": media.get("source_kind"),
                    "source_provider_attempt_id": media.get(
                        "source_provider_attempt_id"
                    ),
                }
            ]
            for role_id in renderable_ids
        }
    audit: dict[str, list[dict[str, Any]]] = {}
    for role_id in renderable_ids:
        rows = coverage.get(role_id)
        if not isinstance(rows, list) or not rows:
            raise SegmentRuntimeError(
                f"{segment_id} role {role_id} has no identity image"
            )
        audit_rows: list[dict[str, Any]] = []
        for row in rows:
            token = row.get("provider_token") if isinstance(row, dict) else None
            media = media_by_token.get(token)
            if (
                not isinstance(media, dict)
                or media.get("provider_role") != "reference_image"
                or media.get("source_kind") != "asset_catalog"
                or not str(media.get("uri") or "").startswith(("https://", "http://"))
            ):
                raise SegmentRuntimeError(
                    f"{segment_id} role {role_id} identity token does not resolve "
                    "to a submitted catalog image"
                )
            readable_subjects = list(
                dict.fromkeys(
                    str(binding_by_id[binding_id].get("readable_subject") or "").strip()
                    for binding_id in media.get("binding_ids", [])
                    if binding_id in binding_by_id
                    and str(
                        binding_by_id[binding_id].get("readable_subject") or ""
                    ).strip()
                )
            )
            if not readable_subjects:
                raise SegmentRuntimeError(
                    f"{segment_id} role {role_id} lacks a model-facing readable name"
                )
            audit_rows.append(
                {
                    "provider_token": token,
                    "readable_subjects": readable_subjects,
                    "image_uri": media["uri"],
                }
            )
        audit[str(role_id)] = audit_rows
    return audit


def predecessor_observation_requirement(
    *, task_dir: Path, segment_id: str, plan: dict[str, Any]
) -> dict[str, Any] | None:
    """Describe the live review required before one serial provider call."""

    shooting = plan.get("shooting_plan")
    if not isinstance(shooting, dict):
        raise SegmentRuntimeError(f"{segment_id} execution plan lacks shooting_plan")
    if shooting.get("predecessor_review_required") is not True:
        return None
    dependencies = shooting.get("depends_on_segment_ids")
    if (
        shooting.get("schedule_mode") != "serial_after_predecessor_review"
        or shooting.get("successor_recompile_required") is not True
        or shooting.get("shooting_plan_status") != "observed_adapted"
        or not isinstance(dependencies, list)
        or len(dependencies) != 1
    ):
        raise SegmentRuntimeError(
            f"{segment_id} predecessor-observation plan is contradictory"
        )
    source_segment_id = dependencies[0]
    source_root = (
        task_dir
        / ".pending/virtual-production/generation-segments"
        / source_segment_id
    )
    source_record = read_json(
        source_root / "production-record.json",
        label="predecessor production record",
    )
    attempt_id = source_record.get("provider_attempt_id")
    if (
        source_record.get("status") != "GENERATED"
        or source_record.get("segment_id") != source_segment_id
        or not isinstance(attempt_id, str)
        or not OBSERVATION_ARGUMENT_RE.fullmatch(f"{segment_id}={attempt_id}")
        or not (source_root / "video.mp4").is_file()
    ):
        raise SegmentRuntimeError(
            f"{segment_id} has no current generated predecessor to review"
        )
    runtime_attempts = {
        item.get("source_provider_attempt_id")
        for item in plan.get("media_bindings", [])
        if isinstance(item, dict) and item.get("source_kind") != "asset_catalog"
    }
    strong_reset = (
        str(shooting.get("seam_class") or "").replace(" ", "_")
        == "strong_coverage_reset"
        and shooting.get("required_predecessor_evidence") == "none"
    )
    expected_runtime_attempts = set() if strong_reset else {attempt_id}
    if runtime_attempts != expected_runtime_attempts:
        raise SegmentRuntimeError(
            f"{segment_id} is not materialized from the current predecessor attempt"
        )

    authored_by_id = {
        item.get("binding_id"): item
        for item in plan.get("authored_bindings", [])
        if isinstance(item, dict) and isinstance(item.get("binding_id"), str)
    }
    binding_summary: list[dict[str, Any]] = []
    for media in plan.get("media_bindings", []):
        if not isinstance(media, dict):
            continue
        authored = [
            authored_by_id[binding_id]
            for binding_id in media.get("binding_ids", [])
            if binding_id in authored_by_id
        ]
        binding_summary.append(
            {
                "provider_token": media.get("provider_token"),
                "provider_role": media.get("provider_role"),
                "source_kind": media.get("source_kind"),
                "asset_namespace": media.get("namespace"),
                "readable_subjects": list(
                    dict.fromkeys(
                        str(item.get("readable_subject"))
                        for item in authored
                        if isinstance(item.get("readable_subject"), str)
                        and item.get("readable_subject").strip()
                    )
                ),
            }
        )
    continuity = plan.get("continuity")
    performers = (
        continuity.get("authorized_independent_performer_asset_ids", [])
        if isinstance(continuity, dict)
        else []
    )
    character_states = (
        continuity.get("character_segment_states", [])
        if isinstance(continuity, dict)
        else []
    )
    predecessor_plan = load_execution_plan(task_dir, source_segment_id)
    predecessor_continuity = predecessor_plan.get("continuity")
    predecessor_character_states = (
        predecessor_continuity.get("character_segment_states", [])
        if isinstance(predecessor_continuity, dict)
        else []
    )
    required_visible_by_shot = {
        f"Shot {shot_number}": [
            item["character_asset_id"]
            for item in character_states
            if shot_number in item.get("required_visible_shots", [])
        ]
        for shot_number in range(
            1,
            int(plan.get("shot_count", 0)) + 1,
        )
    }
    return {
        "segment_id": segment_id,
        "source_segment_id": source_segment_id,
        "source_provider_attempt_id": attempt_id,
        "predecessor_video_path": str((source_root / "video.mp4").resolve()),
        "segment_script_path": str(
            (task_dir / SCRIPT_DIR_RELATIVE / f"{segment_id}.md").resolve()
        ),
        "storyboard_path": str(
            (task_dir / "previsualize-cinematography/storyboard.md").resolve()
        ),
        "authorized_independent_performer_asset_ids": performers,
        "identity_reference_coverage": plan.get(
            "identity_reference_coverage", {}
        ),
        "identity_non_submission_roles": plan.get(
            "identity_non_submission_roles", []
        ),
        "character_segment_states": character_states,
        "predecessor_character_segment_states": predecessor_character_states,
        "required_visible_characters_by_shot": required_visible_by_shot,
        "strict_required_visible_characters_by_shot": {
            shot: [
                asset_id
                for asset_id in asset_ids
                if not _is_npc_ensemble_asset_id(asset_id)
            ]
            for shot, asset_ids in required_visible_by_shot.items()
        },
        "npc_ensemble_presence_fields_by_shot": {
            shot: [
                asset_id
                for asset_id in asset_ids
                if _is_npc_ensemble_asset_id(asset_id)
            ]
            for shot, asset_ids in required_visible_by_shot.items()
        },
        "npc_ensemble_review_policy": (
            "group_level_presence_only: do not audit exact NPC count, species mix, "
            "or member identity; reject only unmotivated whole-group pop-in, "
            "disappearance, duplicate crowd, allegiance change, or a missing "
            "required ensemble field"
        ),
        "resolved_reference_bindings": binding_summary,
        "required_result": "video-review:NO_ISSUES",
        "resume_argument": f"{segment_id}={attempt_id}",
    }


def validate_predecessor_observation_gate(
    *,
    task_dir: Path,
    segment_id: str,
    plan: dict[str, Any],
    observations: dict[str, str] | None,
) -> dict[str, Any] | None:
    """Require a live exact-attempt review result without writing an approval file."""

    requirement = predecessor_observation_requirement(
        task_dir=task_dir,
        segment_id=segment_id,
        plan=plan,
    )
    if requirement is None:
        return None
    actual = (observations or {}).get(segment_id)
    expected = requirement["source_provider_attempt_id"]
    if actual != expected:
        raise SegmentRuntimeError(
            f"{segment_id} is blocked until virtual production reviews "
            f"{requirement['predecessor_video_path']} with the current Segment and "
            "resolved character/location bindings, receives video-review "
            f"NO_ISSUES, adjusts and rematerializes when needed, then passes "
            f"--observed-predecessor {requirement['resume_argument']} in this process"
        )
    return requirement


def preflight_segment(
    *,
    task_dir: Path,
    segment_script_path: Path,
    predecessor_observations: dict[str, str] | None = None,
) -> dict[str, Any]:
    task_dir = task_dir.expanduser().resolve(strict=True)
    segment_script_path = segment_script_path.expanduser().resolve(strict=True)
    segment_id = segment_script_path.stem
    expected = (task_dir / SCRIPT_DIR_RELATIVE / f"{segment_id}.md").resolve()
    if segment_script_path != expected:
        raise SegmentRuntimeError(f"Segment Script must use the current path: {expected}")
    validate_segment_scripts(task_dir, segment_ids=None)
    validate_segment_scripts(task_dir, segment_ids=[segment_id])
    parsed = parse_segment_script(segment_script_path)
    plan = load_execution_plan(task_dir, segment_id)
    observation = validate_predecessor_observation_gate(
        task_dir=task_dir,
        segment_id=segment_id,
        plan=plan,
        observations=predecessor_observations,
    )
    profile = read_json(
        task_dir / CAPABILITY_PROFILE_RELATIVE,
        label="Seedance capability profile",
    )
    capabilities = profile.get("provider_capabilities")
    project_policy = profile.get("project_generation_policy")
    parameters = plan["seedance_parameters"]
    media_counts = plan["media_counts"]
    continuity = plan.get("continuity")
    character_states = (
        continuity.get("character_segment_states", [])
        if isinstance(continuity, dict)
        else []
    )
    identity_audit = identity_reference_audit(
        task_dir=task_dir,
        segment_id=segment_id,
        plan=plan,
    )
    if not isinstance(capabilities, dict) or not isinstance(project_policy, dict):
        raise SegmentRuntimeError("Seedance capability profile is incomplete")
    if (
        project_policy.get(
            "maximum_direct_extension_hops_without_quality_reset"
        )
        != 0
        or project_policy.get("maximum_consecutive_predecessor_media_hops") != 1
        or project_policy.get(
            "require_strong_coverage_reset_after_predecessor_media"
        )
        is not True
    ):
        raise SegmentRuntimeError(
            "Seedance project policy must white-model every extension and allow "
            "only one consecutive predecessor-media handoff"
        )
    if (
        parameters.get("model") != profile.get("model_id")
        or parameters.get("duration") != parsed["duration"]
        or capabilities.get("native_audio_generation") is not True
        or capabilities.get("native_background_audio_generation") is not True
    ):
        raise SegmentRuntimeError(f"{segment_id} is incompatible with the verified model")
    expected_reset = extension_quality_reset_schedule(
        storyboard_segment_rows(
            task_dir,
            validation_through_segment_id=segment_id,
        ),
        project_policy.get(
            "maximum_direct_extension_hops_without_quality_reset"
        ),
    )[segment_id]
    actual_reset = plan.get("quality_reset")
    if not isinstance(actual_reset, dict) or any(
        actual_reset.get(key) != value for key, value in expected_reset.items()
    ):
        raise SegmentRuntimeError(
            f"{segment_id} white-model quality-reset schedule is stale"
        )
    if expected_reset["required"]:
        reset_contract_path = REPOSITORY_ROOT / WHITE_MODEL_RESET_CONTRACT_RELATIVE
        if (
            actual_reset.get("contract_path")
            != WHITE_MODEL_RESET_CONTRACT_RELATIVE.as_posix()
            or actual_reset.get("contract_sha256")
            != sha256_file(reset_contract_path)
            or not any(
                item.get("source_kind") == "white_model_predecessor_video"
                for item in plan.get("media_bindings", [])
                if isinstance(item, dict)
            )
        ):
            raise SegmentRuntimeError(
                f"{segment_id} white-model quality-reset input is invalid"
            )
    limits = {
        "reference_image": capabilities.get("maximum_reference_images"),
        "reference_video": capabilities.get("maximum_reference_videos"),
        "reference_audio": capabilities.get("maximum_reference_audios"),
    }
    for role, count in media_counts.items():
        limit = limits.get(role)
        if isinstance(count, bool) or not isinstance(count, int):
            raise SegmentRuntimeError(f"{segment_id} has invalid {role} count")
        if isinstance(limit, bool) or not isinstance(limit, int) or count > limit:
            raise SegmentRuntimeError(f"{segment_id} exceeds the {role} capability")
    required_visible_by_shot = {
        f"Shot {shot_number}": [
            item["character_asset_id"]
            for item in character_states
            if shot_number in item.get("required_visible_shots", [])
        ]
        for shot_number in range(
            1,
            int(parsed["metadata"].get("shot_count", 0)) + 1,
        )
    }
    return {
        "status": "PASS",
        "segment_id": segment_id,
        "model_id": parameters["model"],
        "duration_seconds": parameters["duration"],
        "operation": plan["shooting_plan"]["operation"],
        "shooting_plan_status": plan["shooting_plan"]["shooting_plan_status"],
        "planned_wave": plan["shooting_plan"]["planned_wave"],
        "reference_image_count": media_counts["reference_image"],
        "reference_video_count": media_counts["reference_video"],
        "reference_audio_count": media_counts["reference_audio"],
        "media_bindings_resolved": True,
        "identity_reference_coverage": identity_audit,
        "identity_non_submission_roles": plan.get(
            "identity_non_submission_roles", []
        ),
        "character_segment_state_count": len(character_states),
        "must_remain_visible_character_ids": [
            item["character_asset_id"]
            for item in character_states
            if item.get("segment_presence_rule") == "must_remain_visible"
        ],
        "required_visible_character_ids_by_shot": required_visible_by_shot,
        "strict_required_visible_character_ids_by_shot": {
            shot: [
                asset_id
                for asset_id in asset_ids
                if not _is_npc_ensemble_asset_id(asset_id)
            ]
            for shot, asset_ids in required_visible_by_shot.items()
        },
        "npc_ensemble_presence_field_ids_by_shot": {
            shot: [
                asset_id
                for asset_id in asset_ids
                if _is_npc_ensemble_asset_id(asset_id)
            ]
            for shot, asset_ids in required_visible_by_shot.items()
        },
        "npc_ensemble_review_policy": (
            "group_level_presence_only: exact NPC count, species mix, and member "
            "identity are non-blocking; reject only unmotivated whole-group pop-in, "
            "disappearance, duplicate crowd, allegiance change, or missing required "
            "ensemble field"
        ),
        "predecessor_observation": (
            "NO_ISSUES_CURRENT_ATTEMPT" if observation is not None else "NOT_REQUIRED"
        ),
        "quality_reset": expected_reset["strategy"],
        "generate_audio": True,
        "return_last_frame": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--segment-script", required=True, type=Path)
    parser.add_argument(
        "--observed-predecessor",
        action="append",
        metavar="SEGMENT_ID=PROVIDER_ATTEMPT_ID",
        help=(
            "Transient exact-attempt acknowledgement; pass only after direct "
            "predecessor review returns NO_ISSUES and the successor is current."
        ),
    )
    args = parser.parse_args()
    try:
        observations = parse_predecessor_observations(args.observed_predecessor)
        result = preflight_segment(
            task_dir=args.task_dir,
            segment_script_path=args.segment_script,
            predecessor_observations=observations,
        )
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
