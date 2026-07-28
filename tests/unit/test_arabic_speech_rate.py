from __future__ import annotations

import unittest

from narrated_fable_drama.core.speech_rate import (
    SpeechRateError,
    analyze_speech,
)


class ArabicSpeechRateTests(unittest.TestCase):
    def test_arabic_line_records_arabic_gate_evidence(self) -> None:
        result = analyze_speech("هذه جملة عربية واضحة.", 3.0)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["language"], "Arabic")
        self.assertEqual(result["language_code"], "ar")
        self.assertEqual(result["arabic_only_no_latin"], "PASS")
        self.assertEqual(result["arabic_word_count"], 4)
        self.assertEqual(result["maximum_arabic_words_per_second"], 2.6)

    def test_english_or_mixed_line_is_rejected_before_rate_measurement(self) -> None:
        for text in ("This is an English line.", "هذه جملة mixed."):
            with self.subTest(text=text):
                with self.assertRaises(SpeechRateError):
                    analyze_speech(text, 3.0)


if __name__ == "__main__":
    unittest.main()
