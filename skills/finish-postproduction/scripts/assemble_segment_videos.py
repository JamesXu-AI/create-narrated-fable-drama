#!/usr/bin/env python3
"""Assemble current Seedance Segment outputs into a task-local picture lock."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


from post_timeline import (
    MAX_FINAL_RUNTIME_SECONDS,
    SegmentRecord,
    TimelineError,
    compile_timelines,
    discover_segments,
    probe_media,
    write_timeline_artifacts,
)
from boundary.qc import (
    BoundaryQCError,
    audit_picture_lock,
    prepare_boundary_qc,
)
from finishing.plan import (
    RepairPlanError,
    ensure_renderable,
    load_repair_plan,
)
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.core.json_io import write_json_atomic
from narrated_fable_drama.media.ffmpeg import (
    MediaCommandError,
    run as run_media_command,
)


def _delivery_dimensions(
    project_context: dict[str, Any], first: SegmentRecord
) -> tuple[int, int]:
    resolution = str(project_context.get("resolution") or "").lower().removesuffix("p")
    short_side_by_resolution = {"480": 480, "720": 720, "1080": 1080, "4k": 2160}
    if resolution not in short_side_by_resolution:
        raise TimelineError("screenplay.md Resolution is invalid")
    aspect = str(project_context.get("aspect_ratio") or "")
    try:
        width_ratio, height_ratio = (int(value) for value in aspect.split(":", 1))
    except (ValueError, TypeError) as exc:
        raise TimelineError("screenplay.md Aspect Ratio is invalid") from exc
    if width_ratio <= 0 or height_ratio <= 0:
        raise TimelineError("screenplay.md Aspect Ratio must be positive")
    short_side = short_side_by_resolution[resolution]
    if width_ratio >= height_ratio:
        height = short_side
        width = round(short_side * width_ratio / height_ratio)
    else:
        width = short_side
        height = round(short_side * height_ratio / width_ratio)
    width += width % 2
    height += height % 2
    return width, height


def _event_source_ranges(
    event: dict[str, Any],
    *,
    segment_id: str,
    media: str,
    source_duration: float,
) -> list[tuple[float, float]]:
    raw = event.get("source_ranges")
    if not isinstance(raw, list) or not raw:
        raise TimelineError(f"{segment_id} lacks explicit {media} source ranges")
    ranges: list[tuple[float, float]] = []
    prior_end = -1.0
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise TimelineError(
                f"{segment_id} {media} source range {index + 1} is invalid"
            )
        source_in = float(item["source_in_seconds"])
        source_out = float(item["source_out_seconds"])
        if (
            source_in < 0
            or source_out <= source_in
            or source_out > source_duration + 1e-3
            or source_in < prior_end - 1e-6
        ):
            raise TimelineError(
                f"{segment_id} {media} source ranges are invalid"
            )
        ranges.append((source_in, source_out))
        prior_end = source_out
    return ranges


def _render_filter(
    records: list[SegmentRecord],
    width: int,
    height: int,
    picture_edl: dict[str, Any],
    audio_timeline: dict[str, Any],
    delivery: dict[str, Any],
) -> str:
    boundaries = picture_edl["boundaries"]
    picture_events = picture_edl["picture_events"]
    if len(boundaries) != max(0, len(records) - 1):
        raise TimelineError("Rendered boundary coverage differs from Segment coverage")
    frame_rate = records[0].probe.frame_rate
    sample_rate = int(delivery["sample_rate_hz"])
    channel_layout = str(delivery["channel_layout"])
    filters: list[str] = []
    if [item.get("segment_id") for item in picture_events] != [
        record.segment_name for record in records
    ]:
        raise TimelineError("Picture-event coverage differs from Segment coverage")
    tracks = audio_timeline.get("tracks")
    if (
        not isinstance(tracks, list)
        or len(tracks) != 1
        or not isinstance(tracks[0], dict)
        or not isinstance(tracks[0].get("events"), list)
    ):
        raise TimelineError("Audio timeline must contain one explicit dubbed track")
    native_events = tracks[0]["events"]
    if [item.get("segment_id") for item in native_events] != [
        record.segment_name for record in records
    ]:
        raise TimelineError("Dubbed-audio event coverage differs from Segment coverage")
    bridges = audio_timeline.get("audio_bridges")
    if not isinstance(bridges, list):
        raise TimelineError("Audio timeline lacks explicit audio_bridges")
    record_index_by_id = {
        record.segment_name: index for index, record in enumerate(records)
    }
    picture_ranges_by_id = {
        record.segment_name: _event_source_ranges(
            picture_events[index],
            segment_id=record.segment_name,
            media="picture",
            source_duration=record.probe.duration_seconds,
        )
        for index, record in enumerate(records)
    }
    audio_ranges_by_id = {
        record.segment_name: _event_source_ranges(
            native_events[index],
            segment_id=record.segment_name,
            media="audio",
            source_duration=record.probe.duration_seconds,
        )
        for index, record in enumerate(records)
    }
    video_source_labels: dict[str, list[str]] = {}
    for record in records:
        count = len(picture_ranges_by_id[record.segment_name])
        index = record_index_by_id[record.segment_name]
        if count == 1:
            video_source_labels[record.segment_name] = [f"{index}:v:0"]
            continue
        labels = [
            f"vsource{index}_{consumer_index}"
            for consumer_index in range(count)
        ]
        filters.append(
            f"[{index}:v:0]split={count}"
            + "".join(f"[{label}]" for label in labels)
        )
        video_source_labels[record.segment_name] = labels
    audio_use_count = {
        record.segment_name: len(audio_ranges_by_id[record.segment_name])
        for record in records
    }
    for bridge in bridges:
        source_segment_id = str(bridge["source_segment_id"])
        if source_segment_id not in audio_use_count:
            raise TimelineError("Audio bridge references an unknown Segment")
        audio_use_count[source_segment_id] += 1
    audio_source_labels: dict[str, list[str]] = {}
    for record in records:
        count = audio_use_count[record.segment_name]
        index = record_index_by_id[record.segment_name]
        if count == 1:
            audio_source_labels[record.segment_name] = [f"{index}:a:0"]
            continue
        labels = [
            f"asource{index}_{consumer_index}"
            for consumer_index in range(count)
        ]
        filters.append(
            f"[{index}:a:0]asplit={count}"
            + "".join(f"[{label}]" for label in labels)
        )
        audio_source_labels[record.segment_name] = labels
    rendered_durations: list[float] = []
    for index, record in enumerate(records):
        event = picture_events[index]
        picture_ranges = picture_ranges_by_id[record.segment_name]
        duration = sum(source_out - source_in for source_in, source_out in picture_ranges)
        rendered_durations.append(duration)
        if not record.probe.has_audio:
            raise TimelineError(
                f"{record.segment_name} has no ElevenLabs dubbed audio"
            )
        color_adjustments = event.get("color_adjustments")
        if not isinstance(color_adjustments, list):
            raise TimelineError(
                f"{record.segment_name} lacks explicit color adjustments"
            )
        video_part_labels: list[str] = []
        for range_index, (source_in, source_out) in enumerate(picture_ranges):
            video_filters = [
                f"trim=start={source_in:.6f}:end={source_out:.6f}",
                "setpts=PTS-STARTPTS",
                f"scale={width}:{height}:force_original_aspect_ratio=decrease",
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
                "setsar=1",
                f"fps={frame_rate}",
                f"format={delivery['pixel_format']}",
                "settb=AVTB",
            ]
            for adjustment in color_adjustments:
                adjustment_start = float(adjustment["source_start_seconds"])
                adjustment_end = float(adjustment["source_end_seconds"])
                if (
                    adjustment_start < source_in - 1e-6
                    or adjustment_end > source_out + 1e-6
                ):
                    continue
                local_start = adjustment_start - source_in
                local_end = adjustment_end - source_in
                video_filters.append(
                    "eq="
                    f"brightness={float(adjustment['brightness']):.6f}:"
                    f"contrast={float(adjustment['contrast']):.6f}:"
                    f"saturation={float(adjustment['saturation']):.6f}:"
                    f"gamma={float(adjustment['gamma']):.6f}:"
                    f"enable='between(t,{local_start:.6f},{local_end:.6f})'"
                )
            part_label = f"vpart{index}_{range_index}"
            source_label = video_source_labels[record.segment_name].pop(0)
            filters.append(
                f"[{source_label}]{','.join(video_filters)}[{part_label}]"
            )
            video_part_labels.append(part_label)
        if len(video_part_labels) == 1:
            filters.append(f"[{video_part_labels[0]}]null[v{index}]")
        else:
            filters.append(
                "".join(f"[{label}]" for label in video_part_labels)
                + f"concat=n={len(video_part_labels)}:v=1:a=0[v{index}]"
            )

        audio_event = native_events[index]
        audio_ranges = audio_ranges_by_id[record.segment_name]
        audio_duration = sum(
            source_out - source_in for source_in, source_out in audio_ranges
        )
        gain_adjustments = audio_event.get("gain_adjustments")
        if not isinstance(gain_adjustments, list):
            raise TimelineError(
                f"{record.segment_name} lacks explicit local gain adjustments"
            )
        audio_part_labels: list[str] = []
        for range_index, (source_in, source_out) in enumerate(audio_ranges):
            part_filters = [
                f"atrim=start={source_in:.6f}:end={source_out:.6f}",
                "asetpts=PTS-STARTPTS",
                f"aresample={sample_rate}",
                (
                    "aformat=sample_fmts=fltp:"
                    f"sample_rates={sample_rate}:channel_layouts={channel_layout}"
                ),
            ]
            for adjustment in gain_adjustments:
                adjustment_start = float(adjustment["source_start_seconds"])
                adjustment_end = float(adjustment["source_end_seconds"])
                if (
                    adjustment_start < source_in - 1e-6
                    or adjustment_end > source_out + 1e-6
                ):
                    continue
                local_start = adjustment_start - source_in
                local_end = adjustment_end - source_in
                part_filters.append(
                    f"volume={float(adjustment['gain_db']):.6f}dB:"
                    f"enable='between(t,{local_start:.6f},{local_end:.6f})'"
                )
            part_label = f"apart{index}_{range_index}"
            source_label = audio_source_labels[record.segment_name].pop(0)
            filters.append(
                f"[{source_label}]{','.join(part_filters)}[{part_label}]"
            )
            audio_part_labels.append(part_label)
        audio_base_label = f"abase{index}"
        if len(audio_part_labels) == 1:
            filters.append(
                f"[{audio_part_labels[0]}]anull[{audio_base_label}]"
            )
        else:
            filters.append(
                "".join(f"[{label}]" for label in audio_part_labels)
                + f"concat=n={len(audio_part_labels)}:v=0:a=1"
                f"[{audio_base_label}]"
            )
        audio_filters = [
            f"volume={float(audio_event['gain_db']):.6f}dB",
        ]
        fade_in = float(audio_event["fade_in_seconds"])
        fade_out = float(audio_event["fade_out_seconds"])
        if fade_in > 0:
            audio_filters.append(f"afade=t=in:st=0:d={fade_in:.6f}")
        if fade_out > 0:
            audio_filters.append(
                f"afade=t=out:st={audio_duration - fade_out:.6f}:d={fade_out:.6f}"
            )
        delay = float(audio_event["timeline_in_seconds"])
        if delay > 0:
            delay_samples = round(delay * sample_rate)
            audio_filters.append(f"adelay={delay_samples}S:all=1")
        filters.append(
            f"[{audio_base_label}]{','.join(audio_filters)}[a{index}]"
        )

    current_video = "v0"
    current_duration = rendered_durations[0]
    for index, boundary in enumerate(boundaries, start=1):
        next_video = f"v{index}"
        output_video = f"vjoin{index}"
        picture_edit = boundary["picture_edit"]
        overlap = float(boundary["overlap_seconds"])
        if picture_edit in {"dissolve", "fade"}:
            if overlap <= 0 or overlap >= min(
                current_duration, rendered_durations[index]
            ):
                raise TimelineError(
                    f"{boundary['from']}->{boundary['to']} has invalid transition overlap"
                )
            transition = "fade" if picture_edit == "dissolve" else "fadeblack"
            offset = current_duration - overlap
            filters.append(
                f"[{current_video}][{next_video}]xfade=transition={transition}:"
                f"duration={overlap:.6f}:offset={offset:.6f}[{output_video}]"
            )
            current_duration += rendered_durations[index] - overlap
        elif picture_edit in {"hard_cut", "baked_effect"}:
            if overlap != 0:
                raise TimelineError(
                    f"{boundary['from']}->{boundary['to']} hard boundary cannot overlap"
                )
            filters.append(
                f"[{current_video}][{next_video}]concat=n=2:v=1:a=0[{output_video}]"
            )
            current_duration += rendered_durations[index]
        else:
            raise TimelineError(f"Unsupported picture edit: {picture_edit}")
        current_video = output_video
    filters.append(f"[{current_video}]null[vout]")

    audio_labels = [f"a{index}" for index in range(len(native_events))]
    for bridge_index, bridge in enumerate(bridges):
        source_in = float(bridge["source_in_seconds"])
        source_out = float(bridge["source_out_seconds"])
        bridge_duration = source_out - source_in
        bridge_filters = [
            f"atrim=start={source_in:.6f}:end={source_out:.6f}",
            "asetpts=PTS-STARTPTS",
            f"aresample={sample_rate}",
            (
                "aformat=sample_fmts=fltp:"
                f"sample_rates={sample_rate}:channel_layouts={channel_layout}"
            ),
            f"volume={float(bridge['gain_db']):.6f}dB",
        ]
        fade_in = float(bridge["fade_in_seconds"])
        fade_out = float(bridge["fade_out_seconds"])
        if fade_in > 0:
            bridge_filters.append(f"afade=t=in:st=0:d={fade_in:.6f}")
        if fade_out > 0:
            bridge_filters.append(
                f"afade=t=out:st={bridge_duration - fade_out:.6f}:d={fade_out:.6f}"
            )
        timeline_in = float(bridge["timeline_in_seconds"])
        if timeline_in > 0:
            bridge_filters.append(
                f"adelay={round(timeline_in * sample_rate)}S:all=1"
            )
        label = f"abridge{bridge_index}"
        source_audio_label = audio_source_labels[
            str(bridge["source_segment_id"])
        ].pop(0)
        filters.append(
            f"[{source_audio_label}]{','.join(bridge_filters)}[{label}]"
        )
        audio_labels.append(label)

    if len(audio_labels) == 1:
        filters.append(f"[{audio_labels[0]}]anull[amixed]")
    else:
        joined = "".join(f"[{label}]" for label in audio_labels)
        filters.append(
            f"{joined}amix=inputs={len(audio_labels)}:"
            "duration=longest:normalize=0[amixed]"
        )
    total_duration = float(picture_edl["duration_seconds"])
    final_audio_filters = [
        f"atrim=start=0:end={total_duration:.6f}",
        "asetpts=PTS-STARTPTS",
    ]
    terminal = audio_timeline["native_audio_policy"]["terminal_audio"]
    terminal_fade = float(terminal["fade_out_seconds"])
    if terminal_fade > total_duration:
        raise TimelineError("Explicit terminal audio fade exceeds final runtime")
    if terminal_fade > 0:
        final_audio_filters.append(
            f"afade=t=out:st={total_duration - terminal_fade:.6f}:"
            f"d={terminal_fade:.6f}"
        )
    filters.append(f"[amixed]{','.join(final_audio_filters)}[aout]")
    return ";".join(filters)


def render_picture_lock(
    records: list[SegmentRecord],
    output: Path,
    project_context: dict[str, Any],
    picture_edl: dict[str, Any],
    audio_timeline: dict[str, Any],
    repair_plan: dict[str, Any],
    *,
    timeline_window: tuple[float, float] | None = None,
) -> None:
    width, height = _delivery_dimensions(project_context, records[0])
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for record in records:
        command.extend(["-i", str(record.video_path)])
    command.extend(
        [
            "-filter_complex",
            _render_filter(
                records,
                width,
                height,
                picture_edl,
                audio_timeline,
                repair_plan["delivery"],
            ),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
        ]
    )
    if timeline_window is not None:
        window_start, window_end = timeline_window
        if window_start < 0 or window_end <= window_start:
            raise TimelineError("Candidate timeline window is invalid")
        command.extend(
            [
                "-ss",
                f"{window_start:.6f}",
                "-t",
                f"{window_end - window_start:.6f}",
            ]
        )
    command.extend(
        [
            "-c:v",
            str(repair_plan["delivery"]["video_codec"]),
            "-preset",
            str(repair_plan["delivery"]["preset"]),
            "-crf",
            str(repair_plan["delivery"]["crf"]),
            "-pix_fmt",
            str(repair_plan["delivery"]["pixel_format"]),
            "-c:a",
            str(repair_plan["delivery"]["audio_codec"]),
            "-b:a",
            str(repair_plan["delivery"]["audio_bitrate"]),
            "-ar",
            str(repair_plan["delivery"]["sample_rate_hz"]),
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    try:
        run_media_command(command, context="Picture-lock render")
    except MediaCommandError as exc:
        raise TimelineError("Picture-lock render failed") from exc


def assemble(
    task_dir: Path,
    *,
    repair_plan_path: Path,
    evidence_manifest_path: Path,
    edl_only: bool = False,
) -> Path:
    task_dir = task_dir.expanduser().resolve()
    records = discover_segments(task_dir)
    repair_plan = load_repair_plan(
        repair_plan_path,
        evidence_manifest_path,
        records,
    )
    ensure_renderable(repair_plan)
    picture_edl, audio_timeline = compile_timelines(
        task_dir,
        repair_plan,
        records,
    )
    output = (
        task_dir
        / ".pending"
        / "finish-postproduction"
        / "post-production"
        / "dubbed-picture-lock.mp4"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if not edl_only:
        try:
            qc_manifest_path, _, qc_manifest = prepare_boundary_qc(
                task_dir,
                records,
                picture_edl,
            )
        except BoundaryQCError as exc:
            raise TimelineError(f"Boundary QC preparation failed: {exc}") from exc
        model_boundary_by_id = {
            str(item["boundary_id"]): item
            for item in repair_plan["boundaries"]
        }
        for item in qc_manifest["boundaries"]:
            model_boundary = model_boundary_by_id[str(item["boundary_id"])]
            item["model_decision"] = {
                "decision": model_boundary["decision"],
                "scope": model_boundary["scope"],
                "picture": model_boundary["picture"],
                "audio": model_boundary["audio"],
                "reason": model_boundary["reason"],
            }
        model_repair_count = sum(
            item["decision"] == "repair"
            for item in repair_plan["boundaries"]
        )
        qc_manifest.update(
            {
                "decision_authority": "editor-restoration-master-model",
                "model_repair_plan": str(
                    repair_plan_path.expanduser().resolve()
                ),
                "evidence_manifest": str(
                    evidence_manifest_path.expanduser().resolve()
                ),
                "planned_repair_count": model_repair_count,
            }
        )
        write_json_atomic(qc_manifest_path, qc_manifest, sort_keys=True)
        if qc_manifest.get("pre_assembly_status") == "review_required":
            blockers = ", ".join(qc_manifest.get("blocking_boundaries", []))
            raise TimelineError(
                "Boundary QC requires visual review before picture lock: " + blockers
            )
        render_picture_lock(
            records,
            output,
            load_project_context(task_dir),
            picture_edl,
            audio_timeline,
            repair_plan,
        )
        rendered = probe_media(output)
        expected = float(picture_edl["duration_seconds"])
        if not rendered.has_audio:
            raise TimelineError("Dubbed picture lock has no audio stream")
        if rendered.duration_seconds > MAX_FINAL_RUNTIME_SECONDS + 1e-3:
            raise TimelineError("Dubbed picture lock exceeds 240 seconds")
        if abs(rendered.duration_seconds - expected) > 0.25:
            raise TimelineError("Dubbed picture-lock duration differs from its EDL")
        picture_edl.update(
            {
                "rendered_output": str(output.resolve()),
                "rendered_output_role": "native_picture_lock",
                "final_delivery_status": "ready_for_clean_master",
                "rendered_duration_seconds": round(rendered.duration_seconds, 6),
                "resolution": {"width": rendered.width, "height": rendered.height},
                "audio_stream_present": True,
                "boundary_qc": {
                    "manifest": str(qc_manifest_path.resolve()),
                    "planned_repair_count": model_repair_count,
                    "source_segments_mutated": False,
                },
                "model_repair_plan": str(
                    repair_plan_path.expanduser().resolve()
                ),
                "evidence_manifest": str(
                    evidence_manifest_path.expanduser().resolve()
                ),
            }
        )
        try:
            final_qc = audit_picture_lock(
                output,
                picture_edl,
                qc_manifest_path,
            )
        except BoundaryQCError as exc:
            raise TimelineError(f"Final-timeline boundary audit failed: {exc}") from exc
        picture_edl["boundary_qc"].update(
            {
                "final_timeline_status": final_qc.get("final_timeline_status"),
                "final_timeline_blocking_boundaries": final_qc.get(
                    "final_timeline_blocking_boundaries", []
                ),
            }
        )
        if final_qc.get("final_timeline_status") == "review_required":
            blockers = ", ".join(
                final_qc.get("final_timeline_blocking_boundaries", [])
            )
            raise TimelineError(
                "Rendered picture lock has a residual boundary anomaly requiring "
                f"visual review: {blockers}"
            )
    edl_path, audio_path = write_timeline_artifacts(task_dir, picture_edl, audio_timeline)
    print(f"picture/audio EDL: {edl_path}", flush=True)
    print(f"audio timeline: {audio_path}", flush=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--repair-plan", required=True, type=Path)
    parser.add_argument("--evidence-manifest", required=True, type=Path)
    parser.add_argument("--edl-only", action="store_true")
    args = parser.parse_args()
    try:
        print(
            assemble(
                args.task_dir,
                repair_plan_path=args.repair_plan,
                evidence_manifest_path=args.evidence_manifest,
                edl_only=args.edl_only,
            )
        )
    except (TimelineError, RepairPlanError, MediaCommandError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
