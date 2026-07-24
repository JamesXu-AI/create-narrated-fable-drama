"""Measure Boundary frame statistics and derive bounded repair plans."""

from __future__ import annotations

from collections.abc import Iterable
import math
from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.boundary import (
    AUTOMATIC_COLOR_MATCH_PICTURE_EDIT_MODES,
    COLOR_MATCH_EXCLUDED_BOUNDARY_CLASSES,
)
from .qc_policy import BoundaryQCError
from narrated_fable_drama.media.ffmpeg import MediaCommandError, run


def _analysis_geometry(record: object, width: int) -> tuple[int, int]:
    probe = getattr(record, "probe")
    source_width = int(getattr(probe, "width"))
    source_height = int(getattr(probe, "height"))
    if source_width <= 0 or source_height <= 0:
        raise BoundaryQCError("Boundary source has invalid dimensions")
    height = max(2, round(source_height * width / source_width))
    height += height % 2
    return width, height


def _extract_yuv_frames(
    path: Path,
    *,
    start_seconds: float,
    frame_count: int,
    frame_rate: int,
    width: int,
    height: int,
) -> list[tuple[bytes, bytes, bytes]]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{max(0.0, start_seconds):.6f}",
        "-i",
        str(path),
        "-vf",
        f"fps={frame_rate},scale={width}:{height}:flags=area,format=yuv444p",
        "-frames:v",
        str(frame_count),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "yuv444p",
        "pipe:1",
    ]
    try:
        result = run(
            command,
            context=f"Boundary frame analysis {path}",
            text=False,
        )
    except MediaCommandError as exc:
        raise BoundaryQCError(f"Could not analyze boundary frames: {path}") from exc
    plane_size = width * height
    frame_size = plane_size * 3
    decoded = len(result.stdout) // frame_size
    if decoded != frame_count or len(result.stdout) != frame_count * frame_size:
        raise BoundaryQCError(
            f"Expected {frame_count} analysis frames from {path}, decoded {decoded}"
        )
    frames: list[tuple[bytes, bytes, bytes]] = []
    for index in range(frame_count):
        offset = index * frame_size
        frame = result.stdout[offset : offset + frame_size]
        frames.append(
            (
                frame[:plane_size],
                frame[plane_size : plane_size * 2],
                frame[plane_size * 2 :],
            )
        )
    return frames


def _extract_tail_yuv_frames(
    path: Path,
    *,
    frame_count: int,
    frame_rate: int,
    width: int,
    height: int,
) -> list[tuple[bytes, bytes, bytes]]:
    """Decode the exact final frames without relying on container-duration rounding."""
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-vf",
        f"fps={frame_rate},scale={width}:{height}:flags=area,format=yuv444p,"
        f"reverse,trim=end_frame={frame_count},reverse",
        "-frames:v",
        str(frame_count),
        "-f",
        "rawvideo",
        "-pix_fmt",
        "yuv444p",
        "pipe:1",
    ]
    try:
        result = run(
            command,
            context=f"Final Boundary frame analysis {path}",
            text=False,
        )
    except MediaCommandError as exc:
        raise BoundaryQCError(f"Could not analyze final boundary frames: {path}") from exc
    plane_size = width * height
    frame_size = plane_size * 3
    decoded = len(result.stdout) // frame_size
    if decoded != frame_count or len(result.stdout) != frame_count * frame_size:
        raise BoundaryQCError(
            f"Expected {frame_count} final analysis frames from {path}, decoded {decoded}"
        )
    return [
        (
            result.stdout[offset : offset + plane_size],
            result.stdout[offset + plane_size : offset + plane_size * 2],
            result.stdout[offset + plane_size * 2 : offset + frame_size],
        )
        for offset in range(0, len(result.stdout), frame_size)
    ]


def _plane_stats(frames: Iterable[tuple[bytes, bytes, bytes]]) -> dict[str, Any]:
    materialized = list(frames)
    if not materialized:
        raise BoundaryQCError("Cannot measure an empty frame set")
    y_plane = b"".join(frame[0] for frame in materialized)
    u_plane = b"".join(frame[1] for frame in materialized)
    v_plane = b"".join(frame[2] for frame in materialized)
    ordered_y = sorted(y_plane)
    sample_count = len(y_plane)
    u_mean = sum(u_plane) / sample_count
    v_mean = sum(v_plane) / sample_count
    saturation = sum(
        math.hypot(u_value - 128, v_value - 128)
        for u_value, v_value in zip(u_plane, v_plane)
    ) / sample_count
    frame_means = [sum(frame[0]) / len(frame[0]) for frame in materialized]
    return {
        "luma_q10": ordered_y[int(sample_count * 0.10)],
        "luma_mean": round(sum(y_plane) / sample_count, 6),
        "luma_q90": ordered_y[int(sample_count * 0.90)],
        "u_mean": round(u_mean, 6),
        "v_mean": round(v_mean, 6),
        "saturation_mean": round(saturation, 6),
        "hue_degrees": round(
            math.degrees(math.atan2(v_mean - 128, u_mean - 128)),
            6,
        ),
        "per_frame_luma_mean": [round(value, 6) for value in frame_means],
    }


def _normalized_luma_correlation(left: bytes, right: bytes) -> float:
    if len(left) != len(right) or not left:
        raise BoundaryQCError("Cannot compare differently sized boundary frames")
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = 0.0
    left_energy = 0.0
    right_energy = 0.0
    for left_value, right_value in zip(left, right):
        left_centered = left_value - left_mean
        right_centered = right_value - right_mean
        numerator += left_centered * right_centered
        left_energy += left_centered * left_centered
        right_energy += right_centered * right_centered
    denominator = math.sqrt(left_energy * right_energy)
    if denominator <= 1e-12:
        return 0.0
    return max(-1.0, min(1.0, numerator / denominator))


def measure_boundary(
    outgoing: object,
    incoming: object,
    config: dict[str, Any],
    boundary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Measure a short robust endpoint window without making a picture verdict."""
    analysis = config["analysis"]
    strict = config["strict_sample"]
    width, height = _analysis_geometry(outgoing, int(analysis["width"]))
    frame_count = int(analysis["anchor_frame_count"])
    frame_rate = int(strict["frame_rate"])
    outgoing_path = Path(getattr(outgoing, "video_path"))
    incoming_path = Path(getattr(incoming, "video_path"))
    outgoing_probe = getattr(outgoing, "probe")
    incoming_probe = getattr(incoming, "probe")
    outgoing_source_out = float(
        (boundary or {}).get(
            "outgoing_source_out_seconds",
            getattr(outgoing_probe, "duration_seconds"),
        )
    )
    incoming_source_in = float(
        (boundary or {}).get("incoming_source_in_seconds", 0.0)
    )
    if boundary is None or (
        abs(outgoing_source_out - float(getattr(outgoing_probe, "duration_seconds")))
        < 1e-9
        and incoming_source_in == 0.0
    ):
        outgoing_frames = _extract_tail_yuv_frames(
            outgoing_path,
            frame_count=frame_count,
            frame_rate=frame_rate,
            width=width,
            height=height,
        )
    else:
        outgoing_frames = _extract_yuv_frames(
            outgoing_path,
            start_seconds=max(0.0, outgoing_source_out - frame_count / frame_rate),
            frame_count=frame_count,
            frame_rate=frame_rate,
            width=width,
            height=height,
        )
    incoming_frames = _extract_yuv_frames(
        incoming_path,
        start_seconds=incoming_source_in,
        frame_count=frame_count,
        frame_rate=frame_rate,
        width=width,
        height=height,
    )
    outgoing_stats = _plane_stats(outgoing_frames)
    incoming_stats = _plane_stats(incoming_frames)
    saturation_factor = outgoing_stats["saturation_mean"] / max(
        1e-6, incoming_stats["saturation_mean"]
    )
    delta_u = outgoing_stats["u_mean"] - incoming_stats["u_mean"]
    delta_v = outgoing_stats["v_mean"] - incoming_stats["v_mean"]
    return {
        "analysis_role": "technical_detection_evidence_only",
        "analysis_frame_width": width,
        "analysis_frame_height": height,
        "analysis_frame_count_per_side": frame_count,
        "outgoing_source_out_seconds": round(outgoing_source_out, 6),
        "incoming_source_in_seconds": round(incoming_source_in, 6),
        "outgoing": outgoing_stats,
        "incoming": incoming_stats,
        "delta_target_minus_incoming": {
            "luma_q10": round(
                outgoing_stats["luma_q10"] - incoming_stats["luma_q10"], 6
            ),
            "luma_mean": round(
                outgoing_stats["luma_mean"] - incoming_stats["luma_mean"], 6
            ),
            "luma_q90": round(
                outgoing_stats["luma_q90"] - incoming_stats["luma_q90"], 6
            ),
            "u_mean": round(delta_u, 6),
            "v_mean": round(delta_v, 6),
            "chroma_center_distance": round(math.hypot(delta_u, delta_v), 6),
            "saturation_factor": round(saturation_factor, 6),
            "saturation_ratio_delta": round(saturation_factor - 1.0, 6),
        },
        "luma_shape_correlation": round(
            _normalized_luma_correlation(
                outgoing_frames[-1][0], incoming_frames[0][0]
            ),
            6,
        ),
    }


def _has_detectable_mismatch(
    metrics: dict[str, Any], config: dict[str, Any]
) -> bool:
    delta = metrics["delta_target_minus_incoming"]
    threshold = config["detection"]
    return any(
        (
            abs(float(delta["luma_mean"])) >= float(threshold["mean_luma_delta"]),
            abs(float(delta["luma_q10"])) >= float(threshold["shadow_luma_delta"]),
            abs(float(delta["luma_q90"]))
            >= float(threshold["highlight_luma_delta"]),
            abs(float(delta["saturation_ratio_delta"]))
            >= float(threshold["saturation_ratio_delta"]),
            float(delta["chroma_center_distance"])
            >= float(threshold["chroma_center_distance"]),
        )
    )


def build_repair_plan(metrics: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    incoming = metrics["incoming"]
    delta = metrics["delta_target_minus_incoming"]
    saturation_factor = float(delta["saturation_factor"])
    u_shift = float(metrics["outgoing"]["u_mean"]) - (
        128.0 + (float(incoming["u_mean"]) - 128.0) * saturation_factor
    )
    v_shift = float(metrics["outgoing"]["v_mean"]) - (
        128.0 + (float(incoming["v_mean"]) - 128.0) * saturation_factor
    )
    return {
        "contract": "finish-boundary-color-repair/v1",
        "repair_scope": "incoming_luma_chroma_only",
        "source_mutation": False,
        "fade_seconds": float(config["repair"]["fade_seconds"]),
        "incoming_luma_knots": {
            "q10": float(incoming["luma_q10"]),
            "mean": float(incoming["luma_mean"]),
            "q90": float(incoming["luma_q90"]),
        },
        "luma_delta": {
            "q10": float(delta["luma_q10"]),
            "mean": float(delta["luma_mean"]),
            "q90": float(delta["luma_q90"]),
        },
        "saturation_factor": round(saturation_factor, 6),
        "u_shift": round(u_shift, 6),
        "v_shift": round(v_shift, 6),
    }


def _repair_is_safe(plan: dict[str, Any], config: dict[str, Any]) -> bool:
    limits = config["safe_limits"]
    luma = plan["luma_delta"]
    return all(
        (
            abs(float(luma["mean"])) <= float(limits["mean_luma_delta"]),
            abs(float(luma["q10"])) <= float(limits["quantile_luma_delta"]),
            abs(float(luma["q90"])) <= float(limits["quantile_luma_delta"]),
            float(limits["minimum_saturation_factor"])
            <= float(plan["saturation_factor"])
            <= float(limits["maximum_saturation_factor"]),
            abs(float(plan["u_shift"])) <= float(limits["maximum_chroma_shift"]),
            abs(float(plan["v_shift"])) <= float(limits["maximum_chroma_shift"]),
        )
    )


def triage_boundary(
    boundary: dict[str, Any],
    metrics: dict[str, Any],
    config: dict[str, Any],
) -> tuple[str, str, dict[str, Any] | None]:
    """Return technical routing only, never a semantic approval decision."""
    if boundary.get("transition_class") in COLOR_MATCH_EXCLUDED_BOUNDARY_CLASSES:
        return (
            "authored_transition_evidence_only",
            "Authored transition or scene change is not eligible for automatic color matching.",
            None,
        )
    if boundary.get("picture_edit") not in AUTOMATIC_COLOR_MATCH_PICTURE_EDIT_MODES:
        return (
            "non_cut_evidence_only",
            "Only a hard cut can receive an automatic boundary color correction.",
            None,
        )
    similarity = float(metrics["luma_shape_correlation"])
    minimum = float(config["analysis"]["minimum_match_similarity"])
    if similarity < minimum:
        return (
            "authored_cut_no_auto_match",
            "The two sides are not a high-confidence visual match; color difference may be authored.",
            None,
        )
    if not _has_detectable_mismatch(metrics, config):
        return (
            "no_technical_correction_needed",
            "High-confidence visual match is already inside the technical detection thresholds.",
            None,
        )
    plan = build_repair_plan(metrics, config)
    if not _repair_is_safe(plan, config):
        return (
            "review_required",
            "The matched boundary exceeds the narrow automatic color-repair limits.",
            plan,
        )
    if not config["auto_apply_safe_color_match"]:
        return (
            "repair_candidate_review_required",
            "A safe correction candidate exists, but automatic application is disabled.",
            plan,
        )
    return (
        "safe_color_match_planned",
        "A high-confidence matched cut has a small correctable luma/chroma discrepancy.",
        plan,
    )


def _piecewise_luma_expression(plan: dict[str, Any], strength: float) -> str:
    knots = plan["incoming_luma_knots"]
    x1 = max(1.0, min(252.0, float(knots["q10"])))
    x2 = max(x1 + 1.0, min(253.0, float(knots["mean"])))
    x3 = max(x2 + 1.0, min(254.0, float(knots["q90"])))
    delta = plan["luma_delta"]
    d1 = float(delta["q10"]) * strength
    d2 = float(delta["mean"]) * strength
    d3 = float(delta["q90"]) * strength
    expression = (
        f"if(lt(val,{x1:.6f}),val+({d1:.6f})*val/{x1:.6f},"
        f"if(lt(val,{x2:.6f}),val+({d1:.6f})+"
        f"(({d2:.6f})-({d1:.6f}))*(val-{x1:.6f})/{x2 - x1:.6f},"
        f"if(lt(val,{x3:.6f}),val+({d2:.6f})+"
        f"(({d3:.6f})-({d2:.6f}))*(val-{x2:.6f})/{x3 - x2:.6f},"
        f"val+({d3:.6f})*(255-val)/{255.0 - x3:.6f})))"
    )
    return f"clip({expression},0,255)"


def repair_lut_filter(plan: dict[str, Any], *, strength: float = 1.0) -> str:
    saturation = 1.0 + (float(plan["saturation_factor"]) - 1.0) * strength
    u_shift = float(plan["u_shift"]) * strength
    v_shift = float(plan["v_shift"]) * strength
    y_expression = _piecewise_luma_expression(plan, strength)
    u_expression = f"clip(128+(val-128)*{saturation:.6f}+({u_shift:.6f}),0,255)"
    v_expression = f"clip(128+(val-128)*{saturation:.6f}+({v_shift:.6f}),0,255)"
    return (
        f"lutyuv=y='{y_expression}':u='{u_expression}':v='{v_expression}'"
    )


def append_segment_repair_filter(
    filters: list[str],
    *,
    input_label: str,
    output_label: str,
    label_prefix: str,
    plan: dict[str, Any],
) -> None:
    """Append a boundary-local correction that decays from the Segment opening."""
    original = f"{label_prefix}original"
    grade_input = f"{label_prefix}gradeinput"
    graded = f"{label_prefix}graded"
    fade = float(plan["fade_seconds"])
    filters.append(f"[{input_label}]split=2[{original}][{grade_input}]")
    filters.append(f"[{grade_input}]{repair_lut_filter(plan)}[{graded}]")
    blend = f"max(0,min(1,({fade:.6f}-T)/{fade:.6f}))"
    filters.append(
        f"[{original}][{graded}]blend=all_expr='A+(B-A)*{blend}'[{output_label}]"
    )
