"""Compile Storyboard dialogue and the picture EDL into exact subtitle cues."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.segment.handoff import load_segment_handoff
from narrated_fable_drama.core.project_context import load_project_context

from .subtitle_alignment import (
    align_authoritative_cues,
    caption_intervals_from_alignment,
    transcribe_final_audio,
)
from .subtitle_style import (
    SubtitleBuildError,
    _caption_chunks,
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
    source_cue_specs = []
    for segment_id, storyboard in storyboards.items():
        event = events[segment_id]
        for block in storyboard.get("timeline_blocks", []):
            if not isinstance(block, dict):
                continue
            for cue in block.get("dialogue_cues", []):
                if not isinstance(cue, dict):
                    continue
                source_cue_specs.append(
                    {
                        "cue_id": str(cue.get("cue_id") or ""),
                        "exact_text": str(cue.get("exact_text") or "").strip(),
                        "segment_id": segment_id,
                        "window_start_seconds": event["start"],
                        "window_end_seconds": event["end"],
                    }
                )
    if any(
        not item["cue_id"] or not item["exact_text"] for item in source_cue_specs
    ):
        raise SubtitleBuildError(
            "Storyboard dialogue lacks a cue ID or exact subtitle text."
        )
    clean_master = (
        task_dir / "finish-postproduction" / "final-clean-master.mp4"
    ).resolve()
    words, alignment_evidence = transcribe_final_audio(
        clean_master,
        target_language=language,
        model_family=str(style["alignment_model_family"]),
        device=str(style["alignment_device"]),
        compute_type=str(style["alignment_compute_type"]),
        beam_size=int(style["alignment_beam_size"]),
        vad_filter=bool(style["alignment_vad_filter"]),
        ownership_windows=[
            (
                float(item["window_start_seconds"]),
                float(item["window_end_seconds"]),
            )
            for item in source_cue_specs
        ],
    )
    audio_alignments = align_authoritative_cues(
        source_cue_specs,
        words,
        minimum_token_coverage=_number(
            style["minimum_alignment_token_coverage"],
            "minimum_alignment_token_coverage",
        ),
        minimum_token_similarity=_number(
            style["minimum_alignment_token_similarity"],
            "minimum_alignment_token_similarity",
        ),
        lookahead_tokens=int(style["alignment_token_lookahead"]),
        outlier_gap_seconds=_number(
            style["alignment_outlier_gap_seconds"],
            "alignment_outlier_gap_seconds",
        ),
        outlier_probability_threshold=_number(
            style["alignment_outlier_probability_threshold"],
            "alignment_outlier_probability_threshold",
        ),
    )
    media_duration = _number(
        edl.get("duration_seconds"),
        "picture EDL duration",
    )
    source_cue_ids = [item["cue_id"] for item in source_cue_specs]
    source_cue_positions = {
        cue_id: index for index, cue_id in enumerate(source_cue_ids)
    }
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
    if subtitle_timing_overrides:
        raise SubtitleBuildError(
            "Source-window subtitle timing overrides are no longer valid; "
            "final-clean-master word alignment is required."
        )
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

        def source_interval(source_cue: dict[str, Any]) -> tuple[float, float]:
            authored_start = _number(source_cue.get("start_seconds"), "cue start")
            authored_end = _number(source_cue.get("end_seconds"), "cue end")
            return authored_start, authored_end

        for block in storyboard.get("timeline_blocks", []):
            if not isinstance(block, dict):
                raise SubtitleBuildError(f"{segment_id} contains an invalid block.")
            for cue in block.get("dialogue_cues", []):
                if not isinstance(cue, dict):
                    raise SubtitleBuildError(f"{segment_id} contains an invalid cue.")
                authored_start = _number(cue.get("start_seconds"), "cue start")
                authored_end = _number(cue.get("end_seconds"), "cue end")
                source_start, source_end = source_interval(cue)
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
                        f"{segment_id} edit intersects dialogue cue "
                        f"{cue.get('cue_id')}."
                    )
                cue_id = str(cue.get("cue_id"))
                source_to_relative(
                    source_start,
                    cue_id=cue_id,
                )
                source_to_relative(
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
                source_cue_count += 1
                alignment = audio_alignments[cue_id]
                intervals = caption_intervals_from_alignment(
                    alignment,
                    chunks,
                    lead_in_seconds=_number(
                        style["subtitle_lead_in_seconds"],
                        "subtitle_lead_in_seconds",
                    ),
                    trail_out_seconds=_number(
                        style["subtitle_trail_out_seconds"],
                        "subtitle_trail_out_seconds",
                    ),
                    media_duration_seconds=media_duration,
                )
                source_position = source_cue_positions[cue_id]
                prior_limit = event["start"]
                if source_position > 0:
                    prior_alignment = audio_alignments[
                        source_cue_ids[source_position - 1]
                    ]
                    prior_limit = max(
                        prior_limit,
                        float(prior_alignment["speech_end_seconds"])
                        + _number(
                            style["subtitle_trail_out_seconds"],
                            "subtitle_trail_out_seconds",
                        ),
                    )
                next_limit = event["end"]
                if source_position + 1 < len(source_cue_ids):
                    next_alignment = audio_alignments[
                        source_cue_ids[source_position + 1]
                    ]
                    next_limit = min(
                        next_limit,
                        float(next_alignment["speech_start_seconds"])
                        - _number(
                            style["subtitle_lead_in_seconds"],
                            "subtitle_lead_in_seconds",
                        ),
                    )
                readability_intervals: list[tuple[float, float]] = []
                for part_index, ((chunk_text, rendered_text), interval) in enumerate(
                    zip(chunks, intervals)
                ):
                    previous_end = (
                        readability_intervals[-1][1]
                        if readability_intervals
                        else prior_limit
                    )
                    following_start = (
                        intervals[part_index + 1][0]
                        if part_index + 1 < len(intervals)
                        else next_limit
                    )
                    required_duration = _required_display_duration(
                        chunk_text,
                        [(chunk_text, rendered_text)],
                        is_cjk=is_cjk,
                        minimum_duration=minimum,
                        style=style,
                    )
                    readability_intervals.append(
                        _minimum_display_interval(
                            interval[0],
                            interval[1],
                            previous_end=previous_end,
                            next_start=following_start,
                            minimum_duration=required_duration,
                        )
                    )
                intervals = readability_intervals
                if (
                    intervals[0][0] < event["start"] - 0.25
                    or intervals[-1][1] > event["end"] + 0.25
                ):
                    raise SubtitleBuildError(
                        f"Final-audio alignment places {cue_id} outside "
                        f"its owning Segment."
                    )
                source_cue_id = str(cue.get("cue_id"))
                for part_index, ((chunk_text, rendered_text), interval) in enumerate(
                    zip(chunks, intervals), start=1
                ):
                    timeline_start, timeline_end = interval
                    part_start = timeline_start - event["start"]
                    part_end = timeline_end - event["start"]
                    part_duration = timeline_end - timeline_start
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
                            "editorial_timing_override_applied": False,
                            "audio_alignment": {
                                "speech_start_seconds": alignment[
                                    "speech_start_seconds"
                                ],
                                "speech_end_seconds": alignment[
                                    "speech_end_seconds"
                                ],
                                "matched_token_count": alignment[
                                    "matched_token_count"
                                ],
                                "expected_token_count": alignment[
                                    "expected_token_count"
                                ],
                                "token_coverage": alignment["token_coverage"],
                                "mean_word_probability": alignment[
                                    "mean_word_probability"
                                ],
                                "anchor_repairs": alignment["anchor_repairs"],
                            },
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
        "timing_authority": "final_clean_master_word_alignment",
        "alignment_evidence": alignment_evidence,
        "language": language,
        "style_path": str(style_path.resolve()),
        "picture_edl_path": str(edl_path.resolve()),
        "source_cue_count": source_cue_count,
        "cue_count": len(cues),
        "cues": cues,
    }
