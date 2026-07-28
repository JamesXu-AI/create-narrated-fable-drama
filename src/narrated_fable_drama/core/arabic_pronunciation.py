"""Deterministic Saudi-Arabic pronunciation text for ElevenLabs TTS."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from narrated_fable_drama.core.project_domain import validate_arabic_dialogue

TTS_MODEL_ID = "eleven_multilingual_v2"
LANGUAGE_CODE = "ar"
ACCENT_PROFILE_ID = "saudi_arabic_neutral_urban_riyadh_v1"
GRAMMATICAL_GENDER_POLICY = "masculine"
PRONUNCIATION_CONTRACT = "arabic-exact-text-plus-derived-tashkeel/v1"
ACCENT_LOCK_PHRASE = "neutral urban Riyadh Saudi accent"
VOICE_DESIGN_ACCENT_DIRECTIVE = (
    "Use one consistent neutral urban Riyadh Saudi accent in Saudi-accented "
    "Modern Standard Arabic. Never switch to Egyptian, Levantine, Emirati, "
    "Kuwaiti, another Gulf dialect, formal newsreader Arabic, or classical "
    "recitation."
)

# Arabic combining marks, including Qur'anic annotation ranges. The TTS compiler
# only inserts ordinary tashkeel, but the wider range prevents a marked string
# from bypassing exact-text comparison.
ARABIC_DIACRITICS_RE = re.compile(
    "["
    "\u0610-\u061a"
    "\u064b-\u065f"
    "\u0670"
    "\u06d6-\u06ed"
    "]"
)
ARABIC_WORD_RE = re.compile(r"[\u0621-\u064a\u066e-\u06d3]+")

_NAME_TASHKEEL = {
    "عثمان": "عُثْمَان",
}
_GENDER_TASHKEEL = {
    "masculine": {
        "أنت": "أَنْتَ",
    },
    "feminine": {
        "أنت": "أَنْتِ",
    },
}


class ArabicPronunciationError(ValueError):
    """Raised when derived TTS text changes the authored Arabic dialogue."""


def strip_arabic_diacritics(text: str) -> str:
    """Remove Arabic combining marks without changing letters or punctuation."""

    normalized = unicodedata.normalize("NFC", text)
    return ARABIC_DIACRITICS_RE.sub("", normalized)


def _replace_words(
    text: str,
    replacements: dict[str, str],
    *,
    rule_prefix: str,
) -> tuple[str, list[str]]:
    applied: list[str] = []

    def replace(match: re.Match[str]) -> str:
        source = match.group(0)
        replacement = replacements.get(source)
        if replacement is None:
            return source
        rule = f"{rule_prefix}:{source}"
        if rule not in applied:
            applied.append(rule)
        return replacement

    return ARABIC_WORD_RE.sub(replace, text), applied


def compile_arabic_tts_text(
    exact_text: Any,
    *,
    grammatical_gender: str = GRAMMATICAL_GENDER_POLICY,
    context: str = "ElevenLabs Arabic cue",
) -> dict[str, Any]:
    """Derive pronunciation-only tashkeel while preserving authored text."""

    locked = validate_arabic_dialogue(exact_text, context=context)
    if ARABIC_DIACRITICS_RE.search(locked):
        raise ArabicPronunciationError(
            f"{context} exact_text must remain unvocalized; tashkeel belongs "
            "only in the derived ElevenLabs tts_text."
        )
    if grammatical_gender not in _GENDER_TASHKEEL:
        raise ArabicPronunciationError(
            f"{context} grammatical_gender must be masculine or feminine."
        )

    rendered, name_rules = _replace_words(
        locked,
        _NAME_TASHKEEL,
        rule_prefix="proper_name",
    )
    rendered, gender_rules = _replace_words(
        rendered,
        _GENDER_TASHKEEL[grammatical_gender],
        rule_prefix=f"second_person_{grammatical_gender}",
    )
    if strip_arabic_diacritics(rendered) != locked:
        raise ArabicPronunciationError(
            f"{context} derived tts_text changes letters, punctuation, or spacing."
        )
    rules = name_rules + gender_rules
    return {
        "contract": PRONUNCIATION_CONTRACT,
        "exact_text": locked,
        "tts_text": rendered,
        "exact_text_sha256": hashlib.sha256(locked.encode("utf-8")).hexdigest(),
        "tts_text_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "tts_text_diacritic_count": len(ARABIC_DIACRITICS_RE.findall(rendered)),
        "grammatical_gender": grammatical_gender,
        "accent_profile_id": ACCENT_PROFILE_ID,
        "applied_rules": rules,
    }


def validate_arabic_tts_text(
    *,
    exact_text: Any,
    tts_text: Any,
    grammatical_gender: str = GRAMMATICAL_GENDER_POLICY,
    context: str = "ElevenLabs Arabic cue",
) -> dict[str, Any]:
    """Require caller-provided TTS text to equal the deterministic derivation."""

    compiled = compile_arabic_tts_text(
        exact_text,
        grammatical_gender=grammatical_gender,
        context=context,
    )
    if not isinstance(tts_text, str) or tts_text != compiled["tts_text"]:
        raise ArabicPronunciationError(
            f"{context} tts_text is stale or is not the approved deterministic "
            "Saudi-Arabic pronunciation rendering."
        )
    return compiled


def has_current_arabic_pronunciation_contract(value: Any) -> bool:
    """Return whether one persisted dubbing record carries every hard lock."""

    return (
        isinstance(value, dict)
        and value.get("language_code") == LANGUAGE_CODE
        and value.get("language_code_sent") is False
        and value.get("tts_model_id") == TTS_MODEL_ID
        and value.get("accent_profile_id") == ACCENT_PROFILE_ID
        and value.get("grammatical_gender_policy")
        == GRAMMATICAL_GENDER_POLICY
        and value.get("pronunciation_contract") == PRONUNCIATION_CONTRACT
    )
