"""Probe the clean master and render its captioned delivery variant."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.media.ffmpeg import (
    MediaCommandError,
    run as run_media_command,
)
from narrated_fable_drama.media.probe import probe_json, stream_by_type
from .subtitle_style import (
    ASS_PLAY_RESOLUTION_HEIGHT,
    SubtitleBuildError,
)


def _probe(path: Path) -> dict[str, Any]:
    try:
        value = probe_json(path)
    except MediaCommandError as exc:
        raise SubtitleBuildError(f"Could not probe media: {path}") from exc
    streams = value.get("streams")
    streams = streams if isinstance(streams, list) else []
    video = stream_by_type(value, "video")
    return {
        "duration_seconds": float(value.get("format", {}).get("duration", 0)),
        "width": int(video.get("width", 0)) if isinstance(video, dict) else 0,
        "height": int(video.get("height", 0)) if isinstance(video, dict) else 0,
        "video_stream_present": isinstance(video, dict),
        "audio_stream_present": any(item.get("codec_type") == "audio" for item in streams),
    }


def _clean_master(task_dir: Path) -> Path:
    candidate = task_dir / "finish-postproduction" / "final-clean-master.mp4"
    if not candidate.is_file() or candidate.stat().st_size <= 0:
        raise SubtitleBuildError("Missing final-clean-master.mp4.")
    return candidate.resolve()


def _ass_color(rgb: str) -> str:
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", rgb):
        raise SubtitleBuildError(f"Invalid subtitle color: {rgb}")
    red, green, blue = rgb[1:3], rgb[3:5], rgb[5:7]
    return f"&H00{blue}{green}{red}".upper()


def _filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_captioned_master(
    task_dir: Path,
    *,
    style: dict[str, Any],
    srt_path: Path,
) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    source = _clean_master(task_dir)
    source_probe = _probe(source)
    if not source_probe["video_stream_present"] or not source_probe["audio_stream_present"]:
        raise SubtitleBuildError("Clean master must contain video and audio streams.")
    delivery_root = task_dir / "finish-postproduction"
    delivery_root.mkdir(parents=True, exist_ok=True)
    clean_output = delivery_root / "final-clean-master.mp4"
    height = source_probe["height"]
    if height <= 0:
        raise SubtitleBuildError("Clean master has an invalid frame height.")
    # SRT is converted by libass on its 384x288 script canvas, then scaled to the
    # output frame. Express percentage-based style values in that coordinate space
    # so they are not multiplied by the output-height/script-height ratio twice.
    ass_scale = ASS_PLAY_RESOLUTION_HEIGHT / height
    font_size = max(
        12.0 * ass_scale,
        ASS_PLAY_RESOLUTION_HEIGHT
        * float(style["font_size_percent_of_frame_height"])
        / 100,
    )
    outline = max(
        1.0 * ass_scale,
        ASS_PLAY_RESOLUTION_HEIGHT
        * float(style["outline_width_percent_of_frame_height"])
        / 100,
    )
    margin_v = max(
        0.0,
        ASS_PLAY_RESOLUTION_HEIGHT * float(style["bottom_margin_percent"]) / 100,
    )
    force_style = ",".join(
        (
            f"FontName={style['font_family']}",
            f"FontSize={font_size:.3f}",
            f"PrimaryColour={_ass_color(str(style['text_color']))}",
            f"OutlineColour={_ass_color(str(style['outline_color']))}",
            f"Outline={outline:.3f}",
            "BorderStyle=1",
            "Alignment=2",
            f"MarginV={margin_v:.3f}",
        )
    )
    captioned = delivery_root / "final-captioned-master.mp4"
    filter_value = f"subtitles=filename='{_filter_path(srt_path)}':force_style='{force_style}'"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(clean_output),
        "-vf",
        filter_value,
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(captioned),
    ]
    try:
        run_media_command(command, context="Captioned-master render")
    except MediaCommandError as exc:
        raise SubtitleBuildError("Captioned-master render failed.") from exc
    captioned_probe = _probe(captioned)
    if (
        not captioned_probe["video_stream_present"]
        or not captioned_probe["audio_stream_present"]
        or abs(captioned_probe["duration_seconds"] - source_probe["duration_seconds"]) > 0.1
    ):
        raise SubtitleBuildError("Captioned master does not match clean-master duration/streams.")
    return clean_output, captioned, source_probe, captioned_probe
