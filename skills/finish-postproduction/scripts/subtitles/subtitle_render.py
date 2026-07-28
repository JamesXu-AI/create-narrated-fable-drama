"""Probe the clean master and render its captioned delivery variant."""

from __future__ import annotations

import hashlib
import math
import tempfile
from pathlib import Path
from typing import Any

from narrated_fable_drama.media.ffmpeg import MediaCommandError
from narrated_fable_drama.media.ffmpeg import run as run_media_command
from narrated_fable_drama.media.probe import probe_json, stream_by_type

from .subtitle_style import (
    SKILL_ROOT,
    SubtitleBuildError,
    _load_json,
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
        "audio_stream_present": any(
            item.get("codec_type") == "audio" for item in streams
        ),
    }


def _clean_master(task_dir: Path) -> Path:
    candidate = task_dir / "finish-postproduction" / "final-clean-master.mp4"
    if not candidate.is_file() or candidate.stat().st_size <= 0:
        raise SubtitleBuildError("Missing final-clean-master.mp4.")
    return candidate.resolve()


def _filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _resolve_bundled_font_file(
    font_asset: str,
    expected_sha256: str,
) -> Path:
    """Resolve one repository-owned font without system font fallback."""

    relative = Path(font_asset.strip())
    if (
        not relative.parts
        or relative.is_absolute()
        or ".." in relative.parts
        or relative.suffix.casefold() not in {".ttf", ".otf"}
    ):
        raise SubtitleBuildError(
            "Subtitle font asset must be a safe relative TTF/OTF path."
        )
    font_path = (SKILL_ROOT / relative).resolve()
    try:
        font_path.relative_to(SKILL_ROOT.resolve())
    except ValueError as exc:
        raise SubtitleBuildError(
            "Subtitle font asset escapes the finish-postproduction Skill."
        ) from exc
    if not font_path.is_file() or font_path.stat().st_size <= 0:
        raise SubtitleBuildError(
            f"Bundled Arabic subtitle font is missing: {font_path}"
        )
    actual_sha256 = hashlib.sha256(font_path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise SubtitleBuildError(
            "Bundled Arabic subtitle font hash does not match subtitle style."
        )
    return font_path


def _require_raqm() -> None:
    try:
        from PIL import features
    except ImportError as exc:
        raise SubtitleBuildError(
            "Pillow is required for shaped Arabic subtitle rendering. "
            "Install the project dependencies with `python3 -m pip install -e .`."
        ) from exc
    if not features.check_feature("raqm"):
        raise SubtitleBuildError(
            "Pillow RAQM support is required for Arabic subtitle shaping. "
            "Install a Pillow wheel with RAQM and the FriBiDi runtime library."
        )


def _select_font_weight(font: Any, font_weight: str) -> None:
    requested = font_weight.strip().casefold()
    variation_name = {
        "normal": "Regular",
        "regular": "Regular",
        "semibold": "SemiBold",
        "bold": "Bold",
    }.get(requested)
    if variation_name is None:
        raise SubtitleBuildError(f"Unsupported subtitle font weight: {font_weight}")
    try:
        available = {
            value.decode("utf-8") if isinstance(value, bytes) else str(value)
            for value in font.get_variation_names()
        }
    except (AttributeError, OSError):
        available = set()
    if available:
        if variation_name not in available:
            raise SubtitleBuildError(
                f"Bundled subtitle font lacks the {variation_name} variation."
            )
        try:
            font.set_variation_by_name(variation_name)
        except (OSError, ValueError) as exc:
            raise SubtitleBuildError(
                f"Could not select bundled subtitle font weight: {variation_name}"
            ) from exc


def _render_cue_overlay(
    cue: dict[str, Any],
    *,
    output_path: Path,
    frame_width: int,
    frame_height: int,
    style: dict[str, Any],
    font_path: Path,
) -> tuple[int, int]:
    """Render one shaped Arabic cue into a tightly bounded RGBA overlay."""

    _require_raqm()
    try:
        from PIL import Image, ImageColor, ImageDraw, ImageFont
    except ImportError as exc:
        raise SubtitleBuildError(
            "Pillow is required for shaped Arabic subtitle rendering. "
            "Install the project dependencies with `python3 -m pip install -e .`."
        ) from exc
    text = str(cue.get("rendered_text") or "")
    if not text.strip():
        raise SubtitleBuildError("Subtitle cue has empty rendered text.")
    font_size = max(
        12,
        int(
            round(
                frame_height
                * float(style["font_size_percent_of_frame_height"])
                / 100.0
            )
        ),
    )
    outline_width = max(
        1,
        int(
            round(
                frame_height
                * float(style["outline_width_percent_of_frame_height"])
                / 100.0
            )
        ),
    )
    try:
        font = ImageFont.truetype(
            str(font_path),
            font_size,
            layout_engine=ImageFont.Layout.RAQM,
        )
        _select_font_weight(font, str(style["font_weight"]))
        font_family = str(font.getname()[0])
        if font_family.casefold() != str(style["font_family"]).strip().casefold():
            raise SubtitleBuildError(
                "Bundled subtitle font family does not match subtitle style: "
                f"expected={style['font_family']}, actual={font_family}"
            )
        text_color = ImageColor.getrgb(str(style["text_color"]))
        outline_color = ImageColor.getrgb(str(style["outline_color"]))
    except SubtitleBuildError:
        raise
    except (OSError, ValueError) as exc:
        raise SubtitleBuildError(
            "Could not load the explicit Arabic subtitle font/style."
        ) from exc
    spacing = max(2, int(round(font_size * 0.15)))
    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        spacing=spacing,
        align="center",
        direction="rtl",
        language="ar",
        stroke_width=outline_width,
    )
    padding = outline_width + 2
    overlay_width = int(math.ceil(bbox[2] - bbox[0])) + padding * 2
    overlay_height = int(math.ceil(bbox[3] - bbox[1])) + padding * 2
    if (
        overlay_width <= 0
        or overlay_height <= 0
        or overlay_width > frame_width
        or overlay_height > frame_height
    ):
        raise SubtitleBuildError("Arabic subtitle overlay exceeds the frame.")
    overlay = Image.new(
        "RGBA",
        (overlay_width, overlay_height),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(overlay)
    draw.multiline_text(
        (padding - bbox[0], padding - bbox[1]),
        text,
        font=font,
        fill=(*text_color, 255),
        spacing=spacing,
        align="center",
        direction="rtl",
        language="ar",
        stroke_width=outline_width,
        stroke_fill=(*outline_color, 255),
    )
    overlay.save(output_path)
    x = (frame_width - overlay_width) // 2
    bottom_margin = int(
        round(frame_height * float(style["bottom_margin_percent"]) / 100.0)
    )
    y = frame_height - bottom_margin - overlay_height
    if x < 0 or y < 0:
        raise SubtitleBuildError("Arabic subtitle safe-area placement is invalid.")
    return x, y


def _caption_filter(
    cues: list[dict[str, Any]],
    *,
    overlay_dir: Path,
    frame_width: int,
    frame_height: int,
    style: dict[str, Any],
    font_path: Path,
) -> tuple[str, str]:
    filters = ["[0:v]setpts=PTS-STARTPTS[v0]"]
    prior_output = "v0"
    for index, cue in enumerate(cues, start=1):
        start = float(cue.get("timeline_start_seconds"))
        end = float(cue.get("timeline_end_seconds"))
        if end <= start:
            raise SubtitleBuildError("Subtitle cue has an invalid render interval.")
        overlay_path = overlay_dir / f"cue-{index:03d}.png"
        x, y = _render_cue_overlay(
            cue,
            output_path=overlay_path,
            frame_width=frame_width,
            frame_height=frame_height,
            style=style,
            font_path=font_path,
        )
        image_label = f"cue{index}"
        output_label = f"v{index}"
        filters.append(
            f"movie=filename='{_filter_path(overlay_path)}',format=rgba"
            f"[{image_label}]"
        )
        filters.append(
            f"[{prior_output}][{image_label}]"
            f"overlay={x}:{y}:"
            f"enable='between(t,{start:.6f},{end:.6f})'"
            f"[{output_label}]"
        )
        prior_output = output_label
    return ";".join(filters), prior_output


def render_captioned_master(
    task_dir: Path,
    *,
    style: dict[str, Any],
    srt_path: Path,
) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    source = _clean_master(task_dir)
    source_probe = _probe(source)
    if (
        not source_probe["video_stream_present"]
        or not source_probe["audio_stream_present"]
    ):
        raise SubtitleBuildError("Clean master must contain video and audio streams.")
    delivery_root = task_dir / "finish-postproduction"
    delivery_root.mkdir(parents=True, exist_ok=True)
    clean_output = delivery_root / "final-clean-master.mp4"
    height = source_probe["height"]
    if height <= 0:
        raise SubtitleBuildError("Clean master has an invalid frame height.")
    font_path = _resolve_bundled_font_file(
        str(style["font_asset"]),
        str(style["font_sha256"]),
    )
    cues_payload = _load_json(srt_path.with_name("subtitle-cues.json"))
    raw_cues = cues_payload.get("cues")
    if not isinstance(raw_cues, list) or not raw_cues:
        raise SubtitleBuildError("Subtitle cue authority is missing for rendering.")
    cues = [cue for cue in raw_cues if isinstance(cue, dict)]
    if len(cues) != len(raw_cues):
        raise SubtitleBuildError("Subtitle cue authority contains an invalid cue.")
    captioned = delivery_root / "final-captioned-master.mp4"
    pending_root = (
        task_dir / ".pending" / "finish-postproduction"
    )
    pending_root.mkdir(parents=True, exist_ok=True)
    temporary_output = delivery_root / ".final-captioned-master.tmp.mp4"
    with tempfile.TemporaryDirectory(
        prefix=".subtitle-render-",
        dir=pending_root,
    ) as temporary:
        filter_value, video_label = _caption_filter(
            cues,
            overlay_dir=Path(temporary),
            frame_width=source_probe["width"],
            frame_height=height,
            style=style,
            font_path=font_path,
        )
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(clean_output),
            "-filter_complex",
            filter_value,
            "-map",
            f"[{video_label}]",
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
            str(temporary_output),
        ]
        try:
            run_media_command(command, context="Captioned-master render")
        except MediaCommandError as exc:
            raise SubtitleBuildError("Captioned-master render failed.") from exc
    captioned_probe = _probe(temporary_output)
    if (
        not captioned_probe["video_stream_present"]
        or not captioned_probe["audio_stream_present"]
        or abs(
            captioned_probe["duration_seconds"]
            - source_probe["duration_seconds"]
        )
        > 0.1
    ):
        temporary_output.unlink(missing_ok=True)
        raise SubtitleBuildError(
            "Captioned master does not match clean-master duration/streams."
        )
    temporary_output.replace(captioned)
    return clean_output, captioned, source_probe, captioned_probe
