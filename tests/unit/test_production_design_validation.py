from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_DESIGN_SCRIPTS = (
    REPOSITORY_ROOT / "skills" / "direct-production-design" / "scripts"
)
sys.path.insert(0, str(PRODUCTION_DESIGN_SCRIPTS))

from validate_production_design import (  # noqa: E402
    ProductionDesignError,
    _current_speaker_voice_count,
)


class ProductionDesignValidationTests(unittest.TestCase):
    def test_reusable_catalog_voices_do_not_expand_current_cast(self) -> None:
        plan = {
            "characters": [
                {"entity_id": "hazel", "speaks": True},
                {"entity_id": "bo", "speaks": True},
            ]
        }
        voice_result = {
            "speakers": [
                {"asset_id": "hazel"},
                {"asset_id": "bo"},
                {"asset_id": "reusable-character-from-another-task"},
            ]
        }

        self.assertEqual(
            _current_speaker_voice_count(plan, voice_result),
            2,
        )

    def test_missing_current_speaker_voice_blocks(self) -> None:
        plan = {
            "characters": [
                {"entity_id": "hazel", "speaks": True},
                {"entity_id": "bo", "speaks": True},
            ]
        }
        voice_result = {"speakers": [{"asset_id": "hazel"}]}

        with self.assertRaisesRegex(ProductionDesignError, "bo"):
            _current_speaker_voice_count(plan, voice_result)


if __name__ == "__main__":
    unittest.main()
