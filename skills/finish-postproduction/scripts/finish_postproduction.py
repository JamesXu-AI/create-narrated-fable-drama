#!/usr/bin/env python3
"""Run the complete picture, Arabic dubbing, subtitle, and delivery finish."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from narrated_fable_drama.core.json_io import load_json_object
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.core.project_domain import SPEECH_AUDIO_SOURCE
from subtitles.subtitle_delivery import build
from subtitles.subtitle_style import DEFAULT_STYLE

from assemble_segment_videos import assemble
from finishing.plan import RepairPlanError
from post_timeline import TimelineError, probe_media


class FinishError(RuntimeError):
    """Raised when a task cannot be promoted to final delivery."""


def _load_project(task_dir: Path) -> dict[str, object]:
    payload = load_project_context(task_dir)
    if payload.get("speech_audio_source") != SPEECH_AUDIO_SOURCE:
        raise FinishError(
            f"screenplay.md Speech Audio Source must be {SPEECH_AUDIO_SOURCE}"
        )
    return payload


def _promote_clean_master(task_dir: Path, picture_lock: Path) -> Path:
    if not picture_lock.is_file() or picture_lock.stat().st_size <= 0:
        raise FinishError("Dubbed picture lock is missing")
    probe = probe_media(picture_lock)
    if not probe.has_audio:
        raise FinishError("Picture lock lacks ElevenLabs dubbed audio")
    delivery_root = task_dir / "finish-postproduction"
    delivery_root.mkdir(parents=True, exist_ok=True)
    clean = delivery_root / "final-clean-master.mp4"
    temporary = (
        task_dir
        / ".pending"
        / "finish-postproduction"
        / "post-production"
        / ".final-clean-master.mp4.tmp"
    )
    temporary.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(picture_lock, temporary)
    temporary.replace(clean)
    return clean


def finish(
    task_dir: Path,
    *,
    repair_plan_path: Path,
    evidence_manifest_path: Path,
    style_path: Path = DEFAULT_STYLE,
) -> dict[str, object]:
    task_dir = task_dir.expanduser().resolve()
    _load_project(task_dir)
    picture_lock = assemble(
        task_dir,
        repair_plan_path=repair_plan_path,
        evidence_manifest_path=evidence_manifest_path,
    )
    clean = _promote_clean_master(task_dir, picture_lock)
    result = build(task_dir, style_path, render=True)
    if result.get("status") != "FINAL_MASTER_READY":
        raise FinishError("Subtitle/delivery finish did not produce FINAL_MASTER_READY")
    delivery_root = task_dir / "finish-postproduction"
    manifest_path = delivery_root / "final-delivery-manifest.json"
    if not manifest_path.is_file() or manifest_path.stat().st_size <= 0:
        raise FinishError("Final delivery manifest is missing")
    delivery_manifest = load_json_object(
        manifest_path,
        label="final delivery manifest",
        error_type=FinishError,
    )
    audio_sources = delivery_manifest.get("audio_sources")
    if not isinstance(audio_sources, dict):
        raise FinishError("Final delivery manifest lacks audio source declarations")
    if (
        audio_sources.get("voice_audio_source") != "elevenlabs_voice_id"
        or audio_sources.get("dialogue_source") != "elevenlabs"
        or audio_sources.get("seedance_speech_in_delivery") is not False
        or audio_sources.get("seedance_generate_audio") is not True
        or audio_sources.get("seedance_audio_in_delivery") is not True
        or audio_sources.get("seedance_audio_use")
        != (
            "non_dialogue_original_audio_after_character_"
            "speech_replacement"
        )
        or audio_sources.get("native_background_audio_source")
        != (
            "seedance_original_nondialogue_and_native_gap_fill"
        )
    ):
        raise FinishError("Main final delivery must preserve ElevenLabs Arabic dubbing")
    boundary_qc = delivery_manifest.get("boundary_qc")
    if (
        not isinstance(boundary_qc, dict)
        or boundary_qc.get("pre_assembly_status") != "ready_for_picture_lock"
        or boundary_qc.get("decision_authority")
        != "editor-restoration-master-model"
        or boundary_qc.get("final_timeline_status")
        != "technical_audit_complete"
        or boundary_qc.get("source_segments_mutated") is not False
    ):
        raise FinishError("Final delivery lacks a completed reversible boundary QC audit")
    return {
        "status": "FINAL_MASTER_READY",
        "clean_master": str(clean.resolve()),
        "captioned_master": str((delivery_root / "final-captioned-master.mp4").resolve()),
        "srt": str((delivery_root / "subtitles" / "master.srt").resolve()),
        "vtt": str((delivery_root / "subtitles" / "master.vtt").resolve()),
        "manifest": str(manifest_path.resolve()),
        "voice_audio_source": "elevenlabs_voice_id",
        "dialogue_source": "elevenlabs",
        "native_background_audio_source": audio_sources.get(
            "native_background_audio_source"
        ),
        "seedance_generate_audio": audio_sources.get("seedance_generate_audio"),
        "seedance_audio_in_delivery": audio_sources.get(
            "seedance_audio_in_delivery"
        ),
        "seedance_speech_in_delivery": audio_sources.get(
            "seedance_speech_in_delivery"
        ),
        "background_music_source": audio_sources.get("background_music_source"),
        "boundary_qc_manifest": boundary_qc.get("manifest"),
        "boundary_repair_count": boundary_qc.get("planned_repair_count", 0),
        "model_repair_plan": str(repair_plan_path.expanduser().resolve()),
        "evidence_manifest": str(evidence_manifest_path.expanduser().resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--repair-plan", required=True, type=Path)
    parser.add_argument("--evidence-manifest", required=True, type=Path)
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE)
    args = parser.parse_args()
    try:
        result = finish(
            args.task_dir,
            repair_plan_path=args.repair_plan,
            evidence_manifest_path=args.evidence_manifest,
            style_path=args.style.expanduser().resolve(),
        )
    except (FinishError, TimelineError, RepairPlanError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
