"""Validate sticky diegetic presence and visibility state authority."""

from __future__ import annotations

from typing import Any

from narrated_fable_drama.contracts.screenplay.schema import (
    DIEGETIC_PRESENCE_STATES,
    SEGMENT_ID_RE,
    VISIBILITY_REQUIREMENTS,
    concrete as _concrete,
    present as _present,
)
from narrated_fable_drama.core.validation import StoryVideoError


def _validate_character_scene_states(screenplay: dict[str, Any]) -> None:
    """Validate sticky diegetic presence and non-downgradable visibility authority."""

    entities = {item["entity_id"]: item for item in screenplay["characters"]}
    segments = screenplay["segments"]
    segment_map = {
        item["story_plan"]["segment_id"]: item for item in segments
    }
    scene_map = {item["scene_id"]: item for item in screenplay["scenes"]}
    rows = screenplay["character_scene_states"]
    row_map: dict[tuple[str, str], dict[str, Any]] = {}

    for row in rows:
        scene_id = row["scene_id"]
        segment_id = row["segment_id"]
        entity_id = row["entity_id"]
        key = (segment_id, entity_id)
        if (
            scene_id not in scene_map
            or segment_id not in segment_map
            or segment_map[segment_id]["story_plan"]["scene_id"] != scene_id
            or entity_id not in entities
            or key in row_map
        ):
            raise StoryVideoError(
                "Character Scene States repeat or reference an invalid "
                "Scene, Segment, or Entity"
            )
        incoming = row["incoming_diegetic_presence"]
        outgoing = row["outgoing_diegetic_presence"]
        visibility = row["visibility_requirement"]
        if (
            incoming not in DIEGETIC_PRESENCE_STATES
            or outgoing not in DIEGETIC_PRESENCE_STATES
            or visibility not in VISIBILITY_REQUIREMENTS
        ):
            raise StoryVideoError(
                f"{segment_id} {entity_id} has an invalid diegetic/visibility state"
            )
        source = row["state_source_segment_id"]
        if source != "none" and (
            not SEGMENT_ID_RE.fullmatch(source)
            or source not in segment_map
        ):
            raise StoryVideoError(
                f"{segment_id} {entity_id} has an invalid State Source Segment"
            )
        if not _concrete(row["position_injury_condition_en"]):
            raise StoryVideoError(
                f"{segment_id} {entity_id} requires concrete position, injury, "
                "and condition authority"
            )
        if incoming != outgoing and not _concrete(row["transition_cause_en"]):
            raise StoryVideoError(
                f"{segment_id} {entity_id} diegetic transition needs a concrete cause"
            )
        if incoming == outgoing and not _present(
            row["transition_cause_en"], allow_none=True
        ):
            raise StoryVideoError(
                f"{segment_id} {entity_id} Transition Cause must be concrete or none"
            )

        shot_ids = [item["shot_id"] for item in segment_map[segment_id]["shots"]]
        required = row["required_visible_shot_ids"]
        if any(item not in shot_ids for item in required):
            raise StoryVideoError(
                f"{segment_id} {entity_id} requires a visible Shot outside the Segment"
            )
        if visibility == "visible_every_shot" and required != shot_ids:
            raise StoryVideoError(
                f"{segment_id} {entity_id} must require every screenplay Shot"
            )
        if visibility == "visible_in_required_shots" and not required:
            raise StoryVideoError(
                f"{segment_id} {entity_id} needs at least one required visible Shot"
            )
        if visibility in {"may_be_offscreen", "must_remain_absent"} and required:
            raise StoryVideoError(
                f"{segment_id} {entity_id} cannot list visible Shots under {visibility}"
            )
        if visibility == "must_remain_absent" and (
            incoming != "absent_from_location"
            or outgoing != "absent_from_location"
        ):
            raise StoryVideoError(
                f"{segment_id} {entity_id} must_remain_absent conflicts with "
                "diegetic presence"
            )
        if (
            visibility != "must_remain_absent"
            and incoming == outgoing == "absent_from_location"
        ):
            raise StoryVideoError(
                f"{segment_id} {entity_id} absent state requires must_remain_absent"
            )

        performers_by_shot = {
            item["shot_id"]: set(item["performer_ids"])
            for item in segment_map[segment_id]["shots"]
        }
        missing_visible = [
            shot_id
            for shot_id in required
            if entity_id not in performers_by_shot[shot_id]
        ]
        if missing_visible:
            raise StoryVideoError(
                f"{segment_id} {entity_id} visibility requirement is missing from "
                f"Shot performers: {missing_visible}"
            )
        row_map[key] = row

    # Every authored performer/speaker has world-state authority.
    for segment in segments:
        segment_id = segment["story_plan"]["segment_id"]
        used = {
            entity_id
            for shot in segment["shots"]
            for entity_id in shot["performer_ids"]
        } | {
            shot["dialogue"]["speaker_entity_id"]
            for shot in segment["shots"]
            if shot["dialogue"] is not None
        }
        missing = sorted(
            entity_id
            for entity_id in used
            if (segment_id, entity_id) not in row_map
        )
        if missing:
            raise StoryVideoError(
                f"{segment_id} lacks Character Scene State rows for {missing}"
            )

    # A non-absent outgoing role is sticky through every later Unit in the Scene.
    for scene in screenplay["scenes"]:
        scene_id = scene["scene_id"]
        latest: dict[str, dict[str, Any]] = {}
        for segment_id in scene["segment_ids_json"]:
            current = {
                entity_id: row
                for (row_segment, entity_id), row in row_map.items()
                if row_segment == segment_id
            }
            missing_live = sorted(
                entity_id
                for entity_id, prior in latest.items()
                if prior["outgoing_diegetic_presence"] == "present_in_location"
                and entity_id not in current
            )
            if missing_live:
                raise StoryVideoError(
                    f"{segment_id} silently drops screenplay-present characters "
                    f"from {scene_id}: {missing_live}"
                )
            for entity_id, row in current.items():
                prior = latest.get(entity_id)
                source = row["state_source_segment_id"]
                if prior is None:
                    if source != "none":
                        raise StoryVideoError(
                            f"{segment_id} {entity_id} has no earlier state in {scene_id}"
                        )
                else:
                    if source != prior["segment_id"]:
                        raise StoryVideoError(
                            f"{segment_id} {entity_id} must source its latest state "
                            f"from {prior['segment_id']}"
                        )
                    if (
                        row["incoming_diegetic_presence"]
                        != prior["outgoing_diegetic_presence"]
                    ):
                        raise StoryVideoError(
                            f"{segment_id} {entity_id} incoming diegetic presence "
                            "differs from its source"
                        )
                latest[entity_id] = row

    # Staging and exact visibility minima must agree with the state authority.
    for segment in segments:
        segment_id = segment["story_plan"]["segment_id"]
        call_map = {
            item["entity_id"]: item for item in segment["performance_calls"]
        }
        for (row_segment, entity_id), row in row_map.items():
            if row_segment != segment_id:
                continue
            call = call_map.get(entity_id)
            if row["visibility_requirement"] == "must_remain_absent":
                if call is not None and call["presence_mode"] != "voice_over":
                    raise StoryVideoError(
                        f"{segment_id} {entity_id} is physically staged despite "
                        "must_remain_absent"
                    )
                continue
            if call is None:
                raise StoryVideoError(
                    f"{segment_id} {entity_id} present state lacks Character Staging"
                )
            if row["visibility_requirement"] == "may_be_offscreen":
                if call["presence_mode"] == "on_screen":
                    raise StoryVideoError(
                        f"{segment_id} {entity_id} is visibly staged but its "
                        "screenplay state only says may_be_offscreen"
                    )
            elif call["presence_mode"] != "on_screen":
                raise StoryVideoError(
                    f"{segment_id} {entity_id} required visibility is staged off-screen"
                )
