"""Measure Boundary frame statistics and derive bounded repair plans."""

from __future__ import annotations

from collections.abc import Iterable
import math
from pathlib import Path
from typing import Any

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
    boundary: dict[str, Any],
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
    outgoing_source_out = float(boundary["outgoing_source_out_seconds"])
    incoming_source_in = float(boundary["incoming_source_in_seconds"])
    if (
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
