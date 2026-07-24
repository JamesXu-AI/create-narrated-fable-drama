#!/usr/bin/env python3
"""Run the complete current picture, native-sound, subtitle, and delivery finish."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from narrated_fable_drama.core.json_io import load_json_object
from narrated_fable_drama.core.project_context import load_project_context
from subtitles.subtitle_delivery import build
from subtitles.subtitle_style import DEFAULT_STYLE

from assemble_segment_videos import assemble
from post_timeline import TimelineError, probe_media


class FinishError(RuntimeError):
    """Raised when a task cannot be promoted to final delivery."""


def _load_project(task_dir: Path) -> dict[str, object]:
    payload = load_project_context(task_dir)
    if payload.get("speech_audio_source") != "seedance_native":
        raise FinishError("screenplay.md Speech Audio Source must be seedance_native")
    return payload


def _promote_clean_master(task_dir: Path, picture_lock: Path) -> Path:
    if not picture_lock.is_file() or picture_lock.stat().st_size <= 0:
        raise FinishError("Native picture lock is missing")
    probe = probe_media(picture_lock)
    if not probe.has_audio:
        raise FinishError("Native picture lock lacks Seedance native audio")
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


def finish(task_dir: Path, *, style_path: Path = DEFAULT_STYLE) -> dict[str, object]:
    task_dir = task_dir.expanduser().resolve()
    _load_project(task_dir)
    picture_lock = assemble(task_dir)
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
        audio_sources.get("seedance_background_music") is not True
        or audio_sources.get("background_music_source") != "seedance_native"
    ):
        raise FinishError(
            "Main final delivery must preserve Seedance-native background music"
        )
    boundary_qc = delivery_manifest.get("boundary_qc")
    if (
        not isinstance(boundary_qc, dict)
        or boundary_qc.get("pre_assembly_status") != "ready_for_picture_lock"
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
        "voice_audio_source": "speaker_reference_audio",
        "dialogue_source": "seedance",
        "native_background_audio_source": audio_sources.get(
            "native_background_audio_source"
        ),
        "seedance_background_music": audio_sources.get(
            "seedance_background_music"
        ),
        "background_music_source": audio_sources.get("background_music_source"),
        "boundary_qc_manifest": boundary_qc.get("manifest"),
        "boundary_repair_count": boundary_qc.get("planned_repair_count", 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE)
    args = parser.parse_args()
    try:
        result = finish(args.task_dir, style_path=args.style.expanduser().resolve())
    except (FinishError, TimelineError, OSError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
