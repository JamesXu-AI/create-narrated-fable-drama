from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from narrated_fable_drama.contracts.asset_catalog import load_asset_catalog
from narrated_fable_drama.core.validation import StoryVideoError


def _visual(path: str, uri: str) -> dict[str, str]:
    return {"path": path, "uri": uri}


def _prop(path: str, uri: str, *, parent: str | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "type": "prop",
        "description_en": "A reusable story prop.",
        "reuse_semantic_description_en": "The same reusable story prop.",
        "visual": _visual(path, uri),
    }
    if parent is not None:
        value["parent_asset_id"] = parent
    return value


class AssetCatalogDerivativeTests(unittest.TestCase):
    def _load(self, assets: dict[str, dict[str, object]]) -> dict[str, object]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repository_root = Path(temporary.name)
        asset_root = repository_root / "workspace" / "assets"
        task_root = repository_root / "workspace" / "tasks" / "task"
        asset_root.mkdir(parents=True)
        task_root.mkdir(parents=True)
        for asset in assets.values():
            visual = asset["visual"]
            assert isinstance(visual, dict)
            media = repository_root / str(visual["path"])
            media.parent.mkdir(parents=True, exist_ok=True)
            media.write_bytes(str(media).encode("utf-8"))
        payload = {
            "contract": "production-design-assets",
            "path_resolution": "repository_root_relative",
            "assets": assets,
        }
        (asset_root / "assets.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        return load_asset_catalog(task_root, repository_root=repository_root)

    def test_prop_may_declare_a_cataloged_parent_state(self) -> None:
        catalog = self._load(
            {
                "lamp-off": _prop(
                    "workspace/assets/props/lamp-off.png",
                    "https://example.com/lamp-off.png",
                ),
                "lamp-repaired": _prop(
                    "workspace/assets/props/lamp-repaired.png",
                    "https://example.com/lamp-repaired.png",
                    parent="lamp-off",
                ),
            }
        )

        self.assertEqual(
            catalog["assets"]["lamp-repaired"]["parent_asset_id"], "lamp-off"
        )

    def test_prop_parent_must_reference_another_prop(self) -> None:
        with self.assertRaisesRegex(
            StoryVideoError, "must reference a current prop"
        ):
            self._load(
                {
                    "lamp-repaired": _prop(
                        "workspace/assets/props/lamp-repaired.png",
                        "https://example.com/lamp-repaired.png",
                        parent="missing-lamp",
                    )
                }
            )

    def test_prop_parent_chain_may_not_cycle(self) -> None:
        with self.assertRaisesRegex(StoryVideoError, "contains a cycle"):
            self._load(
                {
                    "lamp-a": _prop(
                        "workspace/assets/props/lamp-a.png",
                        "https://example.com/lamp-a.png",
                        parent="lamp-b",
                    ),
                    "lamp-b": _prop(
                        "workspace/assets/props/lamp-b.png",
                        "https://example.com/lamp-b.png",
                        parent="lamp-a",
                    ),
                }
            )


if __name__ == "__main__":
    unittest.main()
