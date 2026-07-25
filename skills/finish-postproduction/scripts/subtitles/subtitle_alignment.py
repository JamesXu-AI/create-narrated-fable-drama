"""Align Storyboard-authoritative dialogue text to the final native audio."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median
from typing import Any

from .subtitle_style import SubtitleBuildError

TOKEN_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]"
    r"|[^\W_]+(?:['’][^\W_]+)*",
    re.UNICODE,
)

LANGUAGE_CODES = {
    "arabic": "ar",
    "chinese": "zh",
    "english": "en",
    "french": "fr",
    "german": "de",
    "hindi": "hi",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "korean": "ko",
    "portuguese": "pt",
    "russian": "ru",
    "spanish": "es",
    "turkish": "tr",
}


@dataclass(frozen=True)
class TimedWord:
    """One word emitted by the timing model."""

    text: str
    start_seconds: float
    end_seconds: float
    probability: float


@dataclass(frozen=True)
class ObservedToken:
    """One normalized token linked back to its timed model word."""

    text: str
    word_index: int
    word: TimedWord


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return [match.group(0).replace("’", "'") for match in TOKEN_RE.finditer(normalized)]


def sha256_file(path: Path) -> str:
    """Return a stable content identity for one subtitle source or deliverable."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _language_code(target_language: str) -> str | None:
    normalized = target_language.strip().casefold()
    if normalized in LANGUAGE_CODES:
        return LANGUAGE_CODES[normalized]
    if re.fullmatch(r"[a-z]{2,3}", normalized):
        return normalized
    return None


def _model_name(model_family: str, target_language: str) -> str:
    family = model_family.strip()
    if not family:
        raise SubtitleBuildError("Subtitle alignment model family is empty.")
    if _language_code(target_language) == "en" and not family.endswith(".en"):
        return f"{family}.en"
    return family


def transcribe_final_audio(
    media_path: Path,
    *,
    target_language: str,
    model_family: str,
    device: str,
    compute_type: str,
    beam_size: int,
    vad_filter: bool,
) -> tuple[list[TimedWord], dict[str, Any]]:
    """Return real final-timeline word timestamps from the clean master."""

    if not media_path.is_file() or media_path.stat().st_size <= 0:
        raise SubtitleBuildError(
            "Final clean master is missing for subtitle alignment."
        )
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SubtitleBuildError(
            "faster-whisper is required for final-audio subtitle alignment."
        ) from exc
    model_name = _model_name(model_family, target_language)
    try:
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )
        segments, info = model.transcribe(
            str(media_path),
            language=_language_code(target_language),
            beam_size=beam_size,
            word_timestamps=True,
            vad_filter=vad_filter,
            condition_on_previous_text=False,
        )
        words = [
            TimedWord(
                text=str(word.word).strip(),
                start_seconds=float(word.start),
                end_seconds=float(word.end),
                probability=float(word.probability),
            )
            for segment in segments
            for word in (segment.words or [])
            if str(word.word).strip()
            and word.start is not None
            and word.end is not None
        ]
    except Exception as exc:
        raise SubtitleBuildError(
            f"Final-audio subtitle alignment failed with model {model_name}."
        ) from exc
    if not words:
        raise SubtitleBuildError("Final-audio subtitle alignment produced no words.")
    return words, {
        "model": model_name,
        "device": device,
        "compute_type": compute_type,
        "beam_size": beam_size,
        "vad_filter": vad_filter,
        "detected_language": str(info.language),
        "detected_language_probability": round(
            float(info.language_probability),
            6,
        ),
        "source_path": str(media_path.resolve()),
        "source_sha256": sha256_file(media_path),
    }


def _observed_tokens(words: list[TimedWord]) -> list[ObservedToken]:
    result: list[ObservedToken] = []
    for word_index, word in enumerate(words):
        for token in _tokens(word.text):
            result.append(
                ObservedToken(
                    text=token,
                    word_index=word_index,
                    word=word,
                )
            )
    return result


def _similarity(expected: str, observed: str) -> float:
    if expected == observed:
        return 1.0
    return SequenceMatcher(None, expected, observed, autojunk=False).ratio()


def _match_cue_tokens(
    expected_tokens: list[str],
    observed: list[ObservedToken],
    *,
    cursor: int,
    lookahead_tokens: int,
    minimum_token_similarity: float,
    observed_limit: int | None = None,
) -> tuple[list[ObservedToken | None], int]:
    matches: list[ObservedToken | None] = []
    current = cursor
    for expected in expected_tokens:
        limit = min(
            len(observed),
            current + lookahead_tokens,
            observed_limit if observed_limit is not None else len(observed),
        )
        best_index: int | None = None
        best_score = minimum_token_similarity
        for candidate_index in range(current, limit):
            similarity = _similarity(expected, observed[candidate_index].text)
            distance_penalty = (candidate_index - current) * 0.05
            score = similarity - distance_penalty
            if score >= best_score:
                best_score = score
                best_index = candidate_index
                if similarity == 1.0 and candidate_index == current:
                    break
        if best_index is None:
            matches.append(None)
            continue
        matches.append(observed[best_index])
        current = best_index + 1
    return matches, current


def _typical_word_duration(matches: list[ObservedToken | None]) -> float:
    durations = [
        match.word.end_seconds - match.word.start_seconds
        for match in matches
        if match is not None
        and match.word.probability >= 0.7
        and 0.04 <= match.word.end_seconds - match.word.start_seconds <= 1.2
    ]
    return min(0.5, max(0.18, median(durations) if durations else 0.32))


def _resolved_token_timings(
    matches: list[ObservedToken | None],
    *,
    outlier_gap_seconds: float,
    outlier_probability_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved: list[dict[str, Any]] = []
    repairs: list[dict[str, Any]] = []
    typical_duration = _typical_word_duration(matches)
    matched_positions = [
        index for index, match in enumerate(matches) if match is not None
    ]
    for index, match in enumerate(matches):
        if match is None:
            resolved.append(
                {
                    "matched": False,
                    "start_seconds": None,
                    "end_seconds": None,
                    "probability": None,
                    "observed_text": None,
                    "word_index": None,
                }
            )
            continue
        start = match.word.start_seconds
        end = match.word.end_seconds
        resolved.append(
            {
                "matched": True,
                "start_seconds": start,
                "end_seconds": end,
                "probability": match.word.probability,
                "observed_text": match.word.text,
                "word_index": match.word_index,
            }
        )
    if len(matched_positions) >= 2:
        first_index, second_index = matched_positions[:2]
        first = matches[first_index]
        second = matches[second_index]
        assert first is not None and second is not None
        first_gap = second.word.start_seconds - first.word.end_seconds
        if (
            first.word_index != second.word_index
            and first_gap > outlier_gap_seconds
            and first.word.probability < outlier_probability_threshold
        ):
            repaired_end = max(0.0, second.word.start_seconds - 0.04)
            repaired_start = max(0.0, repaired_end - typical_duration)
            resolved[first_index]["start_seconds"] = repaired_start
            resolved[first_index]["end_seconds"] = repaired_end
            repairs.append(
                {
                    "token_index": first_index,
                    "operation": "replace_low_confidence_leading_outlier",
                    "original_start_seconds": round(first.word.start_seconds, 3),
                    "original_end_seconds": round(first.word.end_seconds, 3),
                    "resolved_start_seconds": round(repaired_start, 3),
                    "resolved_end_seconds": round(repaired_end, 3),
                }
            )
        penultimate_index, last_index = matched_positions[-2:]
        penultimate = matches[penultimate_index]
        last = matches[last_index]
        assert penultimate is not None and last is not None
        last_gap = last.word.start_seconds - penultimate.word.end_seconds
        if (
            penultimate.word_index != last.word_index
            and last_gap > outlier_gap_seconds
            and last.word.probability < outlier_probability_threshold
        ):
            repaired_start = penultimate.word.end_seconds + 0.04
            repaired_end = repaired_start + typical_duration
            resolved[last_index]["start_seconds"] = repaired_start
            resolved[last_index]["end_seconds"] = repaired_end
            repairs.append(
                {
                    "token_index": last_index,
                    "operation": "replace_low_confidence_trailing_outlier",
                    "original_start_seconds": round(last.word.start_seconds, 3),
                    "original_end_seconds": round(last.word.end_seconds, 3),
                    "resolved_start_seconds": round(repaired_start, 3),
                    "resolved_end_seconds": round(repaired_end, 3),
                }
            )
    return resolved, repairs


def align_authoritative_cues(
    cue_specs: list[dict[str, Any]],
    words: list[TimedWord],
    *,
    minimum_token_coverage: float,
    minimum_token_similarity: float,
    lookahead_tokens: int,
    outlier_gap_seconds: float,
    outlier_probability_threshold: float,
) -> dict[str, dict[str, Any]]:
    """Align exact cue text monotonically to measured final-audio words."""

    observed = _observed_tokens(words)
    if not observed:
        raise SubtitleBuildError("Subtitle alignment produced no normalized tokens.")
    cursor = 0
    result: dict[str, dict[str, Any]] = {}
    for cue in cue_specs:
        cue_id = cue["cue_id"]
        if cue_id in result:
            raise SubtitleBuildError(f"Duplicate subtitle cue ID: {cue_id}")
        expected = _tokens(cue["exact_text"])
        if not expected:
            raise SubtitleBuildError(f"Subtitle cue has no alignable text: {cue_id}")
        window_start = cue.get("window_start_seconds")
        window_end = cue.get("window_end_seconds")
        observed_limit: int | None = None
        if window_start is not None or window_end is not None:
            if (
                isinstance(window_start, bool)
                or isinstance(window_end, bool)
                or not isinstance(window_start, (int, float))
                or not isinstance(window_end, (int, float))
                or float(window_end) <= float(window_start)
            ):
                raise SubtitleBuildError(
                    f"Subtitle cue has an invalid final-timeline ownership window: "
                    f"{cue_id}"
                )
            while (
                cursor < len(observed)
                and observed[cursor].word.end_seconds < float(window_start) - 0.05
            ):
                cursor += 1
            observed_limit = cursor
            while (
                observed_limit < len(observed)
                and observed[observed_limit].word.start_seconds
                <= float(window_end) + 0.05
            ):
                observed_limit += 1
        matches, cursor = _match_cue_tokens(
            expected,
            observed,
            cursor=cursor,
            lookahead_tokens=lookahead_tokens,
            minimum_token_similarity=minimum_token_similarity,
            observed_limit=observed_limit,
        )
        matched_count = sum(match is not None for match in matches)
        coverage = matched_count / len(expected)
        if coverage + 1e-9 < minimum_token_coverage:
            raise SubtitleBuildError(
                f"Final-audio alignment coverage is too low for {cue_id}: "
                f"{coverage:.3f} < {minimum_token_coverage:.3f}."
            )
        token_timings, repairs = _resolved_token_timings(
            matches,
            outlier_gap_seconds=outlier_gap_seconds,
            outlier_probability_threshold=outlier_probability_threshold,
        )
        timed = [
            token
            for token in token_timings
            if token["start_seconds"] is not None and token["end_seconds"] is not None
        ]
        probabilities = [
            float(token["probability"])
            for token in timed
            if token["probability"] is not None
        ]
        result[cue_id] = {
            "cue_id": cue_id,
            "expected_token_count": len(expected),
            "matched_token_count": matched_count,
            "token_coverage": round(coverage, 6),
            "mean_word_probability": round(
                sum(probabilities) / len(probabilities),
                6,
            ),
            "speech_start_seconds": round(
                min(float(token["start_seconds"]) for token in timed),
                6,
            ),
            "speech_end_seconds": round(
                max(float(token["end_seconds"]) for token in timed),
                6,
            ),
            "anchor_repairs": repairs,
            "tokens": [
                {
                    "expected_text": expected[index],
                    **token,
                }
                for index, token in enumerate(token_timings)
            ],
        }
    return result


def caption_intervals_from_alignment(
    alignment: dict[str, Any],
    chunks: list[tuple[str, str]],
    *,
    lead_in_seconds: float,
    trail_out_seconds: float,
    media_duration_seconds: float,
) -> list[tuple[float, float]]:
    """Build per-screen intervals from the words that each screen contains."""

    tokens = alignment["tokens"]
    intervals: list[dict[str, float]] = []
    cursor = 0
    for chunk_text, _ in chunks:
        chunk_count = len(_tokens(chunk_text))
        chunk_tokens = tokens[cursor : cursor + chunk_count]
        cursor += chunk_count
        timed = [
            token
            for token in chunk_tokens
            if token["start_seconds"] is not None and token["end_seconds"] is not None
        ]
        if not timed:
            raise SubtitleBuildError(
                f"Subtitle screen lacks final-audio timing: {alignment['cue_id']}"
            )
        speech_start = min(float(token["start_seconds"]) for token in timed)
        speech_end = max(float(token["end_seconds"]) for token in timed)
        intervals.append(
            {
                "start": max(0.0, speech_start - lead_in_seconds),
                "end": min(
                    media_duration_seconds,
                    speech_end + trail_out_seconds,
                ),
                "speech_start": speech_start,
                "speech_end": speech_end,
            }
        )
    if cursor != len(tokens):
        raise SubtitleBuildError(
            f"Subtitle screen token coverage differs from cue: {alignment['cue_id']}"
        )
    for previous, current in zip(intervals, intervals[1:]):
        if current["start"] < previous["end"]:
            boundary = (
                previous["speech_end"] + current["speech_start"]
            ) / 2.0
            previous["end"] = max(previous["start"] + 0.05, boundary)
            current["start"] = min(current["end"] - 0.05, boundary + 0.001)
    result = [(item["start"], item["end"]) for item in intervals]
    if any(end <= start for start, end in result):
        raise SubtitleBuildError(
            f"Subtitle alignment produced an invalid interval: {alignment['cue_id']}"
        )
    return result
