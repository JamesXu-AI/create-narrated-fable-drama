"""Detect disposable character speech in Seedance native audio."""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


SPEECH_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
MINIMUM_SPEECH_TOKENS = 3
MINIMUM_SPEECH_DURATION_SECONDS = 0.6
MINIMUM_MEAN_WORD_PROBABILITY = 0.45


class SeedanceSpeechGateError(RuntimeError):
    """Raised when the original Seedance audio cannot be audited."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _default_model() -> Any:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SeedanceSpeechGateError(
            "faster-whisper is required for the Seedance speech-exclusion gate."
        ) from exc
    try:
        return WhisperModel("small", device="cpu", compute_type="int8")
    except Exception as exc:
        raise SeedanceSpeechGateError(
            "Could not load the multilingual Arabic speech-detection model."
        ) from exc


def _audit_speech_presence(
    media_path: Path,
    *,
    contract: str,
    block_field: str,
    error_type: type[RuntimeError],
    source_role: str,
    transcription_language: str | None,
    token_pattern: re.Pattern[str],
    token_count_field: str,
    total_token_count_field: str,
    model: Any | None = None,
) -> dict[str, Any]:
    """Return a fail-closed record for forbidden speech detection."""

    source = media_path.expanduser().resolve(strict=True)
    detector = model if model is not None else _default_model()
    options: dict[str, Any] = {
        "beam_size": 5,
        "word_timestamps": True,
        "vad_filter": True,
        "condition_on_previous_text": False,
    }
    if transcription_language is not None:
        options["language"] = transcription_language
    try:
        raw_segments, info = detector.transcribe(
            str(source),
            **options,
        )
        segments = list(raw_segments)
    except Exception as exc:
        raise error_type(
            f"Could not inspect {source_role} for forbidden speech."
        ) from exc

    evidence: list[dict[str, Any]] = []
    qualifying: list[int] = []
    total_tokens = 0
    for index, segment in enumerate(segments, start=1):
        words = [
            word
            for word in (getattr(segment, "words", None) or [])
            if str(getattr(word, "word", "")).strip()
        ]
        text = str(getattr(segment, "text", "")).strip()
        tokens = token_pattern.findall(text)
        total_tokens += len(tokens)
        probabilities = [
            float(word.probability)
            for word in words
            if getattr(word, "probability", None) is not None
        ]
        mean_probability = (
            sum(probabilities) / len(probabilities) if probabilities else 0.0
        )
        word_windows = []
        for word in words:
            word_start = getattr(word, "start", None)
            word_end = getattr(word, "end", None)
            if word_start is None or word_end is None:
                continue
            word_start = float(word_start)
            word_end = float(word_end)
            if word_end <= word_start:
                continue
            word_windows.append(
                {
                    "start_seconds": round(word_start, 6),
                    "end_seconds": round(word_end, 6),
                    "probability": round(
                        float(getattr(word, "probability", 0.0)),
                        6,
                    ),
                }
            )
        start = float(getattr(segment, "start", 0.0))
        end = float(getattr(segment, "end", start))
        duration = max(0.0, end - start)
        is_forbidden_speech = (
            len(tokens) >= MINIMUM_SPEECH_TOKENS
            and duration >= MINIMUM_SPEECH_DURATION_SECONDS
            and mean_probability >= MINIMUM_MEAN_WORD_PROBABILITY
        )
        if is_forbidden_speech:
            qualifying.append(index)
        evidence.append(
            {
                "segment_index": index,
                "start_seconds": round(start, 6),
                "end_seconds": round(end, 6),
                "duration_seconds": round(duration, 6),
                "detected_text": text,
                token_count_field: len(tokens),
                "mean_word_probability": round(mean_probability, 6),
                "detected_speech_word_windows": word_windows,
                "forbidden_speech": is_forbidden_speech,
            }
        )
    status = "FAIL" if qualifying else "PASS"
    return {
        "contract": contract,
        "status": status,
        block_field: status == "FAIL",
        "language": (
            "Arabic"
            if transcription_language == "ar"
            else "Auto-detected speech"
        ),
        "language_code": transcription_language or "auto",
        "model": "small",
        "device": "cpu",
        "compute_type": "int8",
        "asr_role": "speech_presence_detection_only_not_text_authority",
        "source_path": str(source),
        "source_sha256": _sha256(source),
        "detected_language": str(getattr(info, "language", "")).strip(),
        "detected_language_probability": round(
            float(getattr(info, "language_probability", 0.0)),
            6,
        ),
        "minimum_speech_tokens": MINIMUM_SPEECH_TOKENS,
        "minimum_speech_duration_seconds": MINIMUM_SPEECH_DURATION_SECONDS,
        "minimum_mean_word_probability": MINIMUM_MEAN_WORD_PROBABILITY,
        total_token_count_field: total_tokens,
        "forbidden_speech_segment_indices": qualifying,
        "segments": evidence,
    }


def audit_seedance_character_speech(
    media_path: Path,
    *,
    model: Any | None = None,
) -> dict[str, Any]:
    """Detect disposable Seedance character speech in any language."""

    return _audit_speech_presence(
        media_path,
        contract="seedance-character-speech-replacement/v2",
        block_field="requires_replacement",
        error_type=SeedanceSpeechGateError,
        source_role="the original Seedance audio",
        transcription_language=None,
        token_pattern=SPEECH_TOKEN_RE,
        token_count_field="speech_token_count",
        total_token_count_field="detected_speech_token_count",
        model=model,
    )
