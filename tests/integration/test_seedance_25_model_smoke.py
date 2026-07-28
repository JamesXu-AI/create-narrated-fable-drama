from __future__ import annotations

import os
import sys
import unittest
import warnings
from pathlib import Path
from unittest import mock

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from narrated_fable_drama.providers import runtime, seedance  # noqa: E402

pytestmark = pytest.mark.live_provider


@unittest.skipUnless(
    os.getenv("RUN_LIVE_PROVIDER_TESTS") == "1",
    "set RUN_LIVE_PROVIDER_TESTS=1 to call the real Seedance provider",
)
class Seedance25ModelSmokeTests(unittest.TestCase):
    MODEL_ID = "dreamina-seedance-2-5-260628"

    def test_model_accepts_a_minimal_video_task(self) -> None:
        missing = runtime.missing_environment(("ARK_BASE_URL", "SEEDANCE_API_KEY"))
        if missing:
            self.skipTest(
                "missing live provider environment variables: " + ", ".join(missing)
            )

        task_id: str | None = None
        try:
            with mock.patch.dict(
                os.environ,
                {"SEEDANCE_MODEL": self.MODEL_ID},
            ):
                result = seedance.create_video_task(
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "A locked-off shot of a blank white card on a "
                                    "neutral studio background. No people, no text."
                                ),
                            }
                        ],
                        "resolution": "480p",
                        "ratio": "16:9",
                        "duration": 4,
                        "generate_audio": False,
                        "watermark": False,
                        "return_last_frame": False,
                    },
                    timeout=120,
                )

            task_id_value = result.get("id")
            self.assertIsInstance(task_id_value, str)
            self.assertTrue(task_id_value)
            task_id = task_id_value
        finally:
            if task_id:
                try:
                    seedance.cancel_video_task(task_id, timeout=120)
                except runtime.SeedMediaError as exc:
                    warnings.warn(
                        f"Seedance task {task_id} was created but could not be "
                        f"cancelled during smoke-test cleanup: {exc}",
                        stacklevel=2,
                    )


if __name__ == "__main__":
    unittest.main()
