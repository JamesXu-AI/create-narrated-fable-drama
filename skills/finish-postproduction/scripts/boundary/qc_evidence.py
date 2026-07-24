"""Render strict seam media, frame evidence, and reversible candidates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .qc_metrics import repair_lut_filter
from .qc_policy import BoundaryQCError, _run


def _boundary_directory(root: Path, boundary: dict[str, Any]) -> Path:
    return root / f"{boundary['from']}--{boundary['to']}"


def _render_strict_sample(
    outgoing: object,
    incoming: object,
    boundary: dict[str, Any],
    output: Path,
    config: dict[str, Any],
) -> None:
    strict = config["strict_sample"]
    frame_rate = int(strict["frame_rate"])
    tail = float(strict["tail_seconds"])
    head = float(strict["head_seconds"])
    outgoing_probe = getattr(outgoing, "probe")
    incoming_probe = getattr(incoming, "probe")
    width = int(getattr(outgoing_probe, "width"))
    height = int(getattr(outgoing_probe, "height"))
    if width <= 0 or height <= 0:
        raise BoundaryQCError("Strict seam source has invalid dimensions")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(Path(getattr(outgoing, "video_path"))),
        "-i",
        str(Path(getattr(incoming, "video_path"))),
    ]
    filters: list[str] = []
    picture_edit = str(boundary.get("picture_edit"))
    overlap = float(boundary.get("overlap_seconds") or 0.0)
    outgoing_source_out = float(
        boundary.get(
            "outgoing_source_out_seconds",
            getattr(outgoing_probe, "duration_seconds"),
        )
    )
    incoming_source_in = float(boundary.get("incoming_source_in_seconds") or 0.0)
    if picture_edit in {"dissolve", "fade"}:
        handle = 1.0 + overlap / 2.0
        outgoing_start = max(0.0, outgoing_source_out - handle)
        filters.extend(
            [
                f"[0:v]trim=start={outgoing_start:.6f}:duration={handle:.6f},"
                f"setpts=PTS-STARTPTS,fps={frame_rate},scale={width}:{height},"
                "setsar=1,format=yuv420p[v0]",
                f"[1:v]trim=start={incoming_source_in:.6f}:duration={handle:.6f},setpts=PTS-STARTPTS,"
                f"fps={frame_rate},scale={width}:{height},setsar=1,format=yuv420p[v1]",
                f"[0:a]atrim=start={outgoing_start:.6f}:duration={handle:.6f},"
                "asetpts=PTS-STARTPTS,aresample=48000,"
                "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a0]",
                f"[1:a]atrim=start={incoming_source_in:.6f}:duration={handle:.6f},asetpts=PTS-STARTPTS,"
                "aresample=48000,"
                "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a1]",
            ]
        )
        transition = "fade" if picture_edit == "dissolve" else "fadeblack"
        offset = handle - overlap
        filters.extend(
            [
                f"[v0][v1]xfade=transition={transition}:duration={overlap:.6f}:"
                f"offset={offset:.6f},fps={frame_rate},"
                f"tpad=stop_mode=clone:stop_duration={1.0 / frame_rate:.6f},"
                f"trim=end_frame={strict['frame_count']},setpts=PTS-STARTPTS[vout]",
                f"[a0][a1]acrossfade=d={overlap:.6f}:c1=qsin:c2=qsin[aout]",
            ]
        )
    else:
        outgoing_start = max(0.0, outgoing_source_out - tail)
        filters.extend(
            [
                f"[0:v]trim=start={outgoing_start:.6f}:duration={tail:.6f},"
                f"setpts=PTS-STARTPTS,fps={frame_rate},scale={width}:{height},"
                "setsar=1,format=yuv420p[v0]",
                f"[1:v]trim=start={incoming_source_in:.6f}:duration={head:.6f},setpts=PTS-STARTPTS,"
                f"fps={frame_rate},scale={width}:{height},setsar=1,format=yuv420p[v1]",
                f"[0:a]atrim=start={outgoing_start:.6f}:duration={tail:.6f},"
                "asetpts=PTS-STARTPTS,aresample=48000,"
                "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a0]",
                f"[1:a]atrim=start={incoming_source_in:.6f}:duration={head:.6f},asetpts=PTS-STARTPTS,"
                "aresample=48000,"
                "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a1]",
                f"[v0][v1]concat=n=2:v=1:a=0,fps={frame_rate},"
                f"tpad=stop_mode=clone:stop_duration={1.0 / frame_rate:.6f},"
                f"trim=end_frame={strict['frame_count']},setpts=PTS-STARTPTS[vout]",
                "[a0][a1]concat=n=2:v=0:a=1[aout]",
            ]
        )
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-frames:v",
            str(strict["frame_count"]),
            "-t",
            "2.000000",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    _run(command, label=f"Strict seam render {boundary['from']}->{boundary['to']}")


def _extract_frame_evidence(
    sample: Path,
    directory: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    strict = config["strict_sample"]
    frame_rate = int(strict["frame_rate"])
    frame_count = int(strict["frame_count"])
    evidence_width = int(strict["evidence_frame_width"])
    frames_dir = directory / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale in frames_dir.glob("frame-*.png"):
        stale.unlink()
    pattern = frames_dir / "frame-%06d.png"
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(sample),
            "-vf",
            f"fps={frame_rate},scale={evidence_width}:-2:flags=lanczos",
            "-frames:v",
            str(frame_count),
            str(pattern),
        ],
        label="Strict seam frame extraction",
    )
    frames = sorted(frames_dir.glob("frame-*.png"))
    if len(frames) != frame_count:
        raise BoundaryQCError(
            f"Strict seam must decode to {frame_count} frames, found {len(frames)}"
        )
    manifest = {
        "contract": "finish-boundary-frame-manifest/v1",
        "sample": str(sample.resolve()),
        "frame_rate": frame_rate,
        "frame_count": frame_count,
        "frames": [
            {
                "frame_index": index,
                "timestamp_seconds": round(index / frame_rate, 6),
                "path": str(path.resolve()),
            }
            for index, path in enumerate(frames)
        ],
    }
    manifest_path = directory / "frame-manifest.json"
    _write_json(manifest_path, manifest)
    contact_sheet = directory / "contact-sheet-48.jpg"
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(sample),
            "-vf",
            f"fps={frame_rate},scale=320:-2:flags=lanczos,"
            "tile=8x6:padding=2:margin=2:color=black",
            "-frames:v",
            "1",
            str(contact_sheet),
        ],
        label="Strict seam contact sheet render",
    )
    return {
        "sample": str(sample.resolve()),
        "frame_manifest": str(manifest_path.resolve()),
        "contact_sheet": str(contact_sheet.resolve()),
        "frames_directory": str(frames_dir.resolve()),
        "frame_count": frame_count,
    }


def _render_repaired_sample(
    source: Path,
    output: Path,
    plan: dict[str, Any],
    *,
    strength: float,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fade = float(plan["fade_seconds"])
    correction_end = 1.0 + fade
    weight = (
        f"if(gte(T,1.000000),"
        f"max(0,min(1,({correction_end:.6f}-T)/{fade:.6f})),0)"
    )
    filters = (
        "[0:v]split=2[original][gradeinput];"
        f"[gradeinput]{repair_lut_filter(plan, strength=strength)}[graded];"
        f"[original][graded]blend=all_expr='A+(B-A)*{weight}'[vout]"
    )
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            filters,
            "-map",
            "[vout]",
            "-map",
            "0:a:0?",
            "-frames:v",
            "48",
            "-t",
            "2.000000",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ],
        label="Boundary repair candidate render",
    )


def _render_comparison(original: Path, repaired: Path, output: Path) -> None:
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(original),
            "-i",
            str(repaired),
            "-filter_complex",
            "[0:v]scale=960:-2[left];[1:v]scale=960:-2[right];"
            "[left][right]hstack=inputs=2[vout]",
            "-map",
            "[vout]",
            "-map",
            "0:a:0?",
            "-t",
            "2.000000",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ],
        label="Original/repaired boundary comparison render",
    )


def _matches_selected(boundary: dict[str, Any], selected: str | None) -> bool:
    if not selected:
        return True
    normalized = selected.replace("->", ":")
    return normalized == f"{boundary['from']}:{boundary['to']}"
