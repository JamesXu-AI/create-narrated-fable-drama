from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from narrated_fable_drama.contracts.segment.common import SegmentRuntimeError
from narrated_fable_drama.contracts.segment.prompt_audit import (
    PROMPT_AUDIT_CONTRACT,
    require_audited_model_prompt,
    require_prompt_audit,
    write_prompt_audit_record,
)
from narrated_fable_drama.contracts.segment.prompt import (
    _prompt_dialogue_blocks,
)


def _parsed(prompt_hash: str = "prompt-v1") -> dict[str, object]:
    return {
        "segment_id": "segment-001",
        "script_sha256": prompt_hash,
        "prompt": f"model prompt for {prompt_hash}",
        "seedance_audio_mode": "original_audio_dialogue_replacement",
        "metadata": {
            "source_storyboard_sha256": "storyboard-v1",
            "dialogue_cues": [
                {
                    "line_id": "L-001",
                    "exact_text": "هذه جملة عربية واضحة.",
                }
            ],
        },
    }


class SeedancePromptAuditTests(unittest.TestCase):
    def test_nested_or_unbalanced_dialogue_braces_are_rejected(self) -> None:
        with self.assertRaisesRegex(
            SegmentRuntimeError,
            "balanced, non-nested",
        ):
            _prompt_dialogue_blocks("{{هذه جملة عربية واضحة.}")

    def test_missing_audit_blocks_human_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                SegmentRuntimeError,
                "audit is missing",
            ):
                require_prompt_audit(Path(temporary), _parsed())

    def test_fresh_audit_record_unlocks_internal_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            parsed = _parsed()
            with mock.patch(
                "narrated_fable_drama.contracts.segment.prompt_audit."
                "parse_segment_script",
                return_value=parsed,
            ):
                written = write_prompt_audit_record(
                    task_dir,
                    "segment-001",
                )
                accepted = require_prompt_audit(task_dir, parsed)
        self.assertEqual(written["contract"], PROMPT_AUDIT_CONTRACT)
        self.assertEqual(accepted["status"], "PASS")
        self.assertEqual(accepted["language"], "Arabic")
        self.assertEqual(accepted["language_code"], "ar")
        self.assertEqual(
            accepted["checks"]["arabic_dialogue_only_no_latin"],
            "PASS",
        )
        self.assertEqual(accepted["model_prompt_language"], "Arabic")
        self.assertEqual(
            accepted["checks"][
                "full_model_prompt_arabic_only_no_latin_except_provider_tokens"
            ],
            "PASS",
        )
        self.assertTrue(accepted["provider_submission_ready"])

    def test_prompt_change_invalidates_previous_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            with mock.patch(
                "narrated_fable_drama.contracts.segment.prompt_audit."
                "parse_segment_script",
                return_value=_parsed("prompt-v1"),
            ):
                write_prompt_audit_record(task_dir, "segment-001")
            changed = _parsed("prompt-v2")
            with mock.patch(
                "narrated_fable_drama.contracts.segment.prompt_audit."
                "parse_segment_script",
                return_value=changed,
            ):
                with self.assertRaisesRegex(
                    SegmentRuntimeError,
                    "missing, stale, or failed",
                ):
                    require_prompt_audit(task_dir, changed)

    def test_authoring_rules_change_invalidates_previous_audit(self) -> None:
        versions = {"authoring": "author-v1", "audit": "audit-v1"}

        def ruleset_hash(path: Path) -> str:
            key = (
                "authoring"
                if "authoring-contract" in path.name
                else "audit"
            )
            return versions[key]

        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            parsed = _parsed()
            with (
                mock.patch(
                    "narrated_fable_drama.contracts.segment.prompt_audit."
                    "parse_segment_script",
                    return_value=parsed,
                ),
                mock.patch(
                    "narrated_fable_drama.contracts.segment.prompt_audit."
                    "sha256_file",
                    side_effect=ruleset_hash,
                ),
            ):
                write_prompt_audit_record(task_dir, "segment-001")
                versions["authoring"] = "author-v2"
                with self.assertRaisesRegex(
                    SegmentRuntimeError,
                    "missing, stale, or failed",
                ):
                    require_prompt_audit(task_dir, parsed)

    def test_provider_prompt_must_equal_audited_model_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            parsed = _parsed()
            with mock.patch(
                "narrated_fable_drama.contracts.segment.prompt_audit."
                "parse_segment_script",
                return_value=parsed,
            ):
                record = write_prompt_audit_record(
                    task_dir,
                    "segment-001",
                )
            require_audited_model_prompt(
                record,
                str(parsed["prompt"]),
                segment_id="segment-001",
            )
            with self.assertRaisesRegex(
                SegmentRuntimeError,
                "changed after the internal audit",
            ):
                require_audited_model_prompt(
                    record,
                    "mutated provider prompt",
                    segment_id="segment-001",
                )

    def test_english_dialogue_cannot_receive_an_audit_record(self) -> None:
        parsed = _parsed()
        parsed["metadata"]["dialogue_cues"][0]["exact_text"] = (
            "This line is still English."
        )
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch(
                "narrated_fable_drama.contracts.segment.prompt_audit."
                "parse_segment_script",
                return_value=parsed,
            ):
                with self.assertRaisesRegex(
                    SegmentRuntimeError,
                    "exact Arabic-only dialogue",
                ):
                    write_prompt_audit_record(
                        Path(temporary),
                        "segment-001",
                    )


if __name__ == "__main__":
    unittest.main()
