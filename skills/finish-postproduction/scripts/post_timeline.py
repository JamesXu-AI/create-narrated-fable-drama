#!/usr/bin/env python3
"""Compile the authored semantic-boundary picture and native-audio timeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.contracts.boundary import (
    build_story_plan_boundaries,
)
from narrated_fable_drama.contracts.screenplay import load_screenplay_file
from narrated_fable_drama.contracts.segment import (
    load_execution_plan,
    parse_segment_script,
    sha256_json,
    storyboard_segment_rows,
)
from narrated_fable_drama.contracts.segment.handoff import load_segment_handoff
from narrated_fable_drama.core.json_io import load_json_object, write_json_atomic
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.media.ffmpeg import MediaCommandError
from narrated_fable_drama.media.probe import (
    fraction_as_float,
    probe_json,
    stream_by_type,
)

SEGMENT_RE = re.compile(r"^segment-([0-9]{3})$")
MAX_FINAL_RUNTIME_SECONDS = 240.0
SEEDANCE_EXTENSION_OUTGOING_TRIM_FRAMES = 6
SEEDANCE_EXTENSION_INCOMING_TRIM_FRAMES = 1
TERMINAL_AUDIO_FADE_SECONDS = 0.12


class TimelineError(RuntimeError):
    """Raised when current task media cannot form a valid final timeline."""


@dataclass(frozen=True)
class MediaProbe:
    duration_seconds: float
    has_audio: bool
    width: int
    height: int
    frame_rate: str


@dataclass(frozen=True)
class SegmentRecord:
    segment_id: int
    segment_name: str
    video_path: Path
    script_path: Path
    probe: MediaProbe
    fields: dict[str, Any]


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    return load_json_object(path, label=label, error_type=TimelineError)


def probe_media(path: Path) -> MediaProbe:
    try:
        payload = probe_json(path)
    except MediaCommandError as exc:
        raise TimelineError(f"Could not probe media: {path}") from exc
    video_stream = stream_by_type(payload, "video")
    if not isinstance(video_stream, dict):
        raise TimelineError(f"Segment media has no video stream: {path}")
    try:
        duration = float(video_stream.get("duration") or payload["format"]["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TimelineError(f"Could not read media duration: {path}") from exc
    frame_rate = str(
        video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "25/1"
    )
    try:
        if fraction_as_float(frame_rate) <= 0:
            raise ValueError
    except (ValueError, ZeroDivisionError):
        raise TimelineError(f"Segment media has invalid frame rate: {path}")
    return MediaProbe(
        duration_seconds=duration,
        has_audio=any(
            item.get("codec_type") == "audio" for item in payload.get("streams", [])
        ),
        width=int(video_stream.get("width") or 0),
        height=int(video_stream.get("height") or 0),
        frame_rate=frame_rate,
    )


def _screenplay_story_plans(
    task_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    screenplay = load_screenplay_file(task_dir / "screenplay-writer" / "screenplay.md")
    story_plans = [segment["story_plan"] for segment in screenplay["segments"]]
    if not story_plans:
        raise TimelineError("screenplay.md contains no Segments")
    expected = [f"segment-{index:03d}" for index in range(1, len(story_plans) + 1)]
    actual = [item["segment_id"] for item in story_plans]
    if actual != expected:
        raise TimelineError("screenplay.md Segment order is invalid")
    return story_plans, screenplay["continuity_boundaries"]


def _validate_project_audio(task_dir: Path) -> dict[str, Any]:
    context = load_project_context(task_dir)
    if context["speech_audio_source"] != "seedance_native":
        raise TimelineError("screenplay.md Speech Audio Source must be seedance_native")
    return context


def discover_segments(task_dir: Path) -> list[SegmentRecord]:
    task_dir = task_dir.expanduser().resolve()
    _validate_project_audio(task_dir)
    story_plans, _ = _screenplay_story_plans(task_dir)
    expected = [str(item["segment_id"]) for item in storyboard_segment_rows(task_dir)]
    if [item["segment_id"] for item in story_plans] != expected:
        raise TimelineError(
            "screenplay.md Segment order differs from the Storyboard Generation Plan"
        )
    virtual_pending = task_dir / ".pending" / "virtual-production"
    media_root = virtual_pending / "generation-segments"
    scripts_root = virtual_pending / "seedance-segment-scripts"
    if not media_root.is_dir() or not scripts_root.is_dir():
        raise TimelineError("Missing current .pending Segment media or Segment Scripts")
    actual_media = sorted(
        item.name for item in media_root.iterdir() if item.is_dir() and SEGMENT_RE.fullmatch(item.name)
    )
    actual_scripts = sorted(path.stem for path in scripts_root.glob("segment-*.md"))
    if actual_media != expected or actual_scripts != expected:
        raise TimelineError("Segment media/Script coverage differs from screenplay.md")
    records: list[SegmentRecord] = []
    for segment_name in expected:
        video = media_root / segment_name / "video.mp4"
        script = scripts_root / f"{segment_name}.md"
        if not video.is_file() or not script.is_file():
            raise TimelineError(f"Incomplete generated Segment: {segment_name}")
        production_record = _load_json(
            media_root / segment_name / "production-record.json",
            label=f"{segment_name} production record",
        )
        if (
            production_record.get("contract")
            != "generated-segment-production-record"
            or production_record.get("segment_id") != segment_name
            or production_record.get("status") != "GENERATED"
        ):
            raise TimelineError(f"{segment_name} is not a completed generated Segment")
        attempt_number = production_record.get("attempt_number")
        if isinstance(attempt_number, bool) or not isinstance(attempt_number, int) or attempt_number < 1:
            raise TimelineError(f"{segment_name} has invalid provider attempt identity")
        provider_attempt_id = f"{segment_name}__attempt-{attempt_number:04d}"
        recorded_attempt = production_record.get("provider_attempt_id")
        if recorded_attempt != provider_attempt_id:
            raise TimelineError(f"{segment_name} production attempt identity is stale")
        parsed_script = parse_segment_script(script)
        execution_plan = load_execution_plan(task_dir, segment_name)
        if (
            production_record.get("segment_prompt_sha256")
            != parsed_script["script_sha256"]
            or production_record.get("seedance_execution_plan_sha256")
            != sha256_json(execution_plan)
            or production_record.get("operation")
            != parsed_script["metadata"]["operation"]
        ):
            raise TimelineError(
                f"{segment_name} production record differs from its Seed Master Script"
            )
        fields = parsed_script["metadata"]
        probe = probe_media(video)
        if not probe.has_audio:
            raise TimelineError(
                f"{segment_name} lacks required Seedance native dialogue/foley/ambience audio"
            )
        if probe.duration_seconds <= 0 or probe.duration_seconds > 15.25:
            raise TimelineError(f"{segment_name} has invalid generated duration")
        records.append(
            SegmentRecord(
                segment_id=int(segment_name.removeprefix("segment-")),
                segment_name=segment_name,
                video_path=video.resolve(),
                script_path=script.resolve(),
                probe=probe,
                fields=fields,
            )
        )
    return records


def _dialogue_cues(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        cue
        for block in handoff.get("timeline_blocks", [])
        if isinstance(block, dict)
        for cue in block.get("dialogue_cues", [])
        if isinstance(cue, dict)
    ]


def _source_windows(
    records: list[SegmentRecord],
    handoffs: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, float]], dict[tuple[str, str], dict[str, Any]]]:
    """Plan the official 6-frame/1-frame Seedance extension seam cleanup."""

    windows = [
        {"source_in_seconds": 0.0, "source_out_seconds": record.probe.duration_seconds}
        for record in records
    ]
    seam_trims: dict[tuple[str, str], dict[str, Any]] = {}
    for index in range(1, len(records)):
        incoming = records[index]
        if incoming.fields.get("operation") != "video_extension":
            continue
        outgoing = records[index - 1]
        outgoing_fps = _fraction_as_float(outgoing.probe.frame_rate)
        incoming_fps = _fraction_as_float(incoming.probe.frame_rate)
        outgoing_trim = SEEDANCE_EXTENSION_OUTGOING_TRIM_FRAMES / outgoing_fps
        incoming_trim = SEEDANCE_EXTENSION_INCOMING_TRIM_FRAMES / incoming_fps
        outgoing_handoff = handoffs.get(outgoing.segment_name)
        incoming_handoff = handoffs.get(incoming.segment_name)
        if not isinstance(outgoing_handoff, dict) or not isinstance(incoming_handoff, dict):
            raise TimelineError(
                f"Missing Segment handoff for extension seam "
                f"{outgoing.segment_name}->{incoming.segment_name}"
            )
        safe = outgoing_handoff.get("segment_safe_cut_design")
        available_hold = (
            float(safe.get("editable_hold_seconds", -1))
            if isinstance(safe, dict)
            else -1.0
        )
        if available_hold + 1e-6 < outgoing_trim:
            raise TimelineError(
                f"{outgoing.segment_name} provides {available_hold:.3f}s editable hold, "
                f"but its Seedance extension seam needs {outgoing_trim:.3f}s for six frames"
            )
        outgoing_cut = windows[index - 1]["source_out_seconds"] - outgoing_trim
        incoming_cut = windows[index]["source_in_seconds"] + incoming_trim
        if outgoing_cut <= windows[index - 1]["source_in_seconds"] or incoming_cut >= windows[index]["source_out_seconds"]:
            raise TimelineError(
                f"Seedance extension seam trim would consume a complete Segment at "
                f"{outgoing.segment_name}->{incoming.segment_name}"
            )
        outgoing_dialogue = _dialogue_cues(outgoing_handoff)
        incoming_dialogue = _dialogue_cues(incoming_handoff)
        if any(float(cue["end_seconds"]) > outgoing_cut + 1e-6 for cue in outgoing_dialogue):
            raise TimelineError(
                f"{outgoing.segment_name} dialogue overlaps the required six-frame extension trim"
            )
        if any(float(cue["start_seconds"]) < incoming_cut - 1e-6 for cue in incoming_dialogue):
            raise TimelineError(
                f"{incoming.segment_name} dialogue overlaps the required one-frame extension trim"
            )
        windows[index - 1]["source_out_seconds"] = outgoing_cut
        windows[index]["source_in_seconds"] = incoming_cut
        seam_trims[(outgoing.segment_name, incoming.segment_name)] = {
            "policy": "seedance_extension_6_tail_frames_1_head_frame",
            "outgoing_trim_frames": SEEDANCE_EXTENSION_OUTGOING_TRIM_FRAMES,
            "incoming_trim_frames": SEEDANCE_EXTENSION_INCOMING_TRIM_FRAMES,
            "outgoing_trim_seconds": round(outgoing_trim, 6),
            "incoming_trim_seconds": round(incoming_trim, 6),
            "outgoing_source_out_seconds": round(outgoing_cut, 6),
            "incoming_source_in_seconds": round(incoming_cut, 6),
            "dialogue_clear": True,
            "editable_hold_verified": True,
        }
    return windows, seam_trims


def compile_timelines(
    task_dir: Path,
    records: list[SegmentRecord] | None = None,
    *,
    runtime_limit_seconds: float = MAX_FINAL_RUNTIME_SECONDS,
) -> tuple[dict[str, Any], dict[str, Any]]:
    task_dir = task_dir.expanduser().resolve()
    records = records if records is not None else discover_segments(task_dir)
    if not records:
        raise TimelineError("No generated Segment media found")
    picture_events: list[dict[str, Any]] = []
    native_events: list[dict[str, Any]] = []
    boundaries: list[dict[str, Any]] = []
    story_plans, authored_boundaries = _screenplay_story_plans(task_dir)
    plan_boundaries = build_story_plan_boundaries(
        story_plans, authored_boundaries
    )
    storyboards = load_segment_handoff(task_dir)
    source_windows, seam_trims = _source_windows(records, storyboards)
    cursor = 0.0
    for index, record in enumerate(records):
        source_in = source_windows[index]["source_in_seconds"]
        source_out = source_windows[index]["source_out_seconds"]
        duration = source_out - source_in
        incoming_execution = (
            plan_boundaries[index - 1]["execution"] if index else None
        )
        incoming_overlap = (
            float(incoming_execution["transition_duration_seconds"])
            if incoming_execution is not None
            and incoming_execution["picture_edit_mode"] in {"dissolve", "fade"}
            else 0.0
        )
        if incoming_overlap < 0 or incoming_overlap >= duration:
            raise TimelineError(
                f"{record.segment_name} has an invalid incoming transition duration"
            )
        start = cursor - incoming_overlap
        end = start + duration
        common = {
            "segment_id": record.segment_name,
            "source": str(record.video_path),
            "source_in_seconds": round(source_in, 6),
            "source_out_seconds": round(source_out, 6),
            "timeline_in_seconds": round(start, 6),
            "timeline_out_seconds": round(end, 6),
            "duration_seconds": round(duration, 6),
        }
        picture_events.append(
            {
                **common,
                "edit": (
                    incoming_execution["picture_edit_mode"]
                    if incoming_execution is not None
                    else "opening"
                ),
                "script": str(record.script_path),
            }
        )
        native_events.append(
            {
                **common,
                "event_id": f"native-{record.segment_name}",
                "purpose": "seedance_native_dialogue_foley_ambience_and_background_music",
                "has_source_audio": True,
                "voice_audio_source": "speaker_reference_audio",
                "dialogue_source": "seedance",
                "native_ambience_source": "seedance",
                "background_music_source": "seedance_native",
                "seedance_background_music": True,
                "preserve_lip_sync": True,
                "cross_boundary_copy_allowed": False,
                "transition_overlap_allowed": incoming_overlap > 0,
                "gain_db": 0.0,
                "terminal_audio_fade_seconds": (
                    TERMINAL_AUDIO_FADE_SECONDS if index == len(records) - 1 else 0.0
                ),
            }
        )
        if index + 1 < len(records):
            boundary_plan = plan_boundaries[index]
            execution = boundary_plan["execution"]
            overlap = (
                float(execution["transition_duration_seconds"])
                if execution["picture_edit_mode"] in {"dissolve", "fade"}
                else 0.0
            )
            if overlap:
                try:
                    storyboard = storyboards[record.segment_name]
                except KeyError as exc:
                    raise TimelineError(
                        f"{record.segment_name} is absent from the Segment handoff"
                    ) from exc
                safe = storyboard.get("segment_safe_cut_design")
                available = (
                    float(safe.get("editable_hold_seconds", -1))
                    if isinstance(safe, dict)
                    else -1
                )
                if available + 1e-6 < overlap:
                    raise TimelineError(
                        f"{record.segment_name} provides {available:.3f}s transition "
                        f"handle but {execution['authored_transition_type']} requires "
                        f"{overlap:.3f}s"
                    )
            boundary = {
                    "from": record.segment_name,
                    "to": records[index + 1].segment_name,
                    "authored_transition_type": execution[
                        "authored_transition_type"
                    ],
                    "transition_class": execution["transition_class"],
                    "timeline_seconds": round(end - overlap, 6),
                    "transition_start_seconds": round(end - overlap, 6),
                    "transition_end_seconds": round(end, 6),
                    "picture_edit": execution["picture_edit_mode"],
                    "audio_edit": execution["audio_edit_mode"],
                    "audio_edge_fade_seconds": execution[
                        "audio_edge_fade_seconds"
                    ],
                    "overlap_seconds": round(overlap, 6),
                }
            seam_trim = seam_trims.get(
                (record.segment_name, records[index + 1].segment_name)
            )
            if seam_trim is not None:
                boundary["seedance_extension_trim"] = seam_trim
                boundary["outgoing_source_out_seconds"] = seam_trim[
                    "outgoing_source_out_seconds"
                ]
                boundary["incoming_source_in_seconds"] = seam_trim[
                    "incoming_source_in_seconds"
                ]
            boundaries.append(boundary)
        cursor = end
    if cursor > runtime_limit_seconds + 1e-6:
        raise TimelineError(
            f"Final runtime {cursor:.3f}s exceeds {runtime_limit_seconds:.3f}s"
        )
    picture_edl = {
        "contract": "finish-picture-audio-edl",
        "edit_policy": "authored_semantic_boundaries",
        "segment_count": len(records),
        "duration_seconds": round(cursor, 6),
        "picture_events": picture_events,
        "boundaries": boundaries,
        "seedance_extension_trim_policy": {
            "enabled": True,
            "outgoing_tail_frames": SEEDANCE_EXTENSION_OUTGOING_TRIM_FRAMES,
            "incoming_head_frames": SEEDANCE_EXTENSION_INCOMING_TRIM_FRAMES,
            "applied_boundary_count": len(seam_trims),
        },
    }
    audio_timeline = {
        "contract": "finish-native-audio-timeline",
        "duration_seconds": round(cursor, 6),
        "native_audio_policy": {
            "generate_audio": True,
            "voice_audio_source": "speaker_reference_audio",
            "dialogue_source": "seedance",
            "native_ambience_source": "seedance",
            "seedance_background_music": True,
            "background_music_source": "seedance_native",
            "preserve_clip_sync": True,
            "cross_segment_native_audio": any(
                boundary["overlap_seconds"] > 0 for boundary in boundaries
            ),
            "terminal_fade_seconds": TERMINAL_AUDIO_FADE_SECONDS,
        },
        "tracks": [
            {
                "track_id": "native-sync",
                "source": "seedance",
                "role": "synchronized_dialogue_foley_and_ambience",
                "events": native_events,
            }
        ],
        "music_provider": "seedance",
        "seedance_background_music": True,
        "background_music_source": "seedance_native",
    }
    return picture_edl, audio_timeline


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    write_json_atomic(path, payload, sort_keys=True)


def write_timeline_artifacts(
    task_dir: Path,
    picture_edl: dict[str, Any],
    audio_timeline: dict[str, Any],
) -> tuple[Path, Path]:
    pending = task_dir.expanduser().resolve() / ".pending" / "finish-postproduction"
    edl_path = pending / "post-production" / "picture-audio-edl.json"
    audio_path = pending / "audio-timeline.json"
    _write_json(edl_path, picture_edl)
    _write_json(audio_path, audio_timeline)
    return edl_path, audio_path
