"""Classify authored boundary semantics without choosing an edit strategy.

The screenplay owns why a boundary exists. Actual picture and sound execution is
selected later by the Editor and Restoration Master model from real-media
evidence.
"""

from __future__ import annotations

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
