from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(
    0,
    str(REPOSITORY_ROOT / "skills/previsualize-cinematography/scripts"),
)

from narrated_fable_drama.contracts.screenplay.boundaries import (
    _validate_shot_scale_grammar,
)
from narrated_fable_drama.contracts.segment.prompt import _validate_prompt
from narrated_fable_drama.contracts.segment.execution import (
    audio_reference_duration_policy,
    provider_identity_roles,
)
from narrated_fable_drama.contracts.segment.common import SegmentRuntimeError
from narrated_fable_drama.core.validation import StoryVideoError
from validate_storyboard import (  # noqa: E402
    StoryboardValidationError,
    _validate_shot_size_authority,
)


def _shot(shot_id: str, scale: str, blocking: str = "holds the established mark") -> dict:
    return {
        "shot_id": shot_id,
        "scale_view": scale,
        "blocking_movement_en": blocking,
    }


def _segments(*shots: dict) -> list[dict]:
    return [
        {
            "story_plan": {"scene_id": "scene-001"},
            "shots": list(shots),
        }
    ]


def _prompt_row() -> dict:
    economy = "Only Fox is visible; Owl remains present outside the crop."
    axis = (
        "The eyeline axis runs Fox-to-Owl; Fox is screen-left looking right, "
        "Owl is screen-right looking left; camera stays north of the axis."
    )
    size_policy = (
        "ECU/CU/MCU dominate; MWS/WS/EWS only for the shortest labeled "
        "position-change exception followed by a tight Shot."
    )
    return {
        "segment_id": "segment-001",
        "visual_style": "Test Style",
        "bindings": [],
        "dialogue_cues": [],
        "prompt_contract": {
            "visible_character_economy_en": economy,
            "eyeline_axis_and_screen_direction_en": axis,
            "shot_size_policy": size_policy,
        },
        "ordered_shots": [
            ["Shot 1", "A-001", "wide"],
            ["Shot 2", "A-002", "close_up"],
        ],
    }


def _prompt(*, include_wide_exception: bool) -> str:
    row = _prompt_row()
    contract = row["prompt_contract"]
    exception = (
        "position-change exception: Fox crosses from the tree mark to the stone "
        "mark, lands opposite Owl, then attention returns to Fox's eyes.\n"
        if include_wide_exception
        else "Fox remains visible in the forest.\n"
    )
    return (
        "Create a 16:9 Test Style video.\n"
        "Visible-character economy: "
        f"{contract['visible_character_economy_en']}\n"
        "Eyeline axis and screen direction: "
        f"{contract['eyeline_axis_and_screen_direction_en']}\n"
        "Close-up-led coverage: "
        f"{contract['shot_size_policy']}\n"
        "Shot 1: wide.\n"
        f"{exception}"
        "Shot 2: close_up.\n"
        "Hold on Fox's eyes and settled breath."
    )


def _storyboard_shot_row(
    number: int,
    screenplay_shot: str,
    size: str,
    space: str,
) -> str:
    return (
        f"| Shot {number} | {screenplay_shot} | {size} | locked camera | "
        f"readable action | {space} | tree | soft light | none; ambience | "
        "settled landing |"
    )


def _storyboard_text(*rows: str) -> str:
    separator = "| " + " | ".join(["---"] * 10) + " |"
    return "\n".join(
        [
            "## Generation Segment 1 — Test",
            "### Ordered Shots",
            (
                "| Shot | Screenplay Shot | Shot Size | Transition and Camera | "
                "Subject Action and Expression | Space, Blocking and Gaze | "
                "Persistent Anchors | Lighting and Color | Dialogue and Native "
                "Audio | Landing and Edit |"
            ),
            separator,
            *rows,
        ]
    )


def _write_screenplay_shot_stub(task_dir: Path, scales: list[str]) -> None:
    screenplay_dir = task_dir / "screenplay-writer"
    screenplay_dir.mkdir()
    rows = [
        f"| A-{index:03d} | BEAT-{index:03d} | {scale} |"
        for index, scale in enumerate(scales, start=1)
    ]
    (screenplay_dir / "screenplay.md").write_text(
        "\n".join(rows),
        encoding="utf-8",
    )


class CloseupVisualDoctrineTests(unittest.TestCase):
    def test_three_voice_references_are_trimmed_below_aggregate_limit(self) -> None:
        durations = audio_reference_duration_policy([6.0, 6.0, 6.0], 15.2)

        self.assertEqual(durations, [5.0, 5.0, 5.0])
        self.assertLessEqual(sum(durations), 15.2)

    def test_two_voice_references_keep_full_duration_when_under_limit(self) -> None:
        self.assertEqual(
            audio_reference_duration_policy([6.0, 6.0], 15.2),
            [6.0, 6.0],
        )

    def test_off_crop_present_role_is_not_submitted_as_positive_identity(self) -> None:
        submitted, internal_only = provider_identity_roles(
            [
                {
                    "character_asset_id": "e",
                    "segment_presence_rule": "must_remain_present",
                    "required_visible_shots": [2, 3],
                },
                {
                    "character_asset_id": "mo",
                    "segment_presence_rule": "must_remain_present",
                    "required_visible_shots": [],
                },
                {
                    "character_asset_id": "mee",
                    "segment_presence_rule": "remain_absent",
                    "required_visible_shots": [],
                },
            ]
        )

        self.assertEqual(submitted, ["e"])
        self.assertEqual(internal_only, ["mo", "mee"])

    def test_screenplay_wide_requires_position_change_exception(self) -> None:
        with self.assertRaisesRegex(
            StoryVideoError, "position-change exception"
        ):
            _validate_shot_scale_grammar(
                _segments(
                    _shot("A-001", "wide"),
                    _shot("A-002", "close_up"),
                    _shot("A-003", "reaction"),
                )
            )

    def test_screenplay_rejects_consecutive_wide_shots(self) -> None:
        with self.assertRaisesRegex(StoryVideoError, "consecutive"):
            _validate_shot_scale_grammar(
                _segments(
                    _shot(
                        "A-001",
                        "wide",
                        "position-change exception: Fox crosses to the door mark.",
                    ),
                    _shot(
                        "A-002",
                        "establishing",
                        "position-change exception: Owl exits through the door.",
                    ),
                    _shot("A-003", "close_up"),
                    _shot("A-004", "reaction"),
                    _shot("A-005", "insert"),
                )
            )

    def test_screenplay_requires_tight_attention_majority(self) -> None:
        with self.assertRaisesRegex(StoryVideoError, "must outnumber"):
            _validate_shot_scale_grammar(
                _segments(
                    _shot("A-001", "medium"),
                    _shot("A-002", "close_up"),
                )
            )

    def test_screenplay_accepts_tight_majority_and_one_brief_wide(self) -> None:
        _validate_shot_scale_grammar(
            _segments(
                _shot(
                    "A-001",
                    "wide",
                    "position-change exception: Fox crosses and lands by Owl.",
                ),
                _shot("A-002", "close_up"),
                _shot("A-003", "reaction"),
            )
        )

    def test_segment_prompt_requires_wide_exception_inside_wide_shot(self) -> None:
        with self.assertRaisesRegex(SegmentRuntimeError, "wider framing"):
            _validate_prompt(
                _prompt(include_wide_exception=False),
                _prompt_row(),
                Path("segment-001.md"),
            )

    def test_segment_prompt_accepts_explicit_visual_doctrine(self) -> None:
        validated = _validate_prompt(
            _prompt(include_wide_exception=True),
            _prompt_row(),
            Path("segment-001.md"),
        )
        self.assertIn("Shot 2: close_up.", validated)

    def test_segment_prompt_allows_authored_english_on_screen_text(self) -> None:
        validated = _validate_prompt(
            _prompt(include_wide_exception=True)
            + "\nA small sign contains 【MOON PLAY】.",
            _prompt_row(),
            Path("segment-001.md"),
        )
        self.assertIn("【MOON PLAY】", validated)

    def test_segment_prompt_rejects_malformed_on_screen_text(self) -> None:
        with self.assertRaisesRegex(
            SegmentRuntimeError, "malformed on-screen text delimiters"
        ):
            _validate_prompt(
                _prompt(include_wide_exception=True)
                + "\nA small sign contains 【MOON PLAY.",
                _prompt_row(),
                Path("segment-001.md"),
            )

    def test_storyboard_wide_requires_literal_position_change_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            _write_screenplay_shot_stub(
                task_dir, ["wide", "close_up", "reaction"]
            )
            storyboard = _storyboard_text(
                _storyboard_shot_row(
                    1, "A-001", "wide", "Fox crosses to Owl."
                ),
                _storyboard_shot_row(
                    2, "A-002", "close_up", "Fox holds screen-left."
                ),
                _storyboard_shot_row(
                    3, "A-003", "medium_close_up", "Owl holds screen-right."
                ),
            )
            with self.assertRaisesRegex(
                StoryboardValidationError, "position-change exception"
            ):
                _validate_shot_size_authority(task_dir, storyboard)

    def test_storyboard_wide_returns_directly_to_tight_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            _write_screenplay_shot_stub(
                task_dir, ["wide", "medium", "close_up", "reaction", "insert"]
            )
            storyboard = _storyboard_text(
                _storyboard_shot_row(
                    1,
                    "A-001",
                    "wide",
                    (
                        "position-change exception: Fox crosses from tree to "
                        "stone and lands opposite Owl."
                    ),
                ),
                _storyboard_shot_row(
                    2, "A-002", "medium", "Fox and Owl hold their marks."
                ),
                _storyboard_shot_row(
                    3, "A-003", "close_up", "Fox holds screen-left."
                ),
                _storyboard_shot_row(
                    4, "A-004", "medium_close_up", "Owl holds screen-right."
                ),
                _storyboard_shot_row(
                    5, "A-005", "extreme_close_up", "Fox's eyes hold right."
                ),
            )
            with self.assertRaisesRegex(
                StoryboardValidationError, "return directly"
            ):
                _validate_shot_size_authority(task_dir, storyboard)


if __name__ == "__main__":
    unittest.main()
