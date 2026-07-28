"""Validate the assembled screenplay structure across all authored tables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.screenplay.schema import (
    CHARACTER_STORY_ROLES,
    DRAMATIC_WORKLOADS,
    ENTITY_KINDS,
    ENVIRONMENT_KINDS,
    INCOMING_VISUAL_REQUIREMENTS,
    MINIMUM_ACTION_REACTION_SECONDS,
    NARRATION_ELIGIBILITIES,
    OFF_CAMERA_SPEECH_MODES,
    ON_CAMERA_SPEECH_MODES,
    SCENE_ENTRY_BOUNDARIES,
    SLUGLINE_RE,
    TRANSITION_DESIGN_TYPES,
    concrete as _concrete,
    present as _present,
)
from narrated_fable_drama.contracts.screenplay.boundaries import (
    _validate_predecessor_inheritance_budget,
    _validate_shot_scale_grammar,
    validate_adjacent_visual_boundary_contract,
    validate_cinematic_segment_contract,
)
from narrated_fable_drama.contracts.screenplay.performance import (
    _validate_performance,
)
from narrated_fable_drama.contracts.screenplay.speech import (
    screenplay_speech_rate_gate,
)
from narrated_fable_drama.contracts.screenplay.state import (
    _validate_character_scene_states,
)
from narrated_fable_drama.core.speech_rate import analyze_speech
from narrated_fable_drama.core.validation import StoryVideoError
from narrated_fable_drama.core.project_domain import (
    ProjectDomainError,
    SOUND_EFFECTS_AUDIO_SOURCE,
    SPEECH_AUDIO_SOURCE,
    TARGET_LANGUAGE,
    validate_arabic_dialogue,
)


def validate_screenplay(screenplay: dict[str, Any]) -> None:
    production = screenplay["production_information"]
    if production["Production Type"] != "ai_narrated_fable_drama":
        raise StoryVideoError(
            "screenplay.md Production Type must be ai_narrated_fable_drama"
        )
    if production["Aspect Ratio"] != "16:9":
        raise StoryVideoError("screenplay.md Aspect Ratio must be 16:9")
    if production["Resolution"] not in {"480p", "720p", "1080p", "4k"}:
        raise StoryVideoError("screenplay.md Resolution is unsupported")
    if production["Speech Audio Source"] != SPEECH_AUDIO_SOURCE:
        raise StoryVideoError(
            f"screenplay.md Speech Audio Source must be {SPEECH_AUDIO_SOURCE}"
        )
    if production["Sound Effects Audio Source"] != SOUND_EFFECTS_AUDIO_SOURCE:
        raise StoryVideoError(
            "screenplay.md Sound Effects Audio Source must be "
            f"{SOUND_EFFECTS_AUDIO_SOURCE}"
        )
    if not _present(production["Target Country"]):
        raise StoryVideoError("screenplay.md Target Country must be present")
    if production["Target Language"] != TARGET_LANGUAGE:
        raise StoryVideoError(
            f"screenplay.md Target Language must be {TARGET_LANGUAGE}"
        )
    if not _present(production["Genre"]):
        raise StoryVideoError("Production Information Genre must be present")
    if not _present(production["Visual Style"]):
        raise StoryVideoError("Production Information Visual Style must be present")
    for field in (
        "Story Premise",
        "Fable Meaning",
        "Framing and Embedded Story Strategy",
        "Speech Transition Strategy",
        "Safety and Culture",
        "Opening Event",
        "Ending Event and Obligation",
    ):
        if not _concrete(production[field]):
            raise StoryVideoError(f"Production Information {field} must be concrete")

    characters = screenplay["characters"]
    if not characters or not any(item["story_role"] == "lead" for item in characters):
        raise StoryVideoError("screenplay.md needs at least one lead Character")
    for item in characters:
        if item["story_role"] not in CHARACTER_STORY_ROLES:
            raise StoryVideoError(
                f"{item['screenplay_character_name_en']} has an invalid Story Role"
            )
        if item["narration_eligibility"] not in NARRATION_ELIGIBILITIES:
            raise StoryVideoError(
                f"{item['screenplay_character_name_en']} has invalid Narration authority"
            )
        if not _concrete(item["narrative_function_en"]) or not _concrete(item["description_en"]):
            raise StoryVideoError(
                f"{item['screenplay_character_name_en']} Character fields must be concrete"
            )
    for entity in characters:
        if entity["entity_kind"] not in ENTITY_KINDS:
            raise StoryVideoError(f"{entity['entity_id']} has an invalid Kind")

    environments = screenplay["environments"]
    scene_environment: dict[str, dict[str, Any]] = {}
    for index, environment in enumerate(environments, start=1):
        expected = f"environment-{index:03d}"
        if environment["environment_id"] != expected or environment["int_ext"] not in ENVIRONMENT_KINDS:
            raise StoryVideoError(f"Environment {index} must be {expected} with valid INT/EXT")
        for field in ("logical_name_en", "time_context_en"):
            if not _present(environment[field]):
                raise StoryVideoError(f"{expected} {field} must be present")
        for field in ("environment_facts_en", "story_function_en"):
            if not _concrete(environment[field]):
                raise StoryVideoError(f"{expected} {field} must be concrete")
        for scene_id in environment["scene_ids_json"]:
            if scene_id in scene_environment:
                raise StoryVideoError(f"{scene_id} appears in multiple Environments")
            scene_environment[scene_id] = environment

    scenes = screenplay["scenes"]
    scene_segments: list[str] = []
    scene_by_segment: dict[str, str] = {}
    for index, scene in enumerate(scenes, start=1):
        expected = f"scene-{index:03d}"
        if scene["scene_id"] != expected or scene["entry_boundary"] not in SCENE_ENTRY_BOUNDARIES:
            raise StoryVideoError(f"Scene {index} must be {expected} with valid Entry Boundary")
        if (index == 1) != (scene["entry_boundary"] == "opening"):
            raise StoryVideoError("Only scene-001 may use opening")
        for field in ("primary_time_en", "primary_place_en"):
            if not _present(scene[field]):
                raise StoryVideoError(f"{expected} {field} must be present")
        for field in (
            "narrative_event_en",
            "entry_reason_en",
            "continuity_reference_reason_en",
        ):
            if not _concrete(
                scene[field], allow_none=field == "continuity_reference_reason_en"
            ):
                raise StoryVideoError(f"{expected} {field} must be concrete")
        for segment_id in scene["segment_ids_json"]:
            if segment_id in scene_by_segment:
                raise StoryVideoError(f"{segment_id} appears in multiple Scenes")
            scene_by_segment[segment_id] = expected
            scene_segments.append(segment_id)
    if set(scene_environment) != {item["scene_id"] for item in scenes}:
        raise StoryVideoError("Scenes and Environment bindings differ")
    if set(screenplay["scene_dramatic_contracts"]) != {item["scene_id"] for item in scenes}:
        raise StoryVideoError("Every Scene needs exactly one Scene Dramatic Contract")

    states = screenplay["continuity_states"]
    for index, state in enumerate(states, start=1):
        expected = f"state-{index:03d}"
        expected_parent = "none" if index == 1 else f"state-{index - 1:03d}"
        if state["state_id"] != expected or state["parent_state_ref"] != expected_parent:
            raise StoryVideoError(
                f"Continuity State {index} must be {expected} with parent {expected_parent}"
            )
        if not _concrete(state["changed_facts_en"]) or not _concrete(state["change_reason_en"]):
            raise StoryVideoError(f"{expected} needs concrete changed facts and reason")

    segments = screenplay["segments"]
    boundaries = screenplay["continuity_boundaries"]
    if not segments:
        raise StoryVideoError("screenplay.md requires at least one Scene Unit")
    if len(boundaries) != len(segments) - 1:
        raise StoryVideoError("Continuity Boundaries must cover every adjacent Segment once")
    state_ids = {item["state_id"] for item in states}
    for index, boundary in enumerate(boundaries, start=1):
        expected = f"boundary-{index:03d}"
        if (
            boundary["boundary_id"] != expected
            or boundary["from_segment_id"] != f"segment-{index:03d}"
            or boundary["to_segment_id"] != f"segment-{index + 1:03d}"
            or boundary["from_state_ref"] not in state_ids
            or boundary["to_state_ref"] not in state_ids
            or boundary["handoff"] not in INCOMING_VISUAL_REQUIREMENTS
            or boundary["transition_type"] not in TRANSITION_DESIGN_TYPES - {"final_end"}
        ):
            raise StoryVideoError(f"Continuity Boundary {index} is invalid")
        for field in ("dramatic_reason_en", "audio_handoff_en", "continuity_handoff_en"):
            if not _concrete(boundary[field]):
                raise StoryVideoError(f"{expected} {field} must be concrete")

    runtime = 0
    known_beats: set[str] = set()
    action_ids: list[str] = []
    line_ids: list[str] = []
    for index, segment in enumerate(segments, start=1):
        plan = segment["story_plan"]
        expected = f"segment-{index:03d}"
        if segment["id"] != index or plan["segment_id"] != expected:
            raise StoryVideoError("Scene Units and Segment IDs must be consecutive")
        if scene_by_segment.get(expected) != plan["scene_id"]:
            raise StoryVideoError(f"{expected} disagrees with Scenes table")
        if not SLUGLINE_RE.fullmatch(segment["heading_en"]):
            raise StoryVideoError(f"{expected} has an invalid Slugline")
        environment = scene_environment.get(plan["scene_id"])
        slug_kind = segment["heading_en"].split(".", 1)[0]
        if environment is None or (
            environment["int_ext"] != "MIXED" and environment["int_ext"] != slug_kind
        ):
            raise StoryVideoError(f"{expected} Slugline conflicts with its Environment")
        if plan["dramatic_workload"] not in DRAMATIC_WORKLOADS:
            raise StoryVideoError(f"{expected} has an invalid Workload")
        duration = plan["estimated_duration_seconds"]
        if isinstance(duration, bool) or not 4 <= duration <= 15:
            raise StoryVideoError(f"{expected} Duration Seconds must be 4-15")
        runtime += duration
        if not any(shot["audio_cues"] for shot in segment["shots"]):
            raise StoryVideoError(f"{expected} requires at least one authored audio event")
        for shot in segment["shots"]:
            action_ids.append(shot["shot_id"])
            if shot["dialogue"] is not None:
                line_ids.append(shot["dialogue"]["line_id"])
        validate_cinematic_segment_contract(
            segment_id=expected,
            scene_id=plan["scene_id"],
            scene_contract=plan["scene_dramatic_contract"],
            shots=segment["shots"],
            known_beat_ids=known_beats,
        )
        spoken_entries = [
            shot["dialogue"]
            for shot in segment["shots"]
            if shot["dialogue"] is not None
        ]
        minimum_playable_seconds = (
            sum(
                analyze_speech(
                    shot["dialogue"]["spoken_text_ar"],
                    float(shot["duration_seconds"]),
                )["required_seconds"]
                for shot in segment["shots"]
                if shot["dialogue"] is not None
            )
            + MINIMUM_ACTION_REACTION_SECONDS
        )
        if duration + 1e-6 < minimum_playable_seconds:
            raise StoryVideoError(
                f"{expected} duration is below its strict speech-plus-action floor"
            )
        call_map = {
            call["entity_id"]: call for call in segment["performance_calls"]
        }
        character_map = {item["entity_id"]: item for item in characters}
        for entry in spoken_entries:
            try:
                validate_arabic_dialogue(
                    entry["spoken_text_ar"],
                    context=entry["line_id"],
                )
            except ProjectDomainError as exc:
                raise StoryVideoError(str(exc)) from exc
            speaker_id = entry["speaker_entity_id"]
            if speaker_id not in call_map or speaker_id not in character_map:
                raise StoryVideoError(
                    f"{entry['line_id']} lacks declared speaker staging or gaze/addressee"
                )
            presence_mode = call_map[speaker_id]["presence_mode"]
            delivery_mode = entry["delivery_mode"]
            narration_authority = character_map[speaker_id][
                "narration_eligibility"
            ]
            if delivery_mode in ON_CAMERA_SPEECH_MODES and presence_mode != "on_screen":
                raise StoryVideoError(
                    f"{entry['line_id']} is on-camera speech but its speaker is "
                    f"staged as {presence_mode}"
                )
            if delivery_mode in OFF_CAMERA_SPEECH_MODES and presence_mode not in {
                "off_screen",
                "voice_over",
            }:
                raise StoryVideoError(
                    f"{entry['line_id']} is off-camera storytelling but its speaker "
                    f"is staged as {presence_mode}"
                )
            if (
                delivery_mode
                in {
                    "on_camera_storytelling",
                    "off_camera_storytelling",
                    "external_voiceover",
                }
                and narration_authority not in {"storyteller", "both"}
            ):
                raise StoryVideoError(
                    f"{character_map[speaker_id]['screenplay_character_name_en']} "
                    "does not own storytelling authority"
                )

        completion_mode = segment["shots"][-1]["completion_mode"]
        if index < len(segments):
            handoff = boundaries[index - 1]["handoff"]
            if (completion_mode == "open") != (handoff == "continuous_motion"):
                raise StoryVideoError(
                    f"{expected} final Completion State must agree with its Handoff"
                )
        elif completion_mode != "completed":
            raise StoryVideoError("The final Scene Unit must end with completed action")
        if index > 1:
            validate_adjacent_visual_boundary_contract(
                segment_id=expected,
                predecessor_scene_id=segments[index - 2]["story_plan"]["scene_id"],
                current_scene_id=plan["scene_id"],
                boundary=boundaries[index - 2],
                predecessor_final_shot=segments[index - 2]["shots"][-1],
                current_first_shot=segment["shots"][0],
            )

    expected_actions = [f"A-{index:03d}" for index in range(1, len(action_ids) + 1)]
    expected_lines = [f"L-{index:03d}" for index in range(1, len(line_ids) + 1)]
    if action_ids != expected_actions:
        raise StoryVideoError("Shot IDs must be globally consecutive in screenplay order")
    if line_ids != expected_lines:
        raise StoryVideoError("Dialogue Line IDs must be globally consecutive in screenplay order")
    try:
        declared_runtime = int(production["Estimated Runtime Seconds"])
    except ValueError as exc:
        raise StoryVideoError("Estimated Runtime Seconds must be an integer") from exc
    if runtime != declared_runtime or runtime > 240:
        raise StoryVideoError("Screenplay runtime is invalid or disagrees across tables")
    if scene_segments != [f"segment-{index:03d}" for index in range(1, len(segments) + 1)]:
        raise StoryVideoError("Scenes must partition Segments once in order")
    _validate_predecessor_inheritance_budget(segments, boundaries)
    _validate_shot_scale_grammar(segments)
    _validate_character_scene_states(screenplay)
    _validate_performance(screenplay)
    screenplay_speech_rate_gate(screenplay)


def load_screenplay_file(path: str | Path) -> dict[str, Any]:
    from narrated_fable_drama.contracts.screenplay import parse_screenplay_markdown

    screenplay_path = Path(path).expanduser().resolve()
    if screenplay_path.name != "screenplay.md":
        raise StoryVideoError("Screenplay file must be named screenplay.md")
    try:
        text = screenplay_path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError) as exc:
        raise StoryVideoError(f"Invalid screenplay file: {screenplay_path}") from exc
    return parse_screenplay_markdown(text)
