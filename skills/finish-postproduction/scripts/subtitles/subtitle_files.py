"""Write JSON, SRT, and VTT artifacts from compiled subtitle authority."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from narrated_fable_drama.core.json_io import write_json_atomic
from .subtitle_style import (
    _format_srt,
    _format_vtt,
)


def _write_subtitle_files(output_dir: Path, authority: dict[str, Any]) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cues_path = output_dir / "subtitle-cues.json"
    srt_path = output_dir / "master.srt"
    vtt_path = output_dir / "master.vtt"
    write_json_atomic(cues_path, authority, sort_keys=True)
    srt_blocks = []
    vtt_blocks = ["WEBVTT", ""]
    for cue in authority["cues"]:
        index = cue["cue_index"]
        start = cue["timeline_start_seconds"]
        end = cue["timeline_end_seconds"]
        text = cue["rendered_text"]
        srt_blocks.append(
            f"{index}\n{_format_srt(start)} --> {_format_srt(end)}\n{text}"
        )
        vtt_blocks.append(
            f"{index}\n{_format_vtt(start)} --> {_format_vtt(end)}\n{text}\n"
        )
    srt_path.write_text("\n\n".join(srt_blocks) + ("\n" if srt_blocks else ""), encoding="utf-8")
    vtt_path.write_text("\n".join(vtt_blocks), encoding="utf-8")
    return cues_path, srt_path, vtt_path
