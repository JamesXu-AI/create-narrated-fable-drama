#!/usr/bin/env python3
"""Validate the current production-design outputs without approval records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from narrated_fable_drama.contracts.asset_catalog import load_asset_catalog
from production_design.contract import load_production_design_plan
from narrated_fable_drama.contracts.role_scope import (
    load_character_performance_map,
)
from narrated_fable_drama.contracts.screenplay import load_screenplay_file
from narrated_fable_drama.core.paths import ProjectPaths
from narrated_fable_drama.core.project_context import load_project_context

from aesthetic_reference import load_aesthetic_reference
from voice_reference_generation import validate_voice_authority


PROJECT_PATHS = ProjectPaths.resolve(Path(__file__))
SKILL_ROOT = PROJECT_PATHS.repository_root / "skills/direct-production-design"
REPOSITORY_ROOT = PROJECT_PATHS.repository_root


class ProductionDesignError(RuntimeError):
    pass


def _validate_silent_group_authority(
    plan: dict[str, object], catalog: dict[str, object]
) -> int:
    assets = catalog["assets"]
    expected_ids: set[str] = set()
    for ensemble in plan["ensemble_rosters"]:
        asset_id = ensemble["asset_id"]
        expected_ids.add(asset_id)
        asset = assets.get(asset_id)
        if not isinstance(asset, dict) or asset.get("type") != "ensemble_roster":
            raise ProductionDesignError(
                f"Missing model-authored ensemble roster {asset_id}"
            )
        if asset.get("description_en") != ensemble["description_en"]:
            raise ProductionDesignError(
                f"{asset_id} description differs from the model plan"
            )
        members = asset.get("members")
        if not isinstance(members, list) or len(members) != 1:
            raise ProductionDesignError(
                f"{asset_id} must contain exactly one current role-group record"
            )
        member = members[0]
        if member.get("member_type_id") != ensemble["member_type_id"]:
            raise ProductionDesignError(
                f"{asset_id} member_type_id differs from the model plan"
            )
        if member.get("allowed_member_types_en") != ensemble["allowed_member_types_en"]:
            raise ProductionDesignError(
                f"{asset_id} allowed member types differ from the model plan"
            )
        if member.get("variation_profile") != ensemble["variation_profile"]:
            raise ProductionDesignError(
                f"{asset_id} variation profile differs from the model plan"
            )
        if member.get("roster_asset", {}).get("subject_count") != ensemble["subject_count"]:
            raise ProductionDesignError(
                f"{asset_id} subject count differs from the model plan"
            )
    actual_ids = {
        asset_id
        for asset_id, asset in assets.items()
        if isinstance(asset, dict) and asset.get("type") == "ensemble_roster"
    }
    if not expected_ids.issubset(actual_ids):
        raise ProductionDesignError(
            "Current ensemble roster set is incomplete; reusable library records "
            "may remain in the catalog, but every current role must exist; "
            f"expected={sorted(expected_ids)}, actual={sorted(actual_ids)}"
        )
    return len(expected_ids)


def validate_task(task_dir: Path) -> dict[str, object]:
    task_dir = task_dir.expanduser().resolve(strict=True)
    try:
        load_project_context(task_dir)
    except Exception as exc:
        raise ProductionDesignError(str(exc)) from exc
    for relative in ("screenplay-writer/screenplay.md",):
        path = task_dir / relative
        if not path.is_file() or path.stat().st_size <= 0:
            raise ProductionDesignError(f"Missing current screenplay input: {relative}")
    catalog = load_asset_catalog(task_dir)
    performance = load_character_performance_map(task_dir)
    screenplay = load_screenplay_file(
        task_dir / "screenplay-writer" / "screenplay.md"
    )
    plan = load_production_design_plan(
        task_dir, performance=performance, screenplay=screenplay
    )
    anonymous_ensemble_count = _validate_silent_group_authority(plan, catalog)
    aesthetic_reference = load_aesthetic_reference(task_dir)
    expected_scene_ids = {
        segment["scene_id"] for segment in performance["scene_segment_calls"]
    }
    planned_scene_ids = {
        scene_id
        for location in plan["locations"]
        for scene_id in location["scene_ids"]
    }
    if planned_scene_ids != expected_scene_ids:
        raise ProductionDesignError(
            "Production-design locations must cover every current screenplay Scene "
            "exactly once; "
            f"expected={sorted(expected_scene_ids)}, actual={sorted(planned_scene_ids)}"
        )
    voice_result = validate_voice_authority(task_dir)
    expected_speaker_count = sum(
        1 for character in plan["characters"] if character["speaks"]
    )
    if voice_result["speaker_count"] != expected_speaker_count:
        raise ProductionDesignError(
            "Voice assets must exactly cover speaking Kind=individual entities; "
            f"expected={expected_speaker_count}, "
            f"actual={voice_result['speaker_count']}"
        )
    return {
        "status": "PASS",
        "asset_count": len(catalog["assets"]),
        "individual_character_count": len(plan["characters"]),
        "anonymous_ensemble_count": anonymous_ensemble_count,
        "story_object_authority_count": len(plan["object_authorities"]),
        "dedicated_story_object_count": sum(
            item["mode"] == "dedicated_asset"
            for item in plan["object_authorities"]
        ),
        "prop_asset_count": len(plan["props"]),
        "speaker_voice_count": voice_result["speaker_count"],
        "location_master_count": len(plan["locations"]),
        "aesthetic_reference_frame_count": (
            aesthetic_reference["reference_count"]
            if aesthetic_reference is not None
            else 0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = validate_task(args.task_dir)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
