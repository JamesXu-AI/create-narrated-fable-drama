"""Validate performer staging, visibility, gaze, and dialogue ownership."""

from __future__ import annotations

from typing import Any

from narrated_fable_drama.contracts.screenplay.schema import (
    APPEARANCE_MODES,
    DIALOGUE_ADDRESSEE_SPECIALS,
    PRESENCE_MODES,
    concrete as _concrete,
)
from narrated_fable_drama.core.validation import StoryVideoError


def _validate_performance(screenplay: dict[str, Any]) -> None:
    entities = {item["entity_id"]: item for item in screenplay["characters"]}
    state_rows_by_segment: dict[str, dict[str, dict[str, Any]]] = {}
    for state in screenplay["character_scene_states"]:
        state_rows_by_segment.setdefault(state["segment_id"], {})[
            state["entity_id"]
        ] = state
    used_entities: set[str] = set()
    speaking_entities: set[str] = set()
    for segment in screenplay["segments"]:
        segment_id = segment["story_plan"]["segment_id"]
        shots = segment["shots"]
        shot_map = {shot["shot_id"]: shot for shot in shots}
        calls = segment["performance_calls"]
        call_map = {call["entity_id"]: call for call in calls}
        if len(call_map) != len(calls) or any(entity_id not in entities for entity_id in call_map):
            raise StoryVideoError(f"{segment_id} repeats or invents Character Staging")
        used_entities.update(call_map)

        expected_performers = {
            entity_id for shot in shots for entity_id in shot["performer_ids"]
        }
        expected_speakers = {
            shot["dialogue"]["speaker_entity_id"]
            for shot in shots
            if shot["dialogue"] is not None
        }
        required_state_calls = {
            entity_id
            for entity_id, state in state_rows_by_segment.get(
                segment_id, {}
            ).items()
            if state["outgoing_diegetic_presence"]
            == "present_in_location"
            or state["incoming_diegetic_presence"]
            == "present_in_location"
        }
        if set(call_map) != expected_performers | expected_speakers | required_state_calls:
            raise StoryVideoError(
                f"{segment_id} Character Staging must cover exactly its performers, "
                "speakers, and screenplay-authorized present characters"
            )

        line_owner: dict[str, str] = {}
        for call in calls:
            entity_id = call["entity_id"]
            entity = entities[entity_id]
            presence = call["presence_mode"]
            appearance = call["appearance_mode"]
            if presence not in PRESENCE_MODES or appearance not in APPEARANCE_MODES:
                raise StoryVideoError(f"{entity_id} has invalid Presence or Appearance")
            if call["speaks"] != bool(call["line_ids"]):
                raise StoryVideoError(f"{entity_id} Speaks and Lines disagree")
            if call["speaks"]:
                speaking_entities.add(entity_id)
            for line_id in call["line_ids"]:
                if line_id in line_owner:
                    raise StoryVideoError(f"{line_id} has repeated Character Staging ownership")
                line_owner[line_id] = entity_id

            action_ids = call["action_block_ids"]
            if any(shot_id not in shot_map for shot_id in action_ids):
                raise StoryVideoError(f"{entity_id} references an unknown Action Shot")
            actual_action_ids = [
                shot["shot_id"] for shot in shots if entity_id in shot["performer_ids"]
            ]
            if action_ids != actual_action_ids:
                raise StoryVideoError(
                    f"{entity_id} Action Shots must exactly match authored Shot performers"
                )

            appearance_fields = (
                call["appearance_trigger_en"],
                call["entry_path_or_opening_position_en"],
                call["first_visible_block_id"],
                call["first_visible_moment_en"],
                call["landing_block_id"],
                call["landing_result_en"],
            )
            if presence != "on_screen":
                if appearance != "not_visible" or any(
                    value != "not_visible" for value in appearance_fields
                ):
                    raise StoryVideoError(
                        f"{entity_id} O.S./V.O. staging must use not_visible throughout"
                    )
                if action_ids:
                    raise StoryVideoError(f"{entity_id} O.S./V.O. cannot own visible Action Shots")
            else:
                if appearance not in {"present_at_open", "enters"}:
                    raise StoryVideoError(
                        f"{entity_id} on-screen staging requires present_at_open or enters"
                    )
                if appearance == "present_at_open":
                    if call["appearance_trigger_en"] != "opening":
                        raise StoryVideoError(
                            f"{entity_id} present_at_open Trigger must be opening"
                        )
                elif not _concrete(call["appearance_trigger_en"]):
                    raise StoryVideoError(f"{entity_id} entrance Trigger must be concrete")
                if not _concrete(call["entry_path_or_opening_position_en"]):
                    raise StoryVideoError(
                        f"{entity_id} requires a concrete Entry Path / Opening Position"
                    )
                first_id = call["first_visible_block_id"]
                landing_id = call["landing_block_id"]
                if first_id not in action_ids or landing_id not in action_ids:
                    raise StoryVideoError(
                        f"{entity_id} First Visible and Landing Shots must be owned Action Shots"
                    )
                positions = {shot["shot_id"]: i for i, shot in enumerate(shots)}
                if positions[first_id] > positions[landing_id]:
                    raise StoryVideoError(
                        f"{entity_id} First Visible Shot must not follow Landing Shot"
                    )
                if not _concrete(call["first_visible_moment_en"]):
                    raise StoryVideoError(
                        f"{entity_id} First Visible Moment must describe an observable event"
                    )
                if not _concrete(call["landing_result_en"]):
                    raise StoryVideoError(
                        f"{entity_id} Landing Moment / Result must describe an observable event"
                    )
                if shot_map[landing_id]["completion_mode"] != "completed":
                    raise StoryVideoError(
                        f"{entity_id} Landing Shot must have a completed action state"
                    )

            if entity["entity_kind"] == "anonymous_ensemble" and call["speaks"]:
                raise StoryVideoError(f"{entity_id} anonymous ensemble cannot own dialogue")

        expected_line_owner = {
            shot["dialogue"]["line_id"]: shot["dialogue"]["speaker_entity_id"]
            for shot in shots
            if shot["dialogue"] is not None
        }
        if line_owner != expected_line_owner:
            raise StoryVideoError(
                f"{segment_id} Character Staging must own every Dialogue Line exactly once"
            )

        for shot in shots:
            relations = shot["gaze_relations"]
            dialogue = shot["dialogue"]
            nonvisible_speaker_ids = set()
            if dialogue is not None:
                dialogue_call = call_map[dialogue["speaker_entity_id"]]
                if dialogue_call["presence_mode"] != "on_screen":
                    nonvisible_speaker_ids.add(dialogue["speaker_entity_id"])
            if set(relations) != set(shot["performer_ids"]) | nonvisible_speaker_ids:
                raise StoryVideoError(
                    f"{shot['shot_id']} Gaze / Addressee must cover every visible Performer and non-visible speaker once"
                )
            for performer_id, relation in relations.items():
                if performer_id not in call_map:
                    raise StoryVideoError(
                        f"{shot['shot_id']} gives gaze authority to an unstaged entity"
                    )
                if call_map[performer_id]["presence_mode"] == "on_screen" and (
                    relation["facing"] == "not_visible" or relation["gaze"] == "not_visible"
                ):
                    raise StoryVideoError(
                        f"{shot['shot_id']} visible performer requires concrete facing and gaze"
                    )
                if call_map[performer_id]["presence_mode"] != "on_screen" and (
                    relation["facing"] != "not_visible" or relation["gaze"] != "not_visible"
                ):
                    raise StoryVideoError(
                        f"{shot['shot_id']} non-visible speaker must use not_visible facing and gaze"
                    )
            if dialogue is None:
                continue
            speaker_id = dialogue["speaker_entity_id"]
            call = call_map[speaker_id]
            relation = relations.get(speaker_id)
            if call["presence_mode"] == "on_screen":
                if speaker_id not in shot["performer_ids"] or relation is None:
                    raise StoryVideoError(
                        f"{dialogue['line_id']} on-screen speaker lacks same-Shot performance and gaze"
                    )
            else:
                if relation is None or relation["facing"] != "not_visible" or relation["gaze"] != "not_visible":
                    raise StoryVideoError(
                        f"{dialogue['line_id']} O.S./V.O. requires not_visible facing and gaze"
                    )
            target = relation["target"]
            if target not in call_map and target not in DIALOGUE_ADDRESSEE_SPECIALS:
                raise StoryVideoError(f"{dialogue['line_id']} has an undeclared dialogue Addressee")
            if target == speaker_id:
                raise StoryVideoError(f"{dialogue['line_id']} must use self for self-address")

    if used_entities != set(entities):
        raise StoryVideoError("Characters table contains unused entities")
    for entity_id, entity in entities.items():
        member_types = entity["ensemble_member_types_en"]
        if entity["entity_kind"] == "anonymous_ensemble":
            if entity["recurring"] or entity["group_role_type_en"] == "none" or not member_types:
                raise StoryVideoError(
                    f"{entity_id} anonymous ensemble needs a non-recurring Group Role and Member Types"
                )
            if entity_id in speaking_entities:
                raise StoryVideoError(f"{entity_id} anonymous ensemble cannot speak")
        elif entity["group_role_type_en"] != "none" or member_types:
            raise StoryVideoError(
                f"{entity_id} individual must use none for Group Role and Member Types"
            )
