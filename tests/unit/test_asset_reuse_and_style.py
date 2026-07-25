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

from build_initial_production_design import (  # noqa: E402
    InitialProductionDesignError,
    _accepted_generated_visuals,
    _require_codex_semantic_decisions,
    _semantic_reuse_review,
    _uncatalogued_exact_path_matches,
)
from production_design.contract import (  # noqa: E402
    DEFAULT_STYLE_EXECUTION_EN,
    DEFAULT_STYLE_MEDIUM_EXCLUSIONS_EN,
    render_generation_prompt,
    validate_generation_prompt_text,
)


WHITE = (
    "Seamless pure-white (#FFFFFF) studio backdrop; no environment, horizon, "
    "floor line, texture, gradient, tint, or background cast shadow."
)


def _prop_prompt() -> dict[str, object]:
    return {
        "intent_en": "Create one reusable crown.",
        "subject_en": "One rounded woven crown with nine soft feathers.",
        "background_en": WHITE,
        "composition_en": "One centered complete three-quarter product view.",
        "continuity": {
            "reference_asset_ids": [],
            "locks_en": ["Preserve one band and exactly nine feathers."],
        },
        "style_en": "3D Healing Animation",
        "exclusions_en": [
            "No text, subtitles, or typography.",
            "No logos or brand marks.",
            "No watermarks.",
            "No duplicate, cloned, or repeated props.",
        ],
    }


class AssetReuseAndStyleTests(unittest.TestCase):
    def test_provider_prompt_expands_default_3d_style(self) -> None:
        rendered = render_generation_prompt(_prop_prompt())
        validated = validate_generation_prompt_text(rendered, asset_type="prop")
        payload = json.loads(validated)

        self.assertEqual(payload["style_execution_en"], DEFAULT_STYLE_EXECUTION_EN)
        self.assertEqual(
            payload["style_medium_exclusions_en"],
            DEFAULT_STYLE_MEDIUM_EXCLUSIONS_EN,
        )
        self.assertIn("stylized soft 3D", payload["style_execution_en"])
        self.assertTrue(
            any(
                "photorealism" in exclusion.casefold()
                for exclusion in payload["style_medium_exclusions_en"]
            )
        )

    def test_semantic_reuse_review_supports_cross_id_candidates_without_images(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository_root = Path(temporary)
            task_root = repository_root / "runtime" / "task"
            task_root.mkdir(parents=True)
            media = (
                repository_root
                / "workspace"
                / "assets"
                / "library"
                / "old-crown.png"
            )
            media.parent.mkdir(parents=True)
            media.write_bytes(b"existing-media")
            catalog = {
                "contract": "production-design-assets",
                "path_resolution": "repository_root_relative",
                "assets": {
                    "old-crown": {
                        "type": "prop",
                        "description_en": "A soft ceremonial crown.",
                        "reuse_semantic_description_en": (
                            "A reusable rounded woven ceremonial crown with nine "
                            "soft feathers in stylized 3D healing animation."
                        ),
                        "visual": {
                            "path": "workspace/assets/library/old-crown.png",
                            "uri": "https://example.com/old-crown.png",
                        },
                    }
                },
            }
            (repository_root / "workspace" / "assets" / "assets.json").write_text(
                json.dumps(catalog), encoding="utf-8"
            )
            jobs = [
                {
                    "asset_id": "new-crown",
                    "kind": "prop",
                    "reuse_semantic_description_en": (
                        "One reusable softly rounded ceremonial crown with exactly "
                        "nine feathers, rendered as gentle stylized 3D animation."
                    ),
                    "prompt": render_generation_prompt(_prop_prompt()),
                    "relative_path": Path("workspace/assets/props/new-crown.png"),
                    "references": [],
                    "depends_on": [],
                }
            ]

            review = _semantic_reuse_review(
                task_root,
                jobs,
                force_regenerate=set(),
                repository_root=repository_root,
            )

        self.assertEqual(review[0]["target_asset_id"], "new-crown")
        self.assertEqual(
            review[0]["existing_candidates"][0]["source_asset_id"],
            "old-crown",
        )
        self.assertNotIn("existing_media_path", review[0]["existing_candidates"][0])
        self.assertNotIn("current_generation_prompt", review[0])
        _require_codex_semantic_decisions(
            review,
            codex_reuse={"new-crown": "old-crown"},
            codex_regenerate_visual=set(),
        )
        with self.assertRaises(InitialProductionDesignError):
            _require_codex_semantic_decisions(
                review,
                codex_reuse={},
                codex_regenerate_visual=set(),
            )

    def test_generated_visual_is_staged_until_explicit_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository_root = Path(temporary)
            review_path = (
                repository_root
                / "workspace"
                / "assets"
                / ".generated-review"
                / "prop"
                / "new-crown.png"
            )
            review_path.parent.mkdir(parents=True)
            review_path.write_bytes(b"reviewed-image")
            jobs = [
                {
                    "asset_id": "new-crown",
                    "kind": "prop",
                    "relative_path": Path("workspace/assets/props/new-crown.png"),
                }
            ]
            final_path = (
                repository_root
                / "workspace"
                / "assets"
                / "props"
                / "new-crown.png"
            )
            self.assertFalse(final_path.exists())

            accepted = _accepted_generated_visuals(
                jobs=jobs,
                accepted={
                    "new-crown": "https://example.com/generated/new-crown.png"
                },
                repository_root=repository_root,
            )

            self.assertFalse(review_path.exists())
            self.assertEqual(final_path.read_bytes(), b"reviewed-image")
            self.assertEqual(
                accepted["new-crown"]["path"],
                "workspace/assets/props/new-crown.png",
            )

    def test_exact_library_media_missing_from_catalog_is_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository_root = Path(temporary)
            task_root = repository_root / "runtime" / "task"
            task_root.mkdir(parents=True)
            existing = (
                repository_root
                / "workspace"
                / "assets"
                / "costumes"
                / "elephant-wounded"
                / "image.png"
            )
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"existing-injured-elephant")
            catalog = {
                "contract": "production-design-assets",
                "path_resolution": "repository_root_relative",
                "assets": {},
            }
            (repository_root / "workspace" / "assets" / "assets.json").write_text(
                json.dumps(catalog), encoding="utf-8"
            )
            jobs = [
                {
                    "asset_id": "costume-elephant-wounded",
                    "kind": "costume",
                    "relative_path": Path(
                        "workspace/assets/costumes/elephant-wounded/image.png"
                    ),
                }
            ]

            matches = _uncatalogued_exact_path_matches(
                task_root,
                jobs,
                repository_root=repository_root,
            )

        self.assertEqual(
            matches,
            [
                {
                    "target_asset_id": "costume-elephant-wounded",
                    "asset_type": "costume",
                    "existing_media_path": (
                        "workspace/assets/costumes/elephant-wounded/image.png"
                    ),
                    "required_catalog_path": "workspace/assets/assets.json",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
