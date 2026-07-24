"""Generate dialogue-identity voice references at their natural authored duration."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import shutil
import struct
import tempfile
from typing import Any
import wave
from pathlib import PurePosixPath

from narrated_fable_drama.contracts.asset_catalog import (
    ASSET_CATALOG_RELATIVE_PATH,
    load_asset_catalog,
)
from narrated_fable_drama.core.json_io import (
    load_optional_json_object,
    write_json_atomic,
)
from narrated_fable_drama.core.paths import ProjectPaths
from narrated_fable_drama.core.validation import StoryVideoError
from narrated_fable_drama.media.ffmpeg import (
    MediaCommandError,
    run as run_media_command,
)
from narrated_fable_drama.providers import runtime as provider_runtime
from narrated_fable_drama.providers import seedaudio


REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root
ASSET_MEDIA_RELATIVE_PATH = Path("workspace/assets")


VOICE_SAMPLE_RATE_HZ = 48000
VOICE_CHANNELS = 2
VOICE_SAMPLE_WIDTH_BYTES = 2
VOICE_MAX_EDGE_SILENCE_SECONDS = 1.0
VOICE_MAX_INTERNAL_WORD_GAP_SECONDS = 0.6
VOICE_DURATION_TOLERANCE_SECONDS = 0.02
VOICE_BRIEF_CONTRACT = "voice-reference-brief/dynamic-duration"
VOICE_DURATION_POLICY = "natural_duration_from_exact_sample_text"


class VoiceReferenceGenerationError(RuntimeError):
    pass


class VoiceAuthorityError(StoryVideoError):
    """Raised when repository-owned voice evidence is missing or inconsistent."""


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    write_json_atomic(path, value)


def _load_json(path: Path) -> dict[str, Any] | None:
    return load_optional_json_object(path)


def _wav_evidence(path: Path) -> dict[str, Any] | None:
    try:
        with wave.open(str(path), "rb") as source:
            if (
                source.getcomptype() != "NONE"
                or source.getframerate() != VOICE_SAMPLE_RATE_HZ
                or source.getnchannels() != VOICE_CHANNELS
                or source.getsampwidth() != VOICE_SAMPLE_WIDTH_BYTES
                or source.getnframes() <= 0
            ):
                return None
            return {
                "duration_seconds": source.getnframes() / float(source.getframerate()),
                "sample_frames": source.getnframes(),
            }
    except (FileNotFoundError, OSError, wave.Error):
        return None


def _existing_voice_is_current(
    path: Path,
    brief: dict[str, Any] | None,
    *,
    expected_brief: dict[str, Any],
) -> bool:
    wav_evidence = _wav_evidence(path)
    if wav_evidence is None or not isinstance(brief, dict):
        return False
    authority = {key: value for key, value in brief.items() if key != "evidence"}
    if authority != expected_brief:
        return False
    evidence = brief.get("evidence")
    if (
        not isinstance(evidence, dict)
        or set(evidence) != {"uri", "words"}
        or not isinstance(evidence.get("uri"), str)
        or not evidence["uri"].strip()
    ):
        return False
    words = evidence.get("words")
    if not isinstance(words, list) or not words:
        return False
    actual_words = [
        "".join(character.casefold() for character in word.get("text", "") if character.isalnum())
        for word in words
        if isinstance(word, dict)
    ]
    if actual_words != _expected_words(expected_brief["sample_text_en"]):
        return False
    previous_start = 0.0
    previous_end = 0.0
    for index, word in enumerate(words):
        if not isinstance(word, dict) or set(word) != {
            "text",
            "start_seconds",
            "end_seconds",
        }:
            return False
        start = word.get("start_seconds")
        end = word.get("end_seconds")
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, (int, float))
            or not isinstance(end, (int, float))
            or start < 0
            or end <= start
            or end
            > wav_evidence["duration_seconds"] + VOICE_DURATION_TOLERANCE_SECONDS
            or (index and start < previous_start)
            or (index and end < previous_end)
            or (
                index
                and start - previous_end > VOICE_MAX_INTERNAL_WORD_GAP_SECONDS
            )
        ):
            return False
        previous_start = float(start)
        previous_end = float(end)
    return (
        float(words[0]["start_seconds"]) <= VOICE_MAX_EDGE_SILENCE_SECONDS
        and wav_evidence["duration_seconds"] - previous_end
        <= VOICE_MAX_EDGE_SILENCE_SECONDS
    )


def _brief(character: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract": VOICE_BRIEF_CONTRACT,
        "entity_id": character["entity_id"],
        "voice_description_en": character["voice_description_en"],
        "sample_text_en": character["voice_sample_text_en"],
        "speech_rate": character["voice_speech_rate"],
        "generation_prompt": character["voice_generation_prompt"],
        "output": {
            "sample_rate_hz": VOICE_SAMPLE_RATE_HZ,
            "channels": VOICE_CHANNELS,
            "codec": "pcm_s16le",
            "duration_policy": VOICE_DURATION_POLICY,
            "timing_authority": "provider_exact_word_subtitles",
            "max_lead_in_seconds": VOICE_MAX_EDGE_SILENCE_SECONDS,
            "max_trailing_silence_seconds": VOICE_MAX_EDGE_SILENCE_SECONDS,
            "max_internal_word_gap_seconds": VOICE_MAX_INTERNAL_WORD_GAP_SECONDS,
        },
    }


def _expected_words(text: str) -> list[str]:
    return [
        "".join(character.casefold() for character in token if character.isalnum())
        for token in re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text, flags=re.UNICODE)
    ]


def _subtitle_word_timing(
    subtitle: Any, *, expected_text: str, provider_duration_seconds: float
) -> list[dict[str, Any]]:
    """Validate exact spoken words against the provider audio's own duration."""

    if provider_duration_seconds <= 0:
        raise VoiceReferenceGenerationError("Seed Audio returned empty audio")

    if not isinstance(subtitle, dict) or not isinstance(subtitle.get("sentences"), list):
        raise VoiceReferenceGenerationError(
            "Seed Audio returned no word-timing subtitle authority"
        )
    words: list[dict[str, Any]] = []
    for sentence in subtitle["sentences"]:
        if not isinstance(sentence, dict) or not isinstance(sentence.get("words"), list):
            raise VoiceReferenceGenerationError(
                "Seed Audio returned invalid word-timing subtitle authority"
            )
        for raw in sentence["words"]:
            if not isinstance(raw, dict) or not isinstance(raw.get("text"), str):
                raise VoiceReferenceGenerationError(
                    "Seed Audio returned an invalid subtitle word"
                )
            normalized = "".join(
                character.casefold()
                for character in raw["text"]
                if character.isalnum()
            )
            if not normalized:
                continue
            start_ms = raw.get("start_time")
            end_ms = raw.get("end_time")
            if (
                isinstance(start_ms, bool)
                or isinstance(end_ms, bool)
                or not isinstance(start_ms, (int, float))
                or not isinstance(end_ms, (int, float))
                or start_ms < 0
                or end_ms <= start_ms
            ):
                raise VoiceReferenceGenerationError(
                    "Seed Audio returned an invalid subtitle word interval"
                )
            words.append(
                {
                    "text": raw["text"],
                    "normalized": normalized,
                    "provider_start_seconds": float(start_ms) / 1000.0,
                    "provider_end_seconds": float(end_ms) / 1000.0,
                }
            )
    expected_words = _expected_words(expected_text)
    actual_words = [word["normalized"] for word in words]
    if not expected_words or actual_words != expected_words:
        raise VoiceReferenceGenerationError(
            "Seed Audio subtitle words differ from the exact sample text: "
            f"expected={expected_words}, actual={actual_words}"
        )
    for index, word in enumerate(words):
        if word["provider_end_seconds"] > (
            provider_duration_seconds + VOICE_DURATION_TOLERANCE_SECONDS
        ):
            raise VoiceReferenceGenerationError(
                "Seed Audio word timing exceeds the generated audio duration: "
                f"word={word['text']!r}, end={word['provider_end_seconds']:.3f}s, "
                f"audio={provider_duration_seconds:.3f}s"
            )
        if index and (
            word["provider_start_seconds"] < words[index - 1]["provider_start_seconds"]
            or word["provider_end_seconds"] < words[index - 1]["provider_end_seconds"]
        ):
            raise VoiceReferenceGenerationError(
                "Seed Audio returned non-monotonic word timing"
            )
    gaps = [
        max(
            0.0,
            words[index]["provider_start_seconds"]
            - words[index - 1]["provider_end_seconds"],
        )
        for index in range(1, len(words))
    ]
    max_gap = max(gaps, default=0.0)
    if max_gap > VOICE_MAX_INTERNAL_WORD_GAP_SECONDS:
        raise VoiceReferenceGenerationError(
            "Seed Audio inserted an overlong pause between sample words: "
            f"{max_gap:.3f}s"
        )
    first_word_start = words[0]["provider_start_seconds"]
    last_word_end = words[-1]["provider_end_seconds"]
    trailing_silence = max(0.0, provider_duration_seconds - last_word_end)
    if first_word_start > VOICE_MAX_EDGE_SILENCE_SECONDS:
        raise VoiceReferenceGenerationError(
            "Seed Audio inserted an overlong lead-in before the sample text: "
            f"lead_in={first_word_start:.3f}s"
        )
    if trailing_silence > VOICE_MAX_EDGE_SILENCE_SECONDS:
        raise VoiceReferenceGenerationError(
            "Seed Audio inserted an overlong tail after the sample text: "
            f"trailing_silence={trailing_silence:.3f}s"
        )
    timed_words = [
        {
            "text": word["text"],
            "start_seconds": round(word["provider_start_seconds"], 6),
            "end_seconds": round(word["provider_end_seconds"], 6),
        }
        for word in words
    ]
    return timed_words


def _duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as source:
            return source.getnframes() / float(source.getframerate())
    except (OSError, wave.Error) as exc:
        raise VoiceReferenceGenerationError(
            f"Cannot inspect generated voice WAV {path}: {exc}"
        ) from exc


def _normalize_to_contract(source: Path, target: Path) -> float:
    """Normalize only the PCM transport format; preserve the authored timeline."""

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp.wav")
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-ar",
        str(VOICE_SAMPLE_RATE_HZ),
        "-ac",
        str(VOICE_CHANNELS),
        "-c:a",
        "pcm_s16le",
        str(temporary),
    ]
    try:
        run_media_command(command, context="Voice PCM normalization")
        evidence = _wav_evidence(temporary)
        if evidence is None:
            raise VoiceReferenceGenerationError(
                f"Normalized voice does not meet the PCM transport contract: {target}"
            )
        temporary.replace(target)
        return evidence["duration_seconds"]
    except MediaCommandError as exc:
        raise VoiceReferenceGenerationError(
            f"Could not normalize voice transport: {target}"
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def _provider_prompt(character: dict[str, Any]) -> str:
    """Serialize the exact model-authored voice Prompt without added prose."""

    return json.dumps(
        character["voice_generation_prompt"], ensure_ascii=False, indent=2
    )


def _generate_one(
    repository_root: Path,
    character: dict[str, Any],
    timeout: int,
    *,
    force_regenerate: bool,
) -> tuple[str, dict[str, Any]]:
    entity_id = character["entity_id"]
    folder = repository_root / ASSET_MEDIA_RELATIVE_PATH / "characters" / entity_id
    target = folder / "voice.wav"
    brief_path = folder / "voice.brief.json"
    expected_brief = _brief(character)
    existing_brief = _load_json(brief_path)
    if (
        not force_regenerate
        and _existing_voice_is_current(
            target,
            existing_brief,
            expected_brief=expected_brief,
        )
        and isinstance(existing_brief, dict)
        and isinstance(existing_brief.get("evidence"), dict)
    ):
        return entity_id, {
            "description_en": character["voice_description_en"],
            "reference": {
                "path": target.relative_to(repository_root).as_posix(),
                "uri": existing_brief["evidence"]["uri"],
            },
        }

    provider_prompt = _provider_prompt(character)

    with tempfile.TemporaryDirectory(prefix=f"voice-{entity_id}-") as temporary_dir:
        args = argparse.Namespace(
            prompt=provider_prompt,
            audio_ref=[],
            image_ref=None,
            output_format="wav",
            sample_rate=VOICE_SAMPLE_RATE_HZ,
            speech_rate=character["voice_speech_rate"],
            loudness_rate=None,
            pitch_rate=None,
            enable_subtitle=True,
            extra_json=None,
            save_dir=temporary_dir,
            store=False,
            timeout=timeout,
        )
        try:
            result = seedaudio.command_generate(args)
            artifacts = result.get("artifacts")
            if not isinstance(artifacts, list) or len(artifacts) != 1:
                raise VoiceReferenceGenerationError(
                    "Seed Audio returned no unique artifact"
                )
            source = Path(artifacts[0]["local_path"])
            provider_duration = _duration(source)
            word_timing = _subtitle_word_timing(
                result.get("subtitle"),
                expected_text=character["voice_sample_text_en"],
                provider_duration_seconds=provider_duration,
            )
            staged_target = Path(temporary_dir) / "final" / "voice.wav"
            final_duration = _normalize_to_contract(source, staged_target)
            if abs(final_duration - provider_duration) > VOICE_DURATION_TOLERANCE_SECONDS:
                raise VoiceReferenceGenerationError(
                    "Technical PCM conversion changed the authored duration: "
                    f"provider={provider_duration:.6f}s, final={final_duration:.6f}s"
                )
            stored = provider_runtime.tos_upload_path(
                staged_target, kind="inputs/audio"
            )
            uri = stored["public_url"]
            folder.mkdir(parents=True, exist_ok=True)
            ready = target.with_name(f".{target.name}.ready")
            ready.unlink(missing_ok=True)
            shutil.copyfile(staged_target, ready)
            ready.replace(target)
        except Exception as exc:
            if "ready" in locals():
                ready.unlink(missing_ok=True)
            raise VoiceReferenceGenerationError(
                f"Voice generation failed for {entity_id}: {exc}. Automatic retry "
                "is disabled; obtain fresh human confirmation."
            ) from exc
    final_brief = {
        **expected_brief,
        "evidence": {
            "uri": uri,
            "words": word_timing,
        },
    }
    _atomic_json(brief_path, final_brief)
    return entity_id, {
        "description_en": character["voice_description_en"],
        "reference": {
            "path": target.relative_to(repository_root).as_posix(),
            "uri": uri,
        },
    }


def ensure_voice_references(
    characters: list[dict[str, Any]],
    *,
    repository_root: Path = REPOSITORY_ROOT,
    timeout: int,
    max_workers: int,
    force_regenerate: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Generate/reuse natural-duration voice samples in deterministic plan order."""

    if not characters:
        return {}
    results: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(
        max_workers=min(max_workers, len(characters)),
        thread_name_prefix="voice-reference",
    ) as executor:
        forced = set(force_regenerate or set())
        futures = {
            executor.submit(
                _generate_one,
                repository_root.expanduser().resolve(),
                character,
                timeout,
                force_regenerate=character["entity_id"] in forced,
            ): character["entity_id"]
            for character in characters
        }
        for future in as_completed(futures):
            entity_id = futures[future]
            try:
                _, voice = future.result()
                results[entity_id] = voice
            except Exception as exc:
                failures.append(f"{entity_id}: {exc}")
    if failures:
        raise VoiceReferenceGenerationError(
            "Voice reference generation failed: " + " | ".join(sorted(failures))
        )
    return {
        character["entity_id"]: results[character["entity_id"]]
        for character in characters
    }


def _catalog_reference_file(
    repository_root: Path, raw_path: Any, label: str
) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise VoiceAuthorityError(f"{label} is missing from the asset catalog.")
    portable = PurePosixPath(raw_path)
    try:
        resolved = repository_root.joinpath(*portable.parts).resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise VoiceAuthorityError(f"{label} cannot be inspected: {raw_path}") from exc
    if not resolved.is_file():
        raise VoiceAuthorityError(f"{label} must identify a regular file: {raw_path}")
    return resolved


def _pcm_data_size(path: Path) -> int:
    """Return PCM payload bytes, including streamed WAVs with 0xffffffff sizes."""

    file_size = path.stat().st_size
    with path.open("rb") as source:
        header = source.read(12)
        if (
            len(header) != 12
            or header[:4] not in (b"RIFF", b"RF64")
            or header[8:] != b"WAVE"
        ):
            raise VoiceAuthorityError(f"Not a RIFF/RF64 WAV file: {path}")
        while source.tell() + 8 <= file_size:
            chunk_id = source.read(4)
            size_bytes = source.read(4)
            if len(chunk_id) != 4 or len(size_bytes) != 4:
                break
            declared_size = struct.unpack("<I", size_bytes)[0]
            payload_offset = source.tell()
            if chunk_id == b"data":
                available = file_size - payload_offset
                return (
                    available
                    if declared_size == 0xFFFFFFFF
                    else min(declared_size, available)
                )
            if declared_size == 0xFFFFFFFF:
                raise VoiceAuthorityError(
                    f"Indeterminate non-audio WAV chunk in {path}"
                )
            source.seek(declared_size + (declared_size % 2), 1)
    raise VoiceAuthorityError(f"WAV evidence has no audio data chunk: {path}")


def _validated_wav_evidence(path: Path) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as source:
            channels = source.getnchannels()
            sample_rate = source.getframerate()
            sample_width = source.getsampwidth()
            compression = source.getcomptype()
    except (OSError, EOFError, wave.Error) as exc:
        raise VoiceAuthorityError(f"Invalid WAV evidence at {path}: {exc}") from exc
    if compression != "NONE":
        raise VoiceAuthorityError(
            f"Voice evidence must be uncompressed PCM WAV: {path}"
        )
    codec = {
        1: "pcm_u8",
        2: "pcm_s16le",
        3: "pcm_s24le",
        4: "pcm_s32le",
    }.get(sample_width)
    block_align = channels * sample_width
    pcm_data_size = _pcm_data_size(path)
    if codec is None or sample_rate <= 0 or block_align <= 0 or pcm_data_size <= 0:
        raise VoiceAuthorityError(f"Unsupported or empty WAV evidence at {path}")
    if pcm_data_size % block_align:
        raise VoiceAuthorityError(
            f"PCM payload is not aligned to complete sample frames: {path}"
        )
    sample_frames = pcm_data_size // block_align
    return {
        "duration_seconds": round(sample_frames / float(sample_rate), 6),
        "byte_size": path.stat().st_size,
        "audio_stream": {
            "codec": codec,
            "sample_rate_hz": sample_rate,
            "channels": channels,
        },
    }


def _validate_dynamic_timing(
    *, asset_id: str, sample_text: str, evidence: Any, audio_duration: float
) -> None:
    if not isinstance(evidence, dict) or set(evidence) != {"uri", "words"}:
        raise VoiceAuthorityError(
            f"character {asset_id} lacks compact dynamic-duration evidence"
        )
    words = evidence.get("words")
    if not isinstance(words, list) or not words:
        raise VoiceAuthorityError(
            f"character {asset_id} lacks exact sample word timing"
        )
    actual_words: list[str] = []
    previous_end = 0.0
    previous_start = 0.0
    max_gap = 0.0
    first_start = 0.0
    last_end = 0.0
    for index, word in enumerate(words):
        if (
            not isinstance(word, dict)
            or set(word) != {"text", "start_seconds", "end_seconds"}
            or not isinstance(word.get("text"), str)
        ):
            raise VoiceAuthorityError(
                f"character {asset_id} has invalid sample word timing"
            )
        start = word.get("start_seconds")
        end = word.get("end_seconds")
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, (int, float))
            or not isinstance(end, (int, float))
            or start < 0
            or end <= start
            or end > audio_duration + VOICE_DURATION_TOLERANCE_SECONDS
            or (index and start < previous_start)
            or (index and end < previous_end)
        ):
            raise VoiceAuthorityError(
                f"character {asset_id} has word timing outside its voice WAV"
            )
        if index:
            max_gap = max(max_gap, float(start) - previous_end)
        else:
            first_start = float(start)
        previous_end = float(end)
        previous_start = float(start)
        last_end = float(end)
        actual_words.append(
            "".join(
                character.casefold()
                for character in word["text"]
                if character.isalnum()
            )
        )
    if actual_words != _expected_words(sample_text):
        raise VoiceAuthorityError(
            f"character {asset_id} spoken words differ from its sample text"
        )
    if (
        first_start > VOICE_MAX_EDGE_SILENCE_SECONDS
        or audio_duration - last_end > VOICE_MAX_EDGE_SILENCE_SECONDS
        or max_gap > VOICE_MAX_INTERNAL_WORD_GAP_SECONDS
    ):
        raise VoiceAuthorityError(
            f"character {asset_id} has an anomalous sample-text pause"
        )


def validate_voice_authority(
    task_root: Path, *, repository_root: Path = REPOSITORY_ROOT
) -> dict[str, Any]:
    task_root = task_root.expanduser().resolve()
    repository_root = repository_root.expanduser().resolve()
    try:
        catalog = load_asset_catalog(task_root, repository_root=repository_root)
    except StoryVideoError as exc:
        raise VoiceAuthorityError(str(exc)) from exc

    validated: list[dict[str, Any]] = []
    for asset_id, asset in sorted(catalog["assets"].items()):
        if asset.get("type") != "character" or "voice" not in asset:
            continue
        reference = asset["voice"]["reference"]
        audio_path = _catalog_reference_file(
            repository_root,
            reference.get("path"),
            f"character {asset_id} voice.reference.path",
        )
        evidence = _validated_wav_evidence(audio_path)
        stream = evidence["audio_stream"]
        if (
            stream["codec"] != "pcm_s16le"
            or stream["sample_rate_hz"] != VOICE_SAMPLE_RATE_HZ
            or stream["channels"] != VOICE_CHANNELS
        ):
            raise VoiceAuthorityError(
                f"character {asset_id} voice must be pcm_s16le, "
                f"{VOICE_SAMPLE_RATE_HZ} Hz, {VOICE_CHANNELS} channels"
            )
        brief_path = audio_path.parent / "voice.brief.json"
        brief = _load_json(brief_path)
        if (
            not isinstance(brief, dict)
            or brief.get("contract") != VOICE_BRIEF_CONTRACT
            or brief.get("entity_id") != asset_id
            or not isinstance(brief.get("sample_text_en"), str)
            or not brief["sample_text_en"].strip()
            or brief.get("output", {}).get("duration_policy")
            != VOICE_DURATION_POLICY
            or "duration_seconds" in brief.get("output", {})
            or not isinstance(brief.get("evidence"), dict)
            or brief["evidence"].get("uri") != reference.get("uri")
        ):
            raise VoiceAuthorityError(
                f"character {asset_id} voice sample brief is stale or incomplete"
            )
        _validate_dynamic_timing(
            asset_id=asset_id,
            sample_text=brief["sample_text_en"],
            evidence=brief["evidence"],
            audio_duration=evidence["duration_seconds"],
        )
        validated.append(
            {
                "asset_id": asset_id,
                "name": asset_id,
                "reference_path": reference["path"],
                "sample_text_en": brief["sample_text_en"],
                "evidence": evidence,
            }
        )

    return {
        "result": "PASS",
        "catalog_path": str(
            (repository_root / ASSET_CATALOG_RELATIVE_PATH).resolve()
        ),
        "speaker_count": len(validated),
        "remote_service_calls": 0,
        "speakers": validated,
    }
