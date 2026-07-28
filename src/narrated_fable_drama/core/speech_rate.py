"""Arabic-only speech-rate gate shared by all spoken-authority stages."""

from __future__ import annotations

import re
from typing import Any

from narrated_fable_drama.core.project_domain import (
    ProjectDomainError,
    TARGET_LANGUAGE,
    validate_arabic_dialogue,
)

ARABIC_LANGUAGE_CODE = "ar"
MAX_ARABIC_WORDS_PER_SECOND = 2.6
LINE_START_END_ALLOWANCE_SECONDS = 0.25
MINIMUM_SPEECH_WINDOW_SECONDS = 0.60

_ARABIC_WORD_RE = re.compile(
    r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]+",
    re.UNICODE,
)


class SpeechRateError(ValueError):
    """Raised when exact speech cannot fit its authored audiovisual window."""


def analyze_speech(text: str, window_seconds: float) -> dict[str, Any]:
    try:
        normalized = validate_arabic_dialogue(
            text,
            context="speech-rate gate",
        )
    except ProjectDomainError as exc:
        raise SpeechRateError(str(exc)) from exc
    if isinstance(window_seconds, bool) or window_seconds <= 0:
        raise SpeechRateError("Speech window must be positive.")
    arabic_word_count = len(_ARABIC_WORD_RE.findall(normalized))
    if arabic_word_count <= 0:
        raise SpeechRateError("Speech-rate gate found no Arabic words.")
    speaking_seconds = arabic_word_count / MAX_ARABIC_WORDS_PER_SECOND
    required = max(
        MINIMUM_SPEECH_WINDOW_SECONDS,
        speaking_seconds + LINE_START_END_ALLOWANCE_SECONDS,
    )
    return {
        "language": TARGET_LANGUAGE,
        "language_code": ARABIC_LANGUAGE_CODE,
        "arabic_only_no_latin": "PASS",
        "arabic_word_count": arabic_word_count,
        "window_seconds": round(float(window_seconds), 3),
        "required_seconds": round(required, 3),
        "arabic_words_per_second": round(
            arabic_word_count / float(window_seconds),
            3,
        ),
        "maximum_arabic_words_per_second": MAX_ARABIC_WORDS_PER_SECOND,
        "status": "PASS" if float(window_seconds) + 1e-6 >= required else "FAIL",
    }


def require_speech_rate(
    *, line_id: str, text: str, window_seconds: float, stage: str
) -> dict[str, Any]:
    result = analyze_speech(text, window_seconds)
    if result["status"] != "PASS":
        raise SpeechRateError(
            f"{stage} {line_id} speech window {result['window_seconds']:.3f}s "
            f"is below the strict Arabic {result['required_seconds']:.3f}s "
            f"minimum ({result['arabic_word_count']} Arabic words at at most "
            f"{MAX_ARABIC_WORDS_PER_SECOND:.1f}/s; plus line allowance)."
        )
    return {"line_id": line_id, **result}
