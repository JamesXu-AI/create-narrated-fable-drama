#!/usr/bin/env python3
"""Compile the authored semantic-boundary picture and native-audio timeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.contracts.boundary import classify_boundary
from narrated_fable_drama.contracts.screenplay import load_screenplay_file
from narrated_fable_drama.contracts.segment import (
    load_execution_plan,
    parse_segment_script,
    sha256_json,
    storyboard_segment_rows,
)
from narrated_fable_drama.core.json_io import load_json_object, write_json_atomic
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.media.ffmpeg import MediaCommandError
from narrated_fable_drama.media.probe import (
    fraction_as_float,
    probe_json,
    stream_by_type,
)
from finishing.plan import materialize_kept_ranges

SEGMENT_RE = re.compile(r"^segment-([0-9]{3})$")
MAX_FINAL_RUNTIME_SECONDS = 240.0


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


def discover_segments(
    task_dir: Path,
    *,
    validation_through_segment_id: str | None = None,
    allow_stale_preview: bool = False,
) -> list[SegmentRecord]:
    task_dir = task_dir.expanduser().resolve()
    if allow_stale_preview and validation_through_segment_id is None:
        raise TimelineError(
            "Stale-source inspection is allowed only for an explicit preview prefix"
        )
    _validate_project_audio(task_dir)
    story_plans, _ = _screenplay_story_plans(task_dir)
    if validation_through_segment_id is not None:
        story_ids = [str(item["segment_id"]) for item in story_plans]
        if validation_through_segment_id not in story_ids:
            raise TimelineError(
                f"Unknown validation Segment ID: {validation_through_segment_id}"
            )
        story_plans = story_plans[
            : story_ids.index(validation_through_segment_id) + 1
        ]
    expected = [
        str(item["segment_id"])
        for item in storyboard_segment_rows(
            task_dir,
            validation_through_segment_id=validation_through_segment_id,
        )
    ]
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
    if validation_through_segment_id is not None:
        actual_media = [
            item for item in actual_media if item <= validation_through_segment_id
        ]
        actual_scripts = [
            item for item in actual_scripts if item <= validation_through_segment_id
        ]
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
        if not allow_stale_preview and (
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


def compile_timelines(
    task_dir: Path,
    repair_plan: dict[str, Any],
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
    if len(authored_boundaries) != max(0, len(records) - 1):
        raise TimelineError("Authored boundary coverage differs from current media")
    segment_plans = repair_plan["segments"]
    model_boundaries = repair_plan["boundaries"]
    if (
        [item["segment_id"] for item in segment_plans]
        != [record.segment_name for record in records]
        or len(model_boundaries) != max(0, len(records) - 1)
    ):
        raise TimelineError("Model repair-plan coverage differs from current media")
    cursor = 0.0
    for index, record in enumerate(records):
        segment_plan = segment_plans[index]
        picture_plan = segment_plan["picture"]
        audio_plan = segment_plan["audio"]
        source_in = float(picture_plan["source_in_seconds"])
        source_out = float(picture_plan["source_out_seconds"])
        picture_ranges = materialize_kept_ranges(picture_plan)
        duration = sum(
            float(item["source_out_seconds"])
            - float(item["source_in_seconds"])
            for item in picture_ranges
        )
        incoming_boundary = model_boundaries[index - 1] if index else None
        incoming_overlap = (
            float(incoming_boundary["picture"]["overlap_seconds"])
            if incoming_boundary is not None
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
            "source_ranges": picture_ranges,
            "removed_intervals": picture_plan["removed_intervals"],
            "timeline_in_seconds": round(start, 6),
            "timeline_out_seconds": round(end, 6),
            "duration_seconds": round(duration, 6),
        }
        picture_events.append(
            {
                **common,
                "edit": (
                    incoming_boundary["picture"]["operation"]
                    if incoming_boundary is not None
                    else "opening"
                ),
                "script": str(record.script_path),
                "color_adjustments": picture_plan["color_adjustments"],
                "model_reason": segment_plan["reason"],
            }
        )
        audio_source_in = float(audio_plan["source_in_seconds"])
        audio_source_out = float(audio_plan["source_out_seconds"])
        audio_ranges = materialize_kept_ranges(audio_plan)
        audio_start = start + float(
            audio_plan["timeline_offset_from_picture_in_seconds"]
        )
        audio_duration = sum(
            float(item["source_out_seconds"])
            - float(item["source_in_seconds"])
            for item in audio_ranges
        )
        if audio_start < -1e-6:
            raise TimelineError(
                f"{record.segment_name} audio begins before the final timeline"
            )
        native_events.append(
            {
                "event_id": f"native-{record.segment_name}",
                "segment_id": record.segment_name,
                "source": str(record.video_path),
                "source_in_seconds": round(audio_source_in, 6),
                "source_out_seconds": round(audio_source_out, 6),
                "source_ranges": audio_ranges,
                "removed_intervals": audio_plan["removed_intervals"],
                "timeline_in_seconds": round(audio_start, 6),
                "timeline_out_seconds": round(audio_start + audio_duration, 6),
                "duration_seconds": round(audio_duration, 6),
                "purpose": "seedance_native_dialogue_foley_ambience_and_background_music",
                "has_source_audio": True,
                "voice_audio_source": "speaker_reference_audio",
                "dialogue_source": "seedance",
                "native_ambience_source": "seedance",
                "background_music_source": "seedance_native",
                "seedance_background_music": True,
                "preserve_lip_sync": True,
                "gain_db": audio_plan["gain_db"],
                "fade_in_seconds": audio_plan["fade_in_seconds"],
                "fade_out_seconds": audio_plan["fade_out_seconds"],
                "gain_adjustments": audio_plan["gain_adjustments"],
            }
        )
        if index + 1 < len(records):
            boundary_plan = model_boundaries[index]
            authored = authored_boundaries[index]
            successor = story_plans[index + 1]
            predecessor = story_plans[index]
            if (
                authored.get("from_segment_id") != record.segment_name
                or authored.get("to_segment_id") != records[index + 1].segment_name
                or boundary_plan.get("from") != record.segment_name
                or boundary_plan.get("to") != records[index + 1].segment_name
            ):
                raise TimelineError("Boundary order differs between authored and model plans")
            overlap = float(boundary_plan["picture"]["overlap_seconds"])
            picture_operation = str(boundary_plan["picture"]["operation"])
            transition_class = classify_boundary(
                transition_type=str(authored["transition_type"]),
                from_scene_id=str(predecessor["scene_id"]),
                to_scene_id=str(successor["scene_id"]),
                successor_incoming_visual_requirement=str(authored["handoff"]),
            )
            boundary = {
                    "from": record.segment_name,
                    "to": records[index + 1].segment_name,
                    "boundary_id": boundary_plan["boundary_id"],
                    "authored_transition_type": authored["transition_type"],
                    "authored_audio_handoff": authored["audio_handoff"],
                    "transition_class": transition_class,
                    "timeline_seconds": round(end - overlap, 6),
                    "transition_start_seconds": round(end - overlap, 6),
                    "transition_end_seconds": round(end, 6),
                    "picture_edit": picture_operation,
                    "audio_edit": boundary_plan["audio"]["operation"],
                    "outgoing_audio_fade_seconds": boundary_plan["audio"][
                        "outgoing_fade_out_seconds"
                    ],
                    "incoming_audio_fade_seconds": boundary_plan["audio"][
                        "incoming_fade_in_seconds"
                    ],
                    "overlap_seconds": round(overlap, 6),
                    "outgoing_source_out_seconds": round(source_out, 6),
                    "incoming_source_in_seconds": round(
                        float(
                            segment_plans[index + 1]["picture"][
                                "source_in_seconds"
                            ]
                        ),
                        6,
                    ),
                    "decision": boundary_plan["decision"],
                    "scope": boundary_plan["scope"],
                    "modification_intervals": boundary_plan[
                        "modification_intervals"
                    ],
                    "model_reason": boundary_plan["reason"],
                }
            boundaries.append(boundary)
        cursor = end
    if cursor > runtime_limit_seconds + 1e-6:
        raise TimelineError(
            f"Final runtime {cursor:.3f}s exceeds {runtime_limit_seconds:.3f}s"
        )
    bridge_events = []
    for bridge in repair_plan["audio_bridges"]:
        source_record = next(
            record
            for record in records
            if record.segment_name == bridge["source_segment_id"]
        )
        source_duration = float(bridge["source_out_seconds"]) - float(
            bridge["source_in_seconds"]
        )
        bridge_events.append(
            {
                **bridge,
                "source": str(source_record.video_path),
                "timeline_out_seconds": round(
                    float(bridge["timeline_in_seconds"]) + source_duration,
                    6,
                ),
                "duration_seconds": round(source_duration, 6),
            }
        )
    last_audio_end = max(
        [
            *(float(event["timeline_out_seconds"]) for event in native_events),
            *(float(event["timeline_out_seconds"]) for event in bridge_events),
        ]
    )
    if last_audio_end + 1e-6 < cursor:
        raise TimelineError(
            "Explicit audio events end before picture; automatic silence padding is forbidden"
        )

    picture_edl = {
        "contract": "finish-picture-audio-edl/v2",
        "edit_policy": "model_authored_from_real_media_evidence",
        "repair_plan_contract": repair_plan["contract"],
        "segment_count": len(records),
        "duration_seconds": round(cursor, 6),
        "picture_events": picture_events,
        "boundaries": boundaries,
    }
    audio_timeline = {
        "contract": "finish-native-audio-timeline/v2",
        "duration_seconds": round(cursor, 6),
        "native_audio_policy": {
            "generate_audio": True,
            "voice_audio_source": "speaker_reference_audio",
            "dialogue_source": "seedance",
            "native_ambience_source": "seedance",
            "seedance_background_music": True,
            "background_music_source": "seedance_native",
            "preserve_clip_sync": True,
            "automatic_silence_padding": False,
            "model_authored_event_placement": True,
            "terminal_audio": repair_plan["terminal_audio"],
        },
        "tracks": [
            {
                "track_id": "native-sync",
                "source": "seedance",
                "role": "synchronized_dialogue_foley_and_ambience",
                "events": native_events,
            }
        ],
        "audio_bridges": bridge_events,
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
