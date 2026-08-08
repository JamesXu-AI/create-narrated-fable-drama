from __future__ import annotations

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

from generation.attempts import _load_resumable_attempt  # noqa: E402
from generation.common import SegmentGenerationError  # noqa: E402


class GenerationAttemptResumptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.segment = {
            "generation_task_id": "segment-008",
            "script_sha256": "prompt-authority",
            "execution_plan_sha256": "plan-authority",
        }

    def test_active_attempt_ignores_regenerated_provider_media_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            active_dir = Path(temp) / "active"
            active_dir.mkdir()
            submission = {
                "generation_task_id": "segment-008",
                "provider_task_id": "provider-task",
                "request_sha256": "old-upload-url-request",
                "segment_prompt_sha256": "prompt-authority",
                "seedance_execution_plan_sha256": "plan-authority",
                "status": "submitted",
            }
            (active_dir / "submission.json").write_text(
                json.dumps(submission),
                encoding="utf-8",
            )

            resumed = _load_resumable_attempt(
                self.segment,
                active_dir,
                {"media": [{"url": "new-upload-url"}]},
            )

            self.assertEqual(resumed, submission)

    def test_active_attempt_still_rejects_changed_prompt_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            active_dir = Path(temp) / "active"
            active_dir.mkdir()
            (active_dir / "submission.json").write_text(
                json.dumps(
                    {
                        "generation_task_id": "segment-008",
                        "provider_task_id": "provider-task",
                        "request_sha256": "old-request",
                        "segment_prompt_sha256": "stale-prompt",
                        "seedance_execution_plan_sha256": "plan-authority",
                        "status": "submitted",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                SegmentGenerationError,
                "active attempt uses stale authority",
            ):
                _load_resumable_attempt(
                    self.segment,
                    active_dir,
                    {"media": [{"url": "new-upload-url"}]},
                )


if __name__ == "__main__":
    unittest.main()
