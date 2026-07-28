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
    _model_name,
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
    def test_arabic_article_variant_keeps_short_cue_above_coverage_gate(
        self,
    ) -> None:
        alignment = _align(
            "كلوا اللحم يا وزرائي واستمتعوا به.",
            [
                _word("لحمة", 1.0, 1.4),
                _word("يا", 1.4, 1.6),
                _word("وزرائي", 1.6, 2.1),
                _word("وستمتع", 2.1, 2.6),
                _word("به", 2.6, 2.9),
            ],
        )
        self.assertEqual(alignment["matched_token_count"], 5)
        self.assertEqual(alignment["expected_token_count"], 6)
        self.assertGreaterEqual(alignment["token_coverage"], 0.75)

    def test_alignment_cannot_steal_an_exact_word_from_the_next_segment(
        self,
    ) -> None:
        alignments = align_authoritative_cues(
            [
                {
                    "cue_id": "L-004",
                    "exact_text": "أنا أسدكم القوي.",
                    "window_start_seconds": 0.0,
                    "window_end_seconds": 5.0,
                },
                {
                    "cue_id": "L-005",
                    "exact_text": "أسدكم قوي وشجاع.",
                    "window_start_seconds": 10.0,
                    "window_end_seconds": 15.0,
                },
            ],
            [
                _word("أنا", 1.0, 1.2),
                _word("أسدكن", 1.2, 1.6),
                _word("القوي", 1.6, 2.0),
                _word("أسدكم", 10.5, 10.8),
                _word("قوي", 10.8, 11.2),
                _word("وشجاع", 11.2, 11.7),
            ],
            minimum_token_coverage=0.75,
            minimum_token_similarity=0.72,
            lookahead_tokens=24,
            outlier_gap_seconds=1.25,
            outlier_probability_threshold=0.65,
        )
        self.assertEqual(
            alignments["L-004"]["tokens"][1]["observed_text"],
            "أسدكن",
        )
        self.assertLess(alignments["L-004"]["speech_end_seconds"], 5.0)
        self.assertGreater(alignments["L-005"]["speech_start_seconds"], 10.0)

    def test_alignment_does_not_steal_a_repeated_word_later_in_the_cue(
        self,
    ) -> None:
        alignment = align_authoritative_cues(
            [
                {
                    "cue_id": "L-017",
                    "exact_text": (
                        "الأسد ظن أن القوة تجعله أعظم لكن أصغر مخلوق كشف ضعفه."
                    ),
                    "window_start_seconds": 149.0,
                    "window_end_seconds": 161.1,
                }
            ],
            [
                _word("ظن", 154.7, 155.1),
                _word("أن", 155.1, 155.5),
                _word("القوة", 155.5, 156.0),
                _word("تجعله", 156.0, 156.4),
                _word("أعظم", 156.4, 156.7),
                _word("لكن", 156.7, 157.0),
                _word("أصغر", 157.7, 157.9),
                _word("مخلوق", 157.9, 158.3),
                _word("كشف", 158.3, 158.7),
                _word("ضعفه", 158.7, 159.1),
            ],
            minimum_token_coverage=0.75,
            minimum_token_similarity=0.72,
            lookahead_tokens=24,
            outlier_gap_seconds=1.25,
            outlier_probability_threshold=0.65,
        )["L-017"]
        self.assertIsNone(alignment["tokens"][0]["observed_text"])
        self.assertEqual(alignment["tokens"][1]["observed_text"], "ظن")
        self.assertEqual(alignment["tokens"][7]["observed_text"], "أصغر")
        self.assertEqual(alignment["matched_token_count"], 10)

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
            "من فضلك لا تقتلني.",
            [
                _word("من", 1.0, 1.3, 0.4),
                _word("فضلك", 10.0, 10.3),
                _word("لا", 10.3, 10.5),
                _word("تقتلني", 10.5, 11.0),
            ],
        )
        self.assertGreater(alignment["speech_start_seconds"], 9.5)
        self.assertEqual(
            alignment["anchor_repairs"][0]["operation"],
            "replace_low_confidence_leading_outlier",
        )

    def test_isolated_leading_word_cannot_span_a_long_silent_gap(self) -> None:
        alignment = _align(
            "لا غالب إلا الله.",
            [
                _word("لا", 1.0, 1.4, 0.78),
                _word("غالب", 5.0, 5.4),
                _word("إلا", 5.4, 5.7),
                _word("الله", 5.7, 6.1),
            ],
        )
        self.assertGreater(alignment["speech_start_seconds"], 4.5)
        self.assertEqual(
            alignment["anchor_repairs"][0]["operation"],
            "replace_isolated_leading_outlier",
        )

    def test_long_low_confidence_leading_word_is_repaired(self) -> None:
        alignment = _align(
            "لا أنا الأقوى.",
            [
                _word("لا", 1.0, 2.5, 0.59),
                _word("أنا", 2.5, 2.9),
                _word("الأقوى", 2.9, 3.4),
            ],
        )
        self.assertGreater(alignment["speech_start_seconds"], 2.0)
        self.assertEqual(
            alignment["anchor_repairs"][0]["operation"],
            "replace_low_confidence_leading_outlier",
        )

    def test_low_confidence_leading_anchor_is_clipped_to_owner_window(
        self,
    ) -> None:
        alignment = align_authoritative_cues(
            [
                {
                    "cue_id": "L-005",
                    "exact_text": "الله خلق كل شيء.",
                    "window_start_seconds": 29.583,
                    "window_end_seconds": 44.625,
                }
            ],
            [
                _word("الله", 29.0, 29.58, 0.003),
                _word("خلق", 29.58, 30.36),
                _word("كل", 30.36, 30.58),
                _word("شيء", 30.58, 31.74),
            ],
            minimum_token_coverage=0.75,
            minimum_token_similarity=0.72,
            lookahead_tokens=12,
            outlier_gap_seconds=1.25,
            outlier_probability_threshold=0.65,
        )["L-005"]
        self.assertGreaterEqual(
            alignment["speech_start_seconds"],
            29.533,
        )
        self.assertAlmostEqual(
            alignment["tokens"][0]["start_seconds"],
            29.583,
        )
        self.assertEqual(
            alignment["anchor_repairs"][0]["operation"],
            "clip_low_confidence_leading_anchor_to_owner_window",
        )

    def test_caption_screens_follow_measured_word_groups(self) -> None:
        alignment = _align(
            "خلق الله كل شيء. قوتك أمانة.",
            [
                _word("خلق", 4.0, 4.3),
                _word("الله", 4.3, 4.7),
                _word("كل", 4.7, 4.9),
                _word("شيء", 4.9, 5.2),
                _word("قوتك", 6.1, 6.5),
                _word("أمانة", 6.5, 7.0),
            ],
        )
        intervals = caption_intervals_from_alignment(
            alignment,
            [
                ("خلق الله كل شيء.", "خلق الله كل شيء."),
                ("قوتك أمانة.", "قوتك أمانة."),
            ],
            lead_in_seconds=0.08,
            trail_out_seconds=0.18,
            media_duration_seconds=12.0,
        )
        self.assertAlmostEqual(intervals[0][0], 3.92)
        self.assertAlmostEqual(intervals[0][1], 5.38)
        self.assertAlmostEqual(intervals[1][0], 6.02)
        self.assertAlmostEqual(intervals[1][1], 7.18)

    def test_insufficient_alignment_coverage_blocks_delivery(self) -> None:
        with self.assertRaisesRegex(
            SubtitleBuildError,
            "coverage is too low",
        ):
            _align(
                "يجب أن تكون هذه الجملة موجودة.",
                [
                    _word("صوت", 1.0, 1.3),
                    _word("مختلف", 1.3, 1.6),
                ],
            )

    def test_english_authority_and_english_model_are_rejected(self) -> None:
        with self.assertRaisesRegex(SubtitleBuildError, "Arabic"):
            _align("This exact line must be present.", [_word("صوت", 1.0, 1.3)])
        with self.assertRaisesRegex(SubtitleBuildError, "English-only"):
            _model_name("small.en", "Arabic")


if __name__ == "__main__":
    unittest.main()
