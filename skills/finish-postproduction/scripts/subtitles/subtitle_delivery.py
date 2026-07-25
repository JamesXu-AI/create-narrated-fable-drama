"""Build subtitle deliverables and verify the final delivery contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from narrated_fable_drama.core.json_io import write_json_atomic
from narrated_fable_drama.core.project_context import load_project_context

from .subtitle_alignment import sha256_file
from .subtitle_compile import compile_cues
from .subtitle_files import (
    _write_subtitle_files,
)
from .subtitle_render import (
    render_captioned_master,
)
from .subtitle_style import (
    DEFAULT_STYLE,
    SubtitleBuildError,
    _load_json,
    _validate_style,
)


def build(task_dir: Path, style_path: Path, *, render: bool) -> dict[str, Any]:
    task_dir = task_dir.expanduser().resolve()
    style_path = style_path.expanduser().resolve()
    authority = compile_cues(task_dir, style_path)
    subtitle_dir = task_dir / "finish-postproduction" / "subtitles"
    cues_path, srt_path, vtt_path = _write_subtitle_files(subtitle_dir, authority)
    result: dict[str, Any] = {
        "status": "SUBTITLES_READY",
        "cue_count": authority["cue_count"],
        "subtitle_cues": str(cues_path),
        "srt": str(srt_path),
        "vtt": str(vtt_path),
    }
    if render:
        style = _load_json(style_path)
        _validate_style(style)
        clean, captioned, clean_probe, captioned_probe = render_captioned_master(
            task_dir, style=style, srt_path=srt_path
        )
        project_context = load_project_context(task_dir)
        if project_context.get("speech_audio_source") != "seedance_native":
            raise SubtitleBuildError(
                "screenplay.md must use seedance_native speech audio."
            )
        audio_timeline_path = (
            task_dir / ".pending" / "finish-postproduction" / "audio-timeline.json"
        )
        audio_timeline = _load_json(audio_timeline_path)
        if audio_timeline.get("seedance_background_music") is not True:
            raise SubtitleBuildError(
                "audio-timeline.json must declare seedance_background_music=true"
            )
        music_provider = audio_timeline.get("music_provider")
        if music_provider != "seedance":
            raise SubtitleBuildError(
                "Main final delivery requires music_provider=seedance"
            )
        if audio_timeline.get("background_music_source") != "seedance_native":
            raise SubtitleBuildError(
                "Main final delivery requires Seedance-native background music"
            )
        boundary_qc_path = (
            task_dir
            / ".pending"
            / "finish-postproduction"
            / "boundary-qc"
            / "boundary-qc-manifest.json"
        )
        boundary_qc = _load_json(boundary_qc_path)
        if (
            boundary_qc.get("pre_assembly_status") != "ready_for_picture_lock"
            or boundary_qc.get("final_timeline_status")
            != "technical_audit_complete"
        ):
            raise SubtitleBuildError(
                "Boundary QC must complete before clean/captioned delivery"
            )
        manifest = {
            "contract": "finish-final-delivery",
            "state": "FINAL_MASTER_READY",
            "clean_master": {
                "path": str(clean.resolve()),
                "sha256": sha256_file(clean),
            },
            "captioned_master": {
                "path": str(captioned.resolve()),
                "sha256": sha256_file(captioned),
            },
            "subtitles": {
                "cue_count": authority["cue_count"],
                "cues_path": str(cues_path.resolve()),
                "cues_sha256": sha256_file(cues_path),
                "srt_path": str(srt_path.resolve()),
                "srt_sha256": sha256_file(srt_path),
                "vtt_path": str(vtt_path.resolve()),
                "vtt_sha256": sha256_file(vtt_path),
                "text_authority": authority["text_authority"],
                "timing_authority": authority["timing_authority"],
                "alignment_evidence": authority["alignment_evidence"],
            },
            "duration_seconds": round(clean_probe["duration_seconds"], 3),
            "resolution": {
                "width": clean_probe["width"],
                "height": clean_probe["height"],
            },
            "video_stream_present": captioned_probe["video_stream_present"],
            "audio_stream_present": captioned_probe["audio_stream_present"],
            "audio_sources": {
                "voice_audio_source": "speaker_reference_audio",
                "dialogue_source": "seedance",
                "native_background_audio_source": "seedance_ambience_foley_and_music",
                "seedance_background_music": True,
                "background_music_source": "seedance_native",
                "generate_audio": True,
            },
            "audio_timeline": str(audio_timeline_path.resolve()),
            "model_repair_plan": boundary_qc.get("model_repair_plan"),
            "finish_evidence_manifest": boundary_qc.get("evidence_manifest"),
            "boundary_qc": {
                "manifest": str(boundary_qc_path.resolve()),
                "decision_authority": boundary_qc.get("decision_authority"),
                "pre_assembly_status": boundary_qc["pre_assembly_status"],
                "final_timeline_status": boundary_qc["final_timeline_status"],
                "planned_repair_count": boundary_qc.get(
                    "planned_repair_count", 0
                ),
                "source_segments_mutated": False,
            },
            "clean_captioned_duration_match": True,
        }
        manifest_path = (
            task_dir / "finish-postproduction" / "final-delivery-manifest.json"
        )
        write_json_atomic(manifest_path, manifest, sort_keys=True)
        result.update(
            {
                "status": "FINAL_MASTER_READY",
                "clean_master": str(clean),
                "captioned_master": str(captioned),
                "delivery_manifest": str(manifest_path),
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE)
    parser.add_argument(
        "--render-captioned",
        action="store_true",
        help=(
            "Render final-clean-master.mp4 and final-captioned-master.mp4 "
            "after subtitle compilation."
        ),
    )
    args = parser.parse_args()
    try:
        result = build(args.task_dir, args.style, render=args.render_captioned)
    except Exception as exc:
        print(
            json.dumps(
                {"status": "FAIL", "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
