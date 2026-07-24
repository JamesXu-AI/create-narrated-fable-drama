"""Subtitle style validation, wrapping, readability, and EDL timing helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.core.json_io import load_json_object
from narrated_fable_drama.core.paths import ProjectPaths


SKILL_ROOT = (
    ProjectPaths.resolve(Path(__file__)).repository_root
    / "skills/finish-postproduction"
)

DEFAULT_STYLE = SKILL_ROOT / "assets" / "subtitle-style.json"
ASS_PLAY_RESOLUTION_HEIGHT = 288.0
SEGMENT_RE = re.compile(r"^segment-([0-9]{3,})$")
STYLE_KEYS = {
    "contract",
    "text_authority",
    "timing_authority",
    "max_lines",
    "max_characters_per_line_cjk",
    "max_characters_per_line_latin",
    "minimum_cue_duration_seconds",
    "maximum_characters_per_second_cjk",
    "maximum_words_per_minute_latin",
    "position",
    "bottom_margin_percent",
    "font_family",
    "font_size_percent_of_frame_height",
    "font_weight",
    "text_color",
    "outline_color",
    "outline_width_percent_of_frame_height",
    "shadow",
    "background_box",
    "speaker_labels",
    "burn_in_required",
    "external_srt_required",
    "external_vtt_required",
}


class SubtitleBuildError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    return load_json_object(
        path,
        label=path.name,
        error_type=SubtitleBuildError,
    )


def _number(value: Any, label: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < minimum:
        raise SubtitleBuildError(f"{label} must be numeric and >= {minimum}.")
    return float(value)


def _validate_style(style: dict[str, Any]) -> None:
    if set(style) != STYLE_KEYS:
        raise SubtitleBuildError(
            f"Subtitle style must use exact keys: {sorted(STYLE_KEYS)}"
        )
    if style["contract"] != "finish-subtitle-style":
        raise SubtitleBuildError("Unsupported subtitle-style contract.")
    if style["text_authority"] != "storyboard_ordered_shot_dialogue_cues":
        raise SubtitleBuildError(
            "Subtitle text authority must be Storyboard-derived Segment cues."
        )
    if (
        style["timing_authority"]
        != "storyboard_speech_windows_plus_picture_edl"
    ):
        raise SubtitleBuildError("Subtitle timing authority is invalid.")
    for field in (
        "shadow",
        "background_box",
        "speaker_labels",
        "burn_in_required",
        "external_srt_required",
        "external_vtt_required",
    ):
        if not isinstance(style[field], bool):
            raise SubtitleBuildError(f"subtitle style {field} must be boolean.")


def _segment_name(value: Any) -> str:
    if isinstance(value, bool):
        raise SubtitleBuildError("EDL Segment ID cannot be boolean.")
    if isinstance(value, int):
        name = f"segment-{value:03d}"
    else:
        raw = str(value).strip()
        name = raw if raw.startswith("segment-") else f"segment-{int(raw):03d}"
    if not SEGMENT_RE.fullmatch(name):
        raise SubtitleBuildError(f"Invalid EDL Segment ID: {value!r}")
    return name


def _target_language(project_context: dict[str, Any]) -> str:
    value = project_context.get("target_language")
    if not isinstance(value, str) or not value.strip():
        raise SubtitleBuildError("screenplay.md Target Language is invalid.")
    return value.strip()


def _is_cjk(text: str) -> bool:
    return any(
        "\u3400" <= char <= "\u4dbf"
        or "\u4e00" <= char <= "\u9fff"
        or "\u3040" <= char <= "\u30ff"
        or "\uac00" <= char <= "\ud7af"
        for char in text
    )


def _wrap_cjk(text: str, limit: int, max_lines: int) -> str:
    compact = "".join(text.split())
    lines = [compact[index : index + limit] for index in range(0, len(compact), limit)]
    if len(lines) > max_lines:
        raise SubtitleBuildError(
            f"Subtitle needs {len(lines)} CJK lines; maximum is {max_lines}: {text!r}"
        )
    return "\n".join(lines)


def _wrap_words(text: str, limit: int, max_lines: int) -> str:
    normalized = " ".join(text.split())
    words = normalized.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= limit or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        raise SubtitleBuildError(
            f"Subtitle needs {len(lines)} lines; maximum is {max_lines}: {text!r}"
        )
    return "\n".join(lines)


def _try_wrap(
    text: str,
    *,
    is_cjk: bool,
    line_limit: int,
    max_lines: int,
) -> str | None:
    try:
        if is_cjk:
            return _wrap_cjk(text, line_limit, max_lines)
        return _wrap_words(text, line_limit, max_lines)
    except SubtitleBuildError as exc:
        if not str(exc).startswith("Subtitle needs "):
            raise
        return None


def _split_oversized_unit(
    text: str,
    *,
    is_cjk: bool,
    line_limit: int,
    max_lines: int,
) -> list[str]:
    units = list("".join(text.split())) if is_cjk else " ".join(text.split()).split(" ")
    separator = "" if is_cjk else " "
    chunks: list[str] = []
    cursor = 0
    while cursor < len(units):
        best_end: int | None = None
        for end in range(cursor + 1, len(units) + 1):
            candidate = separator.join(units[cursor:end])
            if _try_wrap(
                candidate,
                is_cjk=is_cjk,
                line_limit=line_limit,
                max_lines=max_lines,
            ) is None:
                break
            best_end = end
        if best_end is None:
            raise SubtitleBuildError(
                f"Subtitle contains a unit wider than the current line limit: {text!r}"
            )
        chunks.append(separator.join(units[cursor:best_end]))
        cursor = best_end

    # The greedy pass above establishes the minimum number of screens, but it
    # can leave a one-word (or one-character) final screen. Redistribute the
    # same exact units across that minimum screen count so every screen carries
    # a comparable reading load while still satisfying the line limits.
    screen_count = len(chunks)
    if screen_count <= 1:
        return chunks
    target_units = len(units) / screen_count

    @lru_cache(maxsize=None)
    def balanced_split(cursor: int, screens_left: int) -> tuple[float, tuple[int, ...]] | None:
        if screens_left == 0:
            return (0.0, ()) if cursor == len(units) else None
        last_end = len(units) - (screens_left - 1)
        best: tuple[float, tuple[int, ...]] | None = None
        for end in range(cursor + 1, last_end + 1):
            candidate = separator.join(units[cursor:end])
            if _try_wrap(
                candidate,
                is_cjk=is_cjk,
                line_limit=line_limit,
                max_lines=max_lines,
            ) is None:
                break
            remainder = balanced_split(end, screens_left - 1)
            if remainder is None:
                continue
            cost = (end - cursor - target_units) ** 2 + remainder[0]
            proposal = (cost, (end,) + remainder[1])
            if best is None or proposal[0] < best[0]:
                best = proposal
        return best

    split = balanced_split(0, screen_count)
    if split is None:
        return chunks
    balanced: list[str] = []
    cursor = 0
    for end in split[1]:
        balanced.append(separator.join(units[cursor:end]))
        cursor = end
    return balanced


def _caption_chunks(
    text: str,
    *,
    is_cjk: bool,
    line_limit: int,
    max_lines: int,
) -> list[tuple[str, str]]:
    normalized = "".join(text.split()) if is_cjk else " ".join(text.split())
    rendered = _try_wrap(
        normalized,
        is_cjk=is_cjk,
        line_limit=line_limit,
        max_lines=max_lines,
    )
    if rendered is not None:
        return [(normalized, rendered)]

    if is_cjk:
        semantic_units = [
            value
            for value in re.findall(r".*?[。！？!?](?:[”’\"])?|.+$", normalized)
            if value
        ]
        separator = ""
    else:
        semantic_units = [
            value
            for value in re.split(r"(?<=[.!?])\s+", normalized)
            if value
        ]
        separator = " "

    pieces: list[str] = []
    for unit in semantic_units:
        if _try_wrap(
            unit,
            is_cjk=is_cjk,
            line_limit=line_limit,
            max_lines=max_lines,
        ) is not None:
            pieces.append(unit)
        else:
            pieces.extend(
                _split_oversized_unit(
                    unit,
                    is_cjk=is_cjk,
                    line_limit=line_limit,
                    max_lines=max_lines,
                )
            )

    chunks: list[str] = []
    for piece in pieces:
        candidate = piece if not chunks else separator.join((chunks[-1], piece))
        if chunks and _try_wrap(
            candidate,
            is_cjk=is_cjk,
            line_limit=line_limit,
            max_lines=max_lines,
        ) is not None:
            chunks[-1] = candidate
        else:
            chunks.append(piece)

    result: list[tuple[str, str]] = []
    for chunk in chunks:
        wrapped = _try_wrap(
            chunk,
            is_cjk=is_cjk,
            line_limit=line_limit,
            max_lines=max_lines,
        )
        if wrapped is None:
            raise SubtitleBuildError(f"Could not fit subtitle chunk: {chunk!r}")
        result.append((chunk, wrapped))
    reconstructed = separator.join(chunk for chunk, _ in result)
    if reconstructed != normalized:
        raise SubtitleBuildError("Caption splitting changed exact dialogue text.")
    return result


def _caption_intervals(
    start: float,
    end: float,
    chunks: list[tuple[str, str]],
    *,
    is_cjk: bool,
    minimum_duration: float,
) -> list[tuple[float, float]]:
    duration = end - start
    weights = [
        len("".join(text.split())) if is_cjk else len(text.split())
        for text, _ in chunks
    ]
    total_weight = sum(weights)
    if not weights or total_weight <= 0:
        raise SubtitleBuildError("Caption splitting produced an empty cue.")
    durations = [duration * weight / total_weight for weight in weights]
    if any(value + 1e-6 < minimum_duration for value in durations):
        raise SubtitleBuildError(
            "Exact subtitle needs multiple screens but its authored interval is too short."
        )
    intervals: list[tuple[float, float]] = []
    cursor = start
    for index, value in enumerate(durations):
        chunk_end = end if index == len(durations) - 1 else cursor + value
        intervals.append((cursor, chunk_end))
        cursor = chunk_end
    return intervals


def _minimum_display_interval(
    start: float,
    end: float,
    *,
    previous_end: float,
    next_start: float,
    minimum_duration: float,
) -> tuple[float, float]:
    if end - start + 1e-6 >= minimum_duration:
        return start, end
    missing = minimum_duration - (end - start)
    extend_after = min(missing, max(0.0, next_start - end))
    end += extend_after
    missing -= extend_after
    extend_before = min(missing, max(0.0, start - previous_end))
    start -= extend_before
    missing -= extend_before
    if missing > 1e-6:
        raise SubtitleBuildError(
            "Short subtitle cannot reach the current minimum display time without "
            "overlap or crossing its Segment boundary."
        )
    return start, end


def _required_display_duration(
    text: str,
    chunks: list[tuple[str, str]],
    *,
    is_cjk: bool,
    minimum_duration: float,
    style: dict[str, Any],
) -> float:
    """Return the shortest proportional caption interval that passes every limit."""

    weights = [
        len("".join(chunk_text.split())) if is_cjk else len(chunk_text.split())
        for chunk_text, _ in chunks
    ]
    total_weight = sum(weights)
    if not weights or any(weight <= 0 for weight in weights) or total_weight <= 0:
        raise SubtitleBuildError("Caption duration calculation produced an empty cue.")
    minimum_for_each_chunk = max(
        minimum_duration * total_weight / weight for weight in weights
    )
    if is_cjk:
        units_per_second = _number(
            style["maximum_characters_per_second_cjk"],
            "maximum_characters_per_second_cjk",
            minimum=0.1,
        )
    else:
        words_per_minute = _number(
            style["maximum_words_per_minute_latin"],
            "maximum_words_per_minute_latin",
            minimum=1,
        )
        units_per_second = words_per_minute / 60.0
    minimum_for_readability = total_weight / units_per_second
    return max(
        minimum_duration,
        minimum_for_each_chunk,
        minimum_for_readability,
    )


def _readability(text: str, duration: float, style: dict[str, Any]) -> dict[str, Any]:
    if duration <= 0:
        raise SubtitleBuildError("Subtitle duration must be positive.")
    if _is_cjk(text):
        count = len("".join(text.split()))
        rate = count / duration
        limit = _number(
            style["maximum_characters_per_second_cjk"],
            "maximum_characters_per_second_cjk",
            minimum=0.1,
        )
        mode = "characters_per_second"
    else:
        count = len(text.split())
        rate = count / duration * 60.0
        limit = _number(
            style["maximum_words_per_minute_latin"],
            "maximum_words_per_minute_latin",
            minimum=1,
        )
        mode = "words_per_minute"
    if rate > limit + 1e-6:
        raise SubtitleBuildError(
            f"Exact subtitle exceeds reading-speed limit: {rate:.2f} {mode}, "
            f"limit {limit:.2f}; increase the authored cue interval upstream."
        )
    return {
        "mode": mode,
        "unit_count": count,
        "rate": round(rate, 3),
        "limit": round(limit, 3),
        "status": "PASS",
    }


def _format_srt(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt(seconds: float) -> str:
    return _format_srt(seconds).replace(",", ".")


def _picture_events(edl: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = edl.get("picture_events")
    if not isinstance(raw, list) or not raw:
        raise SubtitleBuildError("picture-audio-edl.json has no picture events.")
    boundaries = edl.get("boundaries")
    if not isinstance(boundaries, list) or len(boundaries) != len(raw) - 1:
        raise SubtitleBuildError(
            "picture-audio-edl.json has invalid boundary coverage."
        )
    result: dict[str, dict[str, Any]] = {}
    previous_out = 0.0
    previous_segment_id: str | None = None
    for index, event in enumerate(raw):
        if not isinstance(event, dict):
            raise SubtitleBuildError("Picture event must be an object.")
        segment_id = _segment_name(event.get("segment_id"))
        if segment_id in result:
            raise SubtitleBuildError(f"EDL repeats {segment_id}.")
        start = _number(event.get("timeline_in_seconds"), f"{segment_id} EDL in")
        end = _number(event.get("timeline_out_seconds"), f"{segment_id} EDL out")
        if end <= start:
            raise SubtitleBuildError(f"EDL timing is invalid at {segment_id}.")
        overlap = 0.0
        if index == 0:
            if abs(start) > 0.001:
                raise SubtitleBuildError("The first EDL picture event must start at zero.")
        else:
            boundary = boundaries[index - 1]
            if not isinstance(boundary, dict):
                raise SubtitleBuildError(f"Invalid incoming boundary for {segment_id}.")
            if (
                boundary.get("from") != previous_segment_id
                or boundary.get("to") != segment_id
            ):
                raise SubtitleBuildError(
                    f"EDL boundary order is invalid before {segment_id}."
                )
            overlap = _number(
                boundary.get("overlap_seconds"),
                f"{segment_id} incoming overlap",
            )
            if overlap < 0 or overlap >= end - start:
                raise SubtitleBuildError(
                    f"EDL overlap is invalid before {segment_id}."
                )
            expected_start = previous_out - overlap
            if abs(start - expected_start) > 0.001:
                raise SubtitleBuildError(
                    f"EDL timing does not match its authored boundary at {segment_id}."
                )
        result[segment_id] = {
            **event,
            "start": start,
            "end": end,
            "incoming_overlap_seconds": overlap,
        }
        previous_out = end
        previous_segment_id = segment_id
    return result

