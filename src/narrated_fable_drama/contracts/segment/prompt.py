"""Parse and validate exact Seedance Segment Prompt files."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.contracts.segment.common import (
    PRECISE_TIME_RANGE_RE,
    SCRIPT_RE,
    TOKEN_SCAN_RE,
    SegmentRuntimeError,
    token_sort_key,
)
from narrated_fable_drama.contracts.segment.storyboard import (
    storyboard_segment_rows,
)


def _prompt_dialogue_blocks(text: str) -> list[str]:
    return re.findall(r"\{([^{}]+)\}", text)


def _validate_on_screen_text(prompt: str, segment_id: str) -> None:
    stripped = re.sub(r"【[^【】]+】", "", prompt)
    if "【" in stripped or "】" in stripped:
        raise SegmentRuntimeError(
            f"{segment_id} Prompt has malformed on-screen text delimiters"
        )


def _validate_visual_doctrine(prompt: str, row: dict[str, Any]) -> None:
    contract = row["prompt_contract"]
    required_declarations = {
        "Visible-character economy:": contract["visible_character_economy_en"],
        "Eyeline axis and screen direction:": contract[
            "eyeline_axis_and_screen_direction_en"
        ],
        "Close-up-led coverage:": contract["shot_size_policy"],
    }
    for label, authority in required_declarations.items():
        if label.casefold() not in prompt.casefold() or authority not in prompt:
            raise SegmentRuntimeError(
                f"{row['segment_id']} Prompt must copy the Storyboard declaration "
                f"{label}"
            )

    shot_matches = list(
        re.finditer(
            r"^(?:#{1,6}\s*)?Shot ([1-9][0-9]*): "
            r"(extreme_close_up|close_up|medium_close_up|medium|"
            r"medium_wide|wide|extreme_wide)\.",
            prompt,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    expected_sizes = [shot[2] for shot in row["ordered_shots"]]
    actual = [(int(match.group(1)), match.group(2).casefold()) for match in shot_matches]
    expected = list(enumerate(expected_sizes, start=1))
    if actual != expected:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt Shot headings must exactly preserve "
            "'Shot N: <Storyboard shot_size>.' in order"
        )
    wide_sizes = {"medium_wide", "wide", "extreme_wide"}
    for index, match in enumerate(shot_matches):
        if match.group(2).casefold() not in wide_sizes:
            continue
        end = (
            shot_matches[index + 1].start()
            if index + 1 < len(shot_matches)
            else len(prompt)
        )
        shot_block = prompt[match.end() : end]
        if "position-change exception:" not in shot_block.casefold():
            raise SegmentRuntimeError(
                f"{row['segment_id']} Shot {index + 1} wider framing lacks the "
                "literal position-change exception"
            )


def _validate_prompt(text: str, row: dict[str, Any], path: Path) -> str:
    prompt = text.strip()
    if not prompt:
        raise SegmentRuntimeError(f"Seedance Prompt is empty: {path}")
    tokens = sorted(
        set(match.group(0) for match in TOKEN_SCAN_RE.finditer(prompt)),
        key=token_sort_key,
    )
    expected_tokens = sorted(
        [item["provider_token"] for item in row["bindings"]],
        key=token_sort_key,
    )
    if tokens != expected_tokens:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt provider tokens differ from Storyboard Reference Plan"
        )
    if PRECISE_TIME_RANGE_RE.search(prompt):
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt must use event order, not precise second ranges"
        )
    if row["visual_style"].casefold() not in prompt.casefold():
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt must name the exact approved Visual Style "
            f"{row['visual_style']!r}"
        )
    _validate_on_screen_text(prompt, row["segment_id"])
    _validate_visual_doctrine(prompt, row)
    dialogue_blocks = _prompt_dialogue_blocks(prompt)
    for cue in row["dialogue_cues"]:
        exact = cue["exact_text"]
        if dialogue_blocks.count(exact) != 1:
            raise SegmentRuntimeError(
                f"{cue['line_id']} exact speech must appear once in literal braces"
            )
        if cue["speaker_name"].casefold() not in prompt.casefold():
            raise SegmentRuntimeError(
                f"{cue['line_id']} Prompt lacks readable speaker {cue['speaker_name']}"
            )
        if cue["delivery_mode"] in {
            "off_camera_storytelling",
            "external_voiceover",
        }:
            line_position = prompt.find("{" + exact + "}")
            nearby = prompt[max(0, line_position - 500) : line_position + len(exact) + 100]
            if not re.search(r"\boff[- ](?:screen|camera)|voiceover|voice-over\b", nearby, re.I):
                raise SegmentRuntimeError(
                    f"{cue['line_id']} off-camera storytelling is not explicit near the line"
                )
    unexpected = [item for item in dialogue_blocks if item not in {
        cue["exact_text"] for cue in row["dialogue_cues"]
    }]
    if unexpected:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt contains unauthorised spoken text in braces"
        )
    return prompt


def parse_segment_script(path: Path) -> dict[str, Any]:
    script_path = path.expanduser().resolve()
    try:
        text = script_path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError) as exc:
        raise SegmentRuntimeError(f"Unreadable Seedance Prompt: {script_path}") from exc
    match = SCRIPT_RE.fullmatch(script_path.name)
    if match is None:
        raise SegmentRuntimeError(f"Invalid Seedance Prompt filename: {script_path.name}")
    segment_id = f"segment-{int(match.group(1)):03d}"
    task_dir = script_path.parents[3]
    rows = storyboard_segment_rows(
        task_dir, validation_through_segment_id=segment_id
    )
    row = next(item for item in rows if item["segment_id"] == segment_id)
    prompt = _validate_prompt(text, row, script_path)
    return {
        "segment_id": segment_id,
        "number": int(match.group(1)),
        "path": script_path,
        "text": text,
        "script_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "metadata": row,
        "duration": row["target_duration"],
        "prompt": prompt,
        "bindings": row["bindings"],
    }
