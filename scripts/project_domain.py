"""Fixed project identity for forest-animal educational story production."""

from __future__ import annotations

from typing import Any


STORY_DOMAIN_PROFILE = "forest_animal_education"
VISUAL_STYLE_PROFILE = "soft_cute_3d_healing_animation"


class ProjectDomainError(ValueError):
    """Raised when a task does not belong to this specialized project."""


def validate_project_profiles(
    payload: Any, *, context: str = "task.json"
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ProjectDomainError(f"{context} must contain one JSON object.")
    if payload.get("story_domain_profile") != STORY_DOMAIN_PROFILE:
        raise ProjectDomainError(
            f"{context} story_domain_profile must be {STORY_DOMAIN_PROFILE}."
        )
    if payload.get("visual_style_profile") != VISUAL_STYLE_PROFILE:
        raise ProjectDomainError(
            f"{context} visual_style_profile must be {VISUAL_STYLE_PROFILE}."
        )
    return payload
