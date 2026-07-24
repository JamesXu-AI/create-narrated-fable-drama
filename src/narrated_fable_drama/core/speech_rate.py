"""Shared strict speech-rate gate for screenplay, Storyboard, and Segment Prompts."""

from __future__ import annotations

import re
from typing import Any


MAX_CJK_CHARACTERS_PER_SECOND = 4.0
MAX_WORDS_PER_SECOND = 2.6
LINE_START_END_ALLOWANCE_SECONDS = 0.25
MINIMUM_SPEECH_WINDOW_SECONDS = 0.60

_CJK_RE = re.compile(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]")
_WORD_RE = re.compile(
    r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*|[\u0600-\u06ff]+|[^\W\d_]+",
    re.UNICODE,
)


class SpeechRateError(ValueError):
    """Raised when exact speech cannot fit its authored audiovisual window."""


def analyze_speech(text: str, window_seconds: float) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise SpeechRateError("Speech text must be non-empty.")
    if isinstance(window_seconds, bool) or window_seconds <= 0:
        raise SpeechRateError("Speech window must be positive.")
    cjk_count = len(_CJK_RE.findall(text))
    without_cjk = _CJK_RE.sub(" ", text)
    word_count = len(_WORD_RE.findall(without_cjk))
    speaking_seconds = (
        cjk_count / MAX_CJK_CHARACTERS_PER_SECOND
        + word_count / MAX_WORDS_PER_SECOND
    )
    required = max(
        MINIMUM_SPEECH_WINDOW_SECONDS,
        speaking_seconds + LINE_START_END_ALLOWANCE_SECONDS,
    )
    return {
        "cjk_character_count": cjk_count,
        "word_count": word_count,
        "window_seconds": round(float(window_seconds), 3),
        "required_seconds": round(required, 3),
        "cjk_characters_per_second": round(
            cjk_count / float(window_seconds), 3
        ),
        "words_per_second": round(word_count / float(window_seconds), 3),
        "maximum_cjk_characters_per_second": MAX_CJK_CHARACTERS_PER_SECOND,
        "maximum_words_per_second": MAX_WORDS_PER_SECOND,
        "status": "PASS" if float(window_seconds) + 1e-6 >= required else "FAIL",
    }


def require_speech_rate(
    *, line_id: str, text: str, window_seconds: float, stage: str
) -> dict[str, Any]:
    result = analyze_speech(text, window_seconds)
    if result["status"] != "PASS":
        raise SpeechRateError(
            f"{stage} {line_id} speech window {result['window_seconds']:.3f}s "
            f"is below the strict {result['required_seconds']:.3f}s minimum "
            f"({result['cjk_character_count']} CJK characters at at most "
            f"{MAX_CJK_CHARACTERS_PER_SECOND:.1f}/s; "
            f"{result['word_count']} words at at most "
            f"{MAX_WORDS_PER_SECOND:.1f}/s; plus line allowance)."
        )
    return {"line_id": line_id, **result}
