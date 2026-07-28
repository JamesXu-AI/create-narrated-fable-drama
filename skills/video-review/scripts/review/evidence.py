"""Prepare deterministic media evidence for the Seedance Video Review Skill.

This tool performs media operations only. It never approves or rejects a Scene.
Boundary previews honor the authored editorial transition so semantic review is not
performed against a fabricated hard cut when the film calls for a dissolve or fade.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

from narrated_fable_drama.contracts.boundary import (
    BoundaryExecutionError,
    REVIEW_CUT_LIKE_TRANSITION_TYPES,
    REVIEW_DISSOLVE_TRANSITION_TYPES,
    REVIEW_FADE_TRANSITION_TYPES,
    SUPPORTED_REVIEW_TRANSITION_TYPES,
    classify_review_transition,
)
from review.media_evidence import (
    frame_timestamps,
    summarize_signalstats as summarize_signalstats_shared,
)
from narrated_fable_drama.media.ffmpeg import (
    MediaCommandError,
    require_binary,
    run as run_media_command,
)
from narrated_fable_drama.media.probe import (
    fraction_as_float,
    probe_json,
    stream_by_type,
)

BOUNDARY_FPS = 24
BOUNDARY_SIDE_SECONDS = 1.0
BOUNDARY_SIDE_FRAME_COUNT = int(round(BOUNDARY_SIDE_SECONDS * BOUNDARY_FPS))
BOUNDARY_DURATION_SECONDS = BOUNDARY_SIDE_SECONDS * 2
BOUNDARY_EXPECTED_FRAME_COUNT = BOUNDARY_SIDE_FRAME_COUNT * 2
INTERNAL_SAMPLE_FPS = 2
INTERNAL_SAMPLE_INTERVAL_SECONDS = 0.5
INTERNAL_MAX_COLUMNS = 6
CUT_LIKE_TRANSITIONS = REVIEW_CUT_LIKE_TRANSITION_TYPES
DISSOLVE_TRANSITIONS = REVIEW_DISSOLVE_TRANSITION_TYPES
FADE_TRANSITIONS = REVIEW_FADE_TRANSITION_TYPES
SUPPORTED_BOUNDARY_TRANSITIONS = SUPPORTED_REVIEW_TRANSITION_TYPES
SIGNALSTAT_FIELDS = (
    "YMIN",
    "YLOW",
    "YAVG",
    "YHIGH",
    "YMAX",
    "UAVG",
    "VAVG",
    "SATAVG",
    "BRNG",
)
COLOR_METADATA_FIELDS = (
    "pix_fmt",
    "bits_per_raw_sample",
    "color_range",
    "color_space",
    "color_transfer",
    "color_primaries",
)


class EvidenceError(RuntimeError):
    pass


def run(command: list[str], context: str) -> Any:
    try:
        return run_media_command(command, context=context)
    except MediaCommandError as exc:
        raise EvidenceError(str(exc)) from exc


def probe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise EvidenceError(f"Media input is missing: {path}")
    try:
        payload = probe_json(path)
        duration = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, MediaCommandError) as exc:
        raise EvidenceError(f"Unreadable media metadata: {path}") from exc
    video = stream_by_type(payload, "video")
    audio = stream_by_type(payload, "audio")
    if not isinstance(video, dict) or duration <= 0:
        raise EvidenceError(f"A readable video stream is required: {path}")
    rate = str(video.get("avg_frame_rate") or "0/1")
    try:
        fps = fraction_as_float(rate)
    except (ValueError, ZeroDivisionError) as exc:
        raise EvidenceError(f"Unreadable video frame rate: {path}") from exc
    if fps <= 0:
        raise EvidenceError(f"Invalid video frame rate: {path}")
    return {
        "duration_seconds": duration,
        "fps": fps,
        "video": video,
        "audio": audio,
        "color_metadata": {
            field: video.get(field) if video.get(field) not in {"", None} else "unknown"
            for field in COLOR_METADATA_FIELDS
        },
    }


def require_audio(metadata: dict[str, Any], path: Path) -> dict[str, Any]:
    audio = metadata.get("audio")
    if not isinstance(audio, dict):
        raise EvidenceError(
            f"A readable ElevenLabs-dubbed audio stream is required: {path}"
        )
    return {
        "stream_index": audio.get("index"),
        "codec": audio.get("codec_name"),
        "channels": audio.get("channels"),
        "channel_layout": audio.get("channel_layout"),
        "sample_rate": audio.get("sample_rate"),
        "duration_seconds": audio.get("duration") or metadata["duration_seconds"],
    }


def transition_preview_contract(
    transition_type: str, transition_seconds: float
) -> dict[str, Any]:
    try:
        transition_class = classify_review_transition(transition_type)
    except BoundaryExecutionError as exc:
        raise EvidenceError(str(exc)) from exc
    if transition_seconds < 0:
        raise EvidenceError("Transition duration cannot be negative.")
    if transition_class in {"dissolve", "fade"}:
        if not 0 < transition_seconds < BOUNDARY_DURATION_SECONDS:
            raise EvidenceError(
                f"{transition_type} duration must be greater than 0 and less than "
                f"{BOUNDARY_DURATION_SECONDS:.1f} seconds."
            )
        half = transition_seconds / 2.0
        return {
            "transition_type": transition_type,
            "transition_class": transition_class,
            "transition_seconds": transition_seconds,
            "preview_mode": "rendered_editorial_transition",
            "transition_start_seconds": BOUNDARY_SIDE_SECONDS - half,
            "transition_end_seconds": BOUNDARY_SIDE_SECONDS + half,
            "single_cut_pair_applicable": False,
        }
    if transition_class == "motivated_cut":
        return {
            "transition_type": transition_type,
            "transition_class": "motivated_cut",
            "transition_seconds": 0.0,
            "preview_mode": "source_tail_head_cut",
            "transition_start_seconds": BOUNDARY_SIDE_SECONDS,
            "transition_end_seconds": BOUNDARY_SIDE_SECONDS,
            "single_cut_pair_applicable": True,
        }
    return {
        "transition_type": transition_type,
        "transition_class": "baked_effect",
        "transition_seconds": transition_seconds,
        "preview_mode": "source_tail_head_baked_effect",
        "transition_start_seconds": BOUNDARY_SIDE_SECONDS,
        "transition_end_seconds": BOUNDARY_SIDE_SECONDS,
        "single_cut_pair_applicable": False,
    }


def make_internal_contact_sheet(scene_video: Path, output_dir: Path) -> Path:
    duration = probe(scene_video)["duration_seconds"]
    estimated = max(1, int(math.ceil(duration * INTERNAL_SAMPLE_FPS)))
    columns = min(INTERNAL_MAX_COLUMNS, estimated)
    rows = max(1, int(math.ceil(estimated / columns)))
    output = output_dir / "half-second-contact-sheet.jpg"
    base = (
        f"fps={INTERNAL_SAMPLE_FPS},"
        "scale=320:180:force_original_aspect_ratio=decrease,"
        "pad=320:180:(ow-iw)/2:(oh-ih)/2:black"
    )
    with_timestamp = (
        base
        + ",drawtext=text='%{pts\\:hms}':x=6:y=6:fontsize=14:"
        "fontcolor=white:box=1:boxcolor=black@0.65"
        + f",tile={columns}x{rows}:padding=3:margin=3"
    )
    completed = run_media_command(
        [
            require_binary("ffmpeg"),
            "-y",
            "-i",
            str(scene_video),
            "-vf",
            with_timestamp,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output),
        ],
        context="0.5-second current-Scene contact sheet",
        check=False,
    )
    if completed.returncode == 0 and output.is_file() and output.stat().st_size:
        return output
    raise EvidenceError("Could not create the 0.5-second current-Scene contact sheet.")


def make_internal_cut_evidence(
    scene_video: Path,
    cut_seconds: list[float],
    output_dir: Path,
) -> tuple[Path | None, Path | None]:
    """Extract the exact before/after evidence for every authored internal cut."""
    if not cut_seconds:
        return None, None
    metadata = probe(scene_video)
    duration = float(metadata["duration_seconds"])
    fps = float(metadata["fps"])
    offset = max(1.0 / fps, 1.0 / 48.0)
    frame_paths: list[Path] = []
    records: list[dict[str, Any]] = []
    for index, cut_second in enumerate(cut_seconds, start=1):
        if not 0.0 < cut_second < duration:
            raise EvidenceError(
                f"Internal cut {cut_second:.6f}s must fall inside the current Segment."
            )
        pair: list[str] = []
        for side, timestamp in (
            ("before", max(0.0, cut_second - offset)),
            ("after", min(duration - 1.0 / fps, cut_second + offset)),
        ):
            path = output_dir / f"internal-cut-{index:02d}-{side}.png"
            run(
                [
                    require_binary("ffmpeg"),
                    "-y",
                    "-ss",
                    f"{timestamp:.9f}",
                    "-i",
                    str(scene_video),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2:black",
                    str(path),
                ],
                f"internal cut {index} {side} frame extraction",
            )
            frame_paths.append(path)
            pair.append(str(path.resolve()))
        records.append(
            {
                "cut_index": index,
                "cut_second": cut_second,
                "sample_offset_seconds": offset,
                "before_frame_path": pair[0],
                "after_frame_path": pair[1],
            }
        )
    try:
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise EvidenceError("Pillow is required for internal-cut evidence.") from exc
    sheet = Image.new("RGB", (1280, 400 * len(records)), "black")
    draw = ImageDraw.Draw(sheet)
    for row, record in enumerate(records):
        y = row * 400
        before = Image.open(record["before_frame_path"]).convert("RGB")
        after = Image.open(record["after_frame_path"]).convert("RGB")
        sheet.paste(before, (0, y + 40))
        sheet.paste(after, (640, y + 40))
        draw.text((12, y + 12), f"CUT {row + 1} @ {record['cut_second']:.3f}s | BEFORE", fill="white")
        draw.text((652, y + 12), f"CUT {row + 1} @ {record['cut_second']:.3f}s | AFTER", fill="white")
    sheet_path = output_dir / "internal-cut-contact-sheet.jpg"
    sheet.save(sheet_path, quality=94)
    manifest_path = output_dir / "internal-cut-evidence.json"
    manifest_path.write_text(
        json.dumps(
            {
                "video_path": str(scene_video.resolve()),
                "cut_count": len(records),
                "cuts": records,
                "contact_sheet_path": str(sheet_path.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return sheet_path, manifest_path


def make_boundary_preview(
    previous_video: Path,
    scene_video: Path,
    previous_scene_id: int,
    output_dir: Path,
    *,
    transition_type: str,
    transition_seconds: float,
) -> tuple[Path, dict[str, Any]]:
    previous_meta = probe(previous_video)
    scene_meta = probe(scene_video)
    require_audio(previous_meta, previous_video)
    require_audio(scene_meta, scene_video)
    contract = transition_preview_contract(transition_type, transition_seconds)
    overlap = float(contract["transition_seconds"])
    source_side_seconds = (
        BOUNDARY_SIDE_SECONDS + overlap / 2.0
        if contract["transition_class"] == "dissolve"
        else BOUNDARY_SIDE_SECONDS
    )
    if previous_meta["duration_seconds"] + 1e-6 < source_side_seconds:
        raise EvidenceError(
            "The predecessor is too short for the transition-aware boundary preview."
        )
    if scene_meta["duration_seconds"] + 1e-6 < source_side_seconds:
        raise EvidenceError(
            "The current Segment is too short for the transition-aware boundary preview."
        )
    previous_start = previous_meta["duration_seconds"] - source_side_seconds
    output = output_dir / (
        f"boundary-preview-{transition_type}-from-scene-{previous_scene_id:02d}.mp4"
    )
    video_shape = (
        "scale=640:360:force_original_aspect_ratio=decrease,"
        "pad=640:360:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    )
    audio_shape = (
        "aresample=48000,"
        "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    )
    if contract["transition_class"] == "dissolve":
        xfade_offset = source_side_seconds - overlap
        filter_complex = (
            f"[0:v]fps={BOUNDARY_FPS},trim=start={previous_start:.9f}:"
            f"duration={source_side_seconds:.9f},setpts=PTS-STARTPTS,{video_shape}[previous];"
            f"[1:v]fps={BOUNDARY_FPS},trim=start=0:duration={source_side_seconds:.9f},"
            f"setpts=PTS-STARTPTS,{video_shape}[current];"
            f"[previous][current]xfade=transition=fade:duration={overlap:.9f}:"
            f"offset={xfade_offset:.9f},trim=duration={BOUNDARY_DURATION_SECONDS:.9f},"
            f"setpts=N/({BOUNDARY_FPS}*TB),format=yuv420p[out];"
            f"[0:a:0]atrim=start={previous_start:.9f}:duration={source_side_seconds:.9f},"
            f"asetpts=PTS-STARTPTS,{audio_shape}[previous_audio];"
            f"[1:a:0]atrim=start=0:duration={source_side_seconds:.9f},"
            f"asetpts=PTS-STARTPTS,{audio_shape}[current_audio];"
            f"[previous_audio][current_audio]acrossfade=d={overlap:.9f}:c1=tri:c2=tri,"
            f"atrim=duration={BOUNDARY_DURATION_SECONDS:.9f}[aout]"
        )
    elif contract["transition_class"] == "fade":
        half = overlap / 2.0
        fade_out_start = BOUNDARY_SIDE_SECONDS - half
        filter_complex = (
            f"[0:v]fps={BOUNDARY_FPS},reverse,trim=end_frame={BOUNDARY_SIDE_FRAME_COUNT},"
            f"reverse,setpts=N/({BOUNDARY_FPS}*TB),{video_shape},"
            f"fade=t=out:st={fade_out_start:.9f}:d={half:.9f}:color=black[previous];"
            f"[1:v]fps={BOUNDARY_FPS},trim=end_frame={BOUNDARY_SIDE_FRAME_COUNT},"
            f"setpts=N/({BOUNDARY_FPS}*TB),{video_shape},"
            f"fade=t=in:st=0:d={half:.9f}:color=black[current];"
            f"[previous][current]concat=n=2:v=1:a=0,setpts=N/({BOUNDARY_FPS}*TB),"
            "format=yuv420p[out];"
            f"[0:a:0]atrim=start={previous_start:.9f}:duration={BOUNDARY_SIDE_SECONDS:.9f},"
            f"asetpts=PTS-STARTPTS,{audio_shape},"
            f"afade=t=out:st={fade_out_start:.9f}:d={half:.9f}[previous_audio];"
            f"[1:a:0]atrim=start=0:duration={BOUNDARY_SIDE_SECONDS:.9f},"
            f"asetpts=PTS-STARTPTS,{audio_shape},"
            f"afade=t=in:st=0:d={half:.9f}[current_audio];"
            "[previous_audio][current_audio]concat=n=2:v=0:a=1[aout]"
        )
    else:
        filter_complex = (
            f"[0:v]fps={BOUNDARY_FPS},reverse,trim=end_frame={BOUNDARY_SIDE_FRAME_COUNT},"
            f"reverse,setpts=N/({BOUNDARY_FPS}*TB),{video_shape}[previous];"
            f"[0:a:0]atrim=start={previous_start:.9f}:duration={BOUNDARY_SIDE_SECONDS:.9f},"
            f"asetpts=PTS-STARTPTS,{audio_shape}[previous_audio];"
            f"[1:v]fps={BOUNDARY_FPS},trim=end_frame={BOUNDARY_SIDE_FRAME_COUNT},"
            f"setpts=N/({BOUNDARY_FPS}*TB),{video_shape}[current];"
            f"[1:a:0]atrim=start=0:duration={BOUNDARY_SIDE_SECONDS:.9f},"
            f"asetpts=PTS-STARTPTS,{audio_shape}[current_audio];"
            f"[previous][current]concat=n=2:v=1:a=0,setpts=N/({BOUNDARY_FPS}*TB),"
            "format=yuv420p[out];"
            "[previous_audio][current_audio]concat=n=2:v=0:a=1[aout]"
        )
    run(
        [
            require_binary("ffmpeg"),
            "-y",
            "-i",
            str(previous_video),
            "-i",
            str(scene_video),
            "-filter_complex",
            filter_complex,
            "-map",
            "[out]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ],
        "transition-aware two-second boundary preview creation",
    )
    actual = probe(output)["duration_seconds"]
    if abs(actual - BOUNDARY_DURATION_SECONDS) > (1.5 / BOUNDARY_FPS):
        raise EvidenceError(
            f"Boundary preview must be exactly two seconds; measured {actual:.6f}s."
        )
    return output, contract


def make_exact_seam_pair(
    previous_video: Path, scene_video: Path, previous_scene_id: int, output_dir: Path
) -> Path:
    output = output_dir / f"boundary-from-scene-{previous_scene_id:02d}.png"
    filters = (
        "[0:v]reverse,trim=end_frame=1,setpts=PTS-STARTPTS,"
        "scale=640:360:force_original_aspect_ratio=decrease,"
        "pad=640:360:(ow-iw)/2:(oh-ih)/2:black,"
        "drawtext=text='PREVIOUS LAST':x=12:y=12:fontsize=26:"
        "fontcolor=white:box=1:boxcolor=black@0.65[previous_last];"
        "[1:v]trim=end_frame=1,setpts=PTS-STARTPTS,"
        "scale=640:360:force_original_aspect_ratio=decrease,"
        "pad=640:360:(ow-iw)/2:(oh-ih)/2:black,"
        "drawtext=text='CURRENT FIRST':x=12:y=12:fontsize=26:"
        "fontcolor=white:box=1:boxcolor=black@0.65[current_first];"
        "[previous_last][current_first]hstack=inputs=2[out]"
    )
    run(
        [
            require_binary("ffmpeg"),
            "-y",
            "-sseof",
            "-1",
            "-i",
            str(previous_video),
            "-i",
            str(scene_video),
            "-filter_complex",
            filters,
            "-map",
            "[out]",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(output),
        ],
        "exact seam-pair creation",
    )
    return output


def extract_every_boundary_frame(
    boundary_preview: Path,
    output_dir: Path,
    transition_contract: dict[str, Any],
) -> Path:
    frames_dir = output_dir / "boundary-timeline-frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("frame-*.png"):
        old.unlink()
    run(
        [
            require_binary("ffmpeg"),
            "-y",
            "-i",
            str(boundary_preview),
            "-map",
            "0:v:0",
            "-vsync",
            "0",
            str(frames_dir / "frame-%06d.png"),
        ],
        "every-frame boundary extraction",
    )
    paths = sorted(frames_dir.glob("frame-*.png"))
    timestamps = frame_timestamps(boundary_preview)
    if not paths or len(paths) != len(timestamps):
        raise EvidenceError(
            "Every-frame extraction count does not match the decoded timestamp count."
        )
    expected = BOUNDARY_EXPECTED_FRAME_COUNT
    if len(paths) != expected:
        raise EvidenceError(
            f"Strict two-second {BOUNDARY_FPS}fps seam must decode to {expected} frames; "
            f"found {len(paths)}."
        )
    manifest = {
        "boundary_duration_seconds": BOUNDARY_DURATION_SECONDS,
        "boundary_fps": BOUNDARY_FPS,
        "frame_count": len(paths),
        "transition_contract": transition_contract,
        "inspection_contract": (
            "inspect every frame and adjacent pair in timestamp order, interpreting "
            "intentional visual change under the authored transition semantics"
        ),
        "frames": [
            {
                "index": index,
                "timestamp_seconds": timestamp,
                "path": str(path.resolve()),
            }
            for index, (path, timestamp) in enumerate(zip(paths, timestamps))
        ],
    }
    manifest_path = output_dir / "boundary-timeline-frames.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest_path


def make_boundary_all_frames_contact_sheet(
    boundary_preview: Path, output_dir: Path
) -> Path:
    """Render all 48 seam frames so a transient flash/pop cannot hide between endpoints."""

    output = output_dir / "boundary-all-48-frames.jpg"
    filters = (
        f"fps={BOUNDARY_FPS},"
        "scale=320:180:force_original_aspect_ratio=decrease,"
        "pad=320:180:(ow-iw)/2:(oh-ih)/2:black,"
        "drawtext=text='frame %{n}  %{pts\\:hms}':x=6:y=6:fontsize=14:"
        "fontcolor=white:box=1:boxcolor=black@0.7,"
        "tile=8x6:padding=3:margin=3"
    )
    run(
        [
            require_binary("ffmpeg"),
            "-y",
            "-i",
            str(boundary_preview),
            "-vf",
            filters,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output),
        ],
        "all-48-frame boundary contact sheet creation",
    )
    return output


def extract_review_audio(scene_video: Path, output_dir: Path) -> Path:
    output = output_dir / "scene-review-audio.wav"
    run(
        [
            require_binary("ffmpeg"),
            "-y",
            "-i",
            str(scene_video),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output),
        ],
        "review-audio extraction",
    )
    return output


def measure_seam_ssim(previous_video: Path, scene_video: Path) -> float | None:
    completed = run_media_command(
        [
            require_binary("ffmpeg"),
            "-i",
            str(previous_video),
            "-i",
            str(scene_video),
            "-filter_complex",
            (
                "[0:v]reverse,trim=end_frame=1,setpts=PTS-STARTPTS,"
                "scale=640:360:force_original_aspect_ratio=decrease,"
                "pad=640:360:(ow-iw)/2:(oh-ih)/2:black[a];"
                "[1:v]trim=end_frame=1,setpts=PTS-STARTPTS,"
                "scale=640:360:force_original_aspect_ratio=decrease,"
                "pad=640:360:(ow-iw)/2:(oh-ih)/2:black[b];"
                "[a][b]ssim"
            ),
            "-frames:v",
            "1",
            "-f",
            "null",
            "-",
        ],
        context="Boundary endpoint SSIM",
        check=False,
    )
    match = re.search(r"All:([0-9.]+)", completed.stderr or "")
    return float(match.group(1)) if match else None


def _parse_signalstats(text: str) -> list[dict[str, float]]:
    samples: list[dict[str, float]] = []
    current: dict[str, float] | None = None
    frame_re = re.compile(r"^frame:\d+\s+pts:\S+\s+pts_time:([-+0-9.eE]+)$")
    value_re = re.compile(r"^lavfi\.signalstats\.([A-Z]+)=([-+0-9.eE]+)$")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        frame_match = frame_re.fullmatch(line)
        if frame_match:
            if current is not None:
                samples.append(current)
            current = {"timestamp_seconds": float(frame_match.group(1))}
            continue
        value_match = value_re.fullmatch(line)
        if current is None or value_match is None:
            continue
        field, raw_value = value_match.groups()
        if field in SIGNALSTAT_FIELDS:
            current[field] = float(raw_value)
    if current is not None:
        samples.append(current)
    complete = [
        sample
        for sample in samples
        if all(field in sample for field in SIGNALSTAT_FIELDS)
    ]
    if not complete:
        raise EvidenceError("Could not decode video signal statistics.")
    return complete


def signalstats_samples(
    video: Path,
    *,
    sample_fps: int | None = None,
    endpoint: str | None = None,
) -> list[dict[str, float]]:
    if endpoint not in {None, "first", "last"}:
        raise EvidenceError(f"Unsupported signal-stat endpoint: {endpoint}")
    filters: list[str] = []
    if sample_fps is not None:
        filters.append(f"fps={sample_fps}")
    elif endpoint == "first":
        filters.extend(("trim=end_frame=1", "setpts=PTS-STARTPTS"))
    elif endpoint == "last":
        filters.extend(("reverse", "trim=end_frame=1", "setpts=PTS-STARTPTS"))
    filters.extend(
        (
            "scale=320:180:force_original_aspect_ratio=decrease",
            "pad=320:180:(ow-iw)/2:(oh-ih)/2:black",
            "format=yuv444p",
            "signalstats=stat=brng",
            "metadata=print:file=-",
        )
    )
    completed = run(
        [
            require_binary("ffmpeg"),
            "-hide_banner",
            "-v",
            "error",
            "-i",
            str(video),
            "-vf",
            ",".join(filters),
            "-an",
            "-f",
            "null",
            "-",
        ],
        f"video signal-stat measurement for {video.name}",
    )
    return _parse_signalstats(completed.stdout)


def summarize_signalstats(samples: list[dict[str, float]]) -> dict[str, Any]:
    return summarize_signalstats_shared(samples, fields=SIGNALSTAT_FIELDS)


def seam_signalstats(previous_video: Path, scene_video: Path) -> dict[str, Any]:
    previous_last = signalstats_samples(previous_video, endpoint="last")[-1]
    current_first = signalstats_samples(scene_video, endpoint="first")[0]
    deltas = {
        field: round(current_first[field] - previous_last[field], 4)
        for field in SIGNALSTAT_FIELDS
    }
    return {
        "previous_last": {
            key: round(value, 4) for key, value in previous_last.items()
        },
        "current_first": {
            key: round(value, 4) for key, value in current_first.items()
        },
        "signed_delta_current_minus_previous": deltas,
        "absolute_luma_average_delta": round(abs(deltas["YAVG"]), 4),
        "absolute_saturation_average_delta": round(abs(deltas["SATAVG"]), 4),
        "chroma_vector_delta": round(
            math.hypot(deltas["UAVG"], deltas["VAVG"]), 4
        ),
    }


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    scene_video = args.scene_video.expanduser().resolve()
    scene_meta = probe(scene_video)
    scene_audio = require_audio(scene_meta, scene_video)
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir is not None
        else None
    )
    if not args.metrics_only and output_dir is None:
        raise EvidenceError("--output-dir is required unless --metrics-only is used.")
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
    contact_sheet = (
        make_internal_contact_sheet(scene_video, output_dir)
        if output_dir is not None
        else None
    )
    internal_cut_sheet = None
    internal_cut_manifest = None
    audio_track = None
    if output_dir is not None:
        internal_cut_sheet, internal_cut_manifest = make_internal_cut_evidence(
            scene_video,
            list(args.internal_cut_second or []),
            output_dir,
        )
        audio_track = extract_review_audio(scene_video, output_dir)
    internal_signalstats = summarize_signalstats(
        signalstats_samples(scene_video, sample_fps=INTERNAL_SAMPLE_FPS)
    )

    boundary_preview = None
    boundary_pair = None
    boundary_manifest = None
    boundary_all_frames_sheet = None
    boundary_audio = None
    boundary_ssim = None
    boundary_signalstats = None
    boundary_transition_contract = None
    predecessor_boundary_second = None
    previous_color_metadata = None
    if args.previous_video is not None:
        if args.previous_scene_id is None:
            raise EvidenceError("--previous-scene-id is required with --previous-video.")
        previous_video = args.previous_video.expanduser().resolve()
        previous_meta = probe(previous_video)
        previous_color_metadata = previous_meta["color_metadata"]
        predecessor_boundary_second = max(
            0.0,
            previous_meta["duration_seconds"] - (1.0 / previous_meta["fps"]),
        )
        boundary_transition_contract = transition_preview_contract(
            args.transition_type, args.transition_seconds
        )
        if output_dir is not None:
            boundary_preview, boundary_transition_contract = make_boundary_preview(
                previous_video,
                scene_video,
                args.previous_scene_id,
                output_dir,
                transition_type=args.transition_type,
                transition_seconds=args.transition_seconds,
            )
            boundary_pair = make_exact_seam_pair(
                previous_video, scene_video, args.previous_scene_id, output_dir
            )
            boundary_manifest = extract_every_boundary_frame(
                boundary_preview, output_dir, boundary_transition_contract
            )
            boundary_all_frames_sheet = make_boundary_all_frames_contact_sheet(
                boundary_preview, output_dir
            )
            boundary_audio = require_audio(probe(boundary_preview), boundary_preview)
        boundary_ssim = measure_seam_ssim(previous_video, scene_video)
        boundary_signalstats = seam_signalstats(previous_video, scene_video)

    return {
        "scene_id": args.scene_id,
        "predecessor_boundary_second": predecessor_boundary_second,
        "metrics": {
            "boundary_ssim": boundary_ssim,
            "boundary_ssim_role": (
                "source-endpoint diagnostic only; never a semantic continuity gate"
                if args.previous_video is not None
                else None
            ),
            "boundary_transition_contract": boundary_transition_contract,
            "boundary_preview_each_side_seconds": BOUNDARY_SIDE_SECONDS,
            "boundary_preview_total_seconds": (
                BOUNDARY_DURATION_SECONDS
                if args.previous_video is not None
                else None
            ),
            "boundary_preview_fps": (
                BOUNDARY_FPS if args.previous_video is not None else None
            ),
            "boundary_frame_count": (
                BOUNDARY_EXPECTED_FRAME_COUNT
                if args.previous_video is not None
                else None
            ),
            "internal_frame_sample_interval_seconds": (
                INTERNAL_SAMPLE_INTERVAL_SECONDS
            ),
            "signalstats_color_model": "limited_range_yuv_yavg_uavg_vavg_satavg",
            "internal_signalstats": internal_signalstats,
            "boundary_signalstats": boundary_signalstats,
            "scene_color_metadata": scene_meta["color_metadata"],
            "previous_color_metadata": previous_color_metadata,
            "boundary_color_metadata_match": (
                previous_color_metadata == scene_meta["color_metadata"]
                if previous_color_metadata is not None
                else None
            ),
        },
        "audio": {
            "scene": scene_audio,
            "boundary_preview": boundary_audio,
        },
        "artifacts": {
            "internal_frame_contact_sheet": (
                str(contact_sheet.resolve()) if contact_sheet else None
            ),
            "internal_cut_contact_sheet": (
                str(internal_cut_sheet.resolve()) if internal_cut_sheet else None
            ),
            "internal_cut_evidence_manifest": (
                str(internal_cut_manifest.resolve()) if internal_cut_manifest else None
            ),
            "boundary_contact_sheet": (
                str(boundary_pair.resolve()) if boundary_pair else None
            ),
            "boundary_all_frames_contact_sheet": (
                str(boundary_all_frames_sheet.resolve())
                if boundary_all_frames_sheet else None
            ),
            "boundary_preview": (
                str(boundary_preview.resolve()) if boundary_preview else None
            ),
            "boundary_frame_manifest": (
                str(boundary_manifest.resolve()) if boundary_manifest else None
            ),
            "audio_review_track": (
                str(audio_track.resolve()) if audio_track else None
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-id", type=int, required=True)
    parser.add_argument("--scene-video", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--metrics-only",
        action="store_true",
        help="Compute technical metrics without writing inspection media.",
    )
    parser.add_argument("--previous-scene-id", type=int)
    parser.add_argument("--previous-video", type=Path)
    parser.add_argument(
        "--transition-type",
        choices=sorted(SUPPORTED_BOUNDARY_TRANSITIONS),
        default="hard_cut",
        help="Authored edit semantics at the incoming boundary.",
    )
    parser.add_argument(
        "--transition-seconds",
        type=float,
        default=0.0,
        help="Rendered duration for dissolve/fade transitions; ignored for cut-like edits.",
    )
    parser.add_argument(
        "--internal-cut-second",
        action="append",
        type=float,
        default=[],
        help="Authored internal cut timestamp; repeat once per cut.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        payload = prepare(parse_args())
    except EvidenceError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
