from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(
    0,
    str(REPOSITORY_ROOT / "skills/previsualize-cinematography/scripts"),
)

import validate_storyboard as storyboard_validation  # noqa: E402

from narrated_fable_drama.contracts.screenplay.parser import (  # noqa: E402
    _physical_owner,
    _visual_control_triggers,
)
from narrated_fable_drama.contracts.story_objects import (  # noqa: E402
    expected_visual_authority_mode,
    requires_dedicated_visual_asset,
)
from narrated_fable_drama.core.validation import StoryVideoError  # noqa: E402


def _story_object(
    *,
    owner_kind: str,
    triggers: list[str],
    authority_shots: list[str] | None = None,
) -> dict[str, object]:
    return {
        "object_id": "object-001",
        "physical_owner_kind": owner_kind,
        "visual_control_triggers": triggers,
        "visual_authority_shot_ids": list(authority_shots or []),
    }


def _storyboard(reference_namespace: str) -> str:
    reference_headers = (
        "| Provider Token | Provider Role | Asset Namespace | Readable Subject | "
        "Purpose | Shot Scope | Forbidden Inheritance |"
    )
    reference_row = (
        f"| @Image1 | reference_image | {reference_namespace} | controlled object | "
        "stable visual authority | Shot 1 | unrelated environment |"
    )
    shot_headers = (
        "| Shot | Screenplay Shot | Shot Size | Transition and Camera | "
        "Subject Action and Expression | Space, Blocking and Gaze | "
        "Persistent Anchors | Lighting and Color | Dialogue and Native Audio | "
        "Landing and Edit |"
    )
    shot_row = (
        "| Shot 1 | A-001 | close_up | locked | visible action | stable relation | "
        "object | neutral | none; quiet | settled |"
    )
    return "\n".join(
        [
            "## Generation Segment 1 — Generic test",
            "",
            "### Reference Plan",
            "",
            reference_headers,
            "| --- | --- | --- | --- | --- | --- | --- |",
            reference_row,
            "",
            "### Ordered Shots",
            "",
            shot_headers,
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            shot_row,
            "",
        ]
    )


class StoryObjectAuthorityTests(unittest.TestCase):
    def test_story_object_control_grammar_is_generic_and_closed(self) -> None:
        self.assertEqual(
            _physical_owner(
                "environment:environment-main",
                label="Physical Owner",
            ),
            ("environment", "environment-main"),
        )
        self.assertEqual(
            _visual_control_triggers(
                "recurring_identity, interaction_geometry",
                label="Visual Control Triggers",
            ),
            ["recurring_identity", "interaction_geometry"],
        )
        with self.assertRaises(StoryVideoError):
            _visual_control_triggers(
                "story_specific_exception",
                label="Visual Control Triggers",
            )

    def test_independent_controlled_object_requires_dedicated_asset(self) -> None:
        self.assertTrue(
            requires_dedicated_visual_asset(
                _story_object(
                    owner_kind="independent",
                    triggers=["distinctive_identity"],
                )
            )
        )

    def test_owner_can_cover_recurring_identity_without_dedicated_asset(self) -> None:
        self.assertFalse(
            requires_dedicated_visual_asset(
                _story_object(
                    owner_kind="environment",
                    triggers=["recurring_identity"],
                )
            )
        )

    def test_detail_view_requires_dedicated_asset_even_with_owner(self) -> None:
        self.assertTrue(
            requires_dedicated_visual_asset(
                _story_object(
                    owner_kind="character",
                    triggers=["detail_view"],
                )
            )
        )

    def test_controlled_child_of_prompt_only_parent_is_promoted(self) -> None:
        self.assertEqual(
            expected_visual_authority_mode(
                _story_object(
                    owner_kind="object",
                    triggers=["distinctive_identity"],
                ),
                parent_mode="segment_prompt_only",
            ),
            "dedicated_asset",
        )

    def test_uncontrolled_child_of_prompt_only_parent_stays_prompt_only(self) -> None:
        self.assertEqual(
            expected_visual_authority_mode(
                _story_object(owner_kind="object", triggers=[]),
                parent_mode="segment_prompt_only",
            ),
            "segment_prompt_only",
        )

    def test_storyboard_binds_authority_asset_at_required_shot(self) -> None:
        screenplay = {
            "story_objects": [
                _story_object(
                    owner_kind="independent",
                    triggers=["detail_view"],
                    authority_shots=["A-001"],
                )
            ]
        }
        plan = {
            "object_authorities": [
                {
                    "object_id": "object-001",
                    "mode": "dedicated_asset",
                    "asset_ids": ["prop-controlled"],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            plan_path = (
                task_dir
                / "direct-production-design"
                / "production-design-plan.json"
            )
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with patch.object(
                storyboard_validation,
                "load_screenplay_file",
                return_value=screenplay,
            ):
                storyboard_validation._validate_visual_object_reference_coverage(
                    task_dir,
                    _storyboard("prop-controlled"),
                )

    def test_storyboard_rejects_missing_authority_binding(self) -> None:
        screenplay = {
            "story_objects": [
                _story_object(
                    owner_kind="independent",
                    triggers=["interaction_geometry"],
                    authority_shots=["A-001"],
                )
            ]
        }
        plan = {
            "object_authorities": [
                {
                    "object_id": "object-001",
                    "mode": "dedicated_asset",
                    "asset_ids": ["prop-controlled"],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            plan_path = (
                task_dir
                / "direct-production-design"
                / "production-design-plan.json"
            )
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with patch.object(
                storyboard_validation,
                "load_screenplay_file",
                return_value=screenplay,
            ):
                with self.assertRaisesRegex(
                    storyboard_validation.StoryboardValidationError,
                    "must bind object-001",
                ):
                    storyboard_validation._validate_visual_object_reference_coverage(
                        task_dir,
                        _storyboard("different-asset"),
                    )

    def test_storyboard_accepts_cataloged_state_derivative_binding(self) -> None:
        screenplay = {
            "story_objects": [
                _story_object(
                    owner_kind="independent",
                    triggers=["state_change"],
                    authority_shots=["A-001"],
                )
            ]
        }
        plan = {
            "object_authorities": [
                {
                    "object_id": "object-001",
                    "mode": "dedicated_asset",
                    "asset_ids": ["prop-controlled"],
                }
            ]
        }
        catalog = {
            "assets": {
                "prop-controlled-repaired": {
                    "type": "prop",
                    "parent_asset_id": "prop-controlled",
                }
            }
        }
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary) / "workspace" / "tasks" / "task"
            plan_path = (
                task_dir
                / "direct-production-design"
                / "production-design-plan.json"
            )
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            catalog_path = task_dir.parent.parent / "assets" / "assets.json"
            catalog_path.parent.mkdir(parents=True)
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            with patch.object(
                storyboard_validation,
                "load_screenplay_file",
                return_value=screenplay,
            ):
                storyboard_validation._validate_visual_object_reference_coverage(
                    task_dir,
                    _storyboard("prop-controlled-repaired"),
                )


if __name__ == "__main__":
    unittest.main()
