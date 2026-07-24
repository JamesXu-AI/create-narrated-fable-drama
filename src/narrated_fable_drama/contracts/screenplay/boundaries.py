"""Validate Shot grammar and authored adjacent-boundary semantics."""

from __future__ import annotations

from typing import Any

from narrated_fable_drama.contracts.screenplay.schema import (
    BEAT_ID_RE,
    INHERITED_VISUAL_PHASE_RE,
    STAGE_TABLEAU_RISK_RE,
    TIGHT_ATTENTION_VIEWS,
    WIDE_SCALE_VIEWS,
    concrete as _concrete,
)
from narrated_fable_drama.contracts.boundary import EDITORIAL_CUT_TYPES
from narrated_fable_drama.core.validation import StoryVideoError


def validate_cinematic_segment_contract(
    *,
    segment_id: str,
    scene_id: str,
    scene_contract: Any,
    shots: list[dict[str, Any]],
    known_beat_ids: set[str] | None = None,
) -> None:
    if not isinstance(scene_contract, dict) or scene_contract.get("scene_id") != scene_id:
        raise StoryVideoError(f"{segment_id} has an invalid Scene dramatic contract")
    for field in (
        "scene_purpose",
        "character_objective",
        "obstacle",
        "power_relationship",
        "turning_point",
        "outcome",
        "visual_progression",
        "exit_impulse",
    ):
        if not _concrete(scene_contract.get(field)):
            raise StoryVideoError(f"{segment_id} Scene contract {field} must be concrete")
    if not isinstance(shots, list) or not shots:
        raise StoryVideoError(f"{segment_id} must contain at least one authored Shot Beat")
    known = known_beat_ids if known_beat_ids is not None else set()
    for shot in shots:
        beat_id = shot.get("beat_id")
        if not isinstance(beat_id, str) or not BEAT_ID_RE.fullmatch(beat_id) or beat_id in known:
            raise StoryVideoError(f"{segment_id} repeats or invalidates a Beat ID")
        known.add(beat_id)
        if STAGE_TABLEAU_RISK_RE.search(str(shot.get("visual_action_en", ""))):
            raise StoryVideoError(f"{segment_id} contains stage-tableau action language")


def validate_adjacent_visual_boundary_contract(
    *,
    segment_id: str,
    predecessor_scene_id: str,
    current_scene_id: str,
    boundary: dict[str, Any],
    predecessor_final_shot: dict[str, Any],
    current_first_shot: dict[str, Any],
) -> None:
    incoming = boundary["handoff"]
    same_scene = predecessor_scene_id == current_scene_id
    if same_scene and incoming == "independent":
        raise StoryVideoError(f"{segment_id} shares a Scene with its predecessor and must be serial")
    if not same_scene and incoming in {"continuous_motion", "strong_coverage_reset"}:
        raise StoryVideoError(
            f"{segment_id} cannot use {incoming} across a Scene boundary"
        )
    if incoming == "continuous_motion":
        combined = " ".join(
            [
                boundary["continuity_handoff_en"],
                predecessor_final_shot["completion_state_en"],
                predecessor_final_shot["blocking_movement_en"],
            ]
        )
        if not INHERITED_VISUAL_PHASE_RE.search(combined):
            raise StoryVideoError(
                f"{segment_id} continuous_motion must name its unfinished inherited phase"
            )
    if incoming == "strong_coverage_reset":
        if predecessor_final_shot["completion_mode"] != "completed":
            raise StoryVideoError(
                f"{segment_id} strong_coverage_reset requires a settled predecessor"
            )
        if boundary["transition_type"] not in EDITORIAL_CUT_TYPES:
            raise StoryVideoError(
                f"{segment_id} strong_coverage_reset requires a decisive editorial cut"
            )
        if current_first_shot["scale_view"] not in TIGHT_ATTENTION_VIEWS:
            raise StoryVideoError(
                f"{segment_id} strong_coverage_reset must open on a close-up, "
                "reaction, insert, or POV attention beat"
            )


def _validate_predecessor_inheritance_budget(
    segments: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
) -> None:
    """Allow one predecessor-media boundary, then require a strong camera reset."""

    prior_same_scene_inherited = False
    inherited_modes = {"state_match", "continuous_motion"}
    for index, boundary in enumerate(boundaries):
        same_scene = (
            segments[index]["story_plan"]["scene_id"]
            == segments[index + 1]["story_plan"]["scene_id"]
        )
        if not same_scene:
            prior_same_scene_inherited = False
            continue
        handoff = boundary["handoff"]
        inherited = handoff in inherited_modes
        if prior_same_scene_inherited and handoff != "strong_coverage_reset":
            raise StoryVideoError(
                f"{segments[index + 1]['story_plan']['segment_id']} follows a "
                "predecessor-media boundary and must use strong_coverage_reset"
            )
        prior_same_scene_inherited = inherited


def _validate_shot_scale_grammar(segments: list[dict[str, Any]]) -> None:
    """Reject stage-like wide coverage while preserving authored shot judgment."""

    shots_by_scene: dict[str, list[dict[str, Any]]] = {}
    for segment in segments:
        scene_id = segment["story_plan"]["scene_id"]
        shots_by_scene.setdefault(scene_id, []).extend(segment["shots"])

    for scene_id, shots in shots_by_scene.items():
        if len(shots) >= 3 and not any(
            shot["scale_view"] in TIGHT_ATTENTION_VIEWS for shot in shots
        ):
            raise StoryVideoError(
                f"{scene_id} has three or more Shots but no close-up, reaction, "
                "insert, or POV attention beat"
            )
        consecutive_wide = 0
        for shot in shots:
            if shot["scale_view"] in WIDE_SCALE_VIEWS:
                consecutive_wide += 1
                if consecutive_wide >= 3:
                    raise StoryVideoError(
                        f"{scene_id} contains three consecutive establishing/wide "
                        "Shots and reads as stage-tableau coverage"
                    )
            else:
                consecutive_wide = 0
