"""Build real-media evidence without selecting any editing strategy."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.contracts.segment import sha256_json
from narrated_fable_drama.contracts.segment.handoff import load_segment_handoff
from narrated_fable_drama.core.json_io import load_json_object, write_json_atomic
from narrated_fable_drama.media.ffmpeg import MediaCommandError, run

from post_timeline import (
    SegmentRecord,
    TimelineError,
    _screenplay_story_plans,
    discover_segments,
)
from .plan import BOUNDARY_WINDOW_SECONDS, EVIDENCE_CONTRACT


_LOUDNESS_RE = re.compile(r"^\s*I:\s*(-?(?:inf|\d+(?:\.\d+)?))\s+LUFS", re.MULTILINE)
_LRA_RE = re.compile(r"^\s*LRA:\s*(-?(?:inf|\d+(?:\.\d+)?))\s+LU", re.MULTILINE)
_PEAK_RE = re.compile(r"^\s*Peak:\s*(-?(?:inf|\d+(?:\.\d+)?))\s+dBFS", re.MULTILINE)
_SILENCE_START_RE = re.compile(r"silence_start:\s*(\d+(?:\.\d+)?)")
_SILENCE_END_RE = re.compile(
    r"silence_end:\s*(\d+(?:\.\d+)?)\s*\|\s*silence_duration:\s*(\d+(?:\.\d+)?)"
)
_FREEZE_EVENT_RE = re.compile(
    r"freeze_(start|duration|end):\s*(\d+(?:\.\d+)?)"
)


class FinishEvidenceError(RuntimeError):
    """Raised when required real-media evidence cannot be generated."""


def _sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError as exc:
        raise FinishEvidenceError(f"Cannot hash evidence source: {path}") from exc


def _production_record(task_dir: Path, segment_id: str) -> dict[str, Any]:
    path = (
        task_dir
        / ".pending"
        / "virtual-production"
        / "generation-segments"
        / segment_id
        / "production-record.json"
    )
    return load_json_object(
        path,
        label=f"{segment_id} production record",
        error_type=FinishEvidenceError,
    )


def _audio_measurement(
    source: Path,
    *,
    start_seconds: float,
    end_seconds: float,
) -> dict[str, Any]:
    duration = end_seconds - start_seconds
    if duration <= 0:
        raise FinishEvidenceError(f"Audio evidence interval is empty: {source}")
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(source),
        "-map",
        "0:a:0",
        "-af",
        (
            f"atrim=start={start_seconds:.6f}:end={end_seconds:.6f},"
            "asetpts=PTS-STARTPTS,"
            "silencedetect=noise=-50dB:d=0.05,"
            "ebur128=peak=true"
        ),
        "-f",
        "null",
        "-",
    ]
    try:
        completed = run(
            command,
            context=f"Audio evidence analysis {source}",
        )
    except MediaCommandError as exc:
        raise FinishEvidenceError(f"Could not analyze source audio: {source}") from exc
    report = completed.stderr
    loudness = _LOUDNESS_RE.findall(report)
    lra = _LRA_RE.findall(report)
    peak = _PEAK_RE.findall(report)
    if not loudness or not lra or not peak:
        raise FinishEvidenceError(f"FFmpeg returned incomplete loudness evidence: {source}")

    starts = [float(value) for value in _SILENCE_START_RE.findall(report)]
    ends = [
        (float(end), float(length))
        for end, length in _SILENCE_END_RE.findall(report)
    ]
    silences: list[dict[str, float]] = []
    for index, start in enumerate(starts):
        if index < len(ends):
            end, measured_duration = ends[index]
        else:
            end = duration
            measured_duration = max(0.0, end - start)
        silences.append(
            {
                "start_seconds": round(start, 6),
                "end_seconds": round(min(duration, end), 6),
                "duration_seconds": round(measured_duration, 6),
            }
        )
    return {
        "analysis_role": "measurement_only_no_edit_decision",
        "source_start_seconds": round(start_seconds, 6),
        "source_end_seconds": round(end_seconds, 6),
        "integrated_lufs": loudness[-1],
        "loudness_range_lu": lra[-1],
        "true_peak_dbfs": peak[-1],
        "silence_detection": {
            "noise_threshold_db": -50.0,
            "minimum_duration_seconds": 0.05,
            "intervals_relative_to_window": silences,
        },
    }


def _render_seam_preview(
    outgoing: SegmentRecord,
    incoming: SegmentRecord,
    directory: Path,
) -> dict[str, str]:
    window = BOUNDARY_WINDOW_SECONDS
    if (
        outgoing.probe.duration_seconds < window
        or incoming.probe.duration_seconds < window
    ):
        raise FinishEvidenceError(
            f"{outgoing.segment_name}->{incoming.segment_name} cannot provide "
            f"the required {window:.1f}s evidence on each side"
        )
    outgoing_start = outgoing.probe.duration_seconds - window
    preview = directory / "source-seam-3s-plus-3s.mp4"
    contact_sheet = directory / "source-seam-contact-sheet.jpg"
    waveform = directory / "source-seam-waveform.png"
    directory.mkdir(parents=True, exist_ok=True)
    width = outgoing.probe.width
    height = outgoing.probe.height
    filters = (
        f"[0:v]trim=start={outgoing_start:.6f}:end={outgoing.probe.duration_seconds:.6f},"
        f"setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[v0];"
        f"[1:v]trim=start=0:end={window:.6f},setpts=PTS-STARTPTS,"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[v1];"
        f"[0:a]atrim=start={outgoing_start:.6f}:end={outgoing.probe.duration_seconds:.6f},"
        "asetpts=PTS-STARTPTS,aresample=48000,"
        "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a0];"
        f"[1:a]atrim=start=0:end={window:.6f},asetpts=PTS-STARTPTS,"
        "aresample=48000,"
        "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a1];"
        "[v0][v1]concat=n=2:v=1:a=0[vout];"
        "[a0][a1]concat=n=2:v=0:a=1[aout]"
    )
    try:
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(outgoing.video_path),
                "-i",
                str(incoming.video_path),
                "-filter_complex",
                filters,
                "-map",
                "[vout]",
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
                str(preview),
            ],
            context=f"Boundary evidence preview {outgoing.segment_name}->{incoming.segment_name}",
        )
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(preview),
                "-vf",
                "fps=1,scale=320:-2:flags=lanczos,tile=6x1:padding=2:margin=2:color=black",
                "-frames:v",
                "1",
                str(contact_sheet),
            ],
            context=f"Boundary contact sheet {outgoing.segment_name}->{incoming.segment_name}",
        )
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(preview),
                "-filter_complex",
                "[0:a]aformat=channel_layouts=mono,showwavespic=s=1800x360:colors=0x55ccff[v]",
                "-map",
                "[v]",
                "-frames:v",
                "1",
                str(waveform),
            ],
            context=f"Boundary waveform {outgoing.segment_name}->{incoming.segment_name}",
        )
    except MediaCommandError as exc:
        raise FinishEvidenceError(
            f"Could not render boundary evidence for "
            f"{outgoing.segment_name}->{incoming.segment_name}"
        ) from exc
    return {
        "seam_preview": str(preview.resolve()),
        "contact_sheet": str(contact_sheet.resolve()),
        "waveform": str(waveform.resolve()),
    }


def _segment_visual_evidence(
    record: SegmentRecord,
    root: Path,
) -> tuple[dict[str, str], dict[str, Any]]:
    directory = root / "segments" / record.segment_name
    directory.mkdir(parents=True, exist_ok=True)
    contact_sheet = directory / "full-segment-contact-sheet.jpg"
    try:
        run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(record.video_path),
                "-vf",
                (
                    "fps=2,scale=320:-2:flags=lanczos,"
                    "tile=6x5:padding=2:margin=2:color=black"
                ),
                "-frames:v",
                "1",
                str(contact_sheet),
            ],
            context=f"Full Segment contact sheet {record.segment_name}",
        )
        completed = run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-i",
                str(record.video_path),
                "-an",
                "-vf",
                "freezedetect=n=-50dB:d=0.20",
                "-f",
                "null",
                "-",
            ],
            context=f"Full Segment freeze measurement {record.segment_name}",
        )
    except MediaCommandError as exc:
        raise FinishEvidenceError(
            f"Could not build visual evidence for {record.segment_name}"
        ) from exc
    intervals: list[dict[str, float | str]] = []
    current_start: float | None = None
    current_duration: float | None = None
    for kind, raw_value in _FREEZE_EVENT_RE.findall(completed.stderr):
        value = float(raw_value)
        if kind == "start":
            if current_start is not None:
                raise FinishEvidenceError(
                    f"Malformed freeze evidence for {record.segment_name}"
                )
            current_start = value
            current_duration = None
        elif kind == "duration":
            if current_start is None:
                raise FinishEvidenceError(
                    f"Malformed freeze duration for {record.segment_name}"
                )
            current_duration = value
        else:
            if current_start is None:
                raise FinishEvidenceError(
                    f"Malformed freeze end for {record.segment_name}"
                )
            intervals.append(
                {
                    "start_seconds": round(current_start, 6),
                    "end_seconds": round(value, 6),
                    "duration_seconds": round(
                        current_duration
                        if current_duration is not None
                        else value - current_start,
                        6,
                    ),
                    "interval_state": "closed_interval",
                }
            )
            current_start = None
            current_duration = None
    if current_start is not None:
        end = record.probe.duration_seconds
        intervals.append(
            {
                "start_seconds": round(current_start, 6),
                "end_seconds": round(end, 6),
                "duration_seconds": round(
                    current_duration
                    if current_duration is not None
                    else max(0.0, end - current_start),
                    6,
                ),
                "interval_state": "continues_to_source_end",
            }
        )
    return (
        {
            "full_segment_contact_sheet": str(contact_sheet.resolve()),
            "source_video": str(record.video_path.resolve()),
        },
        {
            "analysis_role": "measurement_only_no_edit_decision",
            "filter": "ffmpeg_freezedetect",
            "noise_tolerance_db": -50.0,
            "minimum_duration_seconds": 0.2,
            "freeze_intervals": intervals,
        },
    )


def generate_evidence(
    task_dir: Path,
    *,
    validation_through_segment_id: str | None = None,
) -> Path:
    """Generate the fixed ±3s evidence set used by the model decision stage."""
    task_dir = task_dir.expanduser().resolve()
    try:
        records = discover_segments(
            task_dir,
            validation_through_segment_id=validation_through_segment_id,
            allow_stale_preview=validation_through_segment_id is not None,
        )
    except TimelineError as exc:
        raise FinishEvidenceError(str(exc)) from exc
    story_plans, authored_boundaries = _screenplay_story_plans(task_dir)
    if validation_through_segment_id is not None:
        story_plans = story_plans[: len(records)]
        authored_boundaries = authored_boundaries[: max(0, len(records) - 1)]
    if len(story_plans) != len(records):
        raise FinishEvidenceError("Screenplay and evidence Segment coverage differ")
    handoffs = load_segment_handoff(task_dir)
    root = (
        task_dir
        / ".pending"
        / "finish-postproduction"
        / "llm-evidence"
    )
    segment_items: list[dict[str, Any]] = []
    source_identity: list[dict[str, str]] = []
    for record in records:
        production = _production_record(task_dir, record.segment_name)
        source_hash = _sha256_file(record.video_path)
        dialogue_cues = [
            cue
            for block in handoffs[record.segment_name]["timeline_blocks"]
            for cue in block["dialogue_cues"]
        ]
        identity = {
            "segment_id": record.segment_name,
            "source_sha256": source_hash,
            "provider_attempt_id": str(production["provider_attempt_id"]),
        }
        source_identity.append(identity)
        visual_artifacts, visual_measurement = _segment_visual_evidence(
            record,
            root,
        )
        segment_items.append(
            {
                **identity,
                "source": str(record.video_path.resolve()),
                "duration_seconds": round(record.probe.duration_seconds, 6),
                "frame_rate": record.probe.frame_rate,
                "width": record.probe.width,
                "height": record.probe.height,
                "has_audio": record.probe.has_audio,
                "dialogue_cues": dialogue_cues,
                "visual_artifacts": visual_artifacts,
                "full_source_visual_measurement": visual_measurement,
                "full_source_audio_measurement": _audio_measurement(
                    record.video_path,
                    start_seconds=0.0,
                    end_seconds=record.probe.duration_seconds,
                ),
            }
        )

    boundary_items: list[dict[str, Any]] = []
    for index, (outgoing, incoming) in enumerate(zip(records, records[1:])):
        authored = authored_boundaries[index]
        if (
            authored.get("from_segment_id") != outgoing.segment_name
            or authored.get("to_segment_id") != incoming.segment_name
        ):
            raise FinishEvidenceError("Authored boundary order differs from media")
        boundary_id = f"{outgoing.segment_name}--{incoming.segment_name}"
        directory = root / "boundaries" / boundary_id
        outgoing_start = outgoing.probe.duration_seconds - BOUNDARY_WINDOW_SECONDS
        artifacts = _render_seam_preview(outgoing, incoming, directory)
        boundary_items.append(
            {
                "boundary_id": boundary_id,
                "from": outgoing.segment_name,
                "to": incoming.segment_name,
                "authored_transition": authored,
                "source_windows": {
                    "outgoing": {
                        "start_seconds": round(outgoing_start, 6),
                        "end_seconds": round(outgoing.probe.duration_seconds, 6),
                    },
                    "incoming": {
                        "start_seconds": 0.0,
                        "end_seconds": BOUNDARY_WINDOW_SECONDS,
                    },
                },
                "artifacts": artifacts,
                "audio_measurements": {
                    "outgoing_tail": _audio_measurement(
                        outgoing.video_path,
                        start_seconds=outgoing_start,
                        end_seconds=outgoing.probe.duration_seconds,
                    ),
                    "incoming_head": _audio_measurement(
                        incoming.video_path,
                        start_seconds=0.0,
                        end_seconds=BOUNDARY_WINDOW_SECONDS,
                    ),
                },
                "decision": "model_required",
            }
        )

    manifest = {
        "contract": EVIDENCE_CONTRACT,
        "task_dir": str(task_dir),
        "coverage": (
            "preview_prefix"
            if validation_through_segment_id is not None
            else "complete_task"
        ),
        "render_authorization": validation_through_segment_id is None,
        "decision_authority": "editor-restoration-master-model",
        "source_policy": "accepted_generated_segments_read_only",
        "observation_window": {
            "outgoing_tail_seconds": BOUNDARY_WINDOW_SECONDS,
            "incoming_head_seconds": BOUNDARY_WINDOW_SECONDS,
        },
        "source_set_sha256": sha256_json(source_identity),
        "segments": segment_items,
        "boundaries": boundary_items,
    }
    path = root / "evidence-manifest.json"
    write_json_atomic(path, manifest, sort_keys=True)
    return path
