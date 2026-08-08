from __future__ import annotations

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
    acoustic_profile,
    compare_profiles,
    load_config,
)


class VoiceIdentityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()

    def test_cross_recording_domain_timbre_differences_are_advisory(
        self,
    ) -> None:
        reference_envelope = np.zeros(26)
        reference_envelope[0] = 1 / np.sqrt(2)
        reference_envelope[1] = -1 / np.sqrt(2)
        orthogonal_envelope = np.zeros(26)
        orthogonal_envelope[0] = 1 / np.sqrt(6)
        orthogonal_envelope[1] = 1 / np.sqrt(6)
        orthogonal_envelope[2] = -2 / np.sqrt(6)

        def profile(similarity: float) -> dict[str, object]:
            envelope = (
                similarity * reference_envelope
                + np.sqrt(1 - similarity**2) * orthogonal_envelope
            )
            return {
                "median_pitch_hz": 150.0,
                "median_spectral_centroid_hz": 500.0,
                "mean_log_mel_spectral_envelope": envelope.tolist(),
            }

        reference = profile(1.0)
        self.assertEqual(
            self.config["minimum_spectral_envelope_similarity"],
            0.75,
        )
        for similarity in (0.726, 0.697):
            comparison = compare_profiles(
                reference,
                profile(similarity),
                config=self.config,
            )
            self.assertEqual(comparison["status"], "PASS")
            self.assertIn(
                "below the review threshold",
                comparison["advisory_reasons"][0],
            )

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

    def test_severe_spectral_envelope_mismatch_blocks(self) -> None:
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
            "below the severe approved-reference limit",
            comparison["failure_reasons"][0],
        )

    def test_pitch_mismatch_still_blocks(self) -> None:
        profile = {
            "median_pitch_hz": 150.0,
            "median_spectral_centroid_hz": 500.0,
            "mean_log_mel_spectral_envelope": [
                float(index) for index in range(26)
            ],
        }
        shifted = dict(profile)
        shifted["median_pitch_hz"] = 500.0
        comparison = compare_profiles(
            profile,
            shifted,
            config=self.config,
        )
        self.assertEqual(comparison["status"], "FAIL")
        self.assertIn(
            "median_pitch_ratio exceeds",
            comparison["failure_reasons"][0],
        )

    def test_moderate_spectral_centroid_difference_is_allowed(self) -> None:
        reference = {
            "median_pitch_hz": 150.0,
            "median_spectral_centroid_hz": 500.0,
            "mean_log_mel_spectral_envelope": [
                float(index) for index in range(26)
            ],
        }
        candidate = dict(reference)
        candidate["median_spectral_centroid_hz"] = 240.0
        comparison = compare_profiles(
            reference,
            candidate,
            config=self.config,
        )
        self.assertEqual(
            self.config["maximum_spectral_centroid_ratio"],
            2.25,
        )
        self.assertEqual(comparison["status"], "PASS")

        candidate["median_spectral_centroid_hz"] = 200.0
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

    def test_recorded_failure_blocks_successor_but_legacy_record_remains_readable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            task_dir = Path(temp)
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
                    }
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                recorded_voice_gate_allows_downstream(
                    task_dir,
                    "segment-001",
                )
            )
            record = json.loads(record_path.read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    unittest.main()
