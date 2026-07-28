from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VIRTUAL_PRODUCTION_SCRIPTS = (
    REPOSITORY_ROOT / "skills" / "virtual-production" / "scripts"
)
sys.path.insert(0, str(VIRTUAL_PRODUCTION_SCRIPTS))

from generation.attempts import _completed_result  # noqa: E402
from generation.common import SegmentGenerationError  # noqa: E402


class SeedanceSourceRetentionTests(unittest.TestCase):
    def _completed_fixture(
        self, directory: Path
    ) -> tuple[dict[str, object], dict[str, object]]:
        source = directory / "seedance-source.mp4"
        source.write_bytes(b"original Seedance video")
        (directory / "video.mp4").write_bytes(b"dubbed video")
        (directory / "last-frame.png").write_bytes(b"final frame")
        dubbing = {
            "contract": "seedance-original-audio-dialogue-replacement/v2",
            "language_code": "ar",
            "language_code_sent": False,
            "tts_model_id": "eleven_multilingual_v2",
            "accent_profile_id": "saudi_arabic_neutral_urban_riyadh_v1",
            "grammatical_gender_policy": "masculine",
            "pronunciation_contract": (
                "arabic-exact-text-plus-derived-tashkeel/v1"
            ),
            "alignment_method": (
                "seedance_detected_or_storyboard_window_natural_phrase_atempo"
            ),
            "sound_effects_audio_source": "seedance_native",
            "native_audio_full_duration": True,
            "elevenlabs_usage_scope": "arabic_dialogue_only",
            "elevenlabs_non_dialogue_request_count": 0,
            "dialogue_gap_fill_source": (
                "digital_silence"
            ),
            "seedance_generate_audio": True,
            "seedance_audio_in_delivery": True,
            "seedance_background_audio_retained": True,
            "seedance_speech_forbidden": True,
            "seedance_speech_in_delivery": False,
            "seedance_clean_background_speech_gate": {"status": "PASS"},
            "seedance_audio_edit": {"status": "APPLIED"},
            "picture_frames_retimed": False,
        }
        (directory / "arabic-embedding-record.json").write_text(
            json.dumps(dubbing),
            encoding="utf-8",
        )
        record = {
            "status": "GENERATED",
            "segment_id": "segment-001",
            "provider_attempt_id": "segment-001__attempt-0001",
            "segment_prompt_sha256": "prompt-sha",
            "seedance_execution_plan_sha256": "execution-sha",
            "operation": "multimodal_reference",
            "prompt_audit": {
                "contract": "seedance-prompt-internal-audit/v3",
                "status": "PASS",
                "prompt_sha256": "prompt-sha",
            },
            "quality_reset": None,
            "seedance_source_path": "seedance-source.mp4",
            "seedance_source_bytes": source.stat().st_size,
            "seedance_source_sha256": hashlib.sha256(
                source.read_bytes()
            ).hexdigest(),
            "dubbing": dubbing,
        }
        (directory / "production-record.json").write_text(
            json.dumps(record),
            encoding="utf-8",
        )
        segment = {
            "generation_task_id": "segment-001",
            "script_sha256": "prompt-sha",
            "execution_plan_sha256": "execution-sha",
            "operation": "multimodal_reference",
            "execution_plan": {"quality_reset": None},
        }
        submission = {
            "status": "succeeded",
            "attempt_number": 1,
            "provider_task_id": "provider-task",
        }
        return segment, submission

    def test_completed_result_keeps_and_returns_seedance_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            segment, submission = self._completed_fixture(directory)

            result = _completed_result(segment, directory, submission)

            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(
                result["seedance_source_path"],
                str((directory / "seedance-source.mp4").resolve()),
            )
            self.assertTrue((directory / "seedance-source.mp4").is_file())

    def test_completed_result_rejects_changed_seedance_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            segment, submission = self._completed_fixture(directory)
            (directory / "seedance-source.mp4").write_bytes(b"changed source")

            with self.assertRaisesRegex(
                SegmentGenerationError,
                "production record is invalid",
            ):
                _completed_result(segment, directory, submission)


if __name__ == "__main__":
    unittest.main()
