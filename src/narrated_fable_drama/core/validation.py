"""Shared validation errors and strict scalar normalizers."""

from __future__ import annotations

import re
from typing import Any


LABEL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
VIDEO_RESOLUTIONS = frozenset({"480p", "720p", "1080p", "4k"})


class StoryVideoError(RuntimeError):
    """Raised when a narrated-fable authority or artifact is invalid."""


def require_utf8_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StoryVideoError(f"{field} must be non-empty UTF-8 text.")
    normalized = value.strip()
    try:
        normalized.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise StoryVideoError(f"{field} must be valid UTF-8 text.") from exc
    return normalized


def normalize_video_resolution(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in VIDEO_RESOLUTIONS:
        raise StoryVideoError(
            f"Resolution must be one of {sorted(VIDEO_RESOLUTIONS)}."
        )
    return normalized
