"""Resolve provider media bindings and extension reset schedules."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from narrated_fable_drama.contracts.segment.common import SegmentRuntimeError


def _require_http_uri(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise SegmentRuntimeError(f"{label} has no HTTP(S) URI")
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise SegmentRuntimeError(f"{label} has no HTTP(S) URI")
    return value


def resolve_catalog_media(
    *, namespace: str, provider_role: str, catalog: dict[str, Any]
) -> dict[str, Any]:
    assets = catalog.get("assets")
    if not isinstance(assets, dict):
        raise SegmentRuntimeError("Asset catalog has no assets object")
    asset = assets.get(namespace)
    if not isinstance(asset, dict):
        raise SegmentRuntimeError(f"Catalog cannot resolve {namespace!r}")
    if provider_role == "reference_image":
        if asset.get("type") == "ensemble_roster":
            members = asset.get("members")
            if not isinstance(members, list) or len(members) != 1:
                raise SegmentRuntimeError(
                    f"{namespace} must expose exactly one closed roster image"
                )
            member = members[0]
            visual = (
                member.get("roster_asset") if isinstance(member, dict) else None
            )
        else:
            visual = asset.get("visual")
        uri = visual.get("uri") if isinstance(visual, dict) else None
        return {
            "asset_id": namespace,
            "asset_type": str(asset.get("type")),
            "uri": _require_http_uri(uri, namespace),
        }
    if provider_role == "reference_audio":
        if asset.get("type") == "character":
            voice = asset.get("voice")
            reference = voice.get("reference") if isinstance(voice, dict) else None
            uri = reference.get("uri") if isinstance(reference, dict) else None
            path = reference.get("path") if isinstance(reference, dict) else None
            asset_type = "character_voice"
        else:
            audio = asset.get("audio")
            uri = audio.get("uri") if isinstance(audio, dict) else None
            path = audio.get("path") if isinstance(audio, dict) else None
            asset_type = str(asset.get("type"))
        if not isinstance(path, str) or not path.strip():
            raise SegmentRuntimeError(f"{namespace} has no local audio path")
        return {
            "asset_id": namespace,
            "asset_type": asset_type,
            "uri": _require_http_uri(uri, namespace),
            "local_path": path,
        }
    raise SegmentRuntimeError(
        f"Catalog media cannot resolve provider role {provider_role}"
    )


def extension_quality_reset_schedule(
    rows: list[dict[str, Any]], maximum_direct_hops: int
) -> dict[str, dict[str, Any]]:
    if isinstance(maximum_direct_hops, bool) or maximum_direct_hops < 0:
        raise SegmentRuntimeError("Maximum extension hops must be non-negative")
    schedule: dict[str, dict[str, Any]] = {}
    direct_hops_after: dict[str, int] = {}
    for row in rows:
        segment_id = row["segment_id"]
        if row["operation"] != "video_extension":
            direct_hops_after[segment_id] = 0
            schedule[segment_id] = {
                "required": False,
                "strategy": "none",
                "source_segment_id": "none",
                "direct_extension_hops_before_current": 0,
                "direct_extension_hops_after_current": 0,
                "maximum_direct_extension_hops_without_quality_reset": maximum_direct_hops,
            }
            continue
        dependencies = row["depends_on_segment_ids"]
        if len(dependencies) != 1 or dependencies[0] not in direct_hops_after:
            raise SegmentRuntimeError(
                f"{segment_id} video extension needs one earlier predecessor"
            )
        source = dependencies[0]
        inherited = direct_hops_after[source]
        required = inherited >= maximum_direct_hops
        after = 0 if required else inherited + 1
        direct_hops_after[segment_id] = after
        schedule[segment_id] = {
            "required": required,
            "strategy": "white_model_video_edit" if required else "none",
            "source_segment_id": source,
            "direct_extension_hops_before_current": inherited,
            "direct_extension_hops_after_current": after,
            "maximum_direct_extension_hops_without_quality_reset": maximum_direct_hops,
        }
    return schedule
