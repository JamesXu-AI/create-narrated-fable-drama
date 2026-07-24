"""Compile authored transition semantics into executable boundary behavior.

The screenplay owns why an edit exists.  This module is the single deterministic
projection from that authored meaning to generation, finishing, and review
contracts.  It deliberately does not judge generated pixels or sound.
"""

from __future__ import annotations

from typing import Any


EDITORIAL_CUT_TYPES = {
    "hard_cut",
    "action_cut",
    "match_cut",
    "eyeline_cut",
    "reaction_cut",
}
TEMPORAL_TRANSITION_TYPES = {"dissolve", "fade"}
BAKED_TRANSITION_TYPES = {
    "animated_wipe",
    "animated_morph",
    "animated_match",
    "effects_wipe",
    "light_flash_transition",
    "particle_bridge",
    "environmental_transition",
}
DESIGNED_TRANSITION_TYPES = TEMPORAL_TRANSITION_TYPES | BAKED_TRANSITION_TYPES
AUTHORING_TRANSITION_TYPES = (
    EDITORIAL_CUT_TYPES | DESIGNED_TRANSITION_TYPES | {"final_end"}
)

# Review accepts a few transport aliases emitted by older evidence callers. They
# are normalized only for evidence rendering and are not valid screenplay
# authoring vocabulary.
REVIEW_CUT_LIKE_TRANSITION_TYPES = EDITORIAL_CUT_TYPES | {"editorial_cut"}
REVIEW_DISSOLVE_TRANSITION_TYPES = {"dissolve", "cross_dissolve"}
REVIEW_FADE_TRANSITION_TYPES = {"fade", "fade_to_black"}
REVIEW_BAKED_TRANSITION_TYPES = set(BAKED_TRANSITION_TYPES)
SUPPORTED_REVIEW_TRANSITION_TYPES = (
    REVIEW_CUT_LIKE_TRANSITION_TYPES
    | REVIEW_DISSOLVE_TRANSITION_TYPES
    | REVIEW_FADE_TRANSITION_TYPES
    | REVIEW_BAKED_TRANSITION_TYPES
)
NON_CUT_REVIEW_TRANSITION_CLASSES = {"dissolve", "fade", "baked_effect"}

AUTOMATIC_COLOR_MATCH_PICTURE_EDIT_MODES = {"hard_cut"}
COLOR_MATCH_EXCLUDED_BOUNDARY_CLASSES = {"designed_transition", "scene_change"}

DEFAULT_TRANSITION_SECONDS = {
    "dissolve": 0.8,
    "fade": 0.6,
}

MOTIVATED_CUT_ALLOWED_CHANGES = [
    "camera_angle",
    "lens",
    "shot_size",
    "composition",
    "focus",
    "visible_background",
    "exposure",
]

SEMANTIC_CONTINUITY_CHECKS = [
    "character_identity",
    "character_relationships",
    "costume_and_appearance_state",
    "injury_and_body_state",
    "prop_ownership_and_state",
    "emotional_and_knowledge_state",
    "event_causality_and_time_order",
    "location_screen_geography",
    "eyeline_and_axis_legibility",
    "motivated_light_direction",
    "native_audio_no_click_dropout_or_restart",
]


class BoundaryExecutionError(ValueError):
    """Raised when authored transition data cannot produce a safe execution."""


def classify_review_transition(transition_type: str) -> str:
    """Classify one evidence-rendering transition without inventing aliases."""

    if transition_type in REVIEW_DISSOLVE_TRANSITION_TYPES:
        return "dissolve"
    if transition_type in REVIEW_FADE_TRANSITION_TYPES:
        return "fade"
    if transition_type in REVIEW_CUT_LIKE_TRANSITION_TYPES:
        return "motivated_cut"
    if transition_type in REVIEW_BAKED_TRANSITION_TYPES:
        return "baked_effect"
    raise BoundaryExecutionError(
        f"Unsupported boundary transition: {transition_type}"
    )


def classify_boundary(
    *,
    transition_type: str,
    from_scene_id: str,
    to_scene_id: str,
    successor_incoming_visual_requirement: str | None = None,
) -> str:
    """Return the semantic boundary class without inspecting generated media."""

    incoming_visual_requirement = successor_incoming_visual_requirement
    if incoming_visual_requirement is None:
        raise BoundaryExecutionError(
            "incoming_visual_requirement must be authored explicitly; boundary "
            "execution cannot default to independence"
        )
    if incoming_visual_requirement not in {
        "independent",
        "state_match",
        "continuous_motion",
        "strong_coverage_reset",
    }:
        raise BoundaryExecutionError(
            f"Unsupported incoming visual requirement: {incoming_visual_requirement}"
        )
    same_scene = from_scene_id == to_scene_id
    if same_scene and incoming_visual_requirement == "independent":
        raise BoundaryExecutionError(
            "same-Scene Segment boundaries must be serial: use state_match for "
            "one soft last-frame inheritance, continuous_motion for one "
            "white-model predecessor extension, or strong_coverage_reset for the "
            "required reference-free camera break"
        )

    if incoming_visual_requirement == "continuous_motion":
        if not same_scene:
            raise BoundaryExecutionError(
                "continuous_motion cannot cross a Scene boundary"
            )
        if transition_type not in EDITORIAL_CUT_TYPES:
            raise BoundaryExecutionError(
                "continuous_motion requires a cut-like authored transition"
            )
        return "continuous_action"
    if incoming_visual_requirement == "strong_coverage_reset":
        if not same_scene:
            raise BoundaryExecutionError(
                "strong_coverage_reset is only for a same-Scene reference-free cut"
            )
        if transition_type not in EDITORIAL_CUT_TYPES:
            raise BoundaryExecutionError(
                "strong_coverage_reset requires a hard/action/match/eyeline/reaction cut"
            )
        return "motivated_cut"
    if transition_type in DESIGNED_TRANSITION_TYPES:
        return "designed_transition"
    if from_scene_id != to_scene_id:
        return "scene_change"
    if transition_type in EDITORIAL_CUT_TYPES:
        return "motivated_cut"
    raise BoundaryExecutionError(f"Unsupported boundary transition: {transition_type}")


def build_boundary_execution(
    *,
    transition_type: str,
    from_scene_id: str,
    to_scene_id: str,
    successor_incoming_visual_requirement: str | None = None,
) -> dict[str, Any]:
    """Project one authored boundary into generation, finishing, and review rules."""

    incoming_visual_requirement = successor_incoming_visual_requirement
    if incoming_visual_requirement is None:
        raise BoundaryExecutionError(
            "incoming_visual_requirement must be authored explicitly; boundary "
            "execution cannot default to independence"
        )
    transition_class = classify_boundary(
        transition_type=transition_type,
        from_scene_id=from_scene_id,
        to_scene_id=to_scene_id,
        successor_incoming_visual_requirement=incoming_visual_requirement,
    )
    duration = DEFAULT_TRANSITION_SECONDS.get(transition_type, 0.0)

    if transition_class == "continuous_action":
        visual_dependency = "screenplay_continuous_motion_requirement"
        # The predecessor-video reference controls how the successor is generated;
        # it is not a separate postproduction edit mode.  The generated successor
        # clip starts at the authored continuation point, so finishing joins the
        # two accepted clips with an ordinary zero-overlap cut.
        picture_edit = "hard_cut"
        audio_edit = "native_clean_cut"
        media_dependency = "predecessor_video"
        continuation_reference_mode = "predecessor_video_reference"
        reference_authority = "approved_complete_direct_predecessor_video"
    elif transition_class == "motivated_cut":
        picture_edit = "hard_cut"
        audio_edit = "native_continuity_declick"
        if incoming_visual_requirement == "strong_coverage_reset":
            visual_dependency = "semantic_state_only_strong_coverage_reset"
            media_dependency = "none"
            continuation_reference_mode = "none"
            reference_authority = "current_location_identity_assets_only"
        else:
            visual_dependency = "same_scene_location_master_context"
            media_dependency = "predecessor_provider_last_frame_reference_image"
            continuation_reference_mode = "first_frame_reference"
            reference_authority = "soft_reference_image_not_strict_first_frame"
    elif transition_class == "scene_change":
        visual_dependency = "new_scene_location_master_context"
        picture_edit = "hard_cut"
        audio_edit = "native_clean_cut"
        media_dependency = "none"
        continuation_reference_mode = "none"
        reference_authority = "none"
    else:
        visual_dependency = "clip_local_transition_handle"
        media_dependency = "none"
        continuation_reference_mode = "none"
        reference_authority = "none"
        if transition_type == "dissolve":
            picture_edit = "dissolve"
            audio_edit = "equal_power_acrossfade"
        elif transition_type == "fade":
            picture_edit = "fade"
            audio_edit = "equal_power_acrossfade"
        else:
            picture_edit = "baked_effect"
            audio_edit = "native_clean_cut"

    if incoming_visual_requirement == "state_match":
        visual_dependency = "screenplay_state_match_requirement"
        if from_scene_id == to_scene_id:
            media_dependency = "predecessor_provider_last_frame_reference_image"
            continuation_reference_mode = "first_frame_reference"
            reference_authority = "soft_reference_image_not_strict_first_frame"
        else:
            media_dependency = "storyboard_decides_nonadjacent_state_authority"
            continuation_reference_mode = "state_reference"
            reference_authority = "declared_earlier_scene_state"

    return {
        "schema_version": "boundary-execution/v3",
        "authored_transition_type": transition_type,
        "transition_class": transition_class,
        "incoming_visual_requirement": incoming_visual_requirement,
        "visual_dependency_mode": visual_dependency,
        "media_dependency": media_dependency,
        "continuation_reference_mode": continuation_reference_mode,
        "reference_authority": reference_authority,
        "picture_edit_mode": picture_edit,
        "audio_edit_mode": audio_edit,
        "transition_duration_seconds": duration,
        "audio_edge_fade_seconds": (
            0.01 if audio_edit == "native_continuity_declick" else 0.0
        ),
        "allowed_visual_changes": (
            list(MOTIVATED_CUT_ALLOWED_CHANGES)
            if transition_class in {"motivated_cut", "scene_change"}
            else []
        ),
        "required_semantic_continuity_checks": list(SEMANTIC_CONTINUITY_CHECKS),
    }


def build_story_plan_boundaries(
    story_plans: list[dict[str, Any]],
    authored_boundaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compile authored boundaries without creating screenplay content."""

    if len(authored_boundaries) != max(0, len(story_plans) - 1):
        raise BoundaryExecutionError(
            "Authored boundary coverage differs from Segment adjacency"
        )
    boundaries: list[dict[str, Any]] = []
    for index in range(1, len(story_plans)):
        predecessor = story_plans[index - 1]
        current = story_plans[index]
        authored = authored_boundaries[index - 1]
        if (
            authored.get("from_segment_id") != predecessor["segment_id"]
            or authored.get("to_segment_id") != current["segment_id"]
        ):
            raise BoundaryExecutionError(
                "Authored boundary does not match adjacent Segment IDs"
            )
        boundaries.append(
            {
                "from": predecessor["segment_id"],
                "to": current["segment_id"],
                "transition_design": authored,
                "execution": build_boundary_execution(
                    transition_type=authored["transition_type"],
                    from_scene_id=predecessor["scene_id"],
                    to_scene_id=current["scene_id"],
                    successor_incoming_visual_requirement=authored["handoff"],
                ),
                "native_audio_dependency": "none",
            }
        )
    return boundaries
