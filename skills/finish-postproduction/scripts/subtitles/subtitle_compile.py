"""Compile Storyboard dialogue and the picture EDL into exact subtitle cues."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.segment.handoff import load_segment_handoff
from narrated_fable_drama.core.project_context import load_project_context
from .subtitle_style import (
    SubtitleBuildError,
    _caption_chunks,
    _caption_intervals,
    _is_cjk,
    _load_json,
    _minimum_display_interval,
    _number,
    _picture_events,
    _readability,
    _required_display_duration,
    _target_language,
    _validate_style,
)


def _source_time_to_retained_time(
    source_ranges: list[tuple[float, float]],
    source_time: float,
    *,
    tolerance_seconds: float,
) -> float | None:
    elapsed = 0.0
    for range_start, range_end in source_ranges:
        if (
            range_start - tolerance_seconds
            <= source_time
            <= range_end + tolerance_seconds
        ):
            return elapsed + max(
                0.0,
                min(range_end - range_start, source_time - range_start),
            )
        elapsed += range_end - range_start
    return None


def compile_cues(task_dir: Path, style_path: Path) -> dict[str, Any]:
    project_context = load_project_context(task_dir)
    style = _load_json(style_path)
    _validate_style(style)
    edl_path = (
        task_dir
        / ".pending"
        / "finish-postproduction"
        / "post-production"
        / "picture-audio-edl.json"
    )
    edl = _load_json(edl_path)
    events = _picture_events(edl)
    storyboards = load_segment_handoff(task_dir)
    storyboard_ids = list(storyboards)
    if storyboard_ids != list(events):
        raise SubtitleBuildError("Storyboard coverage/order differs from picture EDL.")
    language = _target_language(project_context)
    max_lines = int(style["max_lines"])
    if max_lines < 1:
        raise SubtitleBuildError("subtitle max_lines must be positive.")
    cues: list[dict[str, Any]] = []
    source_cue_count = 0
    editorial_refinement = edl.get("editorial_refinement")
    subtitle_timing_overrides = (
        editorial_refinement.get("subtitle_timing_overrides", {})
        if isinstance(editorial_refinement, dict)
        else {}
    )
    if not isinstance(subtitle_timing_overrides, dict):
        raise SubtitleBuildError("EDL subtitle_timing_overrides must be an object.")
    for segment_id, storyboard in storyboards.items():
        if storyboard.get("segment_id") != segment_id:
            raise SubtitleBuildError(f"Storyboard identity mismatch: {segment_id}")
        event = events[segment_id]
        event_duration = event["end"] - event["start"]
        storyboard_duration = _number(
            storyboard.get("duration_seconds"), f"{segment_id} Storyboard duration"
        )
        source_in = _number(
            event.get("source_in_seconds"), f"{segment_id} EDL source in"
        )
        source_out = _number(
            event.get("source_out_seconds"), f"{segment_id} EDL source out"
        )
        if source_in < 0 or source_out <= source_in:
            raise SubtitleBuildError(f"{segment_id} EDL source range is invalid.")
        if source_out > storyboard_duration + 0.25:
            raise SubtitleBuildError(
                f"{segment_id} EDL source out exceeds the Storyboard duration."
            )
        raw_ranges = event.get("source_ranges")
        if not isinstance(raw_ranges, list) or not raw_ranges:
            raise SubtitleBuildError(
                f"{segment_id} EDL lacks explicit retained source ranges."
            )
        source_ranges: list[tuple[float, float]] = []
        prior_range_end = source_in
        for range_index, source_range in enumerate(raw_ranges):
            if not isinstance(source_range, dict):
                raise SubtitleBuildError(
                    f"{segment_id} EDL source range {range_index + 1} is invalid."
                )
            range_start = _number(
                source_range.get("source_in_seconds"),
                f"{segment_id} retained source in",
            )
            range_end = _number(
                source_range.get("source_out_seconds"),
                f"{segment_id} retained source out",
            )
            if (
                range_start < source_in - 0.001
                or range_end > source_out + 0.001
                or range_end <= range_start
                or range_start < prior_range_end - 0.001
            ):
                raise SubtitleBuildError(
                    f"{segment_id} retained source ranges are invalid."
                )
            source_ranges.append((range_start, range_end))
            prior_range_end = range_end
        retained_duration = sum(
            range_end - range_start
            for range_start, range_end in source_ranges
        )
        if abs(event_duration - retained_duration) > 0.05:
            raise SubtitleBuildError(
                f"{segment_id} EDL duration differs from retained picture ranges."
            )

        def source_to_relative(source_time: float, *, cue_id: str) -> float:
            result = _source_time_to_retained_time(
                source_ranges,
                source_time,
                tolerance_seconds=0.05,
            )
            if result is not None:
                return result
            raise SubtitleBuildError(
                f"{segment_id} edit removes dialogue cue {cue_id}."
            )

        ordered_source_cues = [
            cue
            for source_block in storyboard.get("timeline_blocks", [])
            if isinstance(source_block, dict)
            for cue in source_block.get("dialogue_cues", [])
            if isinstance(cue, dict)
        ]
        source_cue_positions = {
            id(source_cue): index
            for index, source_cue in enumerate(ordered_source_cues)
        }

        def source_interval(source_cue: dict[str, Any]) -> tuple[float, float, bool]:
            cue_id = str(source_cue.get("cue_id") or "")
            authored_start = _number(source_cue.get("start_seconds"), "cue start")
            authored_end = _number(source_cue.get("end_seconds"), "cue end")
            override = subtitle_timing_overrides.get(cue_id)
            if override is None:
                return authored_start, authored_end, False
            if not isinstance(override, dict):
                raise SubtitleBuildError(
                    f"Subtitle timing override must be an object: {cue_id}"
                )
            return (
                _number(
                    override.get("source_start_seconds"),
                    f"{cue_id} overridden source start",
                ),
                _number(
                    override.get("source_end_seconds"),
                    f"{cue_id} overridden source end",
                ),
                True,
            )

        for block in storyboard.get("timeline_blocks", []):
            if not isinstance(block, dict):
                raise SubtitleBuildError(f"{segment_id} contains an invalid block.")
            for cue in block.get("dialogue_cues", []):
                if not isinstance(cue, dict):
                    raise SubtitleBuildError(f"{segment_id} contains an invalid cue.")
                authored_start = _number(cue.get("start_seconds"), "cue start")
                authored_end = _number(cue.get("end_seconds"), "cue end")
                source_start, source_end, timing_overridden = source_interval(cue)
                if source_end <= source_start:
                    raise SubtitleBuildError(f"{segment_id} cue timing is invalid.")
                containing_range = next(
                    (
                        (range_start, range_end)
                        for range_start, range_end in source_ranges
                        if source_start >= range_start - 0.05
                        and source_end <= range_end + 0.05
                    ),
                    None,
                )
                if containing_range is None:
                    raise SubtitleBuildError(
                        f"{segment_id} edit intersects dialogue cue {cue.get('cue_id')}."
                    )
                cue_id = str(cue.get("cue_id"))
                relative_start = source_to_relative(
                    source_start,
                    cue_id=cue_id,
                )
                relative_end = source_to_relative(
                    source_end,
                    cue_id=cue_id,
                )
                text = str(cue.get("exact_text", "")).strip()
                if not text:
                    raise SubtitleBuildError(f"{segment_id} cue has no exact text.")
                is_cjk = _is_cjk(text)
                line_limit = int(
                    style[
                        "max_characters_per_line_cjk"
                        if is_cjk
                        else "max_characters_per_line_latin"
                    ]
                )
                chunks = _caption_chunks(
                    text,
                    is_cjk=is_cjk,
                    line_limit=line_limit,
                    max_lines=max_lines,
                )
                minimum = _number(
                    style["minimum_cue_duration_seconds"],
                    "minimum_cue_duration_seconds",
                )
                required_duration = _required_display_duration(
                    text,
                    chunks,
                    is_cjk=is_cjk,
                    minimum_duration=minimum,
                    style=style,
                )
                source_position = source_cue_positions[id(cue)]
                previous_end = (
                    source_to_relative(
                        source_interval(
                            ordered_source_cues[source_position - 1]
                        )[1],
                        cue_id=str(
                            ordered_source_cues[source_position - 1].get(
                                "cue_id"
                            )
                        ),
                    )
                    if source_position > 0
                    else 0.0
                )
                next_start = (
                    source_to_relative(
                        source_interval(
                            ordered_source_cues[source_position + 1]
                        )[0],
                        cue_id=str(
                            ordered_source_cues[source_position + 1].get(
                                "cue_id"
                            )
                        ),
                    )
                    if source_position + 1 < len(ordered_source_cues)
                    else event_duration
                )
                relative_start, relative_end = _minimum_display_interval(
                    relative_start,
                    relative_end,
                    previous_end=previous_end,
                    next_start=next_start,
                    minimum_duration=required_duration,
                )
                source_cue_count += 1
                intervals = _caption_intervals(
                    relative_start,
                    relative_end,
                    chunks,
                    is_cjk=is_cjk,
                    minimum_duration=minimum,
                )
                source_cue_id = str(cue.get("cue_id"))
                for part_index, ((chunk_text, rendered_text), interval) in enumerate(
                    zip(chunks, intervals), start=1
                ):
                    part_start, part_end = interval
                    part_duration = part_end - part_start
                    timeline_start = event["start"] + part_start
                    timeline_end = event["start"] + part_end
                    cues.append(
                        {
                            "cue_index": len(cues) + 1,
                            "segment_id": segment_id,
                            "block_id": block.get("block_id"),
                            "cue_id": (
                                source_cue_id
                                if len(chunks) == 1
                                else f"{source_cue_id}-caption-{part_index:02d}"
                            ),
                            "source_cue_id": source_cue_id,
                            "source_cue_part_index": part_index,
                            "source_cue_part_count": len(chunks),
                            "screenplay_reference": cue.get("screenplay_reference"),
                            "speaker_entity_id": cue.get("speaker_entity_id"),
                            "speaker_screenplay_identity_en": cue.get(
                                "speaker_screenplay_identity_en"
                            ),
                            "source_exact_text": text,
                            "exact_text": chunk_text,
                            "rendered_text": rendered_text,
                            "language": language,
                            "authored_segment_start_seconds": round(authored_start, 3),
                            "authored_segment_end_seconds": round(authored_end, 3),
                            "source_segment_start_seconds": round(source_start, 3),
                            "source_segment_end_seconds": round(source_end, 3),
                            "editorial_timing_override_applied": timing_overridden,
                            "segment_start_seconds": round(part_start, 3),
                            "segment_end_seconds": round(part_end, 3),
                            "timeline_start_seconds": round(timeline_start, 3),
                            "timeline_end_seconds": round(timeline_end, 3),
                            "readability": _readability(
                                chunk_text, part_duration, style
                            ),
                        }
                    )
    for previous, current in zip(cues, cues[1:]):
        if current["timeline_start_seconds"] < previous["timeline_end_seconds"] - 0.001:
            raise SubtitleBuildError(
                f"Subtitle cues overlap: {previous['cue_id']} and {current['cue_id']}."
            )
    return {
        "contract": "finish-subtitle-cues-v2",
        "text_authority": "storyboard_ordered_shot_dialogue_cues",
        "timing_authority": "storyboard_speech_windows_plus_picture_edl",
        "language": language,
        "style_path": str(style_path.resolve()),
        "picture_edl_path": str(edl_path.resolve()),
        "source_cue_count": source_cue_count,
        "cue_count": len(cues),
        "cues": cues,
    }
