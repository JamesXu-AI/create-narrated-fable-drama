"""Compile the shared Storyboard contract into per-Segment runtime metadata."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.contracts.segment.common import (
    ALLOWED_DELIVERY_MODES,
    ALLOWED_OPERATIONS,
    ALLOWED_PROVIDER_ROLES,
    CHARACTER_STATE_HEADERS,
    DIALOGUE_CELL_RE,
    GENERATION_PLAN_HEADERS,
    LOCATION_STATE_HEADERS,
    ORDERED_SHOT_HEADERS,
    REFERENCE_PLAN_HEADERS,
    SPEECH_TRANSITION_HEADERS,
    TOKEN_RE,
    SegmentRuntimeError,
    sha256_file,
    token_sort_key,
)
from narrated_fable_drama.contracts.storyboard import (
    StoryboardDocument,
    table_after_heading,
)
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.core.speech_rate import (
    SpeechRateError,
    require_speech_rate,
)

TIGHT_SHOT_SIZES = {"extreme_close_up", "close_up", "medium_close_up"}
WIDE_EXCEPTION_SHOT_SIZES = {"medium_wide", "wide", "extreme_wide"}
POSITION_CHANGE_EXCEPTION_PREFIX = "position-change exception:"


def _field_table(section: str, heading: str) -> dict[str, str]:
    headers, rows = table_after_heading(
        section,
        heading,
        stop_at_level_two=False,
        error_type=SegmentRuntimeError,
    )
    if headers != ["Field", "Value"]:
        raise SegmentRuntimeError(f"{heading} must use Field | Value")
    values = {row[0]: row[1] for row in rows}
    if len(values) != len(rows):
        raise SegmentRuntimeError(f"{heading} repeats a field")
    return values

def _shot_numbers(value: str) -> list[int]:
    if value.strip().casefold() == "none":
        return []
    numbers = [int(item) for item in re.findall(r"Shot ([1-9][0-9]*)", value)]
    if not numbers:
        raise SegmentRuntimeError(f"Invalid Shot list: {value}")
    return numbers


def _character_names(task_dir: Path) -> dict[str, str]:
    screenplay = (
        task_dir / "screenplay-writer" / "screenplay.md"
    ).read_text(encoding="utf-8")
    headers, rows = table_after_heading(
        screenplay,
        "## Characters",
        error_type=SegmentRuntimeError,
    )
    if not headers or headers[0:2] != ["Entity ID", "Character"]:
        raise SegmentRuntimeError("Screenplay Characters table is invalid")
    return {row[0]: row[1] for row in rows}


def _reference_bindings(
    task_dir: Path, segment_id: str, section: str
) -> list[dict[str, Any]]:
    headers, rows = table_after_heading(
        section,
        "### Reference Plan",
        stop_at_level_two=False,
        error_type=SegmentRuntimeError,
    )
    if tuple(headers) != REFERENCE_PLAN_HEADERS:
        raise SegmentRuntimeError(
            f"{segment_id} Reference Plan columns differ from contract"
        )
    result: list[dict[str, Any]] = []
    seen_tokens: set[str] = set()
    for index, row in enumerate(rows, start=1):
        token, role, namespace, subject, purpose, scope, forbidden = row
        match = TOKEN_RE.fullmatch(token)
        if (
            match is None
            or role not in ALLOWED_PROVIDER_ROLES
            or match.group(1) != ALLOWED_PROVIDER_ROLES[role]
            or token in seen_tokens
            or not all((namespace, subject, purpose, scope, forbidden))
        ):
            raise SegmentRuntimeError(f"{segment_id} has an invalid Reference Plan row")
        seen_tokens.add(token)
        result.append(
            {
                "binding_id": f"{segment_id}-binding-{index:02d}",
                "provider_token": token,
                "provider_role": role,
                "asset_namespace": namespace,
                "readable_subject": subject,
                "purpose_en": purpose,
                "shot_scope": (
                    [f"Shot {number}" for number in _shot_numbers(scope)]
                    if scope.casefold() != "all"
                    else ["all"]
                ),
                "forbidden_inheritance_en": forbidden,
                "prompt_declaration_en": (
                    f"{token} is {subject}; use it only for {purpose}; "
                    f"do not inherit {forbidden}."
                ),
            }
        )
    return result


def _character_states(
    segment_id: str, all_rows: list[list[str]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in all_rows:
        if row[1] != segment_id:
            continue
        (
            _chain,
            _segment,
            entity_id,
            asset_id,
            state_source,
            incoming,
            rule,
            required,
            occlusion,
            condition,
            cause,
            outgoing,
        ) = row
        result.append(
            {
                "screenplay_entity_id": entity_id,
                "character_asset_id": asset_id,
                "state_source_segment_id": state_source,
                "incoming_presence": incoming,
                "segment_presence_rule": rule,
                "outgoing_presence": outgoing,
                "required_visible_shots": _shot_numbers(required),
                "allowed_occlusion_en": occlusion,
                "transition_cause_en": cause,
                "position_and_condition_en": condition,
                "prompt_presence_lock_en": (
                    f"{asset_id}: incoming {incoming}; rule {rule}; outgoing "
                    f"{outgoing}; preserve {condition}; occlusion {occlusion}; "
                    f"transition only by {cause}."
                ),
            }
        )
    return result


def _dialogue_cues(
    task_dir: Path,
    segment_id: str,
    ordered_rows: list[list[str]],
    transition_rows: list[list[str]],
    duration: float,
) -> list[dict[str, Any]]:
    transition_by_line = {row[2]: row for row in transition_rows}
    names = _character_names(task_dir)
    result: list[dict[str, Any]] = []
    for shot_index, row in enumerate(ordered_rows, start=1):
        cell = row[8]
        if "L-" not in cell:
            continue
        match = DIALOGUE_CELL_RE.search(cell)
        if match is None:
            raise SegmentRuntimeError(
                f"{segment_id} Shot {shot_index} Dialogue and Native Audio must use "
                "the exact Line/window/speaker/mode/transition/text syntax"
            )
        line_id, start, end, speaker, mode, transition_id, exact_text = match.groups()
        if mode not in ALLOWED_DELIVERY_MODES:
            raise SegmentRuntimeError(f"{line_id} has an invalid delivery mode")
        transition = transition_by_line.get(line_id)
        if (
            transition is None
            or transition[0] != transition_id
            or transition[1] != segment_id
            or transition[3] != f"{speaker}; mode={mode}"
        ):
            raise SegmentRuntimeError(
                f"{line_id} Ordered Shot differs from Speech Transition Plan"
            )
        start_seconds = float(start)
        end_seconds = float(end)
        if start_seconds < 0 or end_seconds <= start_seconds or end_seconds > duration:
            raise SegmentRuntimeError(f"{line_id} has an invalid Storyboard speech window")
        try:
            speech_rate = require_speech_rate(
                line_id=line_id,
                text=exact_text,
                window_seconds=end_seconds - start_seconds,
                stage=f"segment-prompt gate {segment_id}/Shot {shot_index}",
            )
        except SpeechRateError as exc:
            raise SegmentRuntimeError(str(exc)) from exc
        result.append(
            {
                "line_id": line_id,
                "speaker_entity_id": speaker,
                "speaker_name": names.get(speaker, speaker),
                "delivery_mode": mode,
                "transition_id": transition_id,
                "transition_direction": {
                    "trigger_and_phrase_boundary": transition[4],
                    "listener_and_mouth_behavior": transition[5],
                    "visual_handoff": transition[6],
                    "voice_and_ambience_continuity": transition[7],
                },
                "exact_text": exact_text,
                "shot_number": shot_index,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "speech_rate": speech_rate,
            }
        )
    return result


def storyboard_segment_rows(
    task_dir: Path,
    *,
    validation_through_segment_id: str | None = None,
) -> list[dict[str, Any]]:
    root = task_dir.expanduser().resolve(strict=True)
    project_context = load_project_context(root)
    storyboard = StoryboardDocument.load(root, error_type=SegmentRuntimeError)
    headers, generation_rows = storyboard.table("## Generation Plan")
    if tuple(headers) != GENERATION_PLAN_HEADERS:
        raise SegmentRuntimeError("Generation Plan columns differ from contract")
    location_headers, location_rows = storyboard.table("## Location State Plan")
    if tuple(location_headers) != LOCATION_STATE_HEADERS:
        raise SegmentRuntimeError("Location State Plan columns differ from contract")
    character_headers, character_rows = storyboard.table(
        "## Character Segment State Plan"
    )
    if tuple(character_headers) != CHARACTER_STATE_HEADERS:
        raise SegmentRuntimeError("Character Segment State Plan columns differ from contract")
    speech_headers, speech_rows = storyboard.table("## Speech Transition Plan")
    if tuple(speech_headers) != SPEECH_TRANSITION_HEADERS:
        raise SegmentRuntimeError("Speech Transition Plan columns differ from contract")
    sections = storyboard.segments
    expected = [f"segment-{index:03d}" for index in range(1, len(generation_rows) + 1)]
    if [row[0] for row in generation_rows] != expected or list(sections) != expected:
        raise SegmentRuntimeError(
            "Storyboard Generation Segments must be consecutive and match Generation Plan"
        )
    location_by_segment = {row[1]: row for row in location_rows}
    if list(location_by_segment) != expected:
        raise SegmentRuntimeError("Location State Plan must cover every Segment in order")
    rows: list[dict[str, Any]] = []
    ordered_visual_grammar: list[tuple[str, str, str]] = []
    wave_by_id: dict[str, int] = {}
    source_hash = sha256_file(storyboard.path)
    for generation in generation_rows:
        (
            segment_id,
            screenplay_range,
            scene_value,
            duration_value,
            operation,
            predecessor,
            seam,
            internal_shots,
            packing_reason,
        ) = generation
        if operation not in ALLOWED_OPERATIONS:
            raise SegmentRuntimeError(f"{segment_id} has unsupported operation")
        try:
            duration = int(duration_value)
            declared_shots = int(internal_shots)
        except ValueError as exc:
            raise SegmentRuntimeError(
                f"{segment_id} duration and Internal Shots must be integers"
            ) from exc
        if not 4 <= duration <= 15 or declared_shots < 1:
            raise SegmentRuntimeError(f"{segment_id} has invalid duration or Shot count")
        dependencies = [] if predecessor.casefold() == "none" else [predecessor]
        if any(item not in wave_by_id for item in dependencies):
            raise SegmentRuntimeError(f"{segment_id} has a forward or unknown predecessor")
        planned_wave = (
            0 if not dependencies else 1 + max(wave_by_id[item] for item in dependencies)
        )
        wave_by_id[segment_id] = planned_wave
        section = sections[segment_id]
        direction = _field_table(section, "### Segment Direction")
        for field in (
            "Visible Character Economy",
            "Eyeline Axis and Screen Direction",
        ):
            if not direction.get(field, "").strip():
                raise SegmentRuntimeError(f"{segment_id} lacks {field}")
        axis_value = direction["Eyeline Axis and Screen Direction"]
        if not re.search(r"\baxis\b", axis_value, re.I) or not re.search(
            r"\bscreen(?:-| )?(?:left|right|direction)\b", axis_value, re.I
        ):
            raise SegmentRuntimeError(
                f"{segment_id} eyeline direction must name the axis and a "
                "screen side/direction"
            )
        shot_headers, ordered_rows = storyboard.table(
            "### Ordered Shots",
            section=section,
            stop_at_level_two=False,
        )
        if tuple(shot_headers) != ORDERED_SHOT_HEADERS or len(ordered_rows) != declared_shots:
            raise SegmentRuntimeError(
                f"{segment_id} Ordered Shots differ from Generation Plan"
            )
        for shot in ordered_rows:
            shot_size = shot[2]
            ordered_visual_grammar.append((segment_id, shot[0], shot_size))
            if (
                shot_size in WIDE_EXCEPTION_SHOT_SIZES
                and not shot[5].casefold().startswith(
                    POSITION_CHANGE_EXCEPTION_PREFIX
                )
            ):
                raise SegmentRuntimeError(
                    f"{segment_id} {shot[0]} wider framing lacks the literal "
                    "position-change exception"
                )
        bindings = _reference_bindings(root, segment_id, section)
        location = location_by_segment[segment_id]
        relationship = location[2]
        state_source = location[3]
        character_states = _character_states(segment_id, character_rows)
        visual_performers = [
            item["character_asset_id"]
            for item in character_states
            if item["segment_presence_rule"] != "remain_absent"
        ]
        dialogue_cues = _dialogue_cues(
            root,
            segment_id,
            ordered_rows,
            speech_rows,
            float(duration),
        )
        required_evidence = (
            "approved_complete_predecessor"
            if operation == "video_extension"
            else "none"
            if seam.replace(" ", "_") == "strong_coverage_reset"
            else "approved_provider_last_frame"
            if dependencies and operation == "multimodal_reference"
            else "none"
        )
        world_ids: list[str] = []
        temporal_ids: list[str] = []
        for binding in bindings:
            if binding["asset_namespace"] == "continuity":
                temporal_ids.append(binding["binding_id"])
            elif binding["provider_role"] == "reference_image" and re.search(
                r"\blocation|set|environment|world\b",
                binding["purpose_en"],
                re.I,
            ):
                world_ids.append(binding["binding_id"])
        if not world_ids:
            world_ids = [
                item["binding_id"]
                for item in bindings
                if item["provider_role"] == "reference_image"
            ][:1]
        prompt_contract = {
            "language": "English directions with exact target-language speech",
            "operation_instruction_en": operation,
            "global_constraints_en": (
                f"16:9; visual style exactly {project_context['visual_style']}; "
                "fewest story-active visible characters; preserve the declared "
                "eyeline axis and screen directions; close-up-led coverage with "
                "wider framing only for a labeled position-change exception; "
                "preserve exact speakers, voice identity, mouth behavior, "
                "natural speech transitions, references, continuity, and native audio; "
                "no generated subtitles or on-screen transcription; natural readable "
                "English on-screen text is allowed."
            ),
            "visible_character_economy_en": direction.get(
                "Visible Character Economy", ""
            ),
            "eyeline_axis_and_screen_direction_en": direction.get(
                "Eyeline Axis and Screen Direction", ""
            ),
            "shot_size_policy": (
                "ECU/CU/MCU dominate; MWS/WS/EWS only for the shortest labeled "
                "position-change exception followed by a tight Shot."
            ),
            "reference_priority_order": [
                item["provider_token"]
                for item in sorted(bindings, key=lambda value: token_sort_key(value["provider_token"]))
            ],
            "dialogue_delimiter": "{}",
            "music_delimiter": "()",
            "sound_effect_delimiter": "<>",
            "on_screen_text_delimiter": "【】",
            "generated_on_screen_text_policy": "natural_readable_english_allowed",
            "background_music_policy": "parentheses_only",
            "generated_subtitle_policy": "forbidden",
            "avoid_precise_time_ranges": True,
            "single_dominant_camera_move_per_shot": True,
        }
        row = {
            "segment_id": segment_id,
            "visual_style": project_context["visual_style"],
            "resolution": project_context["resolution"],
            "source_storyboard_sha256": source_hash,
            "scene_ids": re.findall(r"scene-[0-9]{3,}", scene_value),
            "screenplay_range": screenplay_range,
            "target_duration": duration,
            "shot_count": declared_shots,
            "operation": operation,
            "shooting_plan_status": (
                "observed_adapted" if dependencies else "locked"
            ),
            "schedule_mode": (
                "serial_after_predecessor_review" if dependencies else "independent"
            ),
            "planned_wave": planned_wave,
            "depends_on_segment_ids": dependencies,
            "dependency_reason": packing_reason,
            "predecessor_review_required": bool(dependencies),
            "required_predecessor_evidence": required_evidence,
            "successor_recompile_required": bool(dependencies),
            "fallback_operation_and_story_cost": direction.get(
                "Concise Constraints", "Repack at a motivated boundary."
            ),
            "seam_class": seam,
            "seam_resynthesis_allowed": False,
            "seam_story_reason": packing_reason,
            "editorial_intent": direction.get("Outgoing State", packing_reason),
            "reference_video_scope": (
                "complete_predecessor"
                if operation == "video_extension"
                else "provider_last_frame"
                if required_evidence == "approved_provider_last_frame"
                else "none"
            ),
            "reference_video_audio": (
                "preserve_predecessor_audio"
                if operation == "video_extension"
                else "none"
            ),
            "camera_ensemble_color_resynthesis_allowed": False,
            "continuity": {
                "location_state_chain": location[0],
                "relationship": relationship,
                "state_source_segment_id": state_source,
                "world_binding_ids": world_ids,
                "temporal_binding_ids": temporal_ids,
                "embedded_npc_asset_ids": [],
                "authorized_independent_performer_asset_ids": visual_performers,
                "character_segment_states": character_states,
                "population_lock_en": direction.get(
                    "Authorized Population", "No unapproved people or creatures."
                ),
            },
            "prompt_contract": prompt_contract,
            "bindings": bindings,
            "dialogue_cues": dialogue_cues,
            "final_visible_state": direction.get(
                "Outgoing State", ordered_rows[-1][9]
            ),
            "final_sound_state": ordered_rows[-1][8],
            "ordered_shots": ordered_rows,
        }
        rows.append(row)
    for index, (segment_id, shot_label, shot_size) in enumerate(
        ordered_visual_grammar[:-1]
    ):
        if (
            shot_size in WIDE_EXCEPTION_SHOT_SIZES
            and ordered_visual_grammar[index + 1][2] not in TIGHT_SHOT_SIZES
        ):
            raise SegmentRuntimeError(
                f"{segment_id} {shot_label} position-change exception must return "
                "directly to ECU/CU/MCU"
            )
    tight_count = sum(
        shot_size in TIGHT_SHOT_SIZES
        for _, _, shot_size in ordered_visual_grammar
    )
    if (
        len(ordered_visual_grammar) >= 2
        and tight_count <= len(ordered_visual_grammar) - tight_count
    ):
        raise SegmentRuntimeError(
            "ECU/CU/MCU Shots must outnumber all other Storyboard Shot sizes"
        )
    if validation_through_segment_id is not None:
        ids = [row["segment_id"] for row in rows]
        if validation_through_segment_id not in ids:
            raise SegmentRuntimeError(
                f"Unknown validation Segment ID: {validation_through_segment_id}"
            )
        rows = rows[: ids.index(validation_through_segment_id) + 1]
    return rows
