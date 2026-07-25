from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "finish-postproduction"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS))

from subtitles.subtitle_alignment import (  # noqa: E402
    TimedWord,
    align_authoritative_cues,
    caption_intervals_from_alignment,
    sha256_file,
)
from subtitles.subtitle_style import (  # noqa: E402
    DEFAULT_STYLE,
    SubtitleBuildError,  # noqa: E402
    _validate_style,
)


def _word(
    text: str,
    start: float,
    end: float,
    probability: float = 0.99,
) -> TimedWord:
    return TimedWord(
        text=text,
        start_seconds=start,
        end_seconds=end,
        probability=probability,
    )


def _align(
    text: str,
    words: list[TimedWord],
) -> dict[str, object]:
    return align_authoritative_cues(
        [{"cue_id": "L-001", "exact_text": text}],
        words,
        minimum_token_coverage=0.75,
        minimum_token_similarity=0.72,
        lookahead_tokens=12,
        outlier_gap_seconds=1.25,
        outlier_probability_threshold=0.65,
    )["L-001"]


class SubtitleAlignmentTests(unittest.TestCase):
    def test_alignment_source_hash_is_content_stable(self) -> None:
        self.assertEqual(
            sha256_file(DEFAULT_STYLE),
            sha256_file(DEFAULT_STYLE.resolve()),
        )

    def test_repository_style_requires_final_clean_master_timing(self) -> None:
        style = json.loads(DEFAULT_STYLE.read_text(encoding="utf-8"))
        _validate_style(style)
        self.assertEqual(
            style["timing_authority"],
            "final_clean_master_word_alignment",
        )
        style["timing_authority"] = (
            "storyboard_speech_windows_plus_picture_edl"
        )
        with self.assertRaisesRegex(
            SubtitleBuildError,
            "timing authority is invalid",
        ):
            _validate_style(style)

    def test_low_confidence_leading_hallucination_cannot_start_caption_early(
        self,
    ) -> None:
        alignment = _align(
            "Please do not kill me.",
            [
                _word("Please", 1.0, 1.3, 0.4),
                _word("do", 10.0, 10.2),
                _word("not", 10.2, 10.4),
                _word("kill", 10.4, 10.7),
                _word("me", 10.7, 11.0),
            ],
        )
        self.assertGreater(alignment["speech_start_seconds"], 9.5)
        self.assertEqual(
            alignment["anchor_repairs"][0]["operation"],
            "replace_low_confidence_leading_outlier",
        )

    def test_caption_screens_follow_measured_word_groups(self) -> None:
        alignment = _align(
            "Allah created everything. Your strength is a trust.",
            [
                _word("Allah", 4.0, 4.3),
                _word("created", 4.3, 4.7),
                _word("everything", 4.7, 5.2),
                _word("Your", 6.1, 6.3),
                _word("strength", 6.3, 6.7),
                _word("is", 6.7, 6.9),
                _word("a", 6.9, 7.0),
                _word("trust", 7.0, 7.4),
            ],
        )
        intervals = caption_intervals_from_alignment(
            alignment,
            [
                ("Allah created everything.", "Allah created everything."),
                (
                    "Your strength is a trust.",
                    "Your strength is a trust.",
                ),
            ],
            lead_in_seconds=0.08,
            trail_out_seconds=0.18,
            media_duration_seconds=12.0,
        )
        self.assertAlmostEqual(intervals[0][0], 3.92)
        self.assertAlmostEqual(intervals[0][1], 5.38)
        self.assertAlmostEqual(intervals[1][0], 6.02)
        self.assertAlmostEqual(intervals[1][1], 7.58)

    def test_insufficient_alignment_coverage_blocks_delivery(self) -> None:
        with self.assertRaisesRegex(
            SubtitleBuildError,
            "coverage is too low",
        ):
            _align(
                "This exact line must be present.",
                [
                    _word("unrelated", 1.0, 1.3),
                    _word("audio", 1.3, 1.6),
                ],
            )


if __name__ == "__main__":
    unittest.main()
