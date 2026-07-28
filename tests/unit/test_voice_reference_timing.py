from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(
    0,
    str(REPOSITORY_ROOT / "skills/direct-production-design/scripts"),
)

from generate_elevenlabs_role_voices import (  # noqa: E402
    RoleVoiceGenerationError,
    _resolved_preview_seed,
)
from voice_reference_generation import (  # noqa: E402
    VOICE_MAX_INTERNAL_WORD_GAP_SECONDS,
    VOICE_MAX_PUNCTUATED_WORD_GAP_SECONDS,
    VoiceAuthorityError,
    _allowed_word_gap_seconds,
    _validate_dynamic_timing,
)


class VoiceReferenceTimingTests(unittest.TestCase):
    def test_voice_design_preview_uses_fresh_traceable_seed(self) -> None:
        with patch(
            "generate_elevenlabs_role_voices.secrets.randbelow",
            return_value=991827,
        ) as randbelow:
            self.assertEqual(
                _resolved_preview_seed(None),
                (991827, "fresh_random"),
            )
        randbelow.assert_called_once_with(2147483648)
        self.assertEqual(_resolved_preview_seed(17), (17, "explicit"))
        with self.assertRaises(RoleVoiceGenerationError):
            _resolved_preview_seed(2147483648)

    def test_arabic_punctuation_allows_a_natural_phrase_pause(self) -> None:
        self.assertEqual(
            _allowed_word_gap_seconds("يا جدي، أرجوك أن تحكي.", 2),
            VOICE_MAX_PUNCTUATED_WORD_GAP_SECONDS,
        )

    def test_unpunctuated_words_keep_the_strict_dropout_limit(self) -> None:
        self.assertEqual(
            _allowed_word_gap_seconds("يا جدي أرجوك أن تحكي.", 2),
            VOICE_MAX_INTERNAL_WORD_GAP_SECONDS,
        )

    def test_natural_unpunctuated_arabic_pause_is_allowed(self) -> None:
        _validate_dynamic_timing(
            asset_id="uthman",
            sample_text="الضعيف ونقول",
            evidence={
                "uri": "https://example.invalid/voice.wav",
                "words": [
                    {
                        "text": "الضعيف",
                        "start_seconds": 0.0,
                        "end_seconds": 0.4,
                    },
                    {
                        "text": "ونقول",
                        "start_seconds": 1.1,
                        "end_seconds": 1.5,
                    },
                ],
            },
            audio_duration=1.6,
        )

    def test_unpunctuated_dropout_above_new_limit_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            VoiceAuthorityError,
            "anomalous sample-text pause",
        ):
            _validate_dynamic_timing(
                asset_id="uthman",
                sample_text="الضعيف ونقول",
                evidence={
                    "uri": "https://example.invalid/voice.wav",
                    "words": [
                        {
                            "text": "الضعيف",
                            "start_seconds": 0.0,
                            "end_seconds": 0.4,
                        },
                        {
                            "text": "ونقول",
                            "start_seconds": 1.21,
                            "end_seconds": 1.6,
                        },
                    ],
                },
                audio_duration=1.7,
            )


if __name__ == "__main__":
    unittest.main()
