from __future__ import annotations

import base64
import json
import os
import unittest
from unittest import mock

from narrated_fable_drama.core.arabic_pronunciation import (
    ACCENT_PROFILE_ID,
    ArabicPronunciationError,
    compile_arabic_tts_text,
    has_current_arabic_pronunciation_contract,
    strip_arabic_diacritics,
    validate_arabic_tts_text,
)
from narrated_fable_drama.dubbing.arabic_segment import _source_word_spans
from narrated_fable_drama.providers import elevenlabs
from narrated_fable_drama.providers.runtime import SeedMediaError


class ArabicPronunciationTests(unittest.TestCase):
    def test_masculine_tashkeel_preserves_locked_dialogue(self) -> None:
        exact = "نعم، أنت محق... يا عثمان."
        compiled = compile_arabic_tts_text(exact)

        self.assertEqual(
            compiled["tts_text"],
            "نعم، أَنْتَ محق... يا عُثْمَان.",
        )
        self.assertEqual(strip_arabic_diacritics(compiled["tts_text"]), exact)
        self.assertEqual(compiled["accent_profile_id"], ACCENT_PROFILE_ID)
        self.assertEqual(
            compiled["applied_rules"],
            [
                "proper_name:عثمان",
                "second_person_masculine:أنت",
            ],
        )

    def test_feminine_form_is_explicit_but_not_the_project_default(self) -> None:
        compiled = compile_arabic_tts_text(
            "من أنت؟",
            grammatical_gender="feminine",
        )

        self.assertEqual(compiled["tts_text"], "من أَنْتِ؟")
        self.assertEqual(strip_arabic_diacritics(compiled["tts_text"]), "من أنت؟")

    def test_authored_text_cannot_carry_provider_only_tashkeel(self) -> None:
        with self.assertRaises(ArabicPronunciationError):
            compile_arabic_tts_text("أَنْتَ قوي.")

    def test_manual_tts_override_must_match_deterministic_derivation(self) -> None:
        with self.assertRaises(ArabicPronunciationError):
            validate_arabic_tts_text(
                exact_text="أنت قوي.",
                tts_text="أَنْتِ قوي.",
            )

    def test_persisted_contract_requires_every_saudi_lock(self) -> None:
        compiled = compile_arabic_tts_text("أنت قوي.")
        record = {
            "language_code": "ar",
            "language_code_sent": False,
            "tts_model_id": "eleven_multilingual_v2",
            "accent_profile_id": ACCENT_PROFILE_ID,
            "grammatical_gender_policy": "masculine",
            "pronunciation_contract": compiled["contract"],
        }

        self.assertTrue(has_current_arabic_pronunciation_contract(record))
        record["language_code_sent"] = True
        self.assertFalse(has_current_arabic_pronunciation_contract(record))

    def test_provider_rejects_model_drift_before_network_request(self) -> None:
        with (
            mock.patch.dict(
                os.environ,
                {
                    "ELEVENLABS_API_KEY": "test-key",
                    "ELEVENLABS_MODEL_ID": "eleven_v3",
                },
                clear=True,
            ),
            mock.patch(
                "narrated_fable_drama.providers.elevenlabs.urllib.request.urlopen"
            ) as urlopen,
        ):
            with self.assertRaisesRegex(
                SeedMediaError,
                "locked to eleven_multilingual_v2",
            ):
                elevenlabs.synthesize_arabic_speech(
                    exact_text="أنت قوي.",
                    voice_id="voice-123",
                )

        urlopen.assert_not_called()

    def test_provider_sends_derived_tts_text_not_subtitle_text(self) -> None:
        tts_text = "أَنْتَ قوي."

        class _Response:
            headers = {"request-id": "request-1"}

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                characters = list(tts_text)
                payload = {
                    "audio_base64": base64.b64encode(b"ID3-audio").decode(
                        "ascii"
                    ),
                    "alignment": {
                        "characters": characters,
                        "character_start_times_seconds": [
                            index * 0.1 for index in range(len(characters))
                        ],
                        "character_end_times_seconds": [
                            (index + 1) * 0.1
                            for index in range(len(characters))
                        ],
                    },
                }
                return json.dumps(payload).encode("utf-8")

        with (
            mock.patch.dict(
                os.environ,
                {
                    "ELEVENLABS_API_KEY": "test-key",
                    "ELEVENLABS_MODEL_ID": "eleven_multilingual_v2",
                },
                clear=True,
            ),
            mock.patch(
                "narrated_fable_drama.providers.elevenlabs.urllib.request.urlopen",
                return_value=_Response(),
            ) as urlopen,
        ):
            result = elevenlabs.synthesize_arabic_speech(
                exact_text="أنت قوي.",
                voice_id="voice-123",
            )

        body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(body["text"], tts_text)
        self.assertNotIn("language_code", body)
        self.assertEqual(result["exact_text"], "أنت قوي.")
        self.assertEqual(result["tts_text"], tts_text)
        self.assertEqual(
            result["pronunciation_rules"],
            ["second_person_masculine:أنت"],
        )

    def test_diacritic_timestamps_project_back_to_exact_words(self) -> None:
        exact_text = "أنت قوي."
        tts_text = "أَنْتَ قوي."
        characters = list(tts_text)
        spans = _source_word_spans(
            exact_text=exact_text,
            tts_text=tts_text,
            alignment={
                "characters": characters,
                "character_start_times_seconds": [
                    index * 0.1 for index in range(len(characters))
                ],
                "character_end_times_seconds": [
                    (index + 1) * 0.1 for index in range(len(characters))
                ],
            },
            context="L-007",
        )

        self.assertEqual([word["text"] for word in spans], ["أنت", "قوي."])
        self.assertEqual(spans[0]["start"], 0.0)
        self.assertAlmostEqual(spans[1]["start"], 0.7)


if __name__ == "__main__":
    unittest.main()
