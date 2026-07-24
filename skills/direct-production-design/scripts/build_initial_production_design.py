#!/usr/bin/env python3
"""Execute an exact model-authored production-design plan."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from narrated_fable_drama.contracts.asset_catalog import (
    ASSET_CATALOG_RELATIVE_PATH,
    ASSET_MEDIA_RELATIVE_PATH,
)
from production_design.contract import (
    load_production_design_plan,
    render_generation_prompt,
)
from narrated_fable_drama.contracts.role_scope import (
    load_character_performance_map,
    role_asset_scope_gate,
)
from narrated_fable_drama.contracts.screenplay import load_screenplay_file
from narrated_fable_drama.core.paths import ProjectPaths
from narrated_fable_drama.core.json_io import (
    load_json_object,
    write_json_atomic,
)

from aesthetic_reference import load_aesthetic_reference
from generate_visual_asset import (
    DEFAULT_IMAGE_SIZE,
    DEFAULT_TIMEOUT,
    generate_visual_asset,
)
from voice_reference_generation import ensure_voice_references


REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root


class InitialProductionDesignError(RuntimeError):
    pass


def _asset_repository_root(
    task_root: Path, repository_root: Path | None = None
) -> Path:
    return (repository_root or task_root).expanduser().resolve()


def _asset_catalog_path(task_root: Path, repository_root: Path | None = None) -> Path:
    return (
        _asset_repository_root(task_root, repository_root)
        / ASSET_CATALOG_RELATIVE_PATH
    )


def _load(path: Path, label: str) -> dict[str, Any]:
    return load_json_object(
        path,
        label=label,
        error_type=InitialProductionDesignError,
    )


def _write_json(path: Path, value: Any) -> None:
    write_json_atomic(path, value)


def reusable_visual_candidate_from_current_record(
    *,
    root: Path,
    record: Any,
    asset_type: str,
) -> dict[str, str] | None:
    """Return usable media facts only; this function makes no reuse decision."""

    if not isinstance(record, dict) or record.get("type") != asset_type:
        return None
    visual = record.get("visual")
    if not isinstance(visual, dict) and asset_type == "ensemble_roster":
        members = record.get("members")
        if isinstance(members, list) and len(members) == 1:
            roster_asset = members[0].get("roster_asset")
            if isinstance(roster_asset, dict):
                visual = {
                    "path": roster_asset.get("path"),
                    "uri": roster_asset.get("uri"),
                }
    if (
        not isinstance(visual, dict)
        or set(visual) != {"path", "uri"}
        or not isinstance(visual.get("path"), str)
        or not visual["path"].strip()
        or not isinstance(visual.get("uri"), str)
        or not visual["uri"].strip()
        or not (root / visual["path"]).is_file()
    ):
        return None
    return {"path": visual["path"], "uri": visual["uri"]}


def _plan_asset_id(asset: dict[str, Any]) -> str:
    if asset["type"] == "character":
        return str(asset["entity_id"])
    if asset["type"] == "location_master":
        return str(asset["location_id"])
    return str(asset["asset_id"])


def _reuse_semantic_description(asset: dict[str, Any]) -> str:
    prompt = asset["generation_prompt"]
    parts = [
        f"Asset type: {asset['type']}.",
        f"Primary design: {asset['description_en']}",
        f"Visible subject: {prompt['subject_en']}",
        f"Background: {prompt['background_en']}",
        f"Composition: {prompt['composition_en']}",
        f"Visual style: {prompt['style_en']}.",
        "Continuity locks: " + "; ".join(prompt["continuity"]["locks_en"]),
        "Visible exclusions: " + "; ".join(prompt["exclusions_en"]),
    ]
    if asset["type"] == "character":
        topology = asset["body_topology"]
        parts.extend(
            [
                f"Actor identity: {asset['actor_profile']['name_en']}.",
                f"Actor presence: {asset['actor_profile']['screen_presence_en']}",
                f"Body plan: {topology['body_plan_en']}.",
                f"Body topology lock: {topology['topology_lock_en']}",
            ]
        )
    elif asset["type"] == "ensemble_roster":
        parts.extend(
            [
                f"Group role: {asset['group_role_type_en']}.",
                "Allowed member types: "
                + "; ".join(asset["allowed_member_types_en"]),
                f"Exact subject count: {asset['subject_count']}.",
                "Roster lock: "
                + asset["variation_profile"]["locked_traits_en"],
                "Allowed variation: "
                + asset["variation_profile"]["allowed_variation_en"],
            ]
        )
    elif asset["type"] == "costume":
        parts.extend(
            [
                f"Character owner: {asset['character_id']}.",
                f"Appearance state: {asset['appearance_state_en']}",
            ]
        )
    elif asset["type"] == "location_master":
        parts.extend(
            [
                f"Environment state: {asset['environment_state_en']}",
                f"Lighting state: {asset['lighting_state_en']}",
                f"Palette and materials: {asset['palette_materials_en']}",
                "Fixed set elements: "
                + ("; ".join(asset["fixed_set_elements_en"]) or "none"),
                "Landmarks: " + "; ".join(asset["landmarks"]),
            ]
        )
    return " ".join(parts)


def _jobs_from_model_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Copy exact model fields into execution jobs; author no prompt or dependency."""

    groups = (
        plan["characters"],
        plan["ensemble_rosters"],
        plan["props"],
        plan["costumes"],
        plan["locations"],
    )
    jobs: list[dict[str, Any]] = []
    for assets in groups:
        for asset in assets:
            jobs.append(
                {
                    "asset_id": _plan_asset_id(asset),
                    "kind": asset["type"],
                    "reuse_semantic_description_en": (
                        _reuse_semantic_description(asset)
                    ),
                    "prompt": render_generation_prompt(asset["generation_prompt"]),
                    "relative_path": Path(asset["media_path"]),
                    "references": list(
                        asset["generation_prompt"]["continuity"][
                            "reference_asset_ids"
                        ]
                    ),
                    "depends_on": list(
                        asset["generation_prompt"]["continuity"][
                            "reference_asset_ids"
                        ]
                    ),
                }
            )
    return jobs


def _existing_assets(
    root: Path, *, repository_root: Path | None = None
) -> dict[str, Any]:
    path = _asset_catalog_path(root, repository_root)
    if not path.is_file():
        return {}
    catalog = _load(path, "production design asset catalog")
    if catalog.get("contract") != "production-design-assets" or not isinstance(
        catalog.get("assets"), dict
    ):
        raise InitialProductionDesignError(
            "assets.json must be the exact final production-design-assets contract"
        )
    return catalog["assets"]


def _semantic_reuse_review(
    root: Path,
    jobs: list[dict[str, Any]],
    *,
    force_regenerate: set[str],
    repository_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Expose every usable same-type candidate; never infer semantic equivalence."""

    asset_repository_root = _asset_repository_root(root, repository_root)
    previous_assets = _existing_assets(root, repository_root=asset_repository_root)
    review: list[dict[str, Any]] = []
    for job in jobs:
        target_asset_id = job["asset_id"]
        if target_asset_id in force_regenerate:
            continue
        candidates: list[dict[str, Any]] = []
        for source_asset_id, source_record in sorted(previous_assets.items()):
            source_description = (
                source_record.get("reuse_semantic_description_en")
                if isinstance(source_record, dict)
                else None
            )
            if not isinstance(source_description, str) or not source_description.strip():
                continue
            visual = reusable_visual_candidate_from_current_record(
                root=asset_repository_root,
                record=source_record,
                asset_type=job["kind"],
            )
            if visual is None:
                continue
            candidates.append(
                {
                    "source_asset_id": source_asset_id,
                    "existing_reuse_semantic_description_en": (
                        source_description.strip()
                    ),
                }
            )
        if not candidates:
            continue
        review.append(
            {
                "target_asset_id": target_asset_id,
                "asset_type": job["kind"],
                "target_reuse_semantic_description_en": job[
                    "reuse_semantic_description_en"
                ],
                "depends_on": list(job["depends_on"]),
                "existing_candidates": candidates,
            }
        )
    return review


def _require_codex_semantic_decisions(
    review: list[dict[str, Any]],
    *,
    codex_reuse: dict[str, str],
    codex_regenerate_visual: set[str],
) -> None:
    review_by_target = {item["target_asset_id"]: item for item in review}
    review_ids = set(review_by_target)
    if set(codex_reuse) & codex_regenerate_visual:
        raise InitialProductionDesignError(
            "A semantic-review candidate cannot be both reused and regenerated"
        )
    invalid = (set(codex_reuse) | codex_regenerate_visual) - review_ids
    if invalid:
        raise InitialProductionDesignError(
            "Codex decisions do not match the current review candidates: "
            + ", ".join(sorted(invalid))
        )
    for target_asset_id, source_asset_id in sorted(codex_reuse.items()):
        valid_sources = {
            candidate["source_asset_id"]
            for candidate in review_by_target[target_asset_id][
                "existing_candidates"
            ]
        }
        if source_asset_id not in valid_sources:
            raise InitialProductionDesignError(
                "Codex semantic reuse source is not a current inspected candidate: "
                f"{target_asset_id}={source_asset_id}"
            )
    reused_sources = list(codex_reuse.values())
    if len(set(reused_sources)) != len(reused_sources):
        raise InitialProductionDesignError(
            "One existing visual asset cannot be semantically assigned to multiple "
            "current target assets"
        )
    unresolved = review_ids - set(codex_reuse) - codex_regenerate_visual
    if unresolved:
        raise InitialProductionDesignError(
            "Codex semantic reuse decision required for: "
            + ", ".join(sorted(unresolved))
        )


def _reusable_visuals(
    root: Path,
    jobs: list[dict[str, Any]],
    *,
    force_regenerate: set[str],
    codex_reuse: dict[str, str],
    repository_root: Path | None = None,
) -> dict[str, dict[str, str]]:
    asset_repository_root = _asset_repository_root(root, repository_root)
    previous_assets = _existing_assets(root, repository_root=asset_repository_root)
    reusable: dict[str, dict[str, str]] = {}
    for job in jobs:
        target_asset_id = job["asset_id"]
        if target_asset_id in force_regenerate or target_asset_id not in codex_reuse:
            continue
        source_asset_id = codex_reuse[target_asset_id]
        visual = reusable_visual_candidate_from_current_record(
            root=asset_repository_root,
            record=previous_assets.get(source_asset_id),
            asset_type=job["kind"],
        )
        if visual is None:
            raise InitialProductionDesignError(
                "Codex-selected semantic reuse candidate is no longer usable: "
                f"{target_asset_id}={source_asset_id}"
            )
        reusable[target_asset_id] = visual
    return reusable


def _generate_job(
    root: Path,
    job: dict[str, Any],
    timeout: int,
    *,
    input_by_asset: dict[str, Path],
    repository_root: Path | None = None,
) -> dict[str, str]:
    asset_repository_root = _asset_repository_root(root, repository_root)
    review_relative_path = (
        ASSET_MEDIA_RELATIVE_PATH
        / ".generated-review"
        / job["kind"]
        / f"{job['asset_id']}.png"
    )
    target = asset_repository_root / review_relative_path
    result = generate_visual_asset(
        task_root=root,
        asset_id=job["asset_id"],
        asset_kind=job["kind"],
        asset_prompt=job["prompt"],
        output_path=target,
        reference_images=[
            str(asset_repository_root / input_by_asset[reference])
            for reference in job["references"]
        ],
        asset_root=asset_repository_root / ASSET_MEDIA_RELATIVE_PATH,
        size=DEFAULT_IMAGE_SIZE,
        timeout=timeout,
    )
    return {
        "path": review_relative_path.as_posix(),
        "uri": result["source_url"],
    }


def _run_dependency_graph(
    root: Path,
    jobs: list[dict[str, Any]],
    *,
    reusable: dict[str, dict[str, str]],
    timeout: int,
    max_workers: int,
    repository_root: Path | None = None,
) -> dict[str, dict[str, str]]:
    completed = dict(reusable)
    remaining = {
        job["asset_id"]: job for job in jobs if job["asset_id"] not in completed
    }
    while remaining:
        ready = [
            job
            for job in remaining.values()
            if set(job["depends_on"]).issubset(completed)
        ]
        if not ready:
            blocked = {
                asset_id: job["depends_on"] for asset_id, job in remaining.items()
            }
            raise InitialProductionDesignError(
                f"Production-design dependency cycle or missing reference: {blocked}"
            )
        failures: list[str] = []
        input_by_asset = {
            asset_id: Path(media["path"])
            for asset_id, media in completed.items()
        }
        with ThreadPoolExecutor(max_workers=min(max_workers, len(ready))) as executor:
            futures = {
                executor.submit(
                    _generate_job,
                    root,
                    job,
                    timeout,
                    input_by_asset=input_by_asset,
                    repository_root=repository_root,
                ): job["asset_id"]
                for job in ready
            }
            for future in as_completed(futures):
                asset_id = futures[future]
                try:
                    completed[asset_id] = future.result()
                except Exception as exc:
                    failures.append(f"{asset_id}: {exc}")
        if failures:
            raise InitialProductionDesignError(
                "Seedream asset wave failed: " + " | ".join(sorted(failures))
            )
        for job in ready:
            remaining.pop(job["asset_id"])
    return completed


def _final_catalog(
    plan: dict[str, Any],
    *,
    visuals: dict[str, dict[str, str]],
    voice_references: dict[str, dict[str, Any]],
    existing_assets: dict[str, Any] | None = None,
    reused_from: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Copy model semantic fields and attach only observed provider media facts."""

    assets: dict[str, Any] = dict(existing_assets or {})
    for target_asset_id, source_asset_id in (reused_from or {}).items():
        if target_asset_id != source_asset_id:
            assets.pop(source_asset_id, None)
    for character in plan["characters"]:
        asset_id = character["entity_id"]
        record = {
            "type": character["type"],
            "description_en": character["description_en"],
            "reuse_semantic_description_en": _reuse_semantic_description(
                character
            ),
            "actor_profile": character["actor_profile"],
            "body_topology": character["body_topology"],
            "visual": visuals[asset_id],
        }
        if character["speaks"]:
            record["voice"] = voice_references[asset_id]
        assets[asset_id] = record
    for ensemble in plan["ensemble_rosters"]:
        asset_id = ensemble["asset_id"]
        assets[asset_id] = {
            "type": ensemble["type"],
            "description_en": ensemble["description_en"],
            "reuse_semantic_description_en": _reuse_semantic_description(
                ensemble
            ),
            "members": [
                {
                    "member_type_id": ensemble["member_type_id"],
                    "roster_asset": {
                        **visuals[asset_id],
                        "subject_count": ensemble["subject_count"],
                    },
                    "allowed_member_types_en": ensemble[
                        "allowed_member_types_en"
                    ],
                    "variation_profile": ensemble["variation_profile"],
                }
            ],
        }
    for prop in plan["props"]:
        asset_id = prop["asset_id"]
        assets[asset_id] = {
            "type": prop["type"],
            "description_en": prop["description_en"],
            "reuse_semantic_description_en": _reuse_semantic_description(prop),
            "visual": visuals[asset_id],
        }
    for costume in plan["costumes"]:
        asset_id = costume["asset_id"]
        assets[asset_id] = {
            "type": costume["type"],
            "description_en": costume["description_en"],
            "reuse_semantic_description_en": _reuse_semantic_description(
                costume
            ),
            "character_id": costume["character_id"],
            "appearance_state_en": costume["appearance_state_en"],
            "visual": visuals[asset_id],
        }
    for location in plan["locations"]:
        asset_id = location["location_id"]
        assets[asset_id] = {
            "type": location["type"],
            "description_en": location["description_en"],
            "reuse_semantic_description_en": _reuse_semantic_description(
                location
            ),
            "included_prop_ids": location["included_prop_ids"],
            "embedded_npc_asset_ids": location["embedded_npc_asset_ids"],
            "independent_performer_asset_ids": location[
                "independent_performer_asset_ids"
            ],
            "fixed_set_elements_en": location["fixed_set_elements_en"],
            "visual": visuals[asset_id],
        }
    return {
        "contract": "production-design-assets",
        "path_resolution": "repository_root_relative",
        "assets": assets,
    }


def _accepted_generated_visuals(
    *,
    jobs: list[dict[str, Any]],
    accepted: dict[str, str],
    repository_root: Path,
) -> dict[str, dict[str, str]]:
    jobs_by_id = {job["asset_id"]: job for job in jobs}
    visuals: dict[str, dict[str, str]] = {}
    for asset_id, source_uri in sorted(accepted.items()):
        if asset_id not in jobs_by_id:
            raise InitialProductionDesignError(
                f"Generated-visual acceptance names unknown asset {asset_id}"
            )
        parsed = urlsplit(source_uri)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise InitialProductionDesignError(
                f"Generated-visual acceptance for {asset_id} needs its exact HTTP(S) source URI"
            )
        job = jobs_by_id[asset_id]
        review_path = (
            repository_root
            / ASSET_MEDIA_RELATIVE_PATH
            / ".generated-review"
            / job["kind"]
            / f"{asset_id}.png"
        )
        if not review_path.is_file():
            raise InitialProductionDesignError(
                f"Generated-visual review candidate is missing for {asset_id}"
            )
        final_path = repository_root / job["relative_path"]
        final_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.replace(final_path)
        visuals[asset_id] = {
            "path": job["relative_path"].as_posix(),
            "uri": source_uri,
        }
    return visuals


def build_task(
    task_dir: Path,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    max_workers: int = 4,
    regenerate_asset_ids: set[str] | None = None,
    regenerate_voice_asset_ids: set[str] | None = None,
    codex_reuse_asset_ids: dict[str, str] | None = None,
    codex_regenerate_visual_asset_ids: set[str] | None = None,
    codex_accept_generated_visual_assets: dict[str, str] | None = None,
    inspect_semantic_reuse: bool = False,
) -> dict[str, Any]:
    root = task_dir.expanduser().resolve(strict=True)
    if not 1 <= max_workers <= 8:
        raise InitialProductionDesignError("max_workers must be 1-8")
    role_scope = role_asset_scope_gate(root)
    performance = load_character_performance_map(root)
    screenplay_path = root / "screenplay-writer" / "screenplay.md"
    screenplay = load_screenplay_file(screenplay_path)
    plan = load_production_design_plan(
        root, performance=performance, screenplay=screenplay
    )
    # Validate optional aesthetic evidence. Its authored translation must already be
    # inside each model prompt; Python never appends it.
    aesthetic_reference = load_aesthetic_reference(root)
    jobs = _jobs_from_model_plan(plan)
    job_ids = {job["asset_id"] for job in jobs}
    speaking_character_ids = {
        character["entity_id"]
        for character in plan["characters"]
        if character["speaks"]
    }

    force_regenerate = set(regenerate_asset_ids or set())
    force_voice = set(regenerate_voice_asset_ids or set())
    codex_reuse = dict(codex_reuse_asset_ids or {})
    codex_regenerate = set(codex_regenerate_visual_asset_ids or set())
    codex_accept_generated = dict(codex_accept_generated_visual_assets or {})
    if (
        force_regenerate
        | set(codex_reuse)
        | codex_regenerate
        | set(codex_accept_generated)
    ) - job_ids:
        raise InitialProductionDesignError("Asset decision names an unknown plan asset")
    if force_voice - speaking_character_ids:
        raise InitialProductionDesignError(
            "Voice regeneration names a silent or non-character entity"
        )
    if (
        force_regenerate & set(codex_reuse)
        or force_regenerate & codex_regenerate
        or set(codex_reuse) & codex_regenerate
        or set(codex_reuse) & set(codex_accept_generated)
        or codex_regenerate & set(codex_accept_generated)
    ):
        raise InitialProductionDesignError("An asset has contradictory decisions")

    review = _semantic_reuse_review(
        root,
        jobs,
        force_regenerate=force_regenerate | set(codex_accept_generated),
        repository_root=REPOSITORY_ROOT,
    )
    if inspect_semantic_reuse:
        return {
            "status": "REVIEW_REQUIRED" if review else "PASS",
            "review_authority": "codex_direct_semantic_judgment",
            "review_prompt": (
                "direct-production-design/references/"
                "asset-semantic-reuse-review.md"
            ),
            "candidates": review,
        }
    _require_codex_semantic_decisions(
        review,
        codex_reuse=codex_reuse,
        codex_regenerate_visual=codex_regenerate,
    )
    reusable = _reusable_visuals(
        root,
        jobs,
        force_regenerate=force_regenerate | codex_regenerate,
        codex_reuse=codex_reuse,
        repository_root=REPOSITORY_ROOT,
    )
    reusable.update(
        _accepted_generated_visuals(
            jobs=jobs,
            accepted=codex_accept_generated,
            repository_root=REPOSITORY_ROOT,
        )
    )
    voice_references = ensure_voice_references(
        [
            character
            for character in plan["characters"]
            if character["speaks"]
        ],
        repository_root=REPOSITORY_ROOT,
        timeout=timeout,
        max_workers=max_workers,
        force_regenerate=force_voice,
    )
    visuals = _run_dependency_graph(
        root,
        jobs,
        reusable=reusable,
        timeout=timeout,
        max_workers=max_workers,
        repository_root=REPOSITORY_ROOT,
    )
    generated_asset_ids = sorted(job_ids - set(reusable))
    if generated_asset_ids:
        jobs_by_id = {job["asset_id"]: job for job in jobs}
        return {
            "status": "REVIEW_REQUIRED",
            "review_authority": "codex_direct_generated_visual_judgment",
            "review_prompt": (
                "direct-production-design/references/"
                "generated-visual-review.md"
            ),
            "generated_visual_candidates": [
                {
                    "asset_id": asset_id,
                    "asset_type": jobs_by_id[asset_id]["kind"],
                    "review_media_path": visuals[asset_id]["path"],
                    "intended_final_media_path": jobs_by_id[asset_id][
                        "relative_path"
                    ].as_posix(),
                    "source_uri": visuals[asset_id]["uri"],
                    "current_generation_prompt": jobs_by_id[asset_id]["prompt"],
                }
                for asset_id in generated_asset_ids
            ],
        }
    catalog = _final_catalog(
        plan,
        visuals=visuals,
        voice_references=voice_references,
        existing_assets=_existing_assets(root, repository_root=REPOSITORY_ROOT),
        reused_from=codex_reuse,
    )
    _write_json(REPOSITORY_ROOT / ASSET_CATALOG_RELATIVE_PATH, catalog)
    return {
        "status": "PASS",
        "role_asset_scope_gate": role_scope["status"],
        "detailed_screenplay_review": role_scope["detailed_screenplay_review"],
        "asset_count": len(catalog["assets"]),
        "seedream_asset_job_count": len(jobs),
        "aesthetic_reference_frame_count": (
            aesthetic_reference["reference_count"]
            if aesthetic_reference is not None
            else 0
        ),
        "max_workers": max_workers,
        "forced_regeneration_asset_ids": sorted(force_regenerate),
        "forced_voice_regeneration_asset_ids": sorted(force_voice),
        "codex_semantic_reuse_sources": {
            target: codex_reuse[target] for target in sorted(codex_reuse)
        },
        "codex_semantic_visual_regeneration_asset_ids": sorted(codex_regenerate),
        "codex_accepted_generated_visual_asset_ids": sorted(
            codex_accept_generated
        ),
    }


def _parse_codex_reuse_decisions(values: list[str]) -> dict[str, str]:
    decisions: dict[str, str] = {}
    for value in values:
        target_asset_id, separator, source_asset_id = value.partition("=")
        if (
            separator != "="
            or not target_asset_id.strip()
            or not source_asset_id.strip()
            or "=" in source_asset_id
        ):
            raise InitialProductionDesignError(
                "--codex-reuse-asset must use TARGET_ASSET_ID=SOURCE_ASSET_ID"
            )
        target_asset_id = target_asset_id.strip()
        source_asset_id = source_asset_id.strip()
        if target_asset_id in decisions:
            raise InitialProductionDesignError(
                f"Duplicate Codex reuse decision for {target_asset_id}"
            )
        decisions[target_asset_id] = source_asset_id
    return decisions


def _parse_generated_visual_acceptances(values: list[str]) -> dict[str, str]:
    acceptances: dict[str, str] = {}
    for value in values:
        asset_id, separator, source_uri = value.partition("=")
        if separator != "=" or not asset_id.strip() or not source_uri.strip():
            raise InitialProductionDesignError(
                "--codex-accept-generated-visual-asset must use ASSET_ID=SOURCE_URI"
            )
        asset_id = asset_id.strip()
        if asset_id in acceptances:
            raise InitialProductionDesignError(
                f"Duplicate generated-visual acceptance for {asset_id}"
            )
        acceptances[asset_id] = source_uri.strip()
    return acceptances


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--inspect-semantic-reuse", action="store_true")
    parser.add_argument(
        "--codex-reuse-asset",
        action="append",
        default=[],
        metavar="TARGET=SOURCE",
    )
    parser.add_argument(
        "--codex-regenerate-visual-asset", action="append", default=[]
    )
    parser.add_argument(
        "--codex-accept-generated-visual-asset",
        action="append",
        default=[],
        metavar="ASSET_ID=SOURCE_URI",
    )
    parser.add_argument("--regenerate-voice", action="append", default=[])
    parser.add_argument("--regenerate-asset", action="append", default=[])
    args = parser.parse_args()
    try:
        codex_reuse = _parse_codex_reuse_decisions(args.codex_reuse_asset)
        codex_accept_generated = _parse_generated_visual_acceptances(
            args.codex_accept_generated_visual_asset
        )
        result = build_task(
            args.task_dir,
            timeout=args.timeout,
            max_workers=args.max_workers,
            regenerate_asset_ids=set(args.regenerate_asset),
            regenerate_voice_asset_ids=set(args.regenerate_voice),
            codex_reuse_asset_ids=codex_reuse,
            codex_regenerate_visual_asset_ids=set(
                args.codex_regenerate_visual_asset
            ),
            codex_accept_generated_visual_assets=codex_accept_generated,
            inspect_semantic_reuse=args.inspect_semantic_reuse,
        )
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"PASS", "REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
