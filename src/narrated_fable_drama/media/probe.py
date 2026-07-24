"""Shared FFprobe transport and stream selection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narrated_fable_drama.media.ffmpeg import MediaCommandError, require_binary, run


def fraction_as_float(value: str) -> float:
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    return float(value)


def probe_json(
    path: str | Path,
    *,
    count_frames: bool = False,
    timeout: float | None = None,
) -> dict[str, Any]:
    media = Path(path).expanduser().resolve()
    command = [
        require_binary("ffprobe"),
        "-v",
        "error",
        "-show_streams",
        "-show_format",
    ]
    if count_frames:
        command.append("-count_frames")
    command.extend(["-of", "json", str(media)])
    try:
        value = json.loads(
            run(
                command,
                context=f"ffprobe {media}",
                timeout=timeout,
            ).stdout
        )
    except (json.JSONDecodeError, MediaCommandError) as exc:
        raise MediaCommandError(f"Cannot inspect media: {media}") from exc
    if not isinstance(value, dict):
        raise MediaCommandError(f"ffprobe returned an invalid object: {media}")
    return value


def stream_by_type(
    payload: dict[str, Any],
    codec_type: str,
) -> dict[str, Any] | None:
    streams = payload.get("streams")
    if not isinstance(streams, list):
        return None
    return next(
        (
            item
            for item in streams
            if isinstance(item, dict) and item.get("codec_type") == codec_type
        ),
        None,
    )
