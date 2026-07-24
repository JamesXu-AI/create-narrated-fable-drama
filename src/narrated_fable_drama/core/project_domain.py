"""Fixed identity for the AI-narrated fable production workflow."""

from __future__ import annotations

from typing import Any


PRODUCTION_TYPE = "ai_narrated_fable_drama"
ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1080p"
DEFAULT_VISUAL_STYLE = "3D Healing Animation"
SUPPORTED_RESOLUTIONS = frozenset({"480p", "720p", "1080p", "4k"})
NATIVE_AUDIO_SOURCE = "seedance_native"


class ProjectDomainError(ValueError):
    """Raised when screenplay-owned project identity is invalid."""


def validate_project_context(
    payload: Any, *, context: str = "screenplay.md"
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ProjectDomainError(f"{context} project context must be one mapping.")
    expected = {
        "production_type": PRODUCTION_TYPE,
        "aspect_ratio": ASPECT_RATIO,
        "speech_audio_source": NATIVE_AUDIO_SOURCE,
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
    country = payload.get("target_country")
    language = payload.get("target_language")
    if not isinstance(country, str) or not country.strip():
        raise ProjectDomainError(f"{context} Target Country must be present.")
    if not isinstance(language, str) or not language.strip():
        raise ProjectDomainError(f"{context} Target Language must be present.")
    return payload
