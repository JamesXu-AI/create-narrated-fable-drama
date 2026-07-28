from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VIDEO_REVIEW_SCRIPTS = (
    REPOSITORY_ROOT / "skills" / "video-review" / "scripts"
)
VIRTUAL_PRODUCTION_SCRIPTS = (
    REPOSITORY_ROOT / "skills" / "virtual-production" / "scripts"
)
sys.path.insert(0, str(VIDEO_REVIEW_SCRIPTS))
sys.path.insert(0, str(VIRTUAL_PRODUCTION_SCRIPTS))

from generation.voice_precheck import (  # noqa: E402
    recorded_voice_gate_allows_downstream,
)
from review.voice_identity import (  # noqa: E402
    _reviewed_window_within_visual_authority,
    acoustic_profile,
    compare_profiles,
    load_config,
)


class VoiceIdentityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()

    def test_stable_synthetic_voice_produces_a_profile(self) -> None:
        sample_rate = int(self.config["sample_rate_hz"])
        seconds = np.arange(sample_rate * 2) / sample_rate
        samples = (
            np.sin(2 * np.pi * 180 * seconds)
            + 0.4 * np.sin(2 * np.pi * 360 * seconds)
            + 0.2 * np.sin(2 * np.pi * 540 * seconds)
        )
        profile = acoustic_profile(samples, config=self.config)
        self.assertGreater(profile["voiced_frame_count"], 8)
        self.assertAlmostEqual(profile["median_pitch_hz"], 180, delta=8)
        self.assertEqual(
            len(profile["mean_log_mel_spectral_envelope"]),
            26,
        )

    def test_spectral_envelope_mismatch_blocks(self) -> None:
        reference = {
            "median_pitch_hz": 150.0,
            "median_spectral_centroid_hz": 500.0,
            "mean_log_mel_spectral_envelope": [
                float(index) for index in range(26)
            ],
        }
        candidate = {
            "median_pitch_hz": 180.0,
            "median_spectral_centroid_hz": 550.0,
            "mean_log_mel_spectral_envelope": [
                float(index) for index in reversed(range(26))
            ],
        }
        comparison = compare_profiles(
            reference,
            candidate,
            config=self.config,
        )
        self.assertEqual(comparison["status"], "FAIL")
        self.assertIn(
            "spectral_envelope_similarity is below",
            comparison["failure_reasons"][0],
        )

    def test_strong_envelope_allows_moderate_centroid_variance(self) -> None:
        envelope = [float(index) for index in range(26)]
        reference = {
            "median_pitch_hz": 150.0,
            "median_spectral_centroid_hz": 300.0,
            "mean_log_mel_spectral_envelope": envelope,
        }
        candidate = {
            "median_pitch_hz": 180.0,
            "median_spectral_centroid_hz": 630.0,
            "mean_log_mel_spectral_envelope": envelope,
        }
        comparison = compare_profiles(
            reference,
            candidate,
            config=self.config,
        )
        self.assertEqual(comparison["status"], "PASS")
        self.assertTrue(
            comparison["strong_envelope_centroid_variance"]
        )

    def test_excessive_centroid_variance_still_blocks(self) -> None:
        envelope = [float(index) for index in range(26)]
        reference = {
            "median_pitch_hz": 150.0,
            "median_spectral_centroid_hz": 300.0,
            "mean_log_mel_spectral_envelope": envelope,
        }
        candidate = {
            "median_pitch_hz": 180.0,
            "median_spectral_centroid_hz": 700.0,
            "mean_log_mel_spectral_envelope": envelope,
        }
        comparison = compare_profiles(
            reference,
            candidate,
            config=self.config,
        )
        self.assertEqual(comparison["status"], "FAIL")
        self.assertIn(
            "spectral_centroid_ratio exceeds",
            comparison["failure_reasons"][0],
        )

    def test_reviewed_window_can_keep_earlier_detected_mouth_onset(
        self,
    ) -> None:
        self.assertTrue(
            _reviewed_window_within_visual_authority(
                storyboard_start=0.6,
                storyboard_end=7.0,
                detected_start=0.0,
                reviewed_start=0.0,
                reviewed_end=5.82,
            )
        )
        self.assertFalse(
            _reviewed_window_within_visual_authority(
                storyboard_start=0.6,
                storyboard_end=7.0,
                detected_start=0.0,
                reviewed_start=-0.1,
                reviewed_end=5.82,
            )
        )

    def test_missing_or_failed_gate_blocks_successor(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
            prompt_path = (
                task_dir
                / ".pending"
                / "virtual-production"
                / "seedance-segment-scripts"
                / "segment-001.md"
            )
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("موجّه عربي", encoding="utf-8")
            prompt_hash = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
            record_dir = (
                task_dir
                / ".pending"
                / "virtual-production"
                / "generation-segments"
                / "segment-001"
            )
            record_dir.mkdir(parents=True)
            record_path = record_dir / "production-record.json"
            record_path.write_text(
                json.dumps(
                    {
                        "contract": "generated-segment-production-record",
                        "segment_id": "segment-001",
                        "status": "GENERATED",
                        "segment_prompt_sha256": prompt_hash,
                    }
                ),
                encoding="utf-8",
            )
            self.assertFalse(
                recorded_voice_gate_allows_downstream(
                    task_dir,
                    "segment-001",
                )
            )
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["dubbing"] = {
                "contract": "elevenlabs-arabic-segment-embedding/v3",
                "seedance_generate_audio": False,
                "seedance_audio_in_delivery": False,
                "seedance_background_audio_retained": False,
                "seedance_speech_forbidden": True,
                "seedance_speech_in_delivery": False,
            }
            record["voice_identity_gate"] = {
                "status": "PASS",
                "blocks_acceptance": False,
            }
            record_path.write_text(json.dumps(record), encoding="utf-8")
            self.assertFalse(
                recorded_voice_gate_allows_downstream(
                    task_dir,
                    "segment-001",
                )
            )
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["dubbing"] = {
                "contract": "seedance-original-audio-dialogue-replacement/v2",
                "language_code": "ar",
                "language_code_sent": False,
                "tts_model_id": "eleven_multilingual_v2",
                "accent_profile_id": (
                    "saudi_arabic_neutral_urban_riyadh_v1"
                ),
                "grammatical_gender_policy": "masculine",
                "pronunciation_contract": (
                    "arabic-exact-text-plus-derived-tashkeel/v1"
                ),
                "speech_audio_source": "elevenlabs_dubbed",
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
                "seedance_clean_background_speech_gate": {
                    "status": "PASS",
                },
                "seedance_audio_edit": {
                    "status": "APPLIED",
                },
            }
            record_path.write_text(json.dumps(record), encoding="utf-8")
            record["voice_identity_gate"] = {
                "status": "FAIL",
                "blocks_acceptance": True,
            }
            record_path.write_text(json.dumps(record), encoding="utf-8")
            self.assertFalse(
                recorded_voice_gate_allows_downstream(
                    task_dir,
                    "segment-001",
                )
            )
            record["voice_identity_gate"] = {
                "status": "PASS",
                "blocks_acceptance": False,
            }
            record_path.write_text(json.dumps(record), encoding="utf-8")
            self.assertTrue(
                recorded_voice_gate_allows_downstream(
                    task_dir,
                    "segment-001",
                )
            )
            prompt_path.write_text("موجّه عربي جديد", encoding="utf-8")
            self.assertFalse(
                recorded_voice_gate_allows_downstream(
                    task_dir,
                    "segment-001",
                )
            )


if __name__ == "__main__":
    unittest.main()
