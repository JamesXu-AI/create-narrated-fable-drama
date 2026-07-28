from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VIRTUAL_PRODUCTION_SCRIPTS = (
    REPOSITORY_ROOT / "skills" / "virtual-production" / "scripts"
)
sys.path.insert(0, str(VIRTUAL_PRODUCTION_SCRIPTS))

from build_segment_audio import (  # noqa: E402
    _parse_reviewed_cue_seeds,
    _parse_reviewed_cue_speeds,
)
from generation.attempts import (  # noqa: E402
    _finish_picture_generated_attempt,
    generate_one,
)
from generation.runner import (  # noqa: E402
    _published_picture_ready,
    _published_segment_ready,
)
from preflight_segment import (  # noqa: E402
    _require_current_asset_department_gate,
)

from narrated_fable_drama.contracts.segment import (  # noqa: E402
    SegmentRuntimeError,
)


def _dubbing_record() -> dict[str, object]:
    return {
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
        "dialogue_gap_fill_source": "digital_silence",
        "seedance_generate_audio": True,
        "seedance_audio_in_delivery": True,
        "seedance_background_audio_retained": True,
        "seedance_speech_forbidden": True,
        "seedance_speech_in_delivery": False,
        "seedance_clean_background_speech_gate": {"status": "PASS"},
        "seedance_audio_edit": {"status": "APPLIED"},
        "picture_frames_retimed": False,
    }


class SegmentGenerationPipelineTests(unittest.TestCase):
    def test_preflight_blocks_stale_saudi_voice_assets(self) -> None:
        failed = Mock(
            returncode=1,
            stdout=json.dumps(
                {
                    "status": "FAIL",
                    "error": "uthman voice reference is stale",
                }
            ),
            stderr="",
        )
        with patch(
            "preflight_segment.subprocess.run",
            return_value=failed,
        ):
            with self.assertRaisesRegex(
                SegmentRuntimeError,
                "Saudi voice gate failed",
            ):
                _require_current_asset_department_gate(Path("/task"))

    def test_preflight_accepts_current_saudi_voice_assets(self) -> None:
        passed = Mock(
            returncode=0,
            stdout=json.dumps(
                {
                    "status": "PASS",
                    "speaker_voice_count": 6,
                    "distinct_elevenlabs_voice_count": 6,
                }
            ),
            stderr="",
        )
        with patch(
            "preflight_segment.subprocess.run",
            return_value=passed,
        ):
            result = _require_current_asset_department_gate(Path("/task"))

        self.assertEqual(result["status"], "PASS")

    def test_reviewed_cue_speed_parser_accepts_bounded_override(self) -> None:
        self.assertEqual(
            _parse_reviewed_cue_speeds(["L-013=0.7"]),
            {"L-013": 0.7},
        )
        with self.assertRaises(ValueError):
            _parse_reviewed_cue_speeds(["L-013=0.69"])
        with self.assertRaises(ValueError):
            _parse_reviewed_cue_speeds(["L-013=0.7", "L-013=0.8"])

    def test_reviewed_cue_seed_parser_accepts_replay_seed(self) -> None:
        self.assertEqual(
            _parse_reviewed_cue_seeds(["L-013=4294967295"]),
            {"L-013": 4294967295},
        )
        with self.assertRaises(ValueError):
            _parse_reviewed_cue_seeds(["L-013=-1"])
        with self.assertRaises(ValueError):
            _parse_reviewed_cue_seeds(["L-013=1", "L-013=2"])

    def test_picture_ready_predecessor_does_not_wait_for_dubbing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            task_dir = Path(temporary_directory)
            directory = (
                task_dir
                / ".pending"
                / "virtual-production"
                / "generation-segments"
                / "segment-001"
            )
            directory.mkdir(parents=True)
            (directory / "seedance-source.mp4").write_bytes(b"source")
            (directory / "last-frame.png").write_bytes(b"tail")
            (directory / "production-record.json").write_text(
                json.dumps(
                    {
                        "status": "PICTURE_GENERATED",
                        "segment_id": "segment-001",
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(
                _published_picture_ready(task_dir, "segment-001")
            )
            self.assertFalse(
                _published_segment_ready(task_dir, "segment-001")
            )

    def test_audio_finish_promotes_picture_without_replacing_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            task_dir = Path(temporary_directory)
            directory = task_dir / "segment-001"
            directory.mkdir()
            source = directory / "seedance-source.mp4"
            source.write_bytes(b"immutable source")
            (directory / "last-frame.png").write_bytes(b"tail")
            (directory / "submission.json").write_text(
                json.dumps({"status": "succeeded"}),
                encoding="utf-8",
            )
            record = {
                "status": "PICTURE_GENERATED",
                "segment_id": "segment-001",
                "provider_task_id": "provider-task",
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
                "request_sha256": "request-sha",
                "seedance_source_path": "seedance-source.mp4",
                "seedance_source_bytes": source.stat().st_size,
                "seedance_source_sha256": hashlib.sha256(
                    source.read_bytes()
                ).hexdigest(),
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
                "audio_policy": {
                    "seedance_audio_mode": (
                        "original_audio_dialogue_replacement"
                    ),
                    "dialogue_source": "elevenlabs_final",
                },
            }
            submission = {
                "status": "succeeded",
                "attempt_number": 1,
                "provider_task_id": "provider-task",
                "request_sha256": "request-sha",
            }

            def fake_embed(**kwargs):
                Path(kwargs["output_video"]).write_bytes(b"dubbed")
                return _dubbing_record()

            with (
                patch(
                    "generation.attempts.embed_arabic_segment",
                    side_effect=fake_embed,
                ),
                patch(
                    "generation.attempts._probe_media",
                    return_value={"duration_seconds": 15.0},
                ),
            ):
                result = _finish_picture_generated_attempt(
                    segment,
                    task_dir=task_dir,
                    directory=directory,
                    submission=submission,
                    request_timeout=60,
                )

            updated = json.loads(
                (directory / "production-record.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(updated["status"], "GENERATED")
            self.assertFalse((directory / "submission.json").exists())
            self.assertEqual(source.read_bytes(), b"immutable source")
            self.assertEqual(result["provider_attempt_id"], "segment-001__attempt-0001")

    def test_audio_resume_does_not_repeat_provider_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            task_dir = Path(temporary_directory)
            directory = (
                task_dir
                / ".pending"
                / "virtual-production"
                / "generation-segments"
                / "segment-002"
            )
            directory.mkdir(parents=True)
            (directory / "production-record.json").write_text(
                json.dumps(
                    {
                        "status": "PICTURE_GENERATED",
                        "request_sha256": "request-sha",
                    }
                ),
                encoding="utf-8",
            )
            (directory / "submission.json").write_text(
                json.dumps(
                    {
                        "status": "succeeded",
                        "generation_task_id": "segment-002",
                        "provider_task_id": "provider-task",
                        "segment_prompt_sha256": "prompt-sha",
                        "seedance_execution_plan_sha256": "execution-sha",
                        "request_sha256": "request-sha",
                    }
                ),
                encoding="utf-8",
            )
            segment = {
                "generation_task_id": "segment-002",
                "script_sha256": "prompt-sha",
                "execution_plan_sha256": "execution-sha",
            }

            with (
                patch("generation.attempts.preflight_segment") as preflight,
                patch("generation.attempts.request_payload") as request,
                patch(
                    "generation.attempts._finish_picture_generated_attempt",
                    return_value={"status": "succeeded"},
                ) as finish,
            ):
                result = generate_one(
                    segment,
                    task_dir=task_dir,
                    resolution="1080p",
                    ratio="16:9",
                    poll_interval=10,
                    wait_timeout=3600,
                    request_timeout=300,
                )

            self.assertEqual(result, {"status": "succeeded"})
            preflight.assert_not_called()
            request.assert_not_called()
            finish.assert_called_once()


if __name__ == "__main__":
    unittest.main()
