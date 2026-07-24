"""Apply the screenplay-level speech-rate gate."""

from __future__ import annotations

from typing import Any

from narrated_fable_drama.core.speech_rate import SpeechRateError, require_speech_rate
from narrated_fable_drama.core.validation import StoryVideoError


def screenplay_speech_rate_gate(screenplay: dict[str, Any]) -> dict[str, Any]:
    """Validate every exact line against its owning screenplay Shot duration."""

    lines: list[dict[str, Any]] = []
    try:
        for segment in screenplay["segments"]:
            segment_id = segment["story_plan"]["segment_id"]
            for shot in segment["shots"]:
                dialogue = shot["dialogue"]
                if dialogue is None:
                    continue
                result = require_speech_rate(
                    line_id=dialogue["line_id"],
                    text=dialogue["spoken_text_en"],
                    window_seconds=float(shot["duration_seconds"]),
                    stage=f"screenplay {segment_id}/{shot['shot_id']}",
                )
                lines.append(
                    {
                        "segment_id": segment_id,
                        "shot_id": shot["shot_id"],
                        **result,
                    }
                )
    except SpeechRateError as exc:
        raise StoryVideoError(str(exc)) from exc
    return {
        "status": "PASS",
        "stage": "screenplay_full",
        "line_count": len(lines),
        "maximum_cjk_characters_per_second": 4.0,
        "maximum_words_per_second": 2.6,
        "minimum_margin_seconds": round(
            min(
                (
                    item["window_seconds"] - item["required_seconds"]
                    for item in lines
                ),
                default=0.0,
            ),
            3,
        ),
    }

