from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(
    0,
    str(REPOSITORY_ROOT / "skills/direct-production-design/scripts"),
)

from narrated_fable_drama.contracts.role_scope import (  # noqa: E402
    _role_visual_type_budget,
)
from build_initial_production_design import _final_catalog  # noqa: E402
from production_design.contract import (  # noqa: E402
    ProductionDesignPlanError,
    load_production_design_plan,
)


WHITE = (
    "Seamless pure-white (#FFFFFF) studio backdrop; no environment, horizon, "
    "floor line, texture, gradient, tint, or background cast shadow."
)


def _visual_prompt(asset_type: str) -> dict[str, object]:
    character_exclusions = [
        "No text, subtitles, or typography.",
        "No logos or brand marks.",
        "No watermarks.",
        "No duplicate or repeated subject.",
        "No malformed anatomy or extra limbs.",
        "One isolated single subject only; no multiview or collage.",
    ]
    general_exclusions = [
        "No text, subtitles, or typography.",
        "No logos or brand marks.",
        "No watermarks.",
        "No duplicate or repeated subject.",
    ]
    return {
        "intent_en": "Create one reusable visual identity.",
        "subject_en": "One clearly readable neutral subject.",
        "background_en": (
            "One open room with stable neutral depth."
            if asset_type == "location_master"
            else WHITE
        ),
        "composition_en": "Centered complete presentation with clear silhouette.",
        "continuity": {
            "reference_asset_ids": [],
            "locks_en": ["Keep the authored identity and proportions."],
        },
        "style_en": "3D Healing Animation",
        "exclusions_en": (
            character_exclusions
            if asset_type == "character"
            else general_exclusions
        ),
    }


def _character(entity_id: str, *, speaks: bool) -> dict[str, object]:
    voice_description = "A clear measured adult English voice."
    voice_text = "Truth matters."
    return {
        "type": "character",
        "entity_id": entity_id,
        "actor_profile": {
            "name_en": entity_id.title(),
            "personality_en": "Calm, observant, and considerate.",
            "screen_presence_en": "Grounded posture and readable attention.",
            "acting_range_en": "Concern, resolve, relief, and warmth.",
        },
        "description_en": f"One reusable standalone human identity for {entity_id}.",
        "body_topology": {
            "body_plan_en": "upright bipedal human",
            "total_limb_count": 4,
            "limb_sets": [
                {
                    "kind_en": "legs",
                    "count": 2,
                    "function_en": "standing and walking",
                },
                {
                    "kind_en": "arms",
                    "count": 2,
                    "function_en": "gesture and balance",
                },
            ],
            "non_limb_appendages": [
                {"kind_en": "external ears", "count": 2}
            ],
            "topology_lock_en": "Exactly two legs, two arms, and two ears.",
        },
        "voice_description_en": voice_description if speaks else "none",
        "voice_sample_text_en": voice_text if speaks else "none",
        "voice_speech_rate": 0,
        "voice_generation_prompt": (
            {
                "text_en": voice_text,
                "voice_direction_en": voice_description,
                "delivery_en": "Speak once with clear measured diction.",
                "exclusions_en": ["No music, singing, or added words."],
            }
            if speaks
            else "none"
        ),
        "media_path": f"workspace/assets/characters/{entity_id}/identity.png",
        "generation_prompt": _visual_prompt("character"),
    }


def _performance() -> dict[str, object]:
    entities = [
        {
            "entity_id": "speaker",
            "screenplay_character_name_en": "Speaker",
            "entity_kind": "individual",
            "narration_eligibility": "dialogue_only",
            "group_role_type_en": "none",
            "ensemble_member_types_en": [],
        },
        {
            "entity_id": "silent-guide",
            "screenplay_character_name_en": "Silent Guide",
            "entity_kind": "individual",
            "narration_eligibility": "none",
            "group_role_type_en": "none",
            "ensemble_member_types_en": [],
        },
        {
            "entity_id": "crowd",
            "screenplay_character_name_en": "Crowd",
            "entity_kind": "anonymous_ensemble",
            "narration_eligibility": "none",
            "group_role_type_en": "forest crowd",
            "ensemble_member_types_en": ["rabbits"],
        },
    ]
    return {
        "performance_entities": entities,
        "scene_segment_calls": [
            {
                "scene_id": "scene-001",
                "segment_id": "segment-001",
                "calls": [
                    {
                        "entity_id": "speaker",
                        "entity_kind": "individual",
                        "presence_mode": "on_screen",
                        "speaks": True,
                        "state_changing_action": False,
                    },
                    {
                        "entity_id": "silent-guide",
                        "entity_kind": "individual",
                        "presence_mode": "on_screen",
                        "speaks": False,
                        "state_changing_action": False,
                    },
                    {
                        "entity_id": "crowd",
                        "entity_kind": "anonymous_ensemble",
                        "presence_mode": "on_screen",
                        "speaks": False,
                        "state_changing_action": False,
                    },
                ],
            }
        ],
    }


def _plan() -> dict[str, object]:
    return {
        "contract": "production-design-plan",
        "characters": [
            _character("speaker", speaks=True),
            _character("silent-guide", speaks=False),
        ],
        "ensemble_rosters": [
            {
                "type": "ensemble_roster",
                "asset_id": "group-forest-crowd",
                "group_role_type_en": "forest crowd",
                "description_en": "One closed one-subject rabbit crowd roster.",
                "member_type_id": "rabbit-roster",
                "allowed_member_types_en": ["rabbits"],
                "subject_count": 1,
                "variation_profile": {
                    "locked_traits_en": "Preserve one rabbit subject.",
                    "allowed_variation_en": "Allow a neutral pose change.",
                },
                "media_path": "workspace/assets/role-groups/forest-crowd/group.png",
                "generation_prompt": _visual_prompt("ensemble_roster"),
            }
        ],
        "props": [],
        "costumes": [],
        "locations": [
            {
                "type": "location_master",
                "location_id": "loc-room",
                "scene_ids": ["scene-001"],
                "description_en": "One open neutral room without baked performers.",
                "included_prop_ids": [],
                "embedded_npc_asset_ids": [],
                "independent_performer_asset_ids": [
                    "speaker",
                    "silent-guide",
                    "group-forest-crowd",
                ],
                "fixed_set_elements_en": [],
                "environment_state_en": "Quiet open room.",
                "lighting_state_en": "Soft neutral daylight.",
                "palette_materials_en": "Warm matte neutral surfaces.",
                "topology": {
                    "fixed_obstacles": [],
                    "fixed_prop_placements": [],
                    "open_paths": ["clear center"],
                },
                "landmarks": ["open center"],
                "media_path": "workspace/assets/locations/room/master.png",
                "generation_prompt": _visual_prompt("location_master"),
            }
        ],
    }


class RoleKindClassificationTests(unittest.TestCase):
    def test_budget_uses_kind_not_speech(self) -> None:
        budget = _role_visual_type_budget(_performance()["performance_entities"])
        self.assertEqual(budget["individual_character_type_count"], 2)
        self.assertEqual(budget["anonymous_ensemble_type_count"], 1)
        self.assertEqual(budget["total_role_visual_type_count"], 3)

    def test_silent_individual_is_a_character_without_voice(self) -> None:
        performance = _performance()
        screenplay = {
            "production_information": {"Visual Style": "3D Healing Animation"},
            "scenes": [{"scene_id": "scene-001"}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            plan_path = (
                task_root
                / "direct-production-design"
                / "production-design-plan.json"
            )
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text(json.dumps(_plan()), encoding="utf-8")
            parsed = load_production_design_plan(
                task_root,
                performance=performance,
                screenplay=screenplay,
            )

        characters = {item["entity_id"]: item for item in parsed["characters"]}
        self.assertEqual(set(characters), {"speaker", "silent-guide"})
        self.assertTrue(characters["speaker"]["speaks"])
        self.assertFalse(characters["silent-guide"]["speaks"])
        self.assertNotIn("voice_generation_prompt", characters["silent-guide"])
        self.assertEqual(
            [item["group_role_type_en"] for item in parsed["ensemble_rosters"]],
            ["forest crowd"],
        )
        visuals = {
            asset_id: {
                "path": f"workspace/assets/test/{asset_id}.png",
                "uri": f"https://example.com/{asset_id}.png",
            }
            for asset_id in (
                "speaker",
                "silent-guide",
                "group-forest-crowd",
                "loc-room",
            )
        }
        catalog = _final_catalog(
            parsed,
            visuals=visuals,
            voice_references={
                "speaker": {
                    "description_en": "A clear measured adult English voice.",
                    "reference": {
                        "path": "workspace/assets/characters/speaker/voice.wav",
                        "uri": "https://example.com/speaker.wav",
                    },
                }
            },
        )
        self.assertIn("voice", catalog["assets"]["speaker"])
        self.assertNotIn("voice", catalog["assets"]["silent-guide"])

    def test_omitting_silent_individual_is_rejected(self) -> None:
        performance = _performance()
        screenplay = {
            "production_information": {"Visual Style": "3D Healing Animation"},
            "scenes": [{"scene_id": "scene-001"}],
        }
        plan = _plan()
        plan["characters"] = [plan["characters"][0]]
        with tempfile.TemporaryDirectory() as temporary:
            task_root = Path(temporary)
            plan_path = (
                task_root
                / "direct-production-design"
                / "production-design-plan.json"
            )
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            with self.assertRaisesRegex(
                ProductionDesignPlanError,
                "Kind=individual",
            ):
                load_production_design_plan(
                    task_root,
                    performance=performance,
                    screenplay=screenplay,
                )


if __name__ == "__main__":
    unittest.main()
