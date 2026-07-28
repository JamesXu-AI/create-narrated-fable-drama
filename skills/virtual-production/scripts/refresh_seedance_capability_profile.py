#!/usr/bin/env python3
"""Write the task's verified capability profile from the active local adapter."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

from narrated_fable_drama.core.paths import ProjectPaths
from narrated_fable_drama.providers import seedance

REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root


def refresh(task_dir: Path) -> dict[str, Any]:
    task_dir = task_dir.expanduser().resolve(strict=True)
    adapter_path = REPOSITORY_ROOT / "src/narrated_fable_drama/providers/seedance.py"
    if not adapter_path.is_file():
        raise RuntimeError("Current repository Seedance adapter is missing")
    model_id = seedance.model_id()
    value = {
        "contract": "seedance-capability-profile",
        "profile_status": "VERIFIED",
        "provider": "seedance",
        "model_id": model_id,
        "verified_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider_capabilities": {
            "minimum_segment_seconds": 4,
            "maximum_segment_seconds": 15,
            "maximum_reference_images": seedance.MAX_REFERENCE_IMAGES,
            "maximum_reference_videos": seedance.MAX_REFERENCE_VIDEOS,
            "maximum_reference_audios": seedance.MAX_REFERENCE_AUDIOS,
            "supported_resolutions": ["480p", "720p", "1080p", "4k"],
            "recommended_total_reference_minimum": 4,
            "recommended_total_reference_maximum": 5,
            "recommended_independently_referenced_performers_for_simple_composition": 4,
            "maximum_track_completion_reference_videos": 3,
            "maximum_track_completion_source_video_seconds": 15,
            "native_audio_generation": True,
            "native_background_audio_generation": True,
            "native_background_music_generation": True,
            "supported_reference_roles": [
                "reference_image", "reference_audio", "reference_video"
            ],
        },
        "project_generation_policy": {
            "maximum_total_seconds": 240,
            "one_task_per_segment": True,
            "supported_operations": [
                "text_to_video",
                "multimodal_reference",
                "video_extension",
            ],
            "predecessor_evidence_modes": [
                "none",
                "approved_complete_predecessor",
                "approved_provider_last_frame",
            ],
            "prompt_timing_policy": "event_order_without_precise_provider_time_ranges",
            "prompt_authoring_contract": (
                "skills/virtual-production/references/"
                "seedance-2-prompt-authoring-contract.md"
            ),
            "prompt_authoring_structure": "three_section_eight_element",
            "reference_token_policy": (
                "stable_provider_order_with_readable_noun_after_every_use"
            ),
            "prompt_internal_audit_required": True,
            "prompt_internal_audit_contract": (
                "seedance-prompt-internal-audit/v3"
            ),
            "provider_prompt_must_match_audited_hash": True,
            "camera_policy": "one_dominant_camera_move_per_shot",
            "seedance_generate_audio": True,
            "seedance_audio_mode": "original_audio_dialogue_replacement",
            "seedance_audio_use": (
                "retain_non_dialogue_original_audio_and_replace_all_character_speech"
            ),
            "seedance_speech_forbidden": True,
            "seedance_background_audio_retained": (
                "outside_dialogue_replacement_intervals"
            ),
            "seedance_audio_in_delivery": "non_dialogue_original_audio_only",
            "dialogue_source": "elevenlabs_final",
            "sound_effects_source": "seedance_native",
            "dialogue_gap_fill_source": (
                "digital_silence"
            ),
            "elevenlabs_usage_scope": "arabic_dialogue_only",
            "target_language": "Arabic",
            "extension_outgoing_trim_frames": 6,
            "extension_incoming_trim_frames": 1,
            "terminal_audio_fade_required": True,
            "default_background_music_source": "none",
            "background_music_prompt_notation": "forbidden",
            "continuity_reference_audio_policy": "strip_for_extension",
            "return_last_frame_required": True,
            "cross_clip_lipsync_dependency": False,
            "cross_clip_dialogue_dependency": False,
            "cross_clip_native_audio_dependency": "none",
            "maximum_direct_extension_hops_without_quality_reset": 0,
            "extension_quality_reset_strategy": "white_model_video_edit",
            "maximum_consecutive_predecessor_media_hops": 1,
            "require_strong_coverage_reset_after_predecessor_media": True,
            "strong_coverage_reset_opening_shot_sizes": [
                "extreme_close_up",
                "close_up",
                "medium_close_up",
            ],
        },
        "provider_adapter_path": adapter_path.relative_to(REPOSITORY_ROOT).as_posix(),
    }
    output = task_dir / "virtual-production" / "seedance-capability-profile.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, output)
    return {
        "status": "PASS",
        "output": output.relative_to(task_dir).as_posix(),
        "model_id": model_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = refresh(args.task_dir)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
