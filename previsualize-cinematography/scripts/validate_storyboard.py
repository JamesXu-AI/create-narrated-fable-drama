#!/usr/bin/env python3
"""Validate the single-file cinematic Storyboard release without authoring it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_SCRIPTS_ROOT = REPOSITORY_ROOT / "scripts"
if str(PROJECT_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_SCRIPTS_ROOT))

from project_domain import ProjectDomainError, validate_project_profiles  # noqa: E402


REQUIRED_HEADINGS = (
    "## Project Direction",
    "## Generation Plan",
    "## Location State Plan",
    "## Character Segment State Plan",
    "## Continuity Review",
)
SEGMENT_HEADING_RE = re.compile(r"^## Generation Segment ([1-9][0-9]*) — .+$", re.M)
JSONISH_RE = re.compile(r"```(?:json|yaml|yml)|\{\s*[\"']|\[\s*\{", re.I)
REQUIRED_SEGMENT_SUBHEADINGS = (
    "### Segment Direction",
    "### Reference Plan",
    "### Ordered Shots",
    "### Prompt Translation Notes",
)
ORDERED_SHOT_HEADERS = (
    "Shot",
    "Screenplay Shot",
    "Shot Size",
    "Transition and Camera",
    "Subject Action and Expression",
    "Space, Blocking and Gaze",
    "Persistent Anchors",
    "Lighting and Color",
    "Dialogue and Native Audio",
    "Landing and Edit",
)
STORYBOARD_SHOT_SIZES = {
    "extreme_close_up",
    "close_up",
    "medium_close_up",
    "medium",
    "medium_wide",
    "wide",
    "extreme_wide",
}
STRONG_RESET_SHOT_SIZES = {
    "extreme_close_up",
    "close_up",
    "medium_close_up",
}
STRONG_RESET_CAMERA_RE = re.compile(
    r"\b(?:new|changed|reverse|opposite|low|high|top-down|ground-level|profile|"
    r"over-the-shoulder|pov)\b.{0,40}\b(?:angle|viewpoint|composition|camera|side)\b|"
    r"\b(?:angle|viewpoint|composition|camera|side)\b.{0,40}\b"
    r"(?:new|changed|reverse|opposite|low|high|top-down|ground-level|profile|"
    r"over-the-shoulder|pov)\b",
    re.IGNORECASE,
)
TIGHT_SCREENPLAY_SCALE_TO_STORYBOARD_SIZES = {
    "close_up": {"close_up", "extreme_close_up"},
    "extreme_close_up": {"extreme_close_up"},
    "insert": {"close_up", "extreme_close_up"},
    "reaction": {
        "medium",
        "medium_close_up",
        "close_up",
        "extreme_close_up",
    },
}
LOCATION_STATE_HEADERS = (
    "Location State Chain",
    "Segment",
    "Relationship",
    "State Source",
    "Temporal Evidence",
    "World and Population Evidence",
    "Persistent Anchors",
    "Allowed Changes",
)
LOCATION_RELATIONSHIPS = {
    "independent",
    "adjacent_continuation",
    "adjacent_coverage_reset",
    "nonadjacent_revisit",
    "reset_with_reason",
}
CHARACTER_STATE_HEADERS = (
    "Location State Chain",
    "Segment",
    "Screenplay Entity ID",
    "Character Asset ID",
    "State Source",
    "Incoming Presence",
    "Segment Presence Rule",
    "Required Visible Shots",
    "Allowed Occlusion",
    "Position, Injury and Condition",
    "Transition Cause",
    "Outgoing Presence",
)
SCREENPLAY_STATE_HEADERS = (
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
FRAME_PRESENCE_STATES = {"visible", "present_offscreen", "occluded", "absent"}
PRESENCE_RULES = {
    "must_remain_visible",
    "must_remain_present",
    "enter",
    "re_enter",
    "reveal",
    "conceal",
    "exit",
    "remain_absent",
    "reset_with_reason",
}


class StoryboardValidationError(RuntimeError):
    pass


def _storyboard_shot_ids(text: str) -> list[str]:
    return re.findall(
        r"^\|\s*Shot [1-9][0-9]*\s*\|\s*(A-[0-9]{3})\s*\|",
        text,
        re.M,
    )


def _screenplay_shot_ids(text: str) -> list[str]:
    return re.findall(r"^\|\s*(A-[0-9]{3})\s*\|", text, re.M)


def _screenplay_shot_scales(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in re.finditer(
        r"^\|\s*(A-[0-9]{3})\s*\|\s*[^|]+\|\s*"
        r"(establishing|wide|medium|close_up|extreme_close_up|insert|reaction|pov)"
        r"\s*\|",
        text,
        re.M,
    ):
        result[match.group(1)] = match.group(2)
    return result


def _table_after_heading(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    start = text.find(heading)
    if start < 0:
        raise StoryboardValidationError(f"Missing {heading}")
    section = text[start + len(heading):]
    next_heading = re.search(r"^## ", section, re.M)
    if next_heading:
        section = section[:next_heading.start()]
    lines = section.splitlines()
    table_start = next(
        (index for index, line in enumerate(lines) if line.strip().startswith("|")),
        None,
    )
    if table_start is None or table_start + 1 >= len(lines):
        raise StoryboardValidationError(f"{heading} must contain one Markdown table")

    def cells(line: str) -> list[str]:
        return [item.strip() for item in line.strip().strip("|").split("|")]

    headers = cells(lines[table_start])
    separator = cells(lines[table_start + 1])
    if len(separator) != len(headers) or any(not re.fullmatch(r":?-{3,}:?", item) for item in separator):
        raise StoryboardValidationError(f"{heading} has an invalid table separator")
    rows: list[list[str]] = []
    for line in lines[table_start + 2:]:
        if not line.strip().startswith("|"):
            if rows:
                break
            continue
        row = cells(line)
        if len(row) != len(headers):
            raise StoryboardValidationError(f"{heading} has an invalid table row")
        rows.append(row)
    if not rows:
        raise StoryboardValidationError(f"{heading} table must not be empty")
    return headers, rows


def _validate_location_state_plan(text: str, segment_count: int) -> set[str]:
    headers, rows = _table_after_heading(text, "## Location State Plan")
    if tuple(headers) != LOCATION_STATE_HEADERS:
        raise StoryboardValidationError(
            "Location State Plan columns differ from the current contract"
        )
    expected_segments = [f"segment-{index:03d}" for index in range(1, segment_count + 1)]
    segments = [row[1] for row in rows]
    if segments != expected_segments:
        raise StoryboardValidationError(
            "Location State Plan must contain every Generation Segment exactly once in order"
        )
    prior_by_chain: dict[str, str] = {}
    coverage_reset_segments: set[str] = set()
    for index, row in enumerate(rows):
        (
            chain,
            segment,
            relationship,
            source,
            temporal_evidence,
            world_evidence,
            anchors,
            allowed,
        ) = row
        if not chain or relationship not in LOCATION_RELATIONSHIPS:
            raise StoryboardValidationError(f"{segment} has an invalid location-state relationship")
        if not world_evidence or world_evidence.casefold() == "none":
            raise StoryboardValidationError(
                f"{segment} lacks world and population evidence"
            )
        previous_in_chain = prior_by_chain.get(chain)
        if previous_in_chain is None:
            if relationship not in {"independent", "reset_with_reason"} or source.casefold() != "none":
                raise StoryboardValidationError(
                    f"{segment} starts location state chain {chain!r} without an independent/reset origin"
                )
        elif relationship in {"independent"}:
            raise StoryboardValidationError(
                f"{segment} revisits location state chain {chain!r} but is marked independent"
            )
        elif relationship in {
            "adjacent_continuation",
            "adjacent_coverage_reset",
            "nonadjacent_revisit",
        }:
            if source != previous_in_chain:
                raise StoryboardValidationError(
                    f"{segment} must inherit the latest prior Segment in location state chain {chain!r}"
                )
            previous_global = expected_segments[index - 1] if index else None
            if relationship in {
                "adjacent_continuation",
                "adjacent_coverage_reset",
            } and source != previous_global:
                raise StoryboardValidationError(f"{segment} is not an adjacent continuation")
            if relationship == "nonadjacent_revisit" and source == previous_global:
                raise StoryboardValidationError(f"{segment} is adjacent, not a nonadjacent revisit")
            if relationship == "adjacent_coverage_reset":
                if temporal_evidence != "semantic_state_only_no_provider_media":
                    raise StoryboardValidationError(
                        f"{segment} strong coverage reset must use semantic state "
                        "without predecessor media"
                    )
                coverage_reset_segments.add(segment)
            elif temporal_evidence.casefold() == "none" or not temporal_evidence:
                raise StoryboardValidationError(f"{segment} lacks temporal evidence")
            previous_row = rows[index - 1] if index else None
            if (
                relationship == "adjacent_continuation"
                and previous_row is not None
                and previous_row[0] == chain
                and previous_row[2] == "adjacent_continuation"
            ):
                raise StoryboardValidationError(
                    f"{segment} attempts a second consecutive predecessor-media "
                    "inheritance; use adjacent_coverage_reset"
                )
        if anchors.casefold() == "none" or not anchors:
            raise StoryboardValidationError(f"{segment} lacks persistent anchors")
        if relationship == "reset_with_reason" and (not allowed or allowed.casefold() == "none"):
            raise StoryboardValidationError(f"{segment} reset has no authored reason")
        prior_by_chain[chain] = segment
    return coverage_reset_segments


def _comma_values(value: str) -> list[str]:
    if value.casefold() == "none":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _ordered_shot_map(text: str) -> dict[str, dict[str, set[str]]]:
    """Map internal Storyboard Shots to the screenplay Shots they execute."""

    result: dict[str, dict[str, set[str]]] = {}
    matches = list(SEGMENT_HEADING_RE.finditer(text))
    for index, match in enumerate(matches):
        segment_id = f"segment-{int(match.group(1)):03d}"
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end():end]
        headers, rows = _table_after_heading(section, "### Ordered Shots")
        if tuple(headers) != ORDERED_SHOT_HEADERS:
            raise StoryboardValidationError(
                f"{segment_id} Ordered Shots columns differ from the current contract"
            )
        current: dict[str, set[str]] = {}
        for row in rows:
            shot_label = row[0]
            if (
                not re.fullmatch(r"Shot [1-9][0-9]*", shot_label)
                or shot_label in current
            ):
                raise StoryboardValidationError(
                    f"{segment_id} has invalid or repeated internal Shot labels"
                )
            screenplay_shots = set(re.findall(r"A-[0-9]{3,}", row[1]))
            if not screenplay_shots:
                raise StoryboardValidationError(
                    f"{segment_id} {shot_label} lacks screenplay Shot traceability"
                )
            if row[2] not in STORYBOARD_SHOT_SIZES:
                raise StoryboardValidationError(
                    f"{segment_id} {shot_label} has invalid Shot Size {row[2]!r}"
                )
            current[shot_label] = screenplay_shots
        result[segment_id] = current
    return result


def _validate_shot_size_authority(task_dir: Path, storyboard_text: str) -> dict[str, int]:
    """Require explicit sizes and prevent widening screenplay-owned tight views."""

    screenplay_path = task_dir / "screenplay-writer/screenplay.md"
    if not screenplay_path.is_file():
        return {}
    screenplay_scales = _screenplay_shot_scales(
        screenplay_path.read_text(encoding="utf-8")
    )
    size_counts = {size: 0 for size in sorted(STORYBOARD_SHOT_SIZES)}
    matches = list(SEGMENT_HEADING_RE.finditer(storyboard_text))
    for index, match in enumerate(matches):
        segment_id = f"segment-{int(match.group(1)):03d}"
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(storyboard_text)
        )
        section = storyboard_text[match.end():end]
        headers, rows = _table_after_heading(section, "### Ordered Shots")
        if tuple(headers) != ORDERED_SHOT_HEADERS:
            raise StoryboardValidationError(
                f"{segment_id} Ordered Shots columns differ from the current contract"
            )
        for row in rows:
            storyboard_size = row[2]
            size_counts[storyboard_size] += 1
            screenplay_ids = re.findall(r"A-[0-9]{3,}", row[1])
            for screenplay_id in screenplay_ids:
                screenplay_scale = screenplay_scales.get(screenplay_id)
                allowed = TIGHT_SCREENPLAY_SCALE_TO_STORYBOARD_SIZES.get(
                    screenplay_scale or ""
                )
                if allowed is not None and storyboard_size not in allowed:
                    raise StoryboardValidationError(
                        f"{segment_id} {row[0]} widens screenplay "
                        f"{screenplay_id} {screenplay_scale} to {storyboard_size}"
                    )
    return {key: value for key, value in size_counts.items() if value}


def _production_design_asset_map(task_dir: Path) -> dict[str, str]:
    """Resolve screenplay entity IDs to approved individual/closed-roster assets."""

    plan_path = task_dir / "direct-production-design/production-design-plan.json"
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StoryboardValidationError(
            f"Missing or invalid production-design authority: {plan_path}"
        ) from exc
    if not isinstance(plan, dict):
        raise StoryboardValidationError("Production-design plan must be an object")
    result: dict[str, str] = {}
    for row in plan.get("characters", []):
        if isinstance(row, dict):
            entity_id = row.get("entity_id")
            if isinstance(entity_id, str) and entity_id:
                result[entity_id] = entity_id
    group_assets = {
        row.get("group_role_type_en"): row.get("asset_id")
        for row in plan.get("ensemble_rosters", [])
        if isinstance(row, dict)
        and isinstance(row.get("group_role_type_en"), str)
        and isinstance(row.get("asset_id"), str)
    }
    screenplay_path = task_dir / "screenplay-writer/screenplay.md"
    screenplay_text = screenplay_path.read_text(encoding="utf-8")
    headers, rows = _table_after_heading(screenplay_text, "## Characters")
    try:
        entity_index = headers.index("Entity ID")
        kind_index = headers.index("Kind")
        role_index = headers.index("Group Role")
    except ValueError as exc:
        raise StoryboardValidationError(
            "Screenplay Characters table lacks asset-mapping fields"
        ) from exc
    for row in rows:
        if row[kind_index] != "anonymous_ensemble":
            continue
        asset_id = group_assets.get(row[role_index])
        if not isinstance(asset_id, str):
            raise StoryboardValidationError(
                f"No closed-roster asset maps screenplay entity {row[entity_index]}"
            )
        result[row[entity_index]] = asset_id
    return result


def _validate_character_state_plan(
    task_dir: Path,
    storyboard_text: str,
    segment_count: int,
) -> None:
    """Require Storyboard occupancy to preserve screenplay lifecycle authority."""

    headers, rows = _table_after_heading(
        storyboard_text, "## Character Segment State Plan"
    )
    if tuple(headers) != CHARACTER_STATE_HEADERS:
        raise StoryboardValidationError(
            "Character Segment State Plan columns differ from the current contract"
        )
    ordered_shots = _ordered_shot_map(storyboard_text)
    expected_segments = {
        f"segment-{index:03d}" for index in range(1, segment_count + 1)
    }
    authored: dict[tuple[str, str], dict[str, object]] = {}
    latest_by_chain_entity: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        (
            chain,
            segment_id,
            entity_id,
            asset_id,
            source,
            incoming,
            rule,
            required_cell,
            allowed_occlusion,
            position_condition,
            transition_cause,
            outgoing,
        ) = row
        if (
            segment_id not in expected_segments
            or not chain
            or not entity_id
            or not asset_id
            or incoming not in FRAME_PRESENCE_STATES
            or outgoing not in FRAME_PRESENCE_STATES
            or rule not in PRESENCE_RULES
        ):
            raise StoryboardValidationError(
                f"{segment_id or 'unknown Segment'} has an invalid Character state row"
            )
        key = (segment_id, entity_id)
        if key in authored:
            raise StoryboardValidationError(
                f"{segment_id} repeats Character state for {entity_id}"
            )
        required = _comma_values(required_cell)
        if any(item not in ordered_shots[segment_id] for item in required):
            raise StoryboardValidationError(
                f"{segment_id} {entity_id} names an unknown required internal Shot"
            )
        all_internal = list(ordered_shots[segment_id])
        if rule == "must_remain_visible" and required != all_internal:
            raise StoryboardValidationError(
                f"{segment_id} {entity_id} must remain visible in every internal Shot"
            )
        if rule == "remain_absent" and (
            incoming != "absent" or outgoing != "absent" or required
        ):
            raise StoryboardValidationError(
                f"{segment_id} {entity_id} has an invalid absent hold"
            )
        if not allowed_occlusion or not position_condition or not transition_cause:
            raise StoryboardValidationError(
                f"{segment_id} {entity_id} has incomplete Character state authority"
            )
        prior = latest_by_chain_entity.get((chain, entity_id))
        if prior is None:
            if source != "none":
                raise StoryboardValidationError(
                    f"{segment_id} {entity_id} has no earlier state in {chain}"
                )
        else:
            if source != prior["segment_id"]:
                raise StoryboardValidationError(
                    f"{segment_id} {entity_id} must source {prior['segment_id']}"
                )
            if incoming != prior["outgoing"]:
                raise StoryboardValidationError(
                    f"{segment_id} {entity_id} incoming presence differs from its source"
                )
        latest_by_chain_entity[(chain, entity_id)] = {
            "segment_id": segment_id,
            "outgoing": outgoing,
        }
        authored[key] = {
            "asset_id": asset_id,
            "incoming": incoming,
            "rule": rule,
            "required": required,
            "outgoing": outgoing,
        }

    screenplay_text = (
        task_dir / "screenplay-writer/screenplay.md"
    ).read_text(encoding="utf-8")
    screenplay_headers, screenplay_rows = _table_after_heading(
        screenplay_text, "### Character Scene States"
    )
    if tuple(screenplay_headers) != SCREENPLAY_STATE_HEADERS:
        raise StoryboardValidationError(
            "Screenplay Character Scene States columns differ from the current contract"
        )
    expected = {(row[1], row[2]): row for row in screenplay_rows}
    if set(authored) != set(expected):
        missing = sorted(set(expected) - set(authored))
        extra = sorted(set(authored) - set(expected))
        raise StoryboardValidationError(
            "Storyboard Character states must exactly trace screenplay lifecycle "
            f"rows; missing={missing}, extra={extra}"
        )
    asset_map = _production_design_asset_map(task_dir)
    for key, upstream in expected.items():
        segment_id, entity_id = key
        actual = authored[key]
        expected_asset = asset_map.get(entity_id)
        if actual["asset_id"] != expected_asset:
            raise StoryboardValidationError(
                f"{segment_id} {entity_id} must bind approved asset {expected_asset}"
            )
        incoming_world = upstream[4]
        visibility = upstream[5]
        required_screenplay = set(_comma_values(upstream[6]))
        outgoing_world = upstream[9]
        actual_incoming = str(actual["incoming"])
        actual_outgoing = str(actual["outgoing"])
        if (
            (incoming_world == "present_in_location")
            != (actual_incoming != "absent")
            or (outgoing_world == "present_in_location")
            != (actual_outgoing != "absent")
        ):
            raise StoryboardValidationError(
                f"{segment_id} {entity_id} downgrades screenplay diegetic presence"
            )
        required_internal = list(actual["required"])
        covered_screenplay = {
            screenplay_shot
            for shot_label in required_internal
            for screenplay_shot in ordered_shots[segment_id][shot_label]
        }
        if visibility == "visible_every_shot":
            if (
                actual["rule"]
                not in {
                    "must_remain_visible",
                    "enter",
                    "re_enter",
                    "reveal",
                    "exit",
                }
                or required_internal != list(ordered_shots[segment_id])
            ):
                raise StoryboardValidationError(
                    f"{segment_id} {entity_id} downgrades visible_every_shot"
                )
        elif visibility == "visible_in_required_shots":
            if not required_screenplay.issubset(covered_screenplay):
                raise StoryboardValidationError(
                    f"{segment_id} {entity_id} omits required visible screenplay "
                    f"Shots {sorted(required_screenplay - covered_screenplay)}"
                )
        elif visibility == "may_be_offscreen":
            if actual_outgoing == "absent":
                raise StoryboardValidationError(
                    f"{segment_id} {entity_id} treats an offscreen crop as an exit"
                )
        elif visibility == "must_remain_absent":
            if actual["rule"] != "remain_absent":
                raise StoryboardValidationError(
                    f"{segment_id} {entity_id} violates must_remain_absent"
                )


def validate_storyboard(task_dir: Path) -> dict:
    task_dir = task_dir.expanduser().resolve(strict=True)
    task_path = task_dir / "task.json"
    try:
        task = json.loads(task_path.read_text(encoding="utf-8"))
        validate_project_profiles(task, context=str(task_path))
    except (
        FileNotFoundError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ProjectDomainError,
    ) as exc:
        raise StoryboardValidationError(str(exc)) from exc
    release_dir = task_dir / "previsualize-cinematography"
    storyboard = release_dir / "storyboard.md"
    if not storyboard.is_file():
        raise StoryboardValidationError(f"Missing sole release: {storyboard}")
    files = sorted(path.name for path in release_dir.iterdir() if path.is_file())
    if files != ["storyboard.md"]:
        raise StoryboardValidationError(
            "previsualize-cinematography must contain only storyboard.md"
        )
    text = storyboard.read_text(encoding="utf-8")
    if not re.match(r"^# Cinematic Storyboard: .+", text):
        raise StoryboardValidationError("Storyboard title is missing or invalid")
    if JSONISH_RE.search(text):
        raise StoryboardValidationError("Storyboard contains JSON or YAML")
    positions = [text.find(heading) for heading in REQUIRED_HEADINGS]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise StoryboardValidationError("Required top-level sections are missing or out of order")
    matches = list(SEGMENT_HEADING_RE.finditer(text))
    numbers = [int(match.group(1)) for match in matches]
    if not numbers or numbers != list(range(1, len(numbers) + 1)):
        raise StoryboardValidationError("Generation Segment headings must be consecutive from 1")
    coverage_reset_segments = _validate_location_state_plan(text, len(numbers))
    _validate_character_state_plan(task_dir, text, len(numbers))
    shot_size_counts = _validate_shot_size_authority(task_dir, text)
    if not re.search(
        r"^\|\s*Shot Size and Intimacy Grammar\s*\|\s*\S",
        text,
        re.M,
    ):
        raise StoryboardValidationError(
            "Project Direction lacks Shot Size and Intimacy Grammar"
        )
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else positions[-1]
        section = text[match.end():end]
        sub_positions = [section.find(heading) for heading in REQUIRED_SEGMENT_SUBHEADINGS]
        if any(position < 0 for position in sub_positions) or sub_positions != sorted(sub_positions):
            raise StoryboardValidationError(
                f"Generation Segment {numbers[index]} sections are missing or out of order"
            )
        for field in (
            "Location State Chain",
            "Temporal Continuity Evidence",
            "World and Population Evidence",
            "Authorized Population",
            "Character Segment States",
            "Required Presence Locks",
            "Persistent Anchors",
            "Anchor Visibility Requirement",
            "Coverage Reset Requirement",
        ):
            if not re.search(rf"^\|\s*{re.escape(field)}\s*\|\s*\S", section, re.M):
                raise StoryboardValidationError(
                    f"Generation Segment {numbers[index]} lacks {field}"
                )
        segment_id = f"segment-{numbers[index]:03d}"
        reset_match = re.search(
            r"^\|\s*Coverage Reset Requirement\s*\|\s*(.+?)\s*\|\s*$",
            section,
            re.M,
        )
        if reset_match is None:
            raise StoryboardValidationError(
                f"Generation Segment {numbers[index]} lacks Coverage Reset Requirement"
            )
        reset_value = reset_match.group(1).strip()
        ordered_headers, ordered_rows = _table_after_heading(
            section, "### Ordered Shots"
        )
        if tuple(ordered_headers) != ORDERED_SHOT_HEADERS:
            raise StoryboardValidationError(
                f"{segment_id} Ordered Shots columns differ from the current contract"
            )
        if segment_id in coverage_reset_segments:
            opening_size = ordered_rows[0][2]
            expected_reset = (
                "required: no_predecessor_media; "
                f"opening={opening_size}; "
                "camera_break=new_angle_new_viewpoint_new_composition"
            )
            if opening_size not in STRONG_RESET_SHOT_SIZES:
                raise StoryboardValidationError(
                    f"{segment_id} strong coverage reset must open on an extreme "
                    "close-up, close-up, or medium close-up"
                )
            if reset_value != expected_reset:
                raise StoryboardValidationError(
                    f"{segment_id} must use exact Coverage Reset Requirement "
                    f"{expected_reset!r}"
                )
            if not STRONG_RESET_CAMERA_RE.search(ordered_rows[0][3]):
                raise StoryboardValidationError(
                    f"{segment_id} first reset Shot must describe a decisive new "
                    "angle, viewpoint, composition, or camera side"
                )
        elif reset_value != "not_required":
            raise StoryboardValidationError(
                f"{segment_id} must use Coverage Reset Requirement not_required"
            )
        ordered_shots = section.split("### Ordered Shots", 1)[1].split(
            "### Prompt Translation Notes", 1
        )[0]
        if "| Persistent Anchors |" not in ordered_shots:
            raise StoryboardValidationError(
                f"Generation Segment {numbers[index]} Ordered Shots lack Persistent Anchors"
            )
    screenplay = task_dir / "screenplay-writer/screenplay.md"
    if screenplay.is_file():
        expected = _screenplay_shot_ids(screenplay.read_text(encoding="utf-8"))
        actual = _storyboard_shot_ids(text)
        if expected != actual:
            raise StoryboardValidationError(
                "Storyboard Shot coverage or order differs from the approved screenplay"
            )
    return {
        "status": "PASS",
        "storyboard": str(storyboard),
        "generation_segment_count": len(numbers),
        "screenplay_shot_count": len(_storyboard_shot_ids(text)),
        "shot_size_counts": shot_size_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = validate_storyboard(args.task_dir)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
