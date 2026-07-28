"""Repository-owned ElevenLabs adapter for exact Arabic dialogue dubbing."""

from __future__ import annotations

import base64
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from narrated_fable_drama.core.arabic_pronunciation import (
    ACCENT_PROFILE_ID,
    GRAMMATICAL_GENDER_POLICY,
    LANGUAGE_CODE,
    PRONUNCIATION_CONTRACT,
    TTS_MODEL_ID,
    compile_arabic_tts_text,
)
from narrated_fable_drama.providers import runtime as core

ELEVENLABS_ENV = (
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_MODEL_ID",
    "ELEVENLABS_VOICE_MAP",
)
ELEVENLABS_TTS_ENV = (
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_MODEL_ID",
)
DEFAULT_BASE_URL = "https://api.elevenlabs.io"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_VOICE_DESIGN_MODEL_ID = "eleven_multilingual_ttv_v2"
DEFAULT_TTS_VOICE_SETTINGS = {
    "stability": 1.0,
    "similarity_boost": 1.0,
    "style": 0.0,
    "use_speaker_boost": True,
}


def _base_url() -> str:
    value = (core.env("ELEVENLABS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise core.SeedMediaError("ELEVENLABS_BASE_URL must be an https URL")
    return value


def _api_key() -> str:
    value = core.env("ELEVENLABS_API_KEY", required=True)
    assert value is not None
    return value


def _model_id() -> str:
    value = core.env("ELEVENLABS_MODEL_ID", required=True)
    assert value is not None
    if value != TTS_MODEL_ID:
        raise core.SeedMediaError(
            "Arabic dubbing is locked to eleven_multilingual_v2; "
            f"received ELEVENLABS_MODEL_ID={value!r}"
        )
    return TTS_MODEL_ID


def _voice_settings(
    *,
    speed: float,
    approved_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings: dict[str, Any] = dict(DEFAULT_TTS_VOICE_SETTINGS)
    if approved_settings is not None:
        parsed = dict(approved_settings)
    else:
        extra_settings = core.env("ELEVENLABS_VOICE_SETTINGS")
        if extra_settings:
            parsed = core.parse_json_value(extra_settings)
            if not isinstance(parsed, dict):
                raise core.SeedMediaError(
                    "ELEVENLABS_VOICE_SETTINGS must be a JSON object"
                )
        else:
            parsed = {}
    allowed = set(DEFAULT_TTS_VOICE_SETTINGS) | {"speed"}
    unexpected = set(parsed) - allowed
    if unexpected:
        raise core.SeedMediaError(
            "ElevenLabs voice settings contain unsupported keys: "
            f"{sorted(unexpected)}"
        )
    settings.update(parsed)
    settings["speed"] = speed
    try:
        stability = float(settings["stability"])
        similarity = float(settings["similarity_boost"])
        style = float(settings["style"])
    except (KeyError, TypeError, ValueError) as exc:
        raise core.SeedMediaError(
            "ElevenLabs Arabic voice settings must be numeric"
        ) from exc
    if not 0.65 <= stability <= 1.0:
        raise core.SeedMediaError(
            "Saudi-Arabic voice stability must be between 0.65 and 1.0"
        )
    if not 0.80 <= similarity <= 1.0:
        raise core.SeedMediaError(
            "Saudi-Arabic voice similarity_boost must be between 0.80 and 1.0"
        )
    if not 0.0 <= style <= 0.10:
        raise core.SeedMediaError(
            "Saudi-Arabic voice style must be between 0.0 and 0.10"
        )
    if not isinstance(settings.get("use_speaker_boost"), bool):
        raise core.SeedMediaError(
            "ElevenLabs use_speaker_boost must be boolean"
        )
    settings["stability"] = stability
    settings["similarity_boost"] = similarity
    settings["style"] = style
    return settings


def _http_error(exc: urllib.error.HTTPError) -> core.SeedMediaError:
    raw = exc.read().decode("utf-8", errors="replace")
    return core.SeedMediaError(
        json.dumps(
            {
                "http_status": exc.code,
                "request_id": exc.headers.get("request-id"),
                "error": raw[:1000],
            },
            ensure_ascii=False,
        )
    )


def _post_json(
    *,
    path: str,
    body: dict[str, Any],
    timeout: int,
) -> tuple[dict[str, Any], dict[str, str | None]]:
    request = urllib.request.Request(
        f"{_base_url()}{path}",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "xi-api-key": _api_key(),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "create-narrated-fable-drama/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_response = response.read()
            headers = {
                "request_id": (
                    response.headers.get("request-id")
                    or response.headers.get("x-trace-id")
                ),
                "character_cost": response.headers.get("character-cost"),
                "content_type": response.headers.get("content-type"),
            }
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from exc
    except urllib.error.URLError as exc:
        raise core.SeedMediaError(
            f"ElevenLabs network request failed: {exc.reason}"
        ) from exc
    try:
        payload = json.loads(raw_response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise core.SeedMediaError(
            "ElevenLabs returned an invalid JSON response"
        ) from exc
    if not isinstance(payload, dict):
        raise core.SeedMediaError("ElevenLabs returned an unexpected JSON response")
    return payload, headers


def design_voice_previews(
    *,
    voice_description: str,
    text: str,
    seed: int,
    timeout: int = core.DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Design three Arabic-capable voice previews without saving a voice."""

    core.require_environment("ELEVENLABS_API_KEY")
    description = voice_description.strip()
    if not 20 <= len(description) <= 1000:
        raise core.SeedMediaError(
            "ElevenLabs voice description must be 20..1000 characters"
        )
    if not 100 <= len(text) <= 1000:
        raise core.SeedMediaError(
            "ElevenLabs voice-design preview text must be 100..1000 characters"
        )
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or not 0 <= seed <= 2147483647
    ):
        raise core.SeedMediaError(
            "ElevenLabs voice-design seed must be an integer in 0..2147483647"
        )
    payload, headers = _post_json(
        path=("/v1/text-to-voice/design?output_format=mp3_44100_128"),
        body={
            "voice_description": description,
            "model_id": DEFAULT_VOICE_DESIGN_MODEL_ID,
            "text": text,
            "auto_generate_text": False,
            "seed": seed,
            "guidance_scale": 5.0,
            "stream_previews": False,
            "should_enhance": False,
        },
        timeout=timeout,
    )
    raw_previews = payload.get("previews")
    if not isinstance(raw_previews, list) or len(raw_previews) != 3:
        raise core.SeedMediaError(
            "ElevenLabs Voice Design did not return exactly three previews"
        )
    previews: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_previews):
        if not isinstance(raw, dict):
            raise core.SeedMediaError(
                f"ElevenLabs Voice Design preview {index} is invalid"
            )
        generated_voice_id = raw.get("generated_voice_id")
        encoded_audio = raw.get("audio_base_64")
        if (
            not isinstance(generated_voice_id, str)
            or not generated_voice_id.strip()
            or not isinstance(encoded_audio, str)
            or not encoded_audio
        ):
            raise core.SeedMediaError(
                f"ElevenLabs Voice Design preview {index} lacks voice/audio data"
            )
        try:
            audio = base64.b64decode(encoded_audio, validate=True)
        except ValueError as exc:
            raise core.SeedMediaError(
                f"ElevenLabs Voice Design preview {index} has invalid audio"
            ) from exc
        if not audio:
            raise core.SeedMediaError(
                f"ElevenLabs Voice Design preview {index} has empty audio"
            )
        previews.append(
            {
                "generated_voice_id": generated_voice_id.strip(),
                "audio": audio,
                "media_type": raw.get("media_type"),
                "duration_seconds": raw.get("duration_secs"),
                "language": raw.get("language"),
            }
        )
    return {
        "previews": previews,
        "text": payload.get("text"),
        "model_id": DEFAULT_VOICE_DESIGN_MODEL_ID,
        "seed": seed,
        **headers,
    }


def create_voice_from_preview(
    *,
    voice_name: str,
    voice_description: str,
    generated_voice_id: str,
    labels: dict[str, str],
    timeout: int = core.DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Save one explicitly selected Voice Design preview as a reusable voice."""

    core.require_environment("ELEVENLABS_API_KEY")
    name = voice_name.strip()
    description = voice_description.strip()
    preview_id = generated_voice_id.strip()
    if not name:
        raise core.SeedMediaError("ElevenLabs voice name must not be empty")
    if not 20 <= len(description) <= 1000:
        raise core.SeedMediaError(
            "ElevenLabs voice description must be 20..1000 characters"
        )
    if not preview_id:
        raise core.SeedMediaError("ElevenLabs generated voice ID must not be empty")
    if any(
        not isinstance(key, str)
        or not key.strip()
        or not isinstance(value, str)
        or not value.strip()
        for key, value in labels.items()
    ):
        raise core.SeedMediaError(
            "ElevenLabs voice labels must contain non-empty strings"
        )
    payload, headers = _post_json(
        path="/v1/text-to-voice",
        body={
            "voice_name": name,
            "voice_description": description,
            "generated_voice_id": preview_id,
            "labels": labels,
        },
        timeout=timeout,
    )
    voice_id = payload.get("voice_id")
    if not isinstance(voice_id, str) or not voice_id.strip():
        raise core.SeedMediaError("ElevenLabs create-voice response lacks a voice ID")
    return {
        "voice_id": voice_id.strip(),
        "name": payload.get("name"),
        **headers,
    }


def _validated_character_alignment(
    value: Any,
    *,
    text: str,
) -> dict[str, list[Any]]:
    if not isinstance(value, dict):
        raise core.SeedMediaError(
            "ElevenLabs timestamp response lacks character alignment"
        )
    characters = value.get("characters")
    starts = value.get("character_start_times_seconds")
    ends = value.get("character_end_times_seconds")
    if (
        not isinstance(characters, list)
        or not isinstance(starts, list)
        or not isinstance(ends, list)
        or not characters
        or len(characters) != len(starts)
        or len(characters) != len(ends)
        or any(not isinstance(item, str) for item in characters)
        or "".join(characters) != text
    ):
        raise core.SeedMediaError(
            "ElevenLabs timestamps do not preserve the exact locked Arabic text"
        )
    try:
        numeric_starts = [float(item) for item in starts]
        numeric_ends = [float(item) for item in ends]
    except (TypeError, ValueError) as exc:
        raise core.SeedMediaError(
            "ElevenLabs returned invalid character timestamps"
        ) from exc
    if any(
        start < 0 or end <= start
        for start, end in zip(numeric_starts, numeric_ends, strict=True)
    ):
        raise core.SeedMediaError(
            "ElevenLabs returned non-positive character timestamp spans"
        )
    return {
        "characters": characters,
        "character_start_times_seconds": numeric_starts,
        "character_end_times_seconds": numeric_ends,
    }


def voice_map() -> dict[str, str]:
    """Return the required screenplay-entity to ElevenLabs voice-ID mapping."""

    raw = core.env("ELEVENLABS_VOICE_MAP", required=True)
    assert raw is not None
    value = core.parse_json_value(raw)
    if not isinstance(value, dict) or not value:
        raise core.SeedMediaError(
            "ELEVENLABS_VOICE_MAP must be a non-empty JSON object"
        )
    result: dict[str, str] = {}
    for entity_id, voice_id in value.items():
        if (
            not isinstance(entity_id, str)
            or not entity_id.strip()
            or not isinstance(voice_id, str)
            or not voice_id.strip()
        ):
            raise core.SeedMediaError(
                "ELEVENLABS_VOICE_MAP keys and values must be non-empty strings"
            )
        result[entity_id.strip()] = voice_id.strip()
    return result


def synthesize_arabic_speech(
    *,
    exact_text: str,
    voice_id: str,
    speed: float = 1.0,
    seed: int | None = None,
    voice_settings: dict[str, Any] | None = None,
    grammatical_gender: str = GRAMMATICAL_GENDER_POLICY,
    timeout: int = core.DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Synthesize exact Arabic via a pronunciation-only derived TTS string."""

    core.require_environment(*ELEVENLABS_TTS_ENV)
    if not voice_id.strip():
        raise core.SeedMediaError("ElevenLabs voice ID must not be empty")
    if speed < 0.7 or speed > 1.2:
        raise core.SeedMediaError(
            "ElevenLabs voice speed must be between 0.7 and 1.2"
        )
    output_format = (
        core.env("ELEVENLABS_OUTPUT_FORMAT") or DEFAULT_OUTPUT_FORMAT
    ).strip()
    if not output_format.startswith("mp3_"):
        raise core.SeedMediaError(
            "Arabic dubbing currently requires an ElevenLabs mp3_* output format"
        )
    pronunciation = compile_arabic_tts_text(
        exact_text,
        grammatical_gender=grammatical_gender,
        context="ElevenLabs Arabic cue",
    )
    seed_source = "explicit"
    if seed is None:
        seed = secrets.randbits(32)
        seed_source = "fresh_random"
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or not 0 <= seed <= 4294967295
    ):
        raise core.SeedMediaError(
            "ElevenLabs TTS seed must be an integer in 0..4294967295"
        )
    resolved_voice_settings = _voice_settings(
        speed=speed,
        approved_settings=voice_settings,
    )
    model_id = _model_id()
    body = {
        "text": pronunciation["tts_text"],
        "model_id": model_id,
        "voice_settings": resolved_voice_settings,
        "apply_text_normalization": "off",
        "seed": seed,
    }
    url = (
        f"{_base_url()}/v1/text-to-speech/"
        f"{urllib.parse.quote(voice_id, safe='')}"
        "/with-timestamps"
        f"?output_format={urllib.parse.quote(output_format, safe='')}"
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "xi-api-key": _api_key(),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "create-narrated-fable-drama/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_response = response.read()
            request_id = response.headers.get("request-id") or response.headers.get(
                "x-trace-id"
            )
            character_cost = response.headers.get("character-cost")
            content_type = response.headers.get("content-type")
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from exc
    except urllib.error.URLError as exc:
        raise core.SeedMediaError(
            f"ElevenLabs network request failed: {exc.reason}"
        ) from exc
    try:
        payload = json.loads(raw_response.decode("utf-8"))
        encoded_audio = payload["audio_base64"]
        audio = base64.b64decode(encoded_audio, validate=True)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise core.SeedMediaError(
            "ElevenLabs returned an invalid speech-with-timestamps response"
        ) from exc
    if not audio:
        raise core.SeedMediaError("ElevenLabs returned empty audio")
    alignment = _validated_character_alignment(
        payload.get("alignment"),
        text=pronunciation["tts_text"],
    )
    return {
        "audio": audio,
        "alignment": alignment,
        "request_id": request_id,
        "character_cost": character_cost,
        "content_type": content_type,
        "model_id": model_id,
        "voice_id": voice_id,
        "language_code": LANGUAGE_CODE,
        "language_code_sent": False,
        "accent_profile_id": ACCENT_PROFILE_ID,
        "grammatical_gender": grammatical_gender,
        "pronunciation_contract": PRONUNCIATION_CONTRACT,
        "exact_text": pronunciation["exact_text"],
        "tts_text": pronunciation["tts_text"],
        "exact_text_sha256": pronunciation["exact_text_sha256"],
        "tts_text_sha256": pronunciation["tts_text_sha256"],
        "tts_text_diacritic_count": pronunciation[
            "tts_text_diacritic_count"
        ],
        "pronunciation_rules": pronunciation["applied_rules"],
        "voice_settings": resolved_voice_settings,
        "speed": speed,
        "seed": seed,
        "seed_source": seed_source,
        "output_format": output_format,
    }
