#!/usr/bin/env python3
"""Create and gate one distinct Saudi-Arabic ElevenLabs voice per speaker asset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import tempfile
from pathlib import Path
from typing import Any

from production_design.contract import load_production_design_plan
from voice_reference_generation import (
    VoiceAuthorityError,
    _brief,
    _expected_words,
    _normalize_to_contract,
    _wav_evidence,
    validate_voice_authority,
)

from narrated_fable_drama.contracts.asset_catalog import (
    ASSET_CATALOG_RELATIVE_PATH,
)
from narrated_fable_drama.contracts.role_scope import (
    load_character_performance_map,
)
from narrated_fable_drama.contracts.screenplay import load_screenplay_file
from narrated_fable_drama.core.arabic_pronunciation import (
    ACCENT_LOCK_PHRASE,
    ACCENT_PROFILE_ID,
    GRAMMATICAL_GENDER_POLICY,
    PRONUNCIATION_CONTRACT,
    TTS_MODEL_ID,
    compile_arabic_tts_text,
    strip_arabic_diacritics,
)
from narrated_fable_drama.core.json_io import (
    load_json_object,
    write_json_atomic,
)
from narrated_fable_drama.core.paths import ProjectPaths
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.providers import elevenlabs
from narrated_fable_drama.providers import runtime as provider_runtime

REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root
VOICE_MAP_RELATIVE_PATH = Path("direct-production-design/elevenlabs-voice-map.json")
TTS_VOICE_SETTINGS = {
    "stability": 0.72,
    "similarity_boost": 0.86,
    "style": 0.0,
    "use_speaker_boost": True,
    "speed": 1.0,
}
ROLE_TTS_VOICE_SETTINGS = {
    "grandfather": {
        "stability": 0.74,
        "similarity_boost": 0.86,
        "style": 0.0,
        "use_speaker_boost": True,
        "speed": 0.98,
    },
}
ROLE_SEEDS = {
    "uthman": 17012001,
    "grandfather": 17012002,
    "lion": 17012003,
    "elephant": 17012004,
    "zebra": 17012005,
    "mosquito": 17012006,
}
VOICE_NAMES = {
    "uthman": "In-The-Forest Arabic Uthman",
    "grandfather": "In-The-Forest Arabic Grandfather",
    "lion": "In-The-Forest Arabic Lion",
    "elephant": "In-The-Forest Arabic Elephant",
    "zebra": "In-The-Forest Arabic Zebra",
    "mosquito": "In-The-Forest Arabic Mosquito",
}
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
LATIN_RE = re.compile(r"[A-Za-z]")
MAX_VOICE_DESIGN_SEED = 2147483647


class RoleVoiceGenerationError(RuntimeError):
    pass


def _resolved_preview_seed(value: int | None) -> tuple[int, str]:
    if value is None:
        return secrets.randbelow(MAX_VOICE_DESIGN_SEED + 1), "fresh_random"
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > MAX_VOICE_DESIGN_SEED
    ):
        raise RoleVoiceGenerationError(
            "Voice Design preview seed must be an integer in "
            f"0..{MAX_VOICE_DESIGN_SEED}"
        )
    return value, "explicit"


def _voice_labels(entity_id: str) -> dict[str, str]:
    return {
        "language": "ar",
        "accent": "Saudi-Riyadh",
        "use_case": "characters_animation",
        "role": entity_id,
    }


def _load_plan(task_root: Path) -> dict[str, Any]:
    performance = load_character_performance_map(task_root)
    screenplay = load_screenplay_file(task_root / "screenplay-writer" / "screenplay.md")
    return load_production_design_plan(
        task_root,
        performance=performance,
        screenplay=screenplay,
    )


def _speaking_characters(task_root: Path) -> list[dict[str, Any]]:
    plan = _load_plan(task_root)
    characters = [character for character in plan["characters"] if character["speaks"]]
    for character in characters:
        entity_id = character["entity_id"]
        text = character["voice_sample_text_en"]
        description = character["voice_description_en"]
        if not ARABIC_RE.search(text) or LATIN_RE.search(text):
            raise RoleVoiceGenerationError(
                f"{entity_id} voice sample must be locked Arabic without Latin text"
            )
        if not 100 <= len(text) <= 1000:
            raise RoleVoiceGenerationError(
                f"{entity_id} voice sample must be 100..1000 characters for "
                "ElevenLabs Voice Design"
            )
        if (
            "Saudi Arabic" not in description
            or ACCENT_LOCK_PHRASE not in description
        ):
            raise RoleVoiceGenerationError(
                f"{entity_id} voice description must lock the exact neutral "
                "urban Riyadh Saudi accent profile"
            )
        normalized_description = f" {description.casefold()} "
        if (
            " male " not in normalized_description
            and " man " not in normalized_description
        ):
            raise RoleVoiceGenerationError(
                f"{entity_id} must remain an explicitly male speaking role for "
                "the current masculine Arabic grammar policy"
            )
        exclusions = " ".join(
            character["voice_generation_prompt"]["exclusions_en"]
        )
        for forbidden_dialect in ("Egyptian", "Levantine", "Emirati", "Kuwaiti"):
            if forbidden_dialect not in exclusions:
                raise RoleVoiceGenerationError(
                    f"{entity_id} voice exclusions must reject "
                    f"{forbidden_dialect} dialect drift"
                )
    return characters


def _voice_design_prompt(character: dict[str, Any]) -> str:
    """Compile every authored Voice Design instruction into one provider Prompt."""

    prompt = character["voice_generation_prompt"]
    exclusions = " ".join(prompt["exclusions_en"])
    rendered = (
        f"{prompt['voice_direction_en']} "
        f"Delivery: {prompt['delivery_en']} "
        f"Exclusions: {exclusions}"
    ).strip()
    if not 20 <= len(rendered) <= 1000:
        raise RoleVoiceGenerationError(
            f"{character['entity_id']} compiled ElevenLabs Voice Design Prompt "
            "must be 20..1000 characters"
        )
    return rendered


def _load_voice_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = load_json_object(
        path,
        label="asset-department ElevenLabs role voice map",
        error_type=RoleVoiceGenerationError,
    )
    result: dict[str, str] = {}
    for entity_id, voice_id in payload.items():
        if (
            not isinstance(entity_id, str)
            or not entity_id.strip()
            or not isinstance(voice_id, str)
            or not voice_id.strip()
        ):
            raise RoleVoiceGenerationError(
                "ElevenLabs role voice map must contain non-empty string pairs"
            )
        result[entity_id.strip()] = voice_id.strip()
    return result


def _alignment_words(
    alignment: dict[str, list[Any]],
    *,
    exact_text: str,
    tts_text: str,
) -> list[dict[str, Any]]:
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    if "".join(alignment["characters"]) != tts_text:
        raise RoleVoiceGenerationError(
            "ElevenLabs timestamps changed the pronunciation-only TTS text"
        )
    exact_matches = list(re.finditer(r"\S+", exact_text))
    tts_matches = list(re.finditer(r"\S+", tts_text))
    if (
        len(exact_matches) != len(tts_matches)
        or any(
            strip_arabic_diacritics(tts.group(0)) != exact.group(0)
            for exact, tts in zip(exact_matches, tts_matches, strict=True)
        )
    ):
        raise RoleVoiceGenerationError(
            "ElevenLabs pronunciation text changed the locked Arabic word "
            "sequence"
        )
    words: list[dict[str, Any]] = []
    for exact_match, tts_match in zip(
        exact_matches,
        tts_matches,
        strict=True,
    ):
        spoken_indexes = [
            index
            for index in range(tts_match.start(), tts_match.end())
            if tts_text[index].isalnum()
        ]
        if not spoken_indexes:
            continue
        words.append(
            {
                "text": exact_match.group(0),
                "start_seconds": round(
                    float(starts[spoken_indexes[0]]),
                    6,
                ),
                "end_seconds": round(
                    float(ends[spoken_indexes[-1]]),
                    6,
                ),
            }
        )
    actual = [
        "".join(
            character.casefold() for character in word["text"] if character.isalnum()
        )
        for word in words
    ]
    expected = _expected_words(exact_text)
    if actual != expected:
        raise RoleVoiceGenerationError(
            "ElevenLabs character timestamps could not be converted to exact "
            f"Arabic word timing: expected={expected}, actual={actual}"
        )
    return words


def _update_catalog_voice(
    *,
    entity_id: str,
    description: str,
    uri: str,
) -> None:
    catalog_path = REPOSITORY_ROOT / ASSET_CATALOG_RELATIVE_PATH
    catalog = load_json_object(
        catalog_path,
        label="shared asset catalog",
        error_type=RoleVoiceGenerationError,
    )
    asset = catalog.get("assets", {}).get(entity_id)
    if not isinstance(asset, dict) or asset.get("type") != "character":
        raise RoleVoiceGenerationError(
            f"Shared asset catalog lacks character {entity_id}"
        )
    asset["voice"] = {
        "description_en": description,
        "reference": {
            "path": (f"workspace/assets/characters/{entity_id}/voice.wav"),
            "uri": uri,
        },
    }
    write_json_atomic(catalog_path, catalog)


def _generate_reference(
    *,
    character: dict[str, Any],
    voice_id: str,
    voice_design: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    entity_id = character["entity_id"]
    tts_settings = ROLE_TTS_VOICE_SETTINGS.get(
        entity_id,
        TTS_VOICE_SETTINGS,
    )
    os.environ["ELEVENLABS_MODEL_ID"] = TTS_MODEL_ID
    os.environ["ELEVENLABS_VOICE_SETTINGS"] = json.dumps(
        tts_settings,
        separators=(",", ":"),
    )
    folder = REPOSITORY_ROOT / "workspace/assets/characters" / entity_id
    target = folder / "voice.wav"
    brief_path = folder / "voice.brief.json"
    with tempfile.TemporaryDirectory(
        prefix=f"elevenlabs-{entity_id}-"
    ) as temporary_dir:
        result = elevenlabs.synthesize_arabic_speech(
            exact_text=character["voice_sample_text_en"],
            voice_id=voice_id,
            speed=float(tts_settings["speed"]),
            timeout=timeout,
        )
        source = Path(temporary_dir) / "voice.mp3"
        source.write_bytes(result["audio"])
        staged = Path(temporary_dir) / "voice.wav"
        duration = _normalize_to_contract(source, staged)
        words = _alignment_words(
            result["alignment"],
            exact_text=character["voice_sample_text_en"],
            tts_text=result["tts_text"],
        )
        if words[-1]["end_seconds"] > duration + 0.02:
            raise RoleVoiceGenerationError(
                f"{entity_id} word timing exceeds normalized voice duration"
            )
        stored = provider_runtime.tos_upload_path(
            staged,
            kind="inputs/audio",
        )
        uri = stored["public_url"]
        folder.mkdir(parents=True, exist_ok=True)
        ready = target.with_name(f".{target.name}.ready")
        ready.unlink(missing_ok=True)
        shutil.copyfile(staged, ready)
        ready.replace(target)
    brief = {
        **_brief(character),
        "elevenlabs": {
            "voice_id": voice_id,
            "voice_design": voice_design,
            "tts_model_id": result["model_id"],
            "accent_profile_id": result["accent_profile_id"],
            "grammatical_gender_policy": result["grammatical_gender"],
            "pronunciation_contract": result["pronunciation_contract"],
            "exact_text_sha256": result["exact_text_sha256"],
            "tts_text_sha256": result["tts_text_sha256"],
            "tts_text_diacritic_count": result[
                "tts_text_diacritic_count"
            ],
            "language_code_sent": result["language_code_sent"],
            "voice_settings": result["voice_settings"],
        },
        "evidence": {
            "uri": uri,
            "words": words,
        },
    }
    write_json_atomic(brief_path, brief)
    _update_catalog_voice(
        entity_id=entity_id,
        description=character["voice_description_en"],
        uri=uri,
    )
    return {
        "entity_id": entity_id,
        "voice_id": voice_id,
        "reference_path": str(target),
        "reference_uri": uri,
        "duration_seconds": round(duration, 6),
        "word_count": len(words),
    }


def _existing_reference_result(
    character: dict[str, Any],
    *,
    voice_id: str,
) -> dict[str, Any]:
    """Recover a completed reference after a later cast-wide gate failed."""

    entity_id = character["entity_id"]
    _validate_elevenlabs_voice_brief(
        character,
        expected_voice_id=voice_id,
    )
    folder = REPOSITORY_ROOT / "workspace/assets/characters" / entity_id
    target = folder / "voice.wav"
    brief = load_json_object(
        folder / "voice.brief.json",
        label=f"{entity_id} ElevenLabs voice brief",
        error_type=RoleVoiceGenerationError,
    )
    wav_evidence = _wav_evidence(target)
    evidence = brief.get("evidence")
    if (
        wav_evidence is None
        or not isinstance(evidence, dict)
        or not isinstance(evidence.get("uri"), str)
        or not evidence["uri"].strip()
        or not isinstance(evidence.get("words"), list)
        or not evidence["words"]
    ):
        raise RoleVoiceGenerationError(
            f"{entity_id} partial Voice Design selection lacks a recoverable "
            "reference"
        )
    return {
        "entity_id": entity_id,
        "voice_id": voice_id,
        "reference_path": str(target),
        "reference_uri": evidence["uri"],
        "duration_seconds": round(wav_evidence["duration_seconds"], 6),
        "word_count": len(evidence["words"]),
        "recovered_without_provider_call": True,
    }


def _validate_elevenlabs_voice_brief(
    character: dict[str, Any],
    *,
    expected_voice_id: str,
) -> dict[str, Any]:
    entity_id = character["entity_id"]
    brief_path = (
        REPOSITORY_ROOT
        / "workspace"
        / "assets"
        / "characters"
        / entity_id
        / "voice.brief.json"
    )
    brief = load_json_object(
        brief_path,
        label=f"{entity_id} ElevenLabs voice brief",
        error_type=RoleVoiceGenerationError,
    )
    authored_authority = {
        key: value
        for key, value in brief.items()
        if key not in {"elevenlabs", "evidence"}
    }
    if authored_authority != _brief(character):
        raise RoleVoiceGenerationError(
            f"{entity_id} voice reference is stale against the hardened Saudi "
            "accent Prompt"
        )
    pronunciation = compile_arabic_tts_text(
        character["voice_sample_text_en"],
        grammatical_gender=GRAMMATICAL_GENDER_POLICY,
        context=f"{entity_id} voice-reference gate",
    )
    expected_settings = ROLE_TTS_VOICE_SETTINGS.get(
        entity_id,
        TTS_VOICE_SETTINGS,
    )
    expected_provider = {
        "voice_id": expected_voice_id,
        "tts_model_id": TTS_MODEL_ID,
        "accent_profile_id": ACCENT_PROFILE_ID,
        "grammatical_gender_policy": GRAMMATICAL_GENDER_POLICY,
        "pronunciation_contract": PRONUNCIATION_CONTRACT,
        "exact_text_sha256": pronunciation["exact_text_sha256"],
        "tts_text_sha256": pronunciation["tts_text_sha256"],
        "tts_text_diacritic_count": pronunciation[
            "tts_text_diacritic_count"
        ],
        "language_code_sent": False,
        "voice_settings": expected_settings,
    }
    provider = brief.get("elevenlabs")
    if not isinstance(provider, dict):
        raise RoleVoiceGenerationError(
            f"{entity_id} voice reference lacks ElevenLabs provider provenance"
        )
    voice_design = provider.get("voice_design")
    expected_labels = {
        **_voice_labels(entity_id),
    }
    expected_design = {
        "model_id": elevenlabs.DEFAULT_VOICE_DESIGN_MODEL_ID,
        "prompt_sha256": hashlib.sha256(
            _voice_design_prompt(character).encode("utf-8")
        ).hexdigest(),
        "preview_tts_text_sha256": pronunciation["tts_text_sha256"],
        "labels": expected_labels,
    }
    if (
        not isinstance(voice_design, dict)
        or any(
            voice_design.get(key) != value
            for key, value in expected_design.items()
        )
        or not isinstance(
            voice_design.get("selected_generated_voice_id"),
            str,
        )
        or not voice_design["selected_generated_voice_id"].strip()
    ):
        raise RoleVoiceGenerationError(
            f"{entity_id} voice ID was not selected from the current hardened "
            "Saudi Voice Design Prompt"
        )
    observed_provider = {
        key: value
        for key, value in provider.items()
        if key != "voice_design"
    }
    if observed_provider != expected_provider:
        raise RoleVoiceGenerationError(
            f"{entity_id} voice reference lacks the current Multilingual v2, "
            "Saudi accent, masculine pronunciation, or stable-settings evidence"
        )
    return voice_design


def validate_role_voice_map(task_root: Path) -> dict[str, Any]:
    task_root = task_root.expanduser().resolve(strict=True)
    characters = _speaking_characters(task_root)
    expected = [character["entity_id"] for character in characters]
    mapping_path = task_root / VOICE_MAP_RELATIVE_PATH
    mapping = _load_voice_map(mapping_path)
    if set(mapping) != set(expected):
        raise RoleVoiceGenerationError(
            "Asset-department ElevenLabs role map must exactly cover speaking "
            f"characters: expected={sorted(expected)}, actual={sorted(mapping)}"
        )
    if len(set(mapping.values())) != len(mapping):
        raise RoleVoiceGenerationError(
            "Every speaking character must use a distinct ElevenLabs voice ID"
        )
    voice_authority = validate_voice_authority(task_root)
    if voice_authority["speaker_count"] != len(expected):
        raise RoleVoiceGenerationError(
            "Arabic ElevenLabs reference WAVs do not cover all speaking characters"
        )
    for character in characters:
        _validate_elevenlabs_voice_brief(
            character,
            expected_voice_id=mapping[character["entity_id"]],
        )
    return {
        "status": "PASS",
        "department": "direct-production-design",
        "language": "ar-SA",
        "tts_model_id": TTS_MODEL_ID,
        "accent_profile_id": ACCENT_PROFILE_ID,
        "grammatical_gender_policy": GRAMMATICAL_GENDER_POLICY,
        "pronunciation_contract": PRONUNCIATION_CONTRACT,
        "language_code_sent": False,
        "tts_voice_settings": TTS_VOICE_SETTINGS,
        "role_tts_voice_settings": ROLE_TTS_VOICE_SETTINGS,
        "voice_map_path": str(mapping_path),
        "speaker_count": len(expected),
        "distinct_voice_id_count": len(set(mapping.values())),
        "voices": [
            {
                "entity_id": entity_id,
                "voice_id": mapping[entity_id],
            }
            for entity_id in expected
        ],
    }


def generate_role_voices(
    task_root: Path,
    *,
    timeout: int,
    preview_index: int,
    entity_ids: set[str] | None = None,
) -> dict[str, Any]:
    task_root = task_root.expanduser().resolve(strict=True)
    context = load_project_context(task_root)
    if (
        context.get("target_language") != "Arabic"
        or context.get("speech_audio_source") != "elevenlabs_dubbed"
    ):
        raise RoleVoiceGenerationError(
            "Role-voice generation requires the Arabic ElevenLabs project contract"
        )
    if preview_index not in {0, 1, 2}:
        raise RoleVoiceGenerationError(
            "ElevenLabs Voice Design preview index must be 0, 1, or 2"
        )
    characters = _speaking_characters(task_root)
    expected_ids = [character["entity_id"] for character in characters]
    if set(expected_ids) != set(ROLE_SEEDS):
        raise RoleVoiceGenerationError(
            "Role seed authority must exactly cover the current speaking cast"
        )
    selected_ids = set(entity_ids or expected_ids)
    unknown_ids = selected_ids - set(expected_ids)
    if unknown_ids:
        raise RoleVoiceGenerationError(
            f"Unknown speaking character IDs: {sorted(unknown_ids)}"
        )

    os.environ["ELEVENLABS_MODEL_ID"] = TTS_MODEL_ID
    os.environ["ELEVENLABS_VOICE_SETTINGS"] = json.dumps(
        TTS_VOICE_SETTINGS,
        separators=(",", ":"),
    )
    mapping_path = task_root / VOICE_MAP_RELATIVE_PATH
    mapping = _load_voice_map(mapping_path)
    unexpected = set(mapping) - set(expected_ids)
    if unexpected:
        raise RoleVoiceGenerationError(
            f"ElevenLabs role voice map contains unexpected roles: {sorted(unexpected)}"
        )

    generated: list[dict[str, Any]] = []
    for character in characters:
        entity_id = character["entity_id"]
        if entity_id not in selected_ids:
            continue
        voice_id = mapping.get(entity_id)
        if voice_id is None:
            preview_pronunciation = compile_arabic_tts_text(
                character["voice_sample_text_en"],
                grammatical_gender=GRAMMATICAL_GENDER_POLICY,
                context=f"{entity_id} Voice Design preview",
            )
            designed = elevenlabs.design_voice_previews(
                voice_description=_voice_design_prompt(character),
                text=preview_pronunciation["tts_text"],
                seed=ROLE_SEEDS[entity_id],
                timeout=timeout,
            )
            selected = designed["previews"][preview_index]
            created = elevenlabs.create_voice_from_preview(
                voice_name=VOICE_NAMES[entity_id],
                voice_description=_voice_design_prompt(character),
                generated_voice_id=selected["generated_voice_id"],
                labels=_voice_labels(entity_id),
                timeout=timeout,
            )
            voice_id = created["voice_id"]
            voice_design = {
                "model_id": designed["model_id"],
                "prompt_sha256": hashlib.sha256(
                    _voice_design_prompt(character).encode("utf-8")
                ).hexdigest(),
                "preview_tts_text_sha256": preview_pronunciation[
                    "tts_text_sha256"
                ],
                "selected_generated_voice_id": selected[
                    "generated_voice_id"
                ],
                "labels": _voice_labels(entity_id),
            }
            mapping[entity_id] = voice_id
            mapping_path.parent.mkdir(parents=True, exist_ok=True)
            write_json_atomic(mapping_path, mapping)
        else:
            voice_design = _validate_elevenlabs_voice_brief(
                character,
                expected_voice_id=voice_id,
            )
        generated.append(
            _generate_reference(
                character=character,
                voice_id=voice_id,
                voice_design=voice_design,
                timeout=timeout,
            )
        )

    if set(mapping) == set(expected_ids):
        gate: dict[str, Any] = validate_role_voice_map(task_root)
    else:
        gate = {
            "status": "PENDING",
            "missing_entity_ids": sorted(set(expected_ids) - set(mapping)),
            "distinct_voice_id_count": len(set(mapping.values())),
        }
    return {
        "status": gate["status"],
        "generated": generated,
        "gate": gate,
    }


def generate_role_voice_previews(
    task_root: Path,
    *,
    entity_id: str,
    output_dir: Path,
    timeout: int,
    preview_seed: int | None = None,
) -> dict[str, Any]:
    """Generate three reviewable candidates without saving or replacing a voice."""

    task_root = task_root.expanduser().resolve(strict=True)
    context = load_project_context(task_root)
    if (
        context.get("target_language") != "Arabic"
        or context.get("speech_audio_source") != "elevenlabs_dubbed"
    ):
        raise RoleVoiceGenerationError(
            "Role-voice generation requires the Arabic ElevenLabs project contract"
        )
    characters = {
        character["entity_id"]: character
        for character in _speaking_characters(task_root)
    }
    if entity_id not in characters:
        raise RoleVoiceGenerationError(
            f"Unknown speaking character ID: {entity_id}"
        )
    character = characters[entity_id]
    design_prompt = _voice_design_prompt(character)
    resolved_seed, seed_source = _resolved_preview_seed(preview_seed)
    preview_pronunciation = compile_arabic_tts_text(
        character["voice_sample_text_en"],
        grammatical_gender=GRAMMATICAL_GENDER_POLICY,
        context=f"{entity_id} Voice Design preview",
    )
    designed = elevenlabs.design_voice_previews(
        voice_description=design_prompt,
        text=preview_pronunciation["tts_text"],
        seed=resolved_seed,
        timeout=timeout,
    )

    destination = output_dir.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    previews: list[dict[str, Any]] = []
    for index, preview in enumerate(designed["previews"]):
        audio_path = destination / f"{entity_id}-candidate-{index + 1}.mp3"
        if audio_path.exists():
            raise RoleVoiceGenerationError(
                f"Refusing to overwrite existing Voice Design preview: {audio_path}"
            )
        audio_path.write_bytes(preview["audio"])
        previews.append(
            {
                "preview_index": index,
                "generated_voice_id": preview["generated_voice_id"],
                "audio_path": str(audio_path),
                "duration_seconds": preview["duration_seconds"],
                "media_type": preview["media_type"],
                "language": preview["language"],
            }
        )
    metadata = {
        "contract": "elevenlabs-voice-design-review/v1",
        "status": "AWAITING_SELECTION",
        "department": "direct-production-design",
        "task_root": str(task_root),
        "entity_id": entity_id,
        "current_voice_id": _load_voice_map(
            task_root / VOICE_MAP_RELATIVE_PATH
        ).get(entity_id),
        "voice_name": VOICE_NAMES[entity_id],
        "model_id": designed["model_id"],
        "seed": designed["seed"],
        "seed_source": seed_source,
        "request_id": designed["request_id"],
        "character_cost": designed["character_cost"],
        "voice_description": character["voice_description_en"],
        "voice_design_prompt": design_prompt,
        "preview_text": character["voice_sample_text_en"],
        "preview_tts_text": preview_pronunciation["tts_text"],
        "preview_tts_text_sha256": preview_pronunciation[
            "tts_text_sha256"
        ],
        "accent_profile_id": ACCENT_PROFILE_ID,
        "grammatical_gender_policy": GRAMMATICAL_GENDER_POLICY,
        "pronunciation_contract": PRONUNCIATION_CONTRACT,
        "previews": previews,
    }
    metadata_path = destination / "selection.json"
    if metadata_path.exists():
        raise RoleVoiceGenerationError(
            f"Refusing to overwrite existing Voice Design metadata: {metadata_path}"
        )
    write_json_atomic(metadata_path, metadata)
    return {
        "status": "AWAITING_SELECTION",
        "entity_id": entity_id,
        "current_voice_id": _load_voice_map(
            task_root / VOICE_MAP_RELATIVE_PATH
        ).get(entity_id),
        "existing_voice_preserved": True,
        "metadata_path": str(metadata_path),
        "previews": previews,
    }


def select_role_voice_preview(
    task_root: Path,
    *,
    selection_path: Path,
    preview_index: int,
    timeout: int,
    resume_voice_id: str | None = None,
) -> dict[str, Any]:
    """Save one reviewed preview and atomically replace that role's authority."""

    task_root = task_root.expanduser().resolve(strict=True)
    selection_path = selection_path.expanduser().resolve(strict=True)
    selection = load_json_object(
        selection_path,
        label="ElevenLabs Voice Design selection",
        error_type=RoleVoiceGenerationError,
    )
    if selection.get("contract") != "elevenlabs-voice-design-review/v1":
        raise RoleVoiceGenerationError("Unsupported Voice Design selection contract")
    if selection.get("status") != "AWAITING_SELECTION":
        raise RoleVoiceGenerationError(
            "Voice Design selection is not awaiting a human choice"
        )
    if selection.get("task_root") != str(task_root):
        raise RoleVoiceGenerationError(
            "Voice Design selection belongs to a different task"
        )
    entity_id = selection.get("entity_id")
    characters = {
        character["entity_id"]: character
        for character in _speaking_characters(task_root)
    }
    if entity_id not in characters:
        raise RoleVoiceGenerationError(
            "Voice Design selection names an unknown speaking character"
        )
    character = characters[entity_id]
    preview_pronunciation = compile_arabic_tts_text(
        character["voice_sample_text_en"],
        grammatical_gender=GRAMMATICAL_GENDER_POLICY,
        context=f"{entity_id} Voice Design selection",
    )
    if (
        selection.get("voice_design_prompt") != _voice_design_prompt(character)
        or selection.get("model_id")
        != elevenlabs.DEFAULT_VOICE_DESIGN_MODEL_ID
        or selection.get("preview_text") != character["voice_sample_text_en"]
        or selection.get("preview_tts_text")
        != preview_pronunciation["tts_text"]
        or selection.get("preview_tts_text_sha256")
        != preview_pronunciation["tts_text_sha256"]
        or selection.get("accent_profile_id") != ACCENT_PROFILE_ID
        or selection.get("grammatical_gender_policy")
        != GRAMMATICAL_GENDER_POLICY
        or selection.get("pronunciation_contract")
        != PRONUNCIATION_CONTRACT
    ):
        raise RoleVoiceGenerationError(
            "Voice Design selection is stale against the current asset Prompt"
        )
    previews = selection.get("previews")
    if not isinstance(previews, list) or len(previews) != 3:
        raise RoleVoiceGenerationError(
            "Voice Design selection must contain exactly three previews"
        )
    if preview_index not in {0, 1, 2}:
        raise RoleVoiceGenerationError(
            "ElevenLabs Voice Design preview index must be 0, 1, or 2"
        )
    selected = previews[preview_index]
    if (
        not isinstance(selected, dict)
        or selected.get("preview_index") != preview_index
        or not isinstance(selected.get("generated_voice_id"), str)
        or not selected["generated_voice_id"].strip()
    ):
        raise RoleVoiceGenerationError("Selected Voice Design preview is invalid")

    mapping_path = task_root / VOICE_MAP_RELATIVE_PATH
    mapping = _load_voice_map(mapping_path)
    old_voice_id = mapping.get(entity_id)
    selected_generated_voice_id = selected["generated_voice_id"]
    recovered_partial_selection = old_voice_id == selected_generated_voice_id
    if recovered_partial_selection:
        new_voice_id = selected_generated_voice_id
        reference = _existing_reference_result(
            character,
            voice_id=new_voice_id,
        )
    elif resume_voice_id is None:
        created = elevenlabs.create_voice_from_preview(
            voice_name=VOICE_NAMES[entity_id],
            voice_description=_voice_design_prompt(character),
            generated_voice_id=selected_generated_voice_id,
            labels=_voice_labels(entity_id),
            timeout=timeout,
        )
        new_voice_id = created["voice_id"]
    else:
        new_voice_id = resume_voice_id.strip()
        if new_voice_id != selected_generated_voice_id:
            raise RoleVoiceGenerationError(
                "Resumed saved voice ID must match the selected generated voice ID"
            )
    if any(
        mapped_voice_id == new_voice_id
        for mapped_entity_id, mapped_voice_id in mapping.items()
        if mapped_entity_id != entity_id
    ):
        raise RoleVoiceGenerationError(
            "Newly saved role voice duplicates an existing cast voice ID"
        )

    tts_settings = ROLE_TTS_VOICE_SETTINGS.get(entity_id, TTS_VOICE_SETTINGS)
    if not recovered_partial_selection:
        os.environ["ELEVENLABS_MODEL_ID"] = TTS_MODEL_ID
        os.environ["ELEVENLABS_VOICE_SETTINGS"] = json.dumps(
            tts_settings,
            separators=(",", ":"),
        )
        reference = _generate_reference(
            character=character,
            voice_id=new_voice_id,
            voice_design={
                "model_id": selection["model_id"],
                "prompt_sha256": hashlib.sha256(
                    _voice_design_prompt(character).encode("utf-8")
                ).hexdigest(),
                "preview_tts_text_sha256": preview_pronunciation[
                    "tts_text_sha256"
                ],
                "selected_generated_voice_id": selected_generated_voice_id,
                "labels": _voice_labels(entity_id),
            },
            timeout=timeout,
        )
        mapping[entity_id] = new_voice_id
        write_json_atomic(mapping_path, mapping)
    _validate_elevenlabs_voice_brief(
        character,
        expected_voice_id=new_voice_id,
    )
    expected_ids = {
        item["entity_id"] for item in _speaking_characters(task_root)
    }
    if set(mapping) == expected_ids:
        try:
            gate: dict[str, Any] = validate_role_voice_map(task_root)
        except (RoleVoiceGenerationError, VoiceAuthorityError) as exc:
            gate = {
                "status": "PENDING",
                "reason": str(exc),
                "speaker_count": len(expected_ids),
                "distinct_voice_id_count": len(set(mapping.values())),
            }
    else:
        gate = {
            "status": "PENDING",
            "missing_entity_ids": sorted(expected_ids - set(mapping)),
            "distinct_voice_id_count": len(set(mapping.values())),
        }

    previous_voice_id = (
        selection.get("current_voice_id")
        if recovered_partial_selection
        else old_voice_id
    )
    selection["status"] = "SELECTED"
    selection["selected_preview_index"] = preview_index
    selection["selected_generated_voice_id"] = selected_generated_voice_id
    selection["previous_voice_id"] = previous_voice_id
    selection["saved_voice_id"] = new_voice_id
    selection["recovered_partial_selection"] = recovered_partial_selection
    selection["tts_voice_settings"] = tts_settings
    selection["reference"] = reference
    write_json_atomic(selection_path, selection)
    return {
        "status": "PASS",
        "entity_id": entity_id,
        "selected_preview_index": preview_index,
        "previous_voice_id": previous_voice_id,
        "voice_id": new_voice_id,
        "reference": reference,
        "gate": gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument(
        "--preview-index",
        type=int,
        default=0,
        help="Select one of the three Voice Design previews (0, 1, or 2).",
    )
    parser.add_argument(
        "--entity-id",
        action="append",
        default=[],
        help="Generate only this speaking character; repeat for multiple roles.",
    )
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Generate three candidates without saving or replacing a role voice.",
    )
    parser.add_argument(
        "--preview-dir",
        type=Path,
        help="Destination for --preview-only MP3 candidates and selection metadata.",
    )
    parser.add_argument(
        "--preview-seed",
        type=int,
        help=(
            "Optional reproducible Voice Design seed for --preview-only. "
            "Omit to generate a fresh candidate set."
        ),
    )
    parser.add_argument(
        "--select-preview",
        type=Path,
        help="Save one human-approved candidate from Voice Design selection metadata.",
    )
    parser.add_argument(
        "--resume-voice-id",
        help="Resume selection after the chosen preview was already saved remotely.",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.preview_seed is not None and not args.preview_only:
            raise RoleVoiceGenerationError(
                "--preview-seed is valid only with --preview-only"
            )
        if args.validate_only:
            result = validate_role_voice_map(args.task_dir)
        elif args.preview_only:
            if len(args.entity_id) != 1 or args.preview_dir is None:
                raise RoleVoiceGenerationError(
                    "--preview-only requires exactly one --entity-id and "
                    "--preview-dir"
                )
            result = generate_role_voice_previews(
                args.task_dir,
                entity_id=args.entity_id[0],
                output_dir=args.preview_dir,
                timeout=args.timeout,
                preview_seed=args.preview_seed,
            )
        elif args.select_preview is not None:
            if (
                args.entity_id
                or args.preview_dir is not None
                or args.preview_seed is not None
            ):
                raise RoleVoiceGenerationError(
                    "--select-preview cannot be combined with --entity-id, "
                    "--preview-dir, or --preview-seed"
                )
            result = select_role_voice_preview(
                args.task_dir,
                selection_path=args.select_preview,
                preview_index=args.preview_index,
                timeout=args.timeout,
                resume_voice_id=args.resume_voice_id,
            )
        else:
            if args.resume_voice_id is not None:
                raise RoleVoiceGenerationError(
                    "--resume-voice-id requires --select-preview"
                )
            if args.preview_dir is not None or args.preview_seed is not None:
                raise RoleVoiceGenerationError(
                    "--preview-dir and --preview-seed are valid only with "
                    "--preview-only"
                )
            result = generate_role_voices(
                args.task_dir,
                timeout=args.timeout,
                preview_index=args.preview_index,
                entity_ids=set(args.entity_id) or None,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error": str(exc),
                    "automatic_retry": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
