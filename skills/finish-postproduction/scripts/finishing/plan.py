"""Validate an explicit model-authored postproduction repair plan.

This module deliberately contains no edit strategy.  It checks identity,
coverage, bounds, dialogue preservation, and renderer-supported values.  Missing
values are errors; no semantic field receives a default.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from narrated_fable_drama.core.json_io import load_json_object


PLAN_CONTRACT = "llm-postproduction-repair-plan/v1"
EVIDENCE_CONTRACT = "finish-postproduction-evidence/v1"
DECISION_AUTHORITY = "editor-restoration-master-model"
BOUNDARY_WINDOW_SECONDS = 3.0


class RepairPlanError(RuntimeError):
    """Raised when a model-authored finishing plan is missing, stale, or unsafe."""


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    return load_json_object(path, label=label, error_type=RepairPlanError)


def _sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError as exc:
        raise RepairPlanError(f"Cannot hash required file: {path}") from exc


def _exact_keys(value: object, expected: set[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RepairPlanError(f"{label} must be an object")
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        parts: list[str] = []
        if missing:
            parts.append("missing " + ", ".join(missing))
        if unknown:
            parts.append("unknown " + ", ".join(unknown))
        raise RepairPlanError(f"{label} has invalid fields: {'; '.join(parts)}")
    return value


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RepairPlanError(f"{label} must be a non-empty string")
    return value


def _number(
    value: object,
    *,
    label: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RepairPlanError(f"{label} must be a number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise RepairPlanError(f"{label} must be at least {minimum}")
    if maximum is not None and result > maximum:
        raise RepairPlanError(f"{label} must be at most {maximum}")
    return result


def _string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise RepairPlanError(f"{label} must be a list")
    result = [_string(item, label=f"{label} item") for item in value]
    if len(result) != len(set(result)):
        raise RepairPlanError(f"{label} contains duplicates")
    return result


def _ordered_evidence_segments(
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    segments = evidence.get("segments")
    if not isinstance(segments, list) or not segments:
        raise RepairPlanError("Evidence manifest contains no Segments")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(segments):
        if not isinstance(item, dict):
            raise RepairPlanError(f"Evidence Segment {index + 1} is invalid")
        result.append(item)
    return result


def _validate_observation_window(
    plan_window: object,
    evidence_window: object,
) -> None:
    expected = {"outgoing_tail_seconds", "incoming_head_seconds"}
    plan = _exact_keys(plan_window, expected, label="plan observation_window")
    evidence = _exact_keys(
        evidence_window,
        expected,
        label="evidence observation_window",
    )
    for key in sorted(expected):
        planned = _number(plan[key], label=f"plan observation_window.{key}")
        measured = _number(
            evidence[key],
            label=f"evidence observation_window.{key}",
        )
        if abs(planned - BOUNDARY_WINDOW_SECONDS) > 1e-9:
            raise RepairPlanError(
                f"plan observation_window.{key} must be exactly "
                f"{BOUNDARY_WINDOW_SECONDS:.1f} seconds"
            )
        if abs(planned - measured) > 1e-9:
            raise RepairPlanError(
                f"Plan and evidence observation windows differ for {key}"
            )


def _validate_color_adjustment(
    adjustment: object,
    *,
    segment_id: str,
    source_in: float,
    source_out: float,
) -> dict[str, Any]:
    item = _exact_keys(
        adjustment,
        {
            "source_start_seconds",
            "source_end_seconds",
            "brightness",
            "contrast",
            "saturation",
            "gamma",
            "reason",
        },
        label=f"{segment_id} color adjustment",
    )
    start = _number(
        item["source_start_seconds"],
        label=f"{segment_id} color source start",
        minimum=source_in,
        maximum=source_out,
    )
    end = _number(
        item["source_end_seconds"],
        label=f"{segment_id} color source end",
        minimum=source_in,
        maximum=source_out,
    )
    if end <= start:
        raise RepairPlanError(f"{segment_id} color adjustment is empty")
    _number(
        item["brightness"],
        label=f"{segment_id} color brightness",
        minimum=-1.0,
        maximum=1.0,
    )
    _number(
        item["contrast"],
        label=f"{segment_id} color contrast",
        minimum=0.0,
        maximum=4.0,
    )
    _number(
        item["saturation"],
        label=f"{segment_id} color saturation",
        minimum=0.0,
        maximum=4.0,
    )
    _number(
        item["gamma"],
        label=f"{segment_id} color gamma",
        minimum=0.1,
        maximum=10.0,
    )
    _string(item["reason"], label=f"{segment_id} color reason")
    return item


def _validate_gain_adjustment(
    adjustment: object,
    *,
    segment_id: str,
    source_in: float,
    source_out: float,
) -> dict[str, Any]:
    item = _exact_keys(
        adjustment,
        {
            "source_start_seconds",
            "source_end_seconds",
            "gain_db",
            "reason",
        },
        label=f"{segment_id} gain adjustment",
    )
    start = _number(
        item["source_start_seconds"],
        label=f"{segment_id} gain source start",
        minimum=source_in,
        maximum=source_out,
    )
    end = _number(
        item["source_end_seconds"],
        label=f"{segment_id} gain source end",
        minimum=source_in,
        maximum=source_out,
    )
    if end <= start:
        raise RepairPlanError(f"{segment_id} gain adjustment is empty")
    _number(item["gain_db"], label=f"{segment_id} local gain")
    _string(item["reason"], label=f"{segment_id} gain reason")
    return item


def _validate_removed_intervals(
    value: object,
    *,
    segment_id: str,
    media: str,
    source_in: float,
    source_out: float,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RepairPlanError(
            f"{segment_id} {media} removed_intervals must be a list"
        )
    result: list[dict[str, Any]] = []
    prior_end = source_in
    for index, raw in enumerate(value):
        item = _exact_keys(
            raw,
            {"source_start_seconds", "source_end_seconds", "reason"},
            label=f"{segment_id} {media} removed interval {index + 1}",
        )
        start = _number(
            item["source_start_seconds"],
            label=f"{segment_id} {media} removed start",
            minimum=source_in,
            maximum=source_out,
        )
        end = _number(
            item["source_end_seconds"],
            label=f"{segment_id} {media} removed end",
            minimum=source_in,
            maximum=source_out,
        )
        if end <= start:
            raise RepairPlanError(
                f"{segment_id} {media} removed interval is empty"
            )
        if start < prior_end - 1e-6:
            raise RepairPlanError(
                f"{segment_id} {media} removed intervals overlap or are unordered"
            )
        _string(
            item["reason"],
            label=f"{segment_id} {media} removed interval reason",
        )
        prior_end = end
        result.append(item)
    removed_duration = sum(
        float(item["source_end_seconds"])
        - float(item["source_start_seconds"])
        for item in result
    )
    if removed_duration >= source_out - source_in - 1e-6:
        raise RepairPlanError(
            f"{segment_id} {media} removed intervals consume the complete event"
        )
    return result


def _kept_ranges(
    source_in: float,
    source_out: float,
    removed: list[dict[str, Any]],
) -> list[tuple[float, float]]:
    ranges: list[tuple[float, float]] = []
    cursor = source_in
    for item in removed:
        start = float(item["source_start_seconds"])
        end = float(item["source_end_seconds"])
        if start > cursor + 1e-9:
            ranges.append((cursor, start))
        cursor = end
    if source_out > cursor + 1e-9:
        ranges.append((cursor, source_out))
    return ranges


def materialize_kept_ranges(media_plan: dict[str, Any]) -> list[dict[str, float]]:
    """Return ordered source ranges after explicit internal deletions."""
    return [
        {
            "source_in_seconds": start,
            "source_out_seconds": end,
        }
        for start, end in _kept_ranges(
            float(media_plan["source_in_seconds"]),
            float(media_plan["source_out_seconds"]),
            media_plan["removed_intervals"],
        )
    ]


def _one_range_contains(
    ranges: list[tuple[float, float]],
    start: float,
    end: float,
) -> bool:
    return any(
        range_start <= start + 1e-6 and range_end >= end - 1e-6
        for range_start, range_end in ranges
    )


def _retained_interval(
    ranges: list[tuple[float, float]],
    start: float,
    end: float,
    *,
    label: str,
) -> tuple[float, float]:
    """Map one intact source interval onto its retained event timeline."""
    cursor = 0.0
    for range_start, range_end in ranges:
        if range_start <= start + 1e-6 and range_end >= end - 1e-6:
            return (
                cursor + max(0.0, start - range_start),
                cursor + min(range_end - range_start, end - range_start),
            )
        cursor += range_end - range_start
    raise RepairPlanError(f"{label} does not lie inside retained media")


def _intervals_overlap(
    first_start: float,
    first_end: float,
    second_start: float,
    second_end: float,
) -> bool:
    return (
        first_start < second_end - 1e-6
        and first_end > second_start + 1e-6
    )


def _validate_segment_plan(
    item: object,
    *,
    evidence_segment: dict[str, Any],
    record: object,
) -> dict[str, Any]:
    segment_id = str(evidence_segment.get("segment_id"))
    segment = _exact_keys(
        item,
        {
            "segment_id",
            "source_sha256",
            "provider_attempt_id",
            "picture",
            "audio",
            "protected_dialogue_line_ids",
            "reason",
        },
        label=f"{segment_id} plan",
    )
    if segment.get("segment_id") != segment_id:
        raise RepairPlanError(f"Plan Segment order differs at {segment_id}")
    source_hash = _string(
        segment["source_sha256"],
        label=f"{segment_id} source_sha256",
    )
    provider_attempt_id = _string(
        segment["provider_attempt_id"],
        label=f"{segment_id} provider_attempt_id",
    )
    if source_hash != evidence_segment.get("source_sha256"):
        raise RepairPlanError(f"{segment_id} plan source hash is stale")
    if provider_attempt_id != evidence_segment.get("provider_attempt_id"):
        raise RepairPlanError(f"{segment_id} provider attempt is stale")
    source = Path(str(getattr(record, "video_path"))).resolve()
    if source_hash != _sha256_file(source):
        raise RepairPlanError(f"{segment_id} source media changed after evidence")
    duration = float(getattr(getattr(record, "probe"), "duration_seconds"))

    picture = _exact_keys(
        segment["picture"],
        {
            "source_in_seconds",
            "source_out_seconds",
            "removed_intervals",
            "color_adjustments",
        },
        label=f"{segment_id} picture plan",
    )
    picture_in = _number(
        picture["source_in_seconds"],
        label=f"{segment_id} picture source-in",
        minimum=0.0,
        maximum=duration,
    )
    picture_out = _number(
        picture["source_out_seconds"],
        label=f"{segment_id} picture source-out",
        minimum=0.0,
        maximum=duration,
    )
    if picture_out <= picture_in:
        raise RepairPlanError(f"{segment_id} picture source window is empty")
    picture_removed = _validate_removed_intervals(
        picture["removed_intervals"],
        segment_id=segment_id,
        media="picture",
        source_in=picture_in,
        source_out=picture_out,
    )
    picture_ranges = _kept_ranges(
        picture_in,
        picture_out,
        picture_removed,
    )
    color_adjustments = picture["color_adjustments"]
    if not isinstance(color_adjustments, list):
        raise RepairPlanError(f"{segment_id} color_adjustments must be a list")
    for adjustment in color_adjustments:
        validated = _validate_color_adjustment(
            adjustment,
            segment_id=segment_id,
            source_in=picture_in,
            source_out=picture_out,
        )
        if not _one_range_contains(
            picture_ranges,
            float(validated["source_start_seconds"]),
            float(validated["source_end_seconds"]),
        ):
            raise RepairPlanError(
                f"{segment_id} color adjustment intersects removed picture"
            )

    audio = _exact_keys(
        segment["audio"],
        {
            "source_in_seconds",
            "source_out_seconds",
            "removed_intervals",
            "timeline_offset_from_picture_in_seconds",
            "gain_db",
            "fade_in_seconds",
            "fade_out_seconds",
            "gain_adjustments",
        },
        label=f"{segment_id} audio plan",
    )
    audio_in = _number(
        audio["source_in_seconds"],
        label=f"{segment_id} audio source-in",
        minimum=0.0,
        maximum=duration,
    )
    audio_out = _number(
        audio["source_out_seconds"],
        label=f"{segment_id} audio source-out",
        minimum=0.0,
        maximum=duration,
    )
    if audio_out <= audio_in:
        raise RepairPlanError(f"{segment_id} audio source window is empty")
    audio_removed = _validate_removed_intervals(
        audio["removed_intervals"],
        segment_id=segment_id,
        media="audio",
        source_in=audio_in,
        source_out=audio_out,
    )
    audio_ranges = _kept_ranges(audio_in, audio_out, audio_removed)
    audio_duration = sum(end - start for start, end in audio_ranges)
    _number(
        audio["timeline_offset_from_picture_in_seconds"],
        label=f"{segment_id} audio timeline offset",
    )
    _number(audio["gain_db"], label=f"{segment_id} audio gain")
    fade_in = _number(
        audio["fade_in_seconds"],
        label=f"{segment_id} audio fade-in",
        minimum=0.0,
        maximum=audio_duration,
    )
    fade_out = _number(
        audio["fade_out_seconds"],
        label=f"{segment_id} audio fade-out",
        minimum=0.0,
        maximum=audio_duration,
    )
    if fade_in + fade_out > audio_duration + 1e-6:
        raise RepairPlanError(f"{segment_id} audio fades consume the complete event")
    gain_adjustments = audio["gain_adjustments"]
    if not isinstance(gain_adjustments, list):
        raise RepairPlanError(f"{segment_id} gain_adjustments must be a list")
    for adjustment in gain_adjustments:
        validated = _validate_gain_adjustment(
            adjustment,
            segment_id=segment_id,
            source_in=audio_in,
            source_out=audio_out,
        )
        if not _one_range_contains(
            audio_ranges,
            float(validated["source_start_seconds"]),
            float(validated["source_end_seconds"]),
        ):
            raise RepairPlanError(
                f"{segment_id} gain adjustment intersects removed audio"
            )

    evidence_dialogue = evidence_segment.get("dialogue_cues")
    if not isinstance(evidence_dialogue, list):
        raise RepairPlanError(f"{segment_id} evidence dialogue cues are invalid")
    expected_lines: list[str] = []
    for cue in evidence_dialogue:
        if not isinstance(cue, dict):
            raise RepairPlanError(f"{segment_id} evidence dialogue cue is invalid")
        line_id = _string(
            cue.get("line_id"),
            label=f"{segment_id} evidence dialogue line",
        )
        start = _number(
            cue.get("start_seconds"),
            label=f"{segment_id} dialogue start",
        )
        end = _number(
            cue.get("end_seconds"),
            label=f"{segment_id} dialogue end",
        )
        if not _one_range_contains(
            picture_ranges,
            start,
            end,
        ) or not _one_range_contains(audio_ranges, start, end):
            raise RepairPlanError(
                f"{segment_id} edit removes protected dialogue {line_id}"
            )
        retained_start, retained_end = _retained_interval(
            audio_ranges,
            start,
            end,
            label=f"{segment_id} protected dialogue {line_id}",
        )
        if fade_in > 0 and _intervals_overlap(
            retained_start,
            retained_end,
            0.0,
            fade_in,
        ):
            raise RepairPlanError(
                f"{segment_id} audio fade-in overlaps protected dialogue {line_id}"
            )
        if fade_out > 0 and _intervals_overlap(
            retained_start,
            retained_end,
            audio_duration - fade_out,
            audio_duration,
        ):
            raise RepairPlanError(
                f"{segment_id} audio fade-out overlaps protected dialogue {line_id}"
            )
        expected_lines.append(line_id)
    protected = _string_list(
        segment["protected_dialogue_line_ids"],
        label=f"{segment_id} protected dialogue",
    )
    if protected != expected_lines:
        raise RepairPlanError(
            f"{segment_id} must protect every evidence dialogue line in order"
        )
    _string(segment["reason"], label=f"{segment_id} plan reason")
    return segment


def _validate_modification_interval(
    value: object,
    *,
    label: str,
    from_id: str,
    to_id: str,
    evidence_by_id: dict[str, dict[str, Any]],
    scope: str,
) -> dict[str, Any]:
    item = _exact_keys(
        value,
        {"media", "segment_id", "start_seconds", "end_seconds", "reason"},
        label=label,
    )
    media = _string(item["media"], label=f"{label} media")
    if media not in {"picture", "audio", "color"}:
        raise RepairPlanError(f"{label} has unsupported media: {media}")
    segment_id = _string(item["segment_id"], label=f"{label} segment_id")
    if segment_id not in {from_id, to_id}:
        raise RepairPlanError(f"{label} must target one side of its boundary")
    evidence_segment = evidence_by_id[segment_id]
    duration = _number(
        evidence_segment.get("duration_seconds"),
        label=f"{segment_id} evidence duration",
        minimum=0.0,
    )
    start = _number(
        item["start_seconds"],
        label=f"{label} start",
        minimum=0.0,
        maximum=duration,
    )
    end = _number(
        item["end_seconds"],
        label=f"{label} end",
        minimum=0.0,
        maximum=duration,
    )
    if end <= start:
        raise RepairPlanError(f"{label} is empty")
    _string(item["reason"], label=f"{label} reason")
    if scope == "boundary_local":
        if segment_id == from_id:
            allowed_start = duration - BOUNDARY_WINDOW_SECONDS
            allowed_end = duration
        else:
            allowed_start = 0.0
            allowed_end = BOUNDARY_WINDOW_SECONDS
        if start < allowed_start - 1e-6 or end > allowed_end + 1e-6:
            raise RepairPlanError(
                f"{label} exceeds the ±{BOUNDARY_WINDOW_SECONDS:.1f}s "
                "boundary-local modification scope"
            )
    return item


def _validate_boundary_plan(
    item: object,
    *,
    evidence_boundary: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    segment_plan_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    boundary_id = str(evidence_boundary.get("boundary_id"))
    boundary = _exact_keys(
        item,
        {
            "boundary_id",
            "from",
            "to",
            "evidence_boundary_id",
            "decision",
            "scope",
            "picture",
            "audio",
            "modification_intervals",
            "protected_dialogue_line_ids",
            "protected_events",
            "reason",
            "candidates",
        },
        label=f"{boundary_id} plan",
    )
    from_id = str(evidence_boundary.get("from"))
    to_id = str(evidence_boundary.get("to"))
    if (
        boundary.get("boundary_id") != boundary_id
        or boundary.get("evidence_boundary_id") != boundary_id
        or boundary.get("from") != from_id
        or boundary.get("to") != to_id
    ):
        raise RepairPlanError(f"{boundary_id} identity differs from its evidence")
    decision = _string(boundary["decision"], label=f"{boundary_id} decision")
    if decision not in {"no_op", "repair", "regenerate"}:
        raise RepairPlanError(f"{boundary_id} has unsupported decision: {decision}")
    scope = _string(boundary["scope"], label=f"{boundary_id} scope")
    if scope not in {"boundary_local", "segment_scope_review"}:
        raise RepairPlanError(f"{boundary_id} has unsupported scope: {scope}")

    picture = _exact_keys(
        boundary["picture"],
        {"operation", "overlap_seconds"},
        label=f"{boundary_id} picture",
    )
    picture_operation = _string(
        picture["operation"],
        label=f"{boundary_id} picture operation",
    )
    if picture_operation not in {"hard_cut", "dissolve", "fade", "baked_effect"}:
        raise RepairPlanError(
            f"{boundary_id} has unsupported picture operation: {picture_operation}"
        )
    overlap = _number(
        picture["overlap_seconds"],
        label=f"{boundary_id} picture overlap",
        minimum=0.0,
    )
    if picture_operation in {"hard_cut", "baked_effect"} and overlap != 0.0:
        raise RepairPlanError(f"{boundary_id} cut/baked effect cannot overlap")
    if picture_operation in {"dissolve", "fade"} and overlap <= 0.0:
        raise RepairPlanError(f"{boundary_id} dissolve/fade needs explicit overlap")
    picture_ranges_by_id: dict[str, list[tuple[float, float]]] = {}
    for segment_id in (from_id, to_id):
        picture_plan = segment_plan_by_id[segment_id]["picture"]
        picture_ranges = _kept_ranges(
            float(picture_plan["source_in_seconds"]),
            float(picture_plan["source_out_seconds"]),
            picture_plan["removed_intervals"],
        )
        picture_ranges_by_id[segment_id] = picture_ranges
        picture_duration = sum(end - start for start, end in picture_ranges)
        if overlap >= picture_duration:
            raise RepairPlanError(
                f"{boundary_id} overlap consumes {segment_id} picture event"
            )
    if overlap > 0 and (
        picture_ranges_by_id[from_id][-1][1]
        - picture_ranges_by_id[from_id][-1][0]
        < overlap - 1e-6
        or picture_ranges_by_id[to_id][0][1]
        - picture_ranges_by_id[to_id][0][0]
        < overlap - 1e-6
    ):
        raise RepairPlanError(
            f"{boundary_id} transition exceeds a contiguous picture handle"
        )

    audio = _exact_keys(
        boundary["audio"],
        {
            "operation",
            "outgoing_fade_out_seconds",
            "incoming_fade_in_seconds",
        },
        label=f"{boundary_id} audio",
    )
    audio_operation = _string(
        audio["operation"],
        label=f"{boundary_id} audio operation",
    )
    if audio_operation not in {
        "native_cut",
        "soft_cut",
        "crossfade",
        "j_cut",
        "l_cut",
        "ambient_bridge",
        "no_op",
    }:
        raise RepairPlanError(
            f"{boundary_id} has unsupported audio operation: {audio_operation}"
        )
    outgoing_fade = _number(
        audio["outgoing_fade_out_seconds"],
        label=f"{boundary_id} outgoing audio fade",
        minimum=0.0,
    )
    incoming_fade = _number(
        audio["incoming_fade_in_seconds"],
        label=f"{boundary_id} incoming audio fade",
        minimum=0.0,
    )
    if abs(
        outgoing_fade
        - float(segment_plan_by_id[from_id]["audio"]["fade_out_seconds"])
    ) > 1e-9:
        raise RepairPlanError(
            f"{boundary_id} outgoing fade differs from {from_id} audio event"
        )
    if abs(
        incoming_fade
        - float(segment_plan_by_id[to_id]["audio"]["fade_in_seconds"])
    ) > 1e-9:
        raise RepairPlanError(
            f"{boundary_id} incoming fade differs from {to_id} audio event"
        )
    outgoing_picture = segment_plan_by_id[from_id]["picture"]
    outgoing_audio = segment_plan_by_id[from_id]["audio"]
    incoming_audio = segment_plan_by_id[to_id]["audio"]
    outgoing_picture_duration = sum(
        end - start
        for start, end in _kept_ranges(
            float(outgoing_picture["source_in_seconds"]),
            float(outgoing_picture["source_out_seconds"]),
            outgoing_picture["removed_intervals"],
        )
    )
    outgoing_audio_duration = sum(
        end - start
        for start, end in _kept_ranges(
            float(outgoing_audio["source_in_seconds"]),
            float(outgoing_audio["source_out_seconds"]),
            outgoing_audio["removed_intervals"],
        )
    )
    outgoing_audio_end_relative_to_transition = (
        float(outgoing_audio["timeline_offset_from_picture_in_seconds"])
        + outgoing_audio_duration
        - (outgoing_picture_duration - overlap)
    )
    incoming_audio_start_relative_to_transition = float(
        incoming_audio["timeline_offset_from_picture_in_seconds"]
    )
    if audio_operation in {"no_op", "native_cut"} and (
        abs(outgoing_audio_end_relative_to_transition) > 1e-6
        or abs(incoming_audio_start_relative_to_transition) > 1e-6
        or outgoing_fade > 0
        or incoming_fade > 0
    ):
        raise RepairPlanError(
            f"{boundary_id} {audio_operation} must be a zero-offset, zero-fade cut"
        )
    if audio_operation == "soft_cut" and (
        abs(outgoing_audio_end_relative_to_transition) > 1e-6
        or abs(incoming_audio_start_relative_to_transition) > 1e-6
    ):
        raise RepairPlanError(
            f"{boundary_id} soft_cut must keep both native audio events "
            "aligned to a zero-overlap picture seam"
        )
    if (
        audio_operation == "soft_cut"
        and outgoing_fade <= 0
        and incoming_fade <= 0
    ):
        raise RepairPlanError(
            f"{boundary_id} soft_cut requires at least one explicit audio fade"
        )
    if (
        audio_operation == "j_cut"
        and incoming_audio_start_relative_to_transition >= -1e-6
    ):
        raise RepairPlanError(
            f"{boundary_id} j_cut requires incoming audio before picture"
        )
    if (
        audio_operation == "l_cut"
        and outgoing_audio_end_relative_to_transition <= 1e-6
    ):
        raise RepairPlanError(
            f"{boundary_id} l_cut requires outgoing audio after picture"
        )
    if audio_operation == "crossfade" and (
        outgoing_audio_end_relative_to_transition
        <= incoming_audio_start_relative_to_transition + 1e-6
        or outgoing_fade <= 0
        or incoming_fade <= 0
    ):
        raise RepairPlanError(
            f"{boundary_id} crossfade requires real audio overlap and both fades"
        )

    intervals = boundary["modification_intervals"]
    if not isinstance(intervals, list):
        raise RepairPlanError(
            f"{boundary_id} modification_intervals must be a list"
        )
    for index, interval in enumerate(intervals):
        _validate_modification_interval(
            interval,
            label=f"{boundary_id} modification interval {index + 1}",
            from_id=from_id,
            to_id=to_id,
            evidence_by_id=evidence_by_id,
            scope=scope,
        )
    if decision == "no_op" and intervals:
        raise RepairPlanError(
            f"{boundary_id} no_op decision cannot declare modifications"
        )
    if decision == "no_op" and (
        picture_operation != "hard_cut"
        or overlap != 0.0
        or audio_operation != "no_op"
        or outgoing_fade != 0.0
        or incoming_fade != 0.0
    ):
        raise RepairPlanError(
            f"{boundary_id} no_op must preserve a zero-overlap native hard cut"
        )

    expected_protected = [
        *segment_plan_by_id[from_id]["protected_dialogue_line_ids"],
        *segment_plan_by_id[to_id]["protected_dialogue_line_ids"],
    ]
    protected_lines = _string_list(
        boundary["protected_dialogue_line_ids"],
        label=f"{boundary_id} protected dialogue",
    )
    if protected_lines != expected_protected:
        raise RepairPlanError(
            f"{boundary_id} must list protected dialogue from both sides in order"
        )
    _string_list(
        boundary["protected_events"],
        label=f"{boundary_id} protected events",
    )
    _string(boundary["reason"], label=f"{boundary_id} reason")
    _string_list(boundary["candidates"], label=f"{boundary_id} candidates")
    return boundary


def _validate_audio_bridge(
    value: object,
    *,
    evidence_by_id: dict[str, dict[str, Any]],
    boundary_ids: set[str],
) -> dict[str, Any]:
    bridge = _exact_keys(
        value,
        {
            "bridge_id",
            "boundary_id",
            "source_segment_id",
            "source_in_seconds",
            "source_out_seconds",
            "timeline_in_seconds",
            "gain_db",
            "fade_in_seconds",
            "fade_out_seconds",
            "dialogue_free_evidence_ref",
            "reason",
        },
        label="audio bridge",
    )
    bridge_id = _string(bridge["bridge_id"], label="audio bridge ID")
    boundary_id = _string(
        bridge["boundary_id"],
        label=f"{bridge_id} boundary_id",
    )
    if boundary_id not in boundary_ids:
        raise RepairPlanError(f"{bridge_id} references an unknown boundary")
    segment_id = _string(
        bridge["source_segment_id"],
        label=f"{bridge_id} source_segment_id",
    )
    if segment_id not in evidence_by_id:
        raise RepairPlanError(f"{bridge_id} references an unknown source Segment")
    duration = float(evidence_by_id[segment_id]["duration_seconds"])
    source_in = _number(
        bridge["source_in_seconds"],
        label=f"{bridge_id} source-in",
        minimum=0.0,
        maximum=duration,
    )
    source_out = _number(
        bridge["source_out_seconds"],
        label=f"{bridge_id} source-out",
        minimum=0.0,
        maximum=duration,
    )
    if source_out <= source_in:
        raise RepairPlanError(f"{bridge_id} source interval is empty")
    bridge_duration = source_out - source_in
    _number(
        bridge["timeline_in_seconds"],
        label=f"{bridge_id} timeline-in",
        minimum=0.0,
    )
    _number(bridge["gain_db"], label=f"{bridge_id} gain")
    fade_in = _number(
        bridge["fade_in_seconds"],
        label=f"{bridge_id} fade-in",
        minimum=0.0,
        maximum=bridge_duration,
    )
    fade_out = _number(
        bridge["fade_out_seconds"],
        label=f"{bridge_id} fade-out",
        minimum=0.0,
        maximum=bridge_duration,
    )
    if fade_in + fade_out > bridge_duration + 1e-6:
        raise RepairPlanError(f"{bridge_id} fades consume the complete bridge")
    _string(
        bridge["dialogue_free_evidence_ref"],
        label=f"{bridge_id} dialogue-free evidence",
    )
    _string(bridge["reason"], label=f"{bridge_id} reason")
    return bridge


def _interval_covers(
    intervals: list[dict[str, Any]],
    *,
    media: str,
    segment_id: str,
    start_seconds: float,
    end_seconds: float,
) -> bool:
    return any(
        item["media"] == media
        and item["segment_id"] == segment_id
        and float(item["start_seconds"]) <= start_seconds + 1e-6
        and float(item["end_seconds"]) >= end_seconds - 1e-6
        for item in intervals
    )


def _require_interval_coverage(
    intervals: list[dict[str, Any]],
    *,
    media: str,
    segment_id: str,
    start_seconds: float,
    end_seconds: float,
    label: str,
) -> None:
    if end_seconds <= start_seconds + 1e-9:
        return
    if not _interval_covers(
        intervals,
        media=media,
        segment_id=segment_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    ):
        raise RepairPlanError(
            f"{label} is not covered by an explicit model modification interval"
        )


def _validate_declared_modification_coverage(
    plan: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> None:
    """Prove that every actual picture/audio change was explicitly declared."""
    intervals = [
        interval
        for boundary in plan["boundaries"]
        for interval in boundary["modification_intervals"]
    ]
    segment_by_id = {
        str(item["segment_id"]): item for item in plan["segments"]
    }
    for segment_id, segment in segment_by_id.items():
        duration = float(evidence_by_id[segment_id]["duration_seconds"])
        picture = segment["picture"]
        picture_in = float(picture["source_in_seconds"])
        picture_out = float(picture["source_out_seconds"])
        _require_interval_coverage(
            intervals,
            media="picture",
            segment_id=segment_id,
            start_seconds=0.0,
            end_seconds=picture_in,
            label=f"{segment_id} opening picture trim",
        )
        _require_interval_coverage(
            intervals,
            media="picture",
            segment_id=segment_id,
            start_seconds=picture_out,
            end_seconds=duration,
            label=f"{segment_id} closing picture trim",
        )
        for removed in picture["removed_intervals"]:
            _require_interval_coverage(
                intervals,
                media="picture",
                segment_id=segment_id,
                start_seconds=float(removed["source_start_seconds"]),
                end_seconds=float(removed["source_end_seconds"]),
                label=f"{segment_id} internal picture deletion",
            )
        for adjustment in picture["color_adjustments"]:
            _require_interval_coverage(
                intervals,
                media="color",
                segment_id=segment_id,
                start_seconds=float(adjustment["source_start_seconds"]),
                end_seconds=float(adjustment["source_end_seconds"]),
                label=f"{segment_id} color adjustment",
            )

        audio = segment["audio"]
        audio_in = float(audio["source_in_seconds"])
        audio_out = float(audio["source_out_seconds"])
        _require_interval_coverage(
            intervals,
            media="audio",
            segment_id=segment_id,
            start_seconds=0.0,
            end_seconds=audio_in,
            label=f"{segment_id} opening audio trim",
        )
        _require_interval_coverage(
            intervals,
            media="audio",
            segment_id=segment_id,
            start_seconds=audio_out,
            end_seconds=duration,
            label=f"{segment_id} closing audio trim",
        )
        for removed in audio["removed_intervals"]:
            _require_interval_coverage(
                intervals,
                media="audio",
                segment_id=segment_id,
                start_seconds=float(removed["source_start_seconds"]),
                end_seconds=float(removed["source_end_seconds"]),
                label=f"{segment_id} internal audio deletion",
            )
        if abs(float(audio["gain_db"])) > 1e-9:
            _require_interval_coverage(
                intervals,
                media="audio",
                segment_id=segment_id,
                start_seconds=audio_in,
                end_seconds=audio_out,
                label=f"{segment_id} event-wide audio gain",
            )
        for adjustment in audio["gain_adjustments"]:
            _require_interval_coverage(
                intervals,
                media="audio",
                segment_id=segment_id,
                start_seconds=float(adjustment["source_start_seconds"]),
                end_seconds=float(adjustment["source_end_seconds"]),
                label=f"{segment_id} local audio gain",
            )

    for boundary in plan["boundaries"]:
        if boundary["decision"] != "repair":
            continue
        from_id = str(boundary["from"])
        to_id = str(boundary["to"])
        overlap = float(boundary["picture"]["overlap_seconds"])
        if overlap > 0:
            outgoing_picture = segment_by_id[from_id]["picture"]
            incoming_picture = segment_by_id[to_id]["picture"]
            _require_interval_coverage(
                intervals,
                media="picture",
                segment_id=from_id,
                start_seconds=float(outgoing_picture["source_out_seconds"]) - overlap,
                end_seconds=float(outgoing_picture["source_out_seconds"]),
                label=f"{boundary['boundary_id']} outgoing picture overlap",
            )
            _require_interval_coverage(
                intervals,
                media="picture",
                segment_id=to_id,
                start_seconds=float(incoming_picture["source_in_seconds"]),
                end_seconds=float(incoming_picture["source_in_seconds"]) + overlap,
                label=f"{boundary['boundary_id']} incoming picture overlap",
            )
        outgoing_fade = float(
            boundary["audio"]["outgoing_fade_out_seconds"]
        )
        incoming_fade = float(
            boundary["audio"]["incoming_fade_in_seconds"]
        )
        if outgoing_fade > 0:
            outgoing_audio = segment_by_id[from_id]["audio"]
            _require_interval_coverage(
                intervals,
                media="audio",
                segment_id=from_id,
                start_seconds=float(outgoing_audio["source_out_seconds"])
                - outgoing_fade,
                end_seconds=float(outgoing_audio["source_out_seconds"]),
                label=f"{boundary['boundary_id']} outgoing audio fade",
            )
        if incoming_fade > 0:
            incoming_audio = segment_by_id[to_id]["audio"]
            _require_interval_coverage(
                intervals,
                media="audio",
                segment_id=to_id,
                start_seconds=float(incoming_audio["source_in_seconds"]),
                end_seconds=float(incoming_audio["source_in_seconds"])
                + incoming_fade,
                label=f"{boundary['boundary_id']} incoming audio fade",
            )


def _validate_delivery(value: object) -> dict[str, Any]:
    delivery = _exact_keys(
        value,
        {
            "video_codec",
            "preset",
            "crf",
            "pixel_format",
            "audio_codec",
            "audio_bitrate",
            "sample_rate_hz",
            "channel_layout",
        },
        label="delivery plan",
    )
    if _string(delivery["video_codec"], label="delivery video codec") != "libx264":
        raise RepairPlanError("Renderer supports only explicit libx264 delivery")
    _string(delivery["preset"], label="delivery preset")
    _number(delivery["crf"], label="delivery CRF", minimum=0.0, maximum=51.0)
    if _string(delivery["pixel_format"], label="delivery pixel format") != "yuv420p":
        raise RepairPlanError("Renderer supports only explicit yuv420p delivery")
    if _string(delivery["audio_codec"], label="delivery audio codec") != "aac":
        raise RepairPlanError("Renderer supports only explicit AAC delivery")
    _string(delivery["audio_bitrate"], label="delivery audio bitrate")
    _number(
        delivery["sample_rate_hz"],
        label="delivery sample rate",
        minimum=8000.0,
    )
    if _string(delivery["channel_layout"], label="delivery channel layout") != "stereo":
        raise RepairPlanError("Renderer supports only explicit stereo delivery")
    return delivery


def load_repair_plan(
    plan_path: Path,
    evidence_path: Path,
    records: list[object],
) -> dict[str, Any]:
    """Load and strictly validate a complete model-authored repair plan."""
    plan_path = plan_path.expanduser().resolve()
    evidence_path = evidence_path.expanduser().resolve()
    plan = _exact_keys(
        _load_json(plan_path, label="LLM repair plan"),
        {
            "contract",
            "evidence_manifest_sha256",
            "source_set_sha256",
            "decision_authority",
            "observation_window",
            "segments",
            "boundaries",
            "audio_bridges",
            "terminal_audio",
            "delivery",
            "overall_reason",
        },
        label="LLM repair plan",
    )
    evidence = _load_json(evidence_path, label="finish evidence manifest")
    if plan.get("contract") != PLAN_CONTRACT:
        raise RepairPlanError("Unsupported LLM repair-plan contract")
    if evidence.get("contract") != EVIDENCE_CONTRACT:
        raise RepairPlanError("Unsupported finish evidence contract")
    if (
        evidence.get("coverage") != "complete_task"
        or evidence.get("render_authorization") is not True
    ):
        raise RepairPlanError(
            "Preview-prefix evidence cannot authorize candidate or final rendering"
        )
    if plan.get("decision_authority") != DECISION_AUTHORITY:
        raise RepairPlanError("Repair plan lacks Editor/Restoration Master authority")
    if plan.get("evidence_manifest_sha256") != _sha256_file(evidence_path):
        raise RepairPlanError("Repair plan references stale evidence")
    if plan.get("source_set_sha256") != evidence.get("source_set_sha256"):
        raise RepairPlanError("Repair plan source set differs from evidence")
    _validate_observation_window(
        plan["observation_window"],
        evidence.get("observation_window"),
    )

    evidence_segments = _ordered_evidence_segments(evidence)
    evidence_ids = [str(item.get("segment_id")) for item in evidence_segments]
    record_ids = [str(getattr(record, "segment_name")) for record in records]
    if evidence_ids != record_ids:
        raise RepairPlanError("Evidence Segment coverage differs from current media")
    segment_plans = plan["segments"]
    if not isinstance(segment_plans, list) or len(segment_plans) != len(records):
        raise RepairPlanError("Repair plan Segment coverage is incomplete")
    validated_segments = [
        _validate_segment_plan(
            item,
            evidence_segment=evidence_segment,
            record=record,
        )
        for item, evidence_segment, record in zip(
            segment_plans,
            evidence_segments,
            records,
        )
    ]
    segment_plan_by_id = {
        str(item["segment_id"]): item for item in validated_segments
    }
    evidence_by_id = {
        str(item["segment_id"]): item for item in evidence_segments
    }

    evidence_boundaries = evidence.get("boundaries")
    boundary_plans = plan["boundaries"]
    if (
        not isinstance(evidence_boundaries, list)
        or not isinstance(boundary_plans, list)
        or len(evidence_boundaries) != max(0, len(records) - 1)
        or len(boundary_plans) != len(evidence_boundaries)
    ):
        raise RepairPlanError("Repair plan boundary coverage is incomplete")
    for item, evidence_boundary in zip(boundary_plans, evidence_boundaries):
        if not isinstance(evidence_boundary, dict):
            raise RepairPlanError("Evidence boundary is invalid")
        _validate_boundary_plan(
            item,
            evidence_boundary=evidence_boundary,
            evidence_by_id=evidence_by_id,
            segment_plan_by_id=segment_plan_by_id,
        )
    _validate_declared_modification_coverage(plan, evidence_by_id)

    bridges = plan["audio_bridges"]
    if not isinstance(bridges, list):
        raise RepairPlanError("audio_bridges must be a list")
    bridge_ids: list[str] = []
    boundary_ids = {
        str(item["boundary_id"]) for item in plan["boundaries"]
    }
    for value in bridges:
        bridge = _validate_audio_bridge(
            value,
            evidence_by_id=evidence_by_id,
            boundary_ids=boundary_ids,
        )
        bridge_ids.append(str(bridge["bridge_id"]))
    if len(bridge_ids) != len(set(bridge_ids)):
        raise RepairPlanError("audio_bridges contains duplicate IDs")
    bridges_by_boundary = {
        str(item["boundary_id"]) for item in bridges
    }
    for boundary in plan["boundaries"]:
        expects_bridge = boundary["audio"]["operation"] == "ambient_bridge"
        has_bridge = str(boundary["boundary_id"]) in bridges_by_boundary
        if expects_bridge != has_bridge:
            raise RepairPlanError(
                f"{boundary['boundary_id']} ambient-bridge operation and "
                "audio_bridges coverage differ"
            )

    terminal = _exact_keys(
        plan["terminal_audio"],
        {"segment_id", "fade_out_seconds", "reason"},
        label="terminal audio plan",
    )
    if terminal.get("segment_id") != evidence_ids[-1]:
        raise RepairPlanError("Terminal audio plan must name the final Segment")
    final_segment = segment_plan_by_id[evidence_ids[-1]]
    final_picture = final_segment["picture"]
    final_picture_ranges = _kept_ranges(
        float(final_picture["source_in_seconds"]),
        float(final_picture["source_out_seconds"]),
        final_picture["removed_intervals"],
    )
    final_picture_duration = sum(
        end - start for start, end in final_picture_ranges
    )
    terminal_fade = _number(
        terminal["fade_out_seconds"],
        label="terminal audio fade",
        minimum=0.0,
        maximum=final_picture_duration,
    )
    if terminal_fade > 0:
        final_audio = final_segment["audio"]
        final_audio_ranges = _kept_ranges(
            float(final_audio["source_in_seconds"]),
            float(final_audio["source_out_seconds"]),
            final_audio["removed_intervals"],
        )
        audio_offset = float(
            final_audio["timeline_offset_from_picture_in_seconds"]
        )
        terminal_start = final_picture_duration - terminal_fade
        for cue in evidence_by_id[evidence_ids[-1]]["dialogue_cues"]:
            line_id = str(cue["line_id"])
            retained_start, retained_end = _retained_interval(
                final_audio_ranges,
                float(cue["start_seconds"]),
                float(cue["end_seconds"]),
                label=f"{evidence_ids[-1]} protected dialogue {line_id}",
            )
            if _intervals_overlap(
                audio_offset + retained_start,
                audio_offset + retained_end,
                terminal_start,
                final_picture_duration,
            ):
                raise RepairPlanError(
                    "Terminal audio fade overlaps protected dialogue "
                    f"{line_id}"
                )
    _string(terminal["reason"], label="terminal audio reason")
    _validate_delivery(plan["delivery"])
    _string(plan["overall_reason"], label="overall repair-plan reason")
    return plan


def ensure_renderable(plan: dict[str, Any]) -> None:
    """Block rendering when the model explicitly requires regeneration."""
    blocked = [
        str(item["boundary_id"])
        for item in plan["boundaries"]
        if item["decision"] == "regenerate"
    ]
    if blocked:
        raise RepairPlanError(
            "Model repair plan requires source regeneration at: "
            + ", ".join(blocked)
        )
