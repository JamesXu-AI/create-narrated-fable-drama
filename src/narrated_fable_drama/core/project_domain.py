"""Fixed identity for the AI-narrated fable production workflow."""

from __future__ import annotations

import re
from typing import Any

PRODUCTION_TYPE = "ai_narrated_fable_drama"
ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1080p"
DEFAULT_VISUAL_STYLE = "3D Healing Animation"
SUPPORTED_RESOLUTIONS = frozenset({"480p", "720p", "1080p", "4k"})
TARGET_LANGUAGE = "Arabic"
TARGET_COUNTRY = "Saudi Arabia"
SPEECH_AUDIO_SOURCE = "elevenlabs_dubbed"
SOUND_EFFECTS_AUDIO_SOURCE = "seedance_native"
ARABIC_SCRIPT_RE = re.compile(
    r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]"
)
LATIN_LETTER_RE = re.compile(r"[A-Za-z]")


class ProjectDomainError(ValueError):
    """Raised when screenplay-owned project identity is invalid."""


def validate_arabic_dialogue(text: Any, *, context: str) -> str:
    """Require Arabic-only spoken authority while permitting digits/punctuation."""

    if not isinstance(text, str) or not text.strip():
        raise ProjectDomainError(f"{context} Arabic dialogue must be present.")
    normalized = text.strip()
    if ARABIC_SCRIPT_RE.search(normalized) is None:
        raise ProjectDomainError(f"{context} must contain Arabic-script dialogue.")
    if LATIN_LETTER_RE.search(normalized):
        raise ProjectDomainError(
            f"{context} must not mix Latin letters into Arabic dialogue."
        )
    return normalized


def validate_project_context(
    payload: Any, *, context: str = "screenplay.md"
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ProjectDomainError(f"{context} project context must be one mapping.")
    expected = {
        "production_type": PRODUCTION_TYPE,
        "aspect_ratio": ASPECT_RATIO,
        "target_language": TARGET_LANGUAGE,
        "target_country": TARGET_COUNTRY,
        "speech_audio_source": SPEECH_AUDIO_SOURCE,
        "sound_effects_audio_source": SOUND_EFFECTS_AUDIO_SOURCE,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ProjectDomainError(f"{context} {field} must be {value}.")
    resolution = payload.get("resolution")
    if resolution not in SUPPORTED_RESOLUTIONS:
        raise ProjectDomainError(
            f"{context} resolution must be one of "
            f"{sorted(SUPPORTED_RESOLUTIONS)}."
        )
    visual_style = payload.get("visual_style")
    if not isinstance(visual_style, str) or not visual_style.strip():
        raise ProjectDomainError(f"{context} Visual Style must be present.")
    return payload
