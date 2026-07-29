"""Shared visual-authority policy for screenplay-owned story objects."""

from __future__ import annotations

from typing import Any

VISUAL_CONTROL_TRIGGERS = frozenset(
    {
        "recurring_identity",
        "detail_view",
        "state_change",
        "interaction_geometry",
        "distinctive_identity",
    }
)
DEDICATED_ASSET_TRIGGERS = frozenset(
    {
        "detail_view",
        "state_change",
        "interaction_geometry",
    }
)
VISUAL_AUTHORITY_MODES = frozenset(
    {
        "dedicated_asset",
        "covered_by_asset",
        "segment_prompt_only",
    }
)


def requires_dedicated_visual_asset(story_object: dict[str, Any]) -> bool:
    """Return whether the authored control facts require a dedicated image asset."""

    triggers = set(story_object["visual_control_triggers"])
    if not triggers:
        return False
    if story_object["physical_owner_kind"] == "independent":
        return True
    return bool(triggers.intersection(DEDICATED_ASSET_TRIGGERS))


def expected_visual_authority_mode(
    story_object: dict[str, Any],
    *,
    parent_mode: str | None = None,
) -> str:
    """Route one Story Object without inventing story- or asset-specific rules."""

    owner_kind = story_object["physical_owner_kind"]
    triggers = story_object["visual_control_triggers"]
    parent_cannot_cover_control = (
        owner_kind == "object"
        and parent_mode == "segment_prompt_only"
        and bool(triggers)
    )
    if (
        requires_dedicated_visual_asset(story_object)
        or parent_cannot_cover_control
    ):
        return "dedicated_asset"
    if owner_kind == "independent" or (
        owner_kind == "object" and parent_mode == "segment_prompt_only"
    ):
        return "segment_prompt_only"
    return "covered_by_asset"
