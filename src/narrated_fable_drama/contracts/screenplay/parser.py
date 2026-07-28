"""Parse and validate the authored, all-table cinematic screenplay contract."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.core.validation import (
    StoryVideoError,
    require_utf8_text,
)
from narrated_fable_drama.core.speech_rate import (
    SpeechRateError,
    analyze_speech,
    require_speech_rate,
)
from narrated_fable_drama.contracts.screenplay.schema import (
    APPEARANCE_MODES,
    BEAT_ID_RE,
    CHARACTER_STORY_ROLES,
    DIALOGUE_ADDRESSEE_SPECIALS,
    DIEGETIC_PRESENCE_STATES,
    DRAMATIC_WORKLOADS,
    ENTITY_KINDS,
    ENVIRONMENT_KINDS,
    INCOMING_VISUAL_REQUIREMENTS,
    MINIMUM_ACTION_REACTION_SECONDS,
    NARRATION_ELIGIBILITIES,
    OFF_CAMERA_SPEECH_MODES,
    ON_CAMERA_SPEECH_MODES,
    PRESENCE_MODES,
    SCALE_VIEWS,
    SCENE_ENTRY_BOUNDARIES,
    SEGMENT_ID_RE,
    SLUGLINE_RE,
    SPEECH_DELIVERY_MODES,
    STAGE_TABLEAU_RISK_RE,
    TIGHT_ATTENTION_VIEWS,
    TRANSITION_DESIGN_TYPES,
    VISIBILITY_REQUIREMENTS,
    WIDE_SCALE_VIEWS,
    concrete as _concrete,
    present as _present,
)


TITLE_RE = re.compile(r"^# Cinematic Widescreen Production Script: (.+)$")
SCENE_UNIT_RE = re.compile(r"^## Scene Unit ([1-9][0-9]*) — (.+)$")
SCENE_ID_RE = re.compile(r"^scene-[0-9]{3,}$")
ENTITY_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ACTION_ID_RE = re.compile(r"^A-[0-9]{3,}$")
LINE_ID_RE = re.compile(r"^L-[0-9]{3,}$")
GAZE_RE = re.compile(
    r"^([a-z0-9]+(?:-[a-z0-9]+)*) -> ([^()]+?) "
    r"\(facing=(.+?), gaze=(.+)\)$"
)
DIALOGUE_RE = re.compile(
    r'^((?:L)-[0-9]{3,}); speaker=([a-z0-9]+(?:-[a-z0-9]+)*); '
    r'mode=([a-z_]+); gate=([^;]+); transition=([^;]+); '
    r'delivery=([^;]+); text="([^"]+)"$'
)
AUDIO_RE = re.compile(
    r"^(BGM (?:ENTERS|EVOLVES|STOPS|STING)|SFX|AMBIENCE|SILENCE):\s*(.+)$"
)

PRODUCTION_INFORMATION_FIELDS = (
    "Production Type",
    "Genre",
    "Visual Style",
    "Estimated Runtime Seconds",
    "Target Country",
    "Target Language",
    "Aspect Ratio",
    "Resolution",
    "Speech Audio Source",
    "Sound Effects Audio Source",
    "Story Premise",
    "Fable Meaning",
    "Framing and Embedded Story Strategy",
    "Speech Transition Strategy",
    "Safety and Culture",
    "Opening Event",
    "Ending Event and Obligation",
)
CHARACTER_TABLE_COLUMNS = (
    "Entity ID",
    "Character",
    "Story Role",
    "Narrative Function",
    "Kind",
    "Recurring",
    "Group Role",
    "Member Types",
    "Narration",
    "Description",
)
SCENE_UNIT_INFORMATION_FIELDS = (
    "Segment ID",
    "Scene ID",
    "Slugline",
    "Duration Seconds",
    "Workload",
    "Environment",
    "Dramatic Purpose",
    "Start State",
    "End State",
    "Incoming Boundary",
)
SHOT_EXECUTION_COLUMNS = (
    "Shot ID",
    "Beat ID",
    "Scale / View",
    "Duration Seconds",
    "Performers",
    "Dramatic Change",
    "Objective / Tactic",
    "Visual Action",
    "Important Reaction",
    "Blocking / Movement",
    "Gaze / Addressee",
    "Completion State",
    "Audience Focus",
    "BGM / SFX / Ambience",
    "Dialogue",
)
CHARACTER_STAGING_COLUMNS = (
    "Entity ID",
    "Presence",
    "Appearance",
    "Trigger",
    "Entry Path / Opening Position",
    "First Visible Shot",
    "First Visible Moment",
    "Landing Shot",
    "Landing Moment / Result",
    "Speaks",
    "Lines",
    "State Change",
    "Action Shots",
)
ENVIRONMENT_TABLE_COLUMNS = (
    "Environment ID",
    "Logical Environment",
    "Scene IDs",
    "INT/EXT",
    "Time Context",
    "Environment Facts",
    "Story Function",
)
SCENE_TABLE_COLUMNS = (
    "Scene ID",
    "Segment IDs",
    "Primary Time",
    "Primary Place",
    "Narrative Event",
    "Entry Boundary",
    "Entry Reason",
    "Continuity Reference Segment",
    "Continuity Reference Reason",
)
SCENE_CONTRACT_TABLE_COLUMNS = (
    "Scene ID",
    "Purpose",
    "Character Objective",
    "Obstacle",
    "Power Relationship",
    "Turning Point",
    "Outcome",
    "Spatial Progression",
    "Exit Impulse",
)
CHARACTER_SCENE_STATE_TABLE_COLUMNS = (
    "Scene ID",
    "Segment ID",
    "Entity ID",
    "State Source Segment",
    "Incoming Diegetic Presence",
    "Visibility Requirement",
    "Required Visible Shots",
    "Position, Injury and Condition",
    "Transition Cause",
    "Outgoing Diegetic Presence",
)
CONTINUITY_STATE_TABLE_COLUMNS = (
    "State ID",
    "Parent State",
    "Changed Facts",
    "Change Reason",
)
CONTINUITY_BOUNDARY_TABLE_COLUMNS = (
    "Boundary ID",
    "From Segment",
    "To Segment",
    "From State",
    "To State",
    "Handoff",
    "Transition",
    "Dramatic Reason",
    "Audio Handoff",
    "Continuity Handoff",
)

def _next_nonempty(lines: list[str], index: int) -> int:
    while index < len(lines) and not lines[index].strip():
        index += 1
    return index


def _table_cells(line: str, *, label: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        raise StoryVideoError(f"{label} must use a Markdown table row")
    body = stripped[1:-1]
    cells: list[str] = []
    current: list[str] = []
    cursor = 0
    while cursor < len(body):
        character = body[cursor]
        if character == "\\" and cursor + 1 < len(body) and body[cursor + 1] in {"\\", "|"}:
            current.append(body[cursor + 1])
            cursor += 2
            continue
        if character == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        cursor += 1
    cells.append("".join(current).strip())
    return cells


def _parse_table(
    lines: list[str],
    index: int,
    *,
    columns: tuple[str, ...],
    label: str,
    allow_empty: bool = False,
) -> tuple[list[dict[str, str]], int]:
    index = _next_nonempty(lines, index)
    if index >= len(lines) or tuple(_table_cells(lines[index], label=label)) != columns:
        raise StoryVideoError(f"{label} must use the exact ordered columns")
    index += 1
    if index >= len(lines):
        raise StoryVideoError(f"{label} is missing its separator row")
    separator = _table_cells(lines[index], label=label)
    if len(separator) != len(columns) or any(
        not re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    ):
        raise StoryVideoError(f"{label} has an invalid separator row")
    index += 1
    rows: list[dict[str, str]] = []
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            break
        if stripped.startswith("#"):
            break
        cells = _table_cells(lines[index], label=label)
        if len(cells) != len(columns) or any(not cell for cell in cells):
            raise StoryVideoError(f"{label} contains an invalid row")
        rows.append(dict(zip(columns, cells)))
        index += 1
    if not rows and not allow_empty:
        raise StoryVideoError(f"{label} must contain at least one row")
    return rows, index


def _parse_field_table(
    lines: list[str], index: int, fields: tuple[str, ...], *, label: str
) -> tuple[dict[str, str], int]:
    rows, index = _parse_table(
        lines, index, columns=("Field", "Value"), label=label
    )
    actual = [row["Field"] for row in rows]
    if tuple(actual) != fields:
        raise StoryVideoError(f"{label} must use the exact ordered Field rows")
    return {
        row["Field"]: require_utf8_text(row["Value"], f"{label} {row['Field']}")
        for row in rows
    }, index


def _expect_heading(lines: list[str], index: int, heading: str) -> int:
    index = _next_nonempty(lines, index)
    if index >= len(lines) or lines[index].strip() != heading:
        raise StoryVideoError(f"screenplay.md must declare {heading}")
    return index + 1


def _ids(
    value: str,
    pattern: re.Pattern[str],
    *,
    label: str,
    allow_none: bool = False,
) -> list[str]:
    if value == "none" and allow_none:
        return []
    result = [item.strip() for item in value.split(",")]
    if (
        not result
        or any(not pattern.fullmatch(item) for item in result)
        or len(result) != len(set(result))
    ):
        raise StoryVideoError(f"{label} contains invalid or repeated IDs")
    return result


def _yes_no(value: str, *, label: str) -> bool:
    if value not in {"yes", "no"}:
        raise StoryVideoError(f"{label} must be yes or no")
    return value == "yes"


def _positive_number(value: str, *, label: str) -> float:
    if not re.fullmatch(r"[0-9]+(?:\.[0-9])?", value):
        raise StoryVideoError(f"{label} must be a positive number with at most one decimal")
    result = float(value)
    if result <= 0:
        raise StoryVideoError(f"{label} must be positive")
    return result


def _split_br(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"\s*<br\s*/?>\s*", value) if item.strip()]


def _parse_gaze(value: str, *, label: str) -> dict[str, dict[str, str]]:
    if value == "none":
        return {}
    result: dict[str, dict[str, str]] = {}
    for item in _split_br(value):
        match = GAZE_RE.fullmatch(item)
        if not match:
            raise StoryVideoError(
                f"{label} must use '<entity> -> <target> (facing=..., gaze=...)'"
            )
        source, target, facing, gaze = (part.strip() for part in match.groups())
        if source in result:
            raise StoryVideoError(f"{label} repeats gaze authority for {source}")
        if not _concrete(facing) or not _concrete(gaze):
            if not (facing == "not_visible" and gaze == "not_visible"):
                raise StoryVideoError(f"{label} requires concrete facing and gaze")
        if re.search(r"\bcamera\b", target + " " + facing + " " + gaze, re.I):
            raise StoryVideoError(f"{label} may not address the camera")
        result[source] = {"target": target, "facing": facing, "gaze": gaze}
    return result


def _parse_audio(value: str, *, label: str) -> list[dict[str, str]]:
    if value == "none":
        return []
    result: list[dict[str, str]] = []
    for item in _split_br(value):
        match = AUDIO_RE.fullmatch(item)
        if not match or not _concrete(match.group(2)):
            raise StoryVideoError(f"{label} contains an invalid or generic audio cue")
        result.append({"type": match.group(1), "description_en": match.group(2)})
    return result


def _parse_dialogue(value: str, *, label: str) -> dict[str, str] | None:
    if value == "none":
        return None
    match = DIALOGUE_RE.fullmatch(value)
    if not match:
        raise StoryVideoError(f"{label} does not use the exact Dialogue syntax")
    line_id, speaker, mode, gate, transition, delivery, spoken = (
        part.strip() for part in match.groups()
    )
    if mode not in SPEECH_DELIVERY_MODES:
        raise StoryVideoError(f"{label} has an invalid speech delivery mode")
    if (
        not _concrete(gate)
        or not _concrete(transition)
        or not _present(spoken)
    ):
        raise StoryVideoError(
            f"{label} requires a concrete gate, natural speech transition, "
            "and exact spoken text"
        )
    if delivery != "none" and not _present(delivery):
        raise StoryVideoError(f"{label} Delivery must be concrete or none")
    return {
        "line_id": line_id,
        "speaker_entity_id": speaker,
        "delivery_mode": mode,
        "gate_en": gate,
        "speech_transition_en": transition,
        "delivery_en": delivery,
        "spoken_text_ar": spoken,
    }


def _parse_shot_rows(
    rows: list[dict[str, str]], *, label: str
) -> list[dict[str, Any]]:
    shots: list[dict[str, Any]] = []
    for row in rows:
        shot_id = row["Shot ID"]
        if not ACTION_ID_RE.fullmatch(shot_id):
            raise StoryVideoError(f"{label} has an invalid Shot ID")
        scale = row["Scale / View"]
        if scale not in SCALE_VIEWS:
            raise StoryVideoError(f"{shot_id} has an invalid Scale / View")
        performers = _ids(
            row["Performers"], ENTITY_ID_RE, label=f"{shot_id} Performers", allow_none=True
        )
        if any(
            not _concrete(row[field], allow_none=field == "Important Reaction")
            for field in (
                "Dramatic Change",
                "Objective / Tactic",
                "Visual Action",
                "Important Reaction",
                "Blocking / Movement",
                "Audience Focus",
            )
        ):
            raise StoryVideoError(f"{shot_id} contains missing or generic dramatic content")
        if performers and row["Blocking / Movement"] == "none":
            raise StoryVideoError(f"{shot_id} performers require explicit Blocking / Movement")
        completion = row["Completion State"]
        completion_match = re.fullmatch(r"(completed|open):\s*(.+)", completion)
        if not completion_match or not _concrete(completion_match.group(2)):
            raise StoryVideoError(f"{shot_id} has an invalid Completion State")
        beat_id = row["Beat ID"]
        if not BEAT_ID_RE.fullmatch(beat_id):
            raise StoryVideoError(f"{shot_id} has an invalid Beat ID")
        shots.append(
            {
                "shot_id": shot_id,
                "beat_id": beat_id,
                "scale_view": scale,
                "duration_seconds": _positive_number(
                    row["Duration Seconds"], label=f"{shot_id} Duration Seconds"
                ),
                "performer_ids": performers,
                "dramatic_change_en": row["Dramatic Change"],
                "objective_tactic_en": row["Objective / Tactic"],
                "visual_action_en": row["Visual Action"],
                "important_reaction_en": row["Important Reaction"],
                "blocking_movement_en": row["Blocking / Movement"],
                "gaze_relations": _parse_gaze(
                    row["Gaze / Addressee"], label=f"{shot_id} Gaze / Addressee"
                ),
                "completion_mode": completion_match.group(1),
                "completion_state_en": completion,
                "audience_focus_en": row["Audience Focus"],
                "audio_cues": _parse_audio(
                    row["BGM / SFX / Ambience"],
                    label=f"{shot_id} BGM / SFX / Ambience",
                ),
                "audio_cell_en": row["BGM / SFX / Ambience"],
                "dialogue": _parse_dialogue(
                    row["Dialogue"], label=f"{shot_id} Dialogue"
                ),
            }
        )
    return shots


def parse_screenplay_markdown(text: str) -> dict[str, Any]:
    if "```json" in text.casefold() or "_json" in text or "{" in text or "}" in text:
        raise StoryVideoError(
            "screenplay.md must contain Markdown tables only, with no embedded JSON"
        )
    lines = text.lstrip("\ufeff").splitlines()
    if not lines:
        raise StoryVideoError("screenplay.md is empty")
    title = TITLE_RE.fullmatch(lines[0].strip())
    if not title:
        raise StoryVideoError(
            "screenplay.md must begin with "
            "'# Cinematic Widescreen Production Script: <title>'"
        )

    index = _expect_heading(lines, 1, "## Production Information")
    production_information, index = _parse_field_table(
        lines,
        index,
        PRODUCTION_INFORMATION_FIELDS,
        label="Production Information",
    )

    index = _expect_heading(lines, index, "## Characters")
    character_rows, index = _parse_table(
        lines, index, columns=CHARACTER_TABLE_COLUMNS, label="Characters table"
    )
    characters: list[dict[str, Any]] = []
    entity_map: dict[str, dict[str, Any]] = {}
    character_names: set[str] = set()
    for row in character_rows:
        entity_id = row["Entity ID"]
        name = row["Character"]
        if not ENTITY_ID_RE.fullmatch(entity_id) or entity_id in entity_map:
            raise StoryVideoError("Characters table repeats or invalidates an Entity ID")
        if name.casefold() in character_names:
            raise StoryVideoError("Characters table repeats a Character name")
        character_names.add(name.casefold())
        member_types = (
            []
            if row["Member Types"] == "none"
            else [item.strip() for item in row["Member Types"].split(";")]
        )
        entity = {
            "entity_id": entity_id,
            "screenplay_character_name_en": name,
            "story_role": row["Story Role"],
            "narrative_function_en": row["Narrative Function"],
            "entity_kind": row["Kind"],
            "recurring": _yes_no(row["Recurring"], label=f"{entity_id} Recurring"),
            "group_role_type_en": row["Group Role"],
            "ensemble_member_types_en": member_types,
            "narration_eligibility": row["Narration"],
            "description_en": row["Description"],
        }
        characters.append(entity)
        entity_map[entity_id] = entity

    index = _expect_heading(lines, index, "## Script")
    raw_units: list[dict[str, Any]] = []
    while True:
        index = _next_nonempty(lines, index)
        if index >= len(lines) or lines[index].strip() == "## Continuity Appendix":
            break
        match = SCENE_UNIT_RE.fullmatch(lines[index].strip())
        if not match or int(match.group(1)) != len(raw_units) + 1:
            raise StoryVideoError(f"Unexpected screenplay line: {lines[index].strip()}")
        unit_number = int(match.group(1))
        index = _expect_heading(lines, index + 1, "### Scene Unit Information")
        fields, index = _parse_field_table(
            lines,
            index,
            SCENE_UNIT_INFORMATION_FIELDS,
            label=f"Scene Unit {unit_number} Information",
        )
        index = _expect_heading(lines, index, "### Shot Execution")
        shot_rows, index = _parse_table(
            lines,
            index,
            columns=SHOT_EXECUTION_COLUMNS,
            label=f"Scene Unit {unit_number} Shot Execution",
        )
        shots = _parse_shot_rows(shot_rows, label=f"Scene Unit {unit_number}")
        index = _expect_heading(lines, index, "### Character Staging")
        staging_rows, index = _parse_table(
            lines,
            index,
            columns=CHARACTER_STAGING_COLUMNS,
            label=f"Scene Unit {unit_number} Character Staging",
        )
        calls = []
        for row in staging_rows:
            calls.append(
                {
                    "entity_id": row["Entity ID"],
                    "presence_mode": row["Presence"],
                    "appearance_mode": row["Appearance"],
                    "appearance_trigger_en": row["Trigger"],
                    "entry_path_or_opening_position_en": row[
                        "Entry Path / Opening Position"
                    ],
                    "first_visible_block_id": row["First Visible Shot"],
                    "first_visible_moment_en": row["First Visible Moment"],
                    "landing_block_id": row["Landing Shot"],
                    "landing_result_en": row["Landing Moment / Result"],
                    "speaks": _yes_no(row["Speaks"], label=f"{row['Entity ID']} Speaks"),
                    "line_ids": _ids(
                        row["Lines"],
                        LINE_ID_RE,
                        label=f"{row['Entity ID']} Lines",
                        allow_none=True,
                    ),
                    "state_changing_action": _yes_no(
                        row["State Change"], label=f"{row['Entity ID']} State Change"
                    ),
                    "action_block_ids": _ids(
                        row["Action Shots"],
                        ACTION_ID_RE,
                        label=f"{row['Entity ID']} Action Shots",
                        allow_none=True,
                    ),
                }
            )
        raw_units.append(
            {
                "id": unit_number,
                "label_en": match.group(2).strip(),
                "fields": fields,
                "shots": shots,
                "performance_calls": calls,
            }
        )

    index = _expect_heading(lines, index, "## Continuity Appendix")
    index = _expect_heading(lines, index, "### Environments")
    rows, index = _parse_table(
        lines, index, columns=ENVIRONMENT_TABLE_COLUMNS, label="Environments table"
    )
    environments = [
        {
            "environment_id": row["Environment ID"],
            "logical_name_en": row["Logical Environment"],
            "scene_ids_json": _ids(
                row["Scene IDs"], SCENE_ID_RE, label="Environment Scene IDs"
            ),
            "int_ext": row["INT/EXT"],
            "time_context_en": row["Time Context"],
            "environment_facts_en": row["Environment Facts"],
            "story_function_en": row["Story Function"],
        }
        for row in rows
    ]

    index = _expect_heading(lines, index, "### Scenes")
    rows, index = _parse_table(lines, index, columns=SCENE_TABLE_COLUMNS, label="Scenes table")
    scenes = [
        {
            "scene_id": row["Scene ID"],
            "segment_ids_json": _ids(
                row["Segment IDs"], SEGMENT_ID_RE, label="Scene Segment IDs"
            ),
            "primary_time_en": row["Primary Time"],
            "primary_place_en": row["Primary Place"],
            "narrative_event_en": row["Narrative Event"],
            "entry_boundary": row["Entry Boundary"],
            "entry_reason_en": row["Entry Reason"],
            "continuity_reference_segment_id": row["Continuity Reference Segment"],
            "continuity_reference_reason_en": row["Continuity Reference Reason"],
        }
        for row in rows
    ]

    index = _expect_heading(lines, index, "### Scene Dramatic Contracts")
    rows, index = _parse_table(
        lines,
        index,
        columns=SCENE_CONTRACT_TABLE_COLUMNS,
        label="Scene Dramatic Contracts table",
    )
    scene_contracts = {
        row["Scene ID"]: {
            "scene_id": row["Scene ID"],
            "scene_purpose": row["Purpose"],
            "character_objective": row["Character Objective"],
            "obstacle": row["Obstacle"],
            "power_relationship": row["Power Relationship"],
            "turning_point": row["Turning Point"],
            "outcome": row["Outcome"],
            "visual_progression": row["Spatial Progression"],
            "exit_impulse": row["Exit Impulse"],
        }
        for row in rows
    }

    index = _expect_heading(lines, index, "### Character Scene States")
    rows, index = _parse_table(
        lines,
        index,
        columns=CHARACTER_SCENE_STATE_TABLE_COLUMNS,
        label="Character Scene States table",
    )
    character_scene_states = [
        {
            "scene_id": row["Scene ID"],
            "segment_id": row["Segment ID"],
            "entity_id": row["Entity ID"],
            "state_source_segment_id": row["State Source Segment"],
            "incoming_diegetic_presence": row["Incoming Diegetic Presence"],
            "visibility_requirement": row["Visibility Requirement"],
            "required_visible_shot_ids": _ids(
                row["Required Visible Shots"],
                ACTION_ID_RE,
                label=(
                    f"{row['Segment ID']} {row['Entity ID']} "
                    "Required Visible Shots"
                ),
                allow_none=True,
            ),
            "position_injury_condition_en": row[
                "Position, Injury and Condition"
            ],
            "transition_cause_en": row["Transition Cause"],
            "outgoing_diegetic_presence": row["Outgoing Diegetic Presence"],
        }
        for row in rows
    ]

    index = _expect_heading(lines, index, "### Continuity States")
    rows, index = _parse_table(
        lines,
        index,
        columns=CONTINUITY_STATE_TABLE_COLUMNS,
        label="Continuity States table",
    )
    continuity_states = [
        {
            "state_id": row["State ID"],
            "parent_state_ref": row["Parent State"],
            "changed_facts_en": row["Changed Facts"],
            "change_reason_en": row["Change Reason"],
        }
        for row in rows
    ]
    state_map = {item["state_id"]: item for item in continuity_states}

    index = _expect_heading(lines, index, "### Continuity Boundaries")
    rows, index = _parse_table(
        lines,
        index,
        columns=CONTINUITY_BOUNDARY_TABLE_COLUMNS,
        label="Continuity Boundaries table",
        allow_empty=True,
    )
    continuity_boundaries = [
        {
            "boundary_id": row["Boundary ID"],
            "from_segment_id": row["From Segment"],
            "to_segment_id": row["To Segment"],
            "from_state_ref": row["From State"],
            "to_state_ref": row["To State"],
            "handoff": row["Handoff"],
            "transition_type": row["Transition"],
            "dramatic_reason_en": row["Dramatic Reason"],
            "audio_handoff_en": row["Audio Handoff"],
            "continuity_handoff_en": row["Continuity Handoff"],
        }
        for row in rows
    ]
    if _next_nonempty(lines, index) != len(lines):
        raise StoryVideoError("screenplay.md contains content after the appendix")

    boundary_map = {item["boundary_id"]: item for item in continuity_boundaries}
    segments: list[dict[str, Any]] = []
    for unit_index, raw in enumerate(raw_units, start=1):
        fields = raw["fields"]
        expected_segment_id = f"segment-{unit_index:03d}"
        if fields["Segment ID"] != expected_segment_id:
            raise StoryVideoError(
                f"Scene Unit {unit_index} Segment ID must be {expected_segment_id}"
            )
        scene_id = fields["Scene ID"]
        if not SCENE_ID_RE.fullmatch(scene_id):
            raise StoryVideoError(f"{expected_segment_id} has an invalid Scene ID")
        if not SLUGLINE_RE.fullmatch(fields["Slugline"]):
            raise StoryVideoError(f"{expected_segment_id} has an invalid Slugline")
        if not re.fullmatch(r"[0-9]+", fields["Duration Seconds"]):
            raise StoryVideoError(
                f"{expected_segment_id} Duration Seconds must be an integer"
            )
        if not _concrete(fields["Environment"]) or not _concrete(
            fields["Dramatic Purpose"]
        ):
            raise StoryVideoError(
                f"{expected_segment_id} requires concrete Environment and Dramatic Purpose"
            )
        contract = scene_contracts.get(scene_id)
        if contract is None:
            raise StoryVideoError(f"{expected_segment_id} references an unknown Scene")
        start_ref = fields["Start State"]
        end_ref = fields["End State"]
        if start_ref not in state_map or end_ref not in state_map:
            raise StoryVideoError(f"{expected_segment_id} references an unknown continuity state")
        incoming_ref = fields["Incoming Boundary"]
        if unit_index == 1:
            if incoming_ref != "opening":
                raise StoryVideoError("segment-001 Incoming Boundary must be opening")
        else:
            incoming = boundary_map.get(incoming_ref)
            if incoming is None:
                raise StoryVideoError(
                    f"{expected_segment_id} references an unknown Incoming Boundary"
                )
        for call in raw["performance_calls"]:
            if call["entity_id"] not in entity_map:
                raise StoryVideoError(
                    f"{expected_segment_id} stages an undeclared Entity ID"
                )
        plan = {
            "segment_id": expected_segment_id,
            "scene_id": scene_id,
            "estimated_duration_seconds": int(fields["Duration Seconds"]),
            "dramatic_workload": fields["Workload"],
            "location_time_environment_en": fields["Environment"],
            "narrative_purpose_en": fields["Dramatic Purpose"],
            "scene_dramatic_contract": contract,
            "start_state_ref": start_ref,
            "end_state_ref": end_ref,
            "incoming_boundary_ref": incoming_ref,
        }
        segments.append(
            {
                "id": unit_index,
                "heading_en": fields["Slugline"],
                "label_en": raw["label_en"],
                "shots": raw["shots"],
                "story_plan": plan,
                "performance_calls": raw["performance_calls"],
            }
        )

    screenplay = {
        "screenplay_title_en": title.group(1).strip(),
        "production_information": production_information,
        "characters": characters,
        "environments": environments,
        "scenes": scenes,
        "scene_dramatic_contracts": scene_contracts,
        "character_scene_states": character_scene_states,
        "continuity_states": continuity_states,
        "continuity_boundaries": continuity_boundaries,
        "segments": segments,
    }
    # Import at the validation boundary so the parser remains independently
    # loadable while validation can lazily call it for file loading.
    from narrated_fable_drama.contracts.screenplay.validation import (
        validate_screenplay,
    )

    validate_screenplay(screenplay)
    return screenplay
