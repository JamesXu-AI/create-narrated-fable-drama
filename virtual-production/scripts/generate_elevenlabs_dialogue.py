#!/usr/bin/env python3
"""Generate auditable ElevenLabs dialogue clips from local Segment cue authority."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PLAN_RELATIVE = Path(".pending/virtual-production/seedance-segment-plans")
DEFAULT_OUTPUT_RELATIVE = Path(".pending/elevenlabs-tts")
CONFIG_FILENAME = "elevenlabs-config.json"
PROMPT_FILENAME = "dialogue-prompts.md"
MANIFEST_FILENAME = "tts-manifest.json"
API_ROOT = "https://api.elevenlabs.io"


class ElevenLabsDialogueError(RuntimeError):
    """Raised when dialogue authority, API output, or audio QA is invalid."""


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ElevenLabsDialogueError(f"Cannot read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise ElevenLabsDialogueError(f"{label} must be a JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ElevenLabsDialogueError(f"{label} must be a non-empty string")
    return value.strip()


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ElevenLabsDialogueError(f"{label} must be numeric")
    return float(value)


def voice_brief(entity_id: str) -> dict[str, Any]:
    return read_json(
        REPOSITORY_ROOT / "assets/characters" / entity_id / "voice.brief.json",
        label=f"{entity_id} voice brief",
    )


def load_config(path: Path) -> dict[str, Any]:
    config = read_json(path, label="ElevenLabs dialogue config")
    if config.get("contract") != "elevenlabs-dialogue-config-v1":
        raise ElevenLabsDialogueError("Unsupported ElevenLabs dialogue config")
    nonempty_string(config.get("model_id"), "model_id")
    nonempty_string(config.get("output_format"), "output_format")
    settings = config.get("default_voice_settings")
    voices = config.get("voices")
    directions = config.get("line_directions")
    output = config.get("wav_output")
    if (
        not isinstance(settings, dict)
        or not isinstance(voices, dict)
        or not isinstance(directions, dict)
        or not isinstance(output, dict)
    ):
        raise ElevenLabsDialogueError("ElevenLabs dialogue config is incomplete")
    for key in ("stability", "similarity_boost", "style", "speed"):
        value = number(settings.get(key), f"default_voice_settings.{key}")
        if not 0 <= value <= 1 and key != "speed":
            raise ElevenLabsDialogueError(f"{key} must be within 0..1")
        if key == "speed" and not 0.7 <= value <= 1.2:
            raise ElevenLabsDialogueError("speed must be within 0.7..1.2")
    if not isinstance(settings.get("use_speaker_boost"), bool):
        raise ElevenLabsDialogueError("use_speaker_boost must be boolean")
    if (
        output.get("sample_rate_hz") != 48000
        or output.get("channels") != 2
        or output.get("codec") != "pcm_s16le"
    ):
        raise ElevenLabsDialogueError(
            "ElevenLabs delivery WAV must be 48 kHz stereo pcm_s16le"
        )
    return config


def collect_dialogue_cues(task_dir: Path) -> list[dict[str, Any]]:
    plan_root = task_dir / PLAN_RELATIVE
    paths = sorted(plan_root.glob("segment-*.json"))
    if not paths:
        raise ElevenLabsDialogueError(f"No local Segment plans found under {plan_root}")
    cues: list[dict[str, Any]] = []
    seen_line_ids: set[str] = set()
    for plan_path in paths:
        plan = read_json(plan_path, label="Segment plan")
        segment_id = nonempty_string(plan.get("segment_id"), "segment_id")
        if segment_id != plan_path.stem:
            raise ElevenLabsDialogueError(
                f"{plan_path.name} Segment identity is inconsistent"
            )
        for cue in plan.get("dialogue_cues", []):
            if not isinstance(cue, dict):
                raise ElevenLabsDialogueError(
                    f"{segment_id} contains a malformed dialogue cue"
                )
            line_id = nonempty_string(cue.get("line_id"), "line_id")
            if line_id in seen_line_ids:
                raise ElevenLabsDialogueError(f"Duplicate dialogue line: {line_id}")
            seen_line_ids.add(line_id)
            start = number(cue.get("start_seconds"), f"{line_id} start_seconds")
            end = number(cue.get("end_seconds"), f"{line_id} end_seconds")
            if start < 0 or end <= start:
                raise ElevenLabsDialogueError(f"{line_id} has an invalid cue window")
            cues.append(
                {
                    "segment_id": segment_id,
                    "line_id": line_id,
                    "speaker_entity_id": nonempty_string(
                        cue.get("speaker_entity_id"),
                        f"{line_id} speaker_entity_id",
                    ),
                    "speaker_name": nonempty_string(
                        cue.get("speaker_name"), f"{line_id} speaker_name"
                    ),
                    "exact_text": nonempty_string(
                        cue.get("exact_text"), f"{line_id} exact_text"
                    ),
                    "shot_number": cue.get("shot_number"),
                    "start_seconds": start,
                    "end_seconds": end,
                    "window_seconds": round(end - start, 3),
                    "source_plan": plan_path.relative_to(task_dir).as_posix(),
                    "source_plan_sha256": sha256_file(plan_path),
                }
            )
    return cues


def deterministic_seed(
    task_id: str, cue: dict[str, Any], submitted_text: str
) -> int:
    material = (
        f"{task_id}\0{cue['segment_id']}\0{cue['line_id']}\0"
        f"{cue['speaker_entity_id']}\0{submitted_text}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:4], "big")


def merged_voice_settings(
    config: dict[str, Any], voice: dict[str, Any], line_id: str
) -> dict[str, Any]:
    settings = dict(config["default_voice_settings"])
    if isinstance(voice.get("voice_settings"), dict):
        settings.update(voice["voice_settings"])
    line_overrides = config.get("line_voice_settings", {})
    if isinstance(line_overrides, dict) and isinstance(
        line_overrides.get(line_id), dict
    ):
        settings.update(line_overrides[line_id])
    return settings


def build_prompts(
    *,
    task_dir: Path,
    config: dict[str, Any],
    cues: list[dict[str, Any]],
    text_overrides: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    task = read_json(task_dir / "task.json", label="task.json")
    task_id = nonempty_string(task.get("task_id"), "task_id")
    if text_overrides is None:
        language_code = "en"
        translations: dict[str, Any] = {}
    else:
        if (
            text_overrides.get("contract")
            != "elevenlabs-dialogue-text-overrides-v1"
        ):
            raise ElevenLabsDialogueError(
                "Unsupported ElevenLabs dialogue text overrides"
            )
        language_code = nonempty_string(
            text_overrides.get("language_code"), "translation language_code"
        )
        translations = text_overrides.get("translations")
        if not isinstance(translations, dict):
            raise ElevenLabsDialogueError("translations must be an object")
        if set(translations) != {cue["line_id"] for cue in cues}:
            raise ElevenLabsDialogueError(
                "translations must exactly cover current Segment dialogue cues"
            )
    entries: list[dict[str, Any]] = []
    for cue in cues:
        entity_id = cue["speaker_entity_id"]
        voice = config["voices"].get(entity_id)
        if not isinstance(voice, dict):
            raise ElevenLabsDialogueError(
                f"No ElevenLabs voice mapping for {entity_id}"
            )
        direction = config["line_directions"].get(cue["line_id"])
        if not isinstance(direction, str) or not direction.strip():
            raise ElevenLabsDialogueError(
                f"No performance direction for {cue['line_id']}"
            )
        brief = voice_brief(entity_id)
        submitted_text = (
            nonempty_string(
                translations.get(cue["line_id"]),
                f"{cue['line_id']} translated text",
            )
            if text_overrides is not None
            else cue["exact_text"]
        )
        request_body = {
            "text": submitted_text,
            "model_id": config["model_id"],
            "voice_settings": merged_voice_settings(
                config, voice, cue["line_id"]
            ),
            "seed": deterministic_seed(task_id, cue, submitted_text),
            "apply_text_normalization": "auto",
        }
        entries.append(
            {
                **cue,
                "source_exact_text": cue["exact_text"],
                "submitted_text": submitted_text,
                "language_code": language_code,
                "voice_id": nonempty_string(
                    voice.get("voice_id"), f"{entity_id} voice_id"
                ),
                "voice_name": nonempty_string(
                    voice.get("voice_name"), f"{entity_id} voice_name"
                ),
                "voice_description_en": nonempty_string(
                    brief.get("voice_description_en"),
                    f"{entity_id} voice_description_en",
                ),
                "performance_direction_en": direction.strip(),
                "submitted_text_policy": (
                    "exact dialogue only; performance direction is audit metadata "
                    "and is not inserted into spoken text"
                ),
                "request_body": request_body,
                "request_body_sha256": sha256_bytes(
                    json.dumps(
                        request_body,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ),
            }
        )
    if set(config["line_directions"]) != {
        entry["line_id"] for entry in entries
    }:
        raise ElevenLabsDialogueError(
            "line_directions must exactly cover current Segment dialogue cues"
        )
    return entries


def render_prompt_markdown(
    *,
    config_path: Path,
    config: dict[str, Any],
    entries: list[dict[str, Any]],
    text_overrides_path: Path | None,
) -> str:
    lines = [
        "# ElevenLabs Dialogue Prompts",
        "",
        "This file is the auditable prompt authority for external dialogue TTS.",
        "Only each `Submitted text` value is sent as speech text. Performance direction",
        "remains separate so ElevenLabs never speaks the direction itself.",
        "",
        f"- Model: `{config['model_id']}`",
        f"- Provider output: `{config['output_format']}`",
        "- Delivery output: `48 kHz stereo pcm_s16le WAV`",
        f"- Config: `{config_path.as_posix()}`",
        f"- Target language: `{entries[0]['language_code']}`",
        (
            f"- Translation authority: `{text_overrides_path.as_posix()}`"
            if text_overrides_path is not None
            else "- Translation authority: `none; source dialogue is submitted`"
        ),
        "",
    ]
    for entry in entries:
        settings = entry["request_body"]["voice_settings"]
        lines.extend(
            [
                (
                    f"## {entry['line_id']} — {entry['segment_id']} — "
                    f"{entry['speaker_name']}"
                ),
                "",
                f"- Voice: `{entry['voice_name']}` (`{entry['voice_id']}`)",
                (
                    "- Cue window: "
                    f"`{entry['start_seconds']:.3f}s–{entry['end_seconds']:.3f}s` "
                    f"({entry['window_seconds']:.3f}s)"
                ),
                (
                    "- Voice settings: "
                    f"`stability={settings['stability']}, "
                    f"similarity_boost={settings['similarity_boost']}, "
                    f"style={settings['style']}, "
                    f"speaker_boost={settings['use_speaker_boost']}, "
                    f"speed={settings['speed']}`"
                ),
                f"- Seed: `{entry['request_body']['seed']}`",
                "",
                "Voice identity:",
                "",
                entry["voice_description_en"],
                "",
                "Performance direction:",
                "",
                entry["performance_direction_en"],
                "",
                "Source dialogue:",
                "",
                entry["source_exact_text"],
                "",
                "Submitted text:",
                "",
                entry["submitted_text"],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def elevenlabs_request(
    *, voice_id: str, output_format: str, body: dict[str, Any], api_key: str
) -> tuple[dict[str, Any], str | None]:
    query = urlencode({"output_format": output_format})
    endpoint = (
        f"{API_ROOT}/v1/text-to-speech/{voice_id}/with-timestamps?{query}"
    )
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "xi-api-key": api_key,
        },
    )
    try:
        with urlopen(request, timeout=180) as response:
            response_body = response.read()
            request_id = (
                response.headers.get("request-id")
                or response.headers.get("x-request-id")
            )
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ElevenLabsDialogueError(
            f"ElevenLabs HTTP {exc.code}: {detail[:1000]}"
        ) from exc
    except URLError as exc:
        raise ElevenLabsDialogueError(f"ElevenLabs request failed: {exc}") from exc
    try:
        result = json.loads(response_body)
    except Exception as exc:
        raise ElevenLabsDialogueError(
            "ElevenLabs returned non-JSON timing output"
        ) from exc
    if not isinstance(result, dict):
        raise ElevenLabsDialogueError("ElevenLabs response must be an object")
    return result, request_id


def ffprobe_duration(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(completed.stdout.strip())


def spoken_bounds(
    alignment: dict[str, Any], *, exact_text: str
) -> tuple[float, float]:
    characters = alignment.get("characters")
    starts = alignment.get("character_start_times_seconds")
    ends = alignment.get("character_end_times_seconds")
    if (
        not isinstance(characters, list)
        or not isinstance(starts, list)
        or not isinstance(ends, list)
        or "".join(characters) != exact_text
        or not len(characters) == len(starts) == len(ends)
    ):
        raise ElevenLabsDialogueError("Provider character alignment is malformed")
    spoken_indexes = [
        index
        for index, character in enumerate(characters)
        if isinstance(character, str) and not character.isspace()
    ]
    if not spoken_indexes:
        raise ElevenLabsDialogueError("Provider alignment has no spoken characters")
    start = number(starts[spoken_indexes[0]], "alignment spoken start")
    end = number(ends[spoken_indexes[-1]], "alignment spoken end")
    if start < 0 or end <= start:
        raise ElevenLabsDialogueError("Provider spoken bounds are invalid")
    return start, end


def convert_to_delivery_wav(
    source: Path,
    destination: Path,
    *,
    spoken_start: float,
    spoken_end: float,
) -> None:
    trim_start = max(0.0, spoken_start - 0.04)
    trim_end = spoken_end + 0.04
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-ss",
            f"{trim_start:.6f}",
            "-t",
            f"{trim_end - trim_start:.6f}",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ],
        check=True,
    )


def generate_entry(
    *,
    output_dir: Path,
    config: dict[str, Any],
    entry: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    cue_dir = output_dir / "cues" / entry["line_id"]
    cue_dir.mkdir(parents=True, exist_ok=True)
    request_path = cue_dir / "request.json"
    response_path = cue_dir / "response.json"
    source_path = cue_dir / "source.mp3"
    wav_path = cue_dir / "dialogue.wav"
    write_json(
        request_path,
        {
            "provider": "elevenlabs",
            "endpoint": (
                f"/v1/text-to-speech/{entry['voice_id']}/with-timestamps"
            ),
            "output_format": config["output_format"],
            "voice_id": entry["voice_id"],
            "voice_name": entry["voice_name"],
            "performance_direction_en": entry["performance_direction_en"],
            "body": entry["request_body"],
        },
    )

    result, request_id = elevenlabs_request(
        voice_id=entry["voice_id"],
        output_format=config["output_format"],
        body=entry["request_body"],
        api_key=api_key,
    )
    audio_base64 = result.get("audio_base64")
    alignment = result.get("alignment")
    normalized_alignment = result.get("normalized_alignment")
    if (
        not isinstance(audio_base64, str)
        or not isinstance(alignment, dict)
        or not isinstance(normalized_alignment, dict)
    ):
        raise ElevenLabsDialogueError(
            f"{entry['line_id']} response lacks audio or timing alignment"
        )
    aligned_text = "".join(alignment.get("characters", []))
    if aligned_text != entry["submitted_text"]:
        raise ElevenLabsDialogueError(
            f"{entry['line_id']} provider alignment differs from exact dialogue"
        )
    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except Exception as exc:
        raise ElevenLabsDialogueError(
            f"{entry['line_id']} has invalid audio_base64"
        ) from exc
    if len(audio_bytes) < 1024:
        raise ElevenLabsDialogueError(
            f"{entry['line_id']} generated audio is unexpectedly small"
        )
    source_path.write_bytes(audio_bytes)
    spoken_start, spoken_end = spoken_bounds(
        alignment, exact_text=entry["submitted_text"]
    )
    convert_to_delivery_wav(
        source_path,
        wav_path,
        spoken_start=spoken_start,
        spoken_end=spoken_end,
    )
    duration = ffprobe_duration(wav_path)
    fit_status = (
        "PASS"
        if duration <= entry["window_seconds"]
        else "RETIME_REQUIRED"
    )
    response_metadata = {
        "provider": "elevenlabs",
        "request_id": request_id,
        "line_id": entry["line_id"],
        "alignment": alignment,
        "normalized_alignment": normalized_alignment,
        "aligned_text_exact": True,
        "alignment_spoken_start_seconds": round(spoken_start, 6),
        "alignment_spoken_end_seconds": round(spoken_end, 6),
        "alignment_trim_handle_seconds": 0.04,
        "source_audio_path": source_path.relative_to(output_dir).as_posix(),
        "source_audio_sha256": sha256_file(source_path),
        "delivery_wav_path": wav_path.relative_to(output_dir).as_posix(),
        "delivery_wav_sha256": sha256_file(wav_path),
        "delivery_duration_seconds": round(duration, 6),
        "cue_window_seconds": entry["window_seconds"],
        "cue_window_fit": fit_status,
    }
    write_json(response_path, response_metadata)
    return response_metadata


def reuse_entry(
    *,
    output_dir: Path,
    config: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, Any] | None:
    cue_dir = output_dir / "cues" / entry["line_id"]
    request_path = cue_dir / "request.json"
    response_path = cue_dir / "response.json"
    source_path = cue_dir / "source.mp3"
    wav_path = cue_dir / "dialogue.wav"
    if not all(
        path.is_file()
        for path in (request_path, response_path, source_path, wav_path)
    ):
        return None
    request = read_json(request_path, label=f"{entry['line_id']} request")
    if (
        request.get("voice_id") != entry["voice_id"]
        or request.get("output_format") != config["output_format"]
        or request.get("body") != entry["request_body"]
    ):
        return None
    response = read_json(response_path, label=f"{entry['line_id']} response")
    alignment = response.get("alignment")
    if not isinstance(alignment, dict):
        return None
    spoken_start, spoken_end = spoken_bounds(
        alignment, exact_text=entry["submitted_text"]
    )
    convert_to_delivery_wav(
        source_path,
        wav_path,
        spoken_start=spoken_start,
        spoken_end=spoken_end,
    )
    duration = ffprobe_duration(wav_path)
    response.update(
        {
            "source_audio_sha256": sha256_file(source_path),
            "delivery_wav_sha256": sha256_file(wav_path),
            "delivery_duration_seconds": round(duration, 6),
            "cue_window_seconds": entry["window_seconds"],
            "cue_window_fit": (
                "PASS"
                if duration <= entry["window_seconds"]
                else "RETIME_REQUIRED"
            ),
            "alignment_spoken_start_seconds": round(spoken_start, 6),
            "alignment_spoken_end_seconds": round(spoken_end, 6),
            "alignment_trim_handle_seconds": 0.04,
        }
    )
    write_json(response_path, response)
    return response


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--text-overrides",
        type=Path,
        help="Exact translated/substitute dialogue keyed by current line ID.",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Call ElevenLabs and create audio; otherwise write prompts only.",
    )
    parser.add_argument(
        "--line-ids",
        nargs="+",
        help="Generate only these lines; reuse matching existing results for others.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate selected lines even when an exact matching result exists.",
    )
    args = parser.parse_args()
    try:
        task_dir = args.task_dir.expanduser().resolve(strict=True)
        output_dir = (
            args.output_dir.expanduser().resolve()
            if args.output_dir
            else task_dir / DEFAULT_OUTPUT_RELATIVE
        )
        config_path = (
            args.config.expanduser().resolve(strict=True)
            if args.config
            else (output_dir / CONFIG_FILENAME).resolve(strict=True)
        )
        config = load_config(config_path)
        cues = collect_dialogue_cues(task_dir)
        text_overrides_path = (
            args.text_overrides.expanduser().resolve(strict=True)
            if args.text_overrides
            else None
        )
        text_overrides = (
            read_json(
                text_overrides_path,
                label="ElevenLabs dialogue text overrides",
            )
            if text_overrides_path is not None
            else None
        )
        entries = build_prompts(
            task_dir=task_dir,
            config=config,
            cues=cues,
            text_overrides=text_overrides,
        )
        selected_line_ids = set(
            args.line_ids or [entry["line_id"] for entry in entries]
        )
        unknown_line_ids = selected_line_ids - {
            entry["line_id"] for entry in entries
        }
        if unknown_line_ids:
            raise ElevenLabsDialogueError(
                f"Unknown --line-ids: {sorted(unknown_line_ids)}"
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = output_dir / PROMPT_FILENAME
        prompt_path.write_text(
            render_prompt_markdown(
                config_path=config_path,
                config=config,
                entries=entries,
                text_overrides_path=text_overrides_path,
            ),
            encoding="utf-8",
        )
        results: list[dict[str, Any]] = []
        if args.generate:
            api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
            if not api_key:
                raise ElevenLabsDialogueError(
                    "ELEVENLABS_API_KEY is required for --generate"
                )
            for entry in entries:
                existing = reuse_entry(
                    output_dir=output_dir,
                    config=config,
                    entry=entry,
                )
                should_generate = (
                    entry["line_id"] in selected_line_ids
                    and (args.force or existing is None)
                )
                if not should_generate:
                    if existing is not None:
                        print(
                            f"REUSE {entry['line_id']} {entry['segment_id']} "
                            f"{entry['speaker_name']}",
                            flush=True,
                        )
                        results.append(existing)
                    continue
                print(
                    f"GENERATE {entry['line_id']} {entry['segment_id']} "
                    f"{entry['speaker_name']}",
                    flush=True,
                )
                results.append(
                    generate_entry(
                        output_dir=output_dir,
                        config=config,
                        entry=entry,
                        api_key=api_key,
                    )
                )
        manifest = {
            "contract": "elevenlabs-dialogue-generation-v1",
            "status": "GENERATED" if args.generate else "PROMPTS_READY",
            "provider": "elevenlabs",
            "model_id": config["model_id"],
            "output_format": config["output_format"],
            "language_code": entries[0]["language_code"],
            "text_overrides_path": (
                text_overrides_path.relative_to(task_dir).as_posix()
                if text_overrides_path is not None
                else "none"
            ),
            "text_overrides_sha256": (
                sha256_file(text_overrides_path)
                if text_overrides_path is not None
                else "none"
            ),
            "prompt_path": prompt_path.relative_to(task_dir).as_posix(),
            "prompt_sha256": sha256_file(prompt_path),
            "cue_count": len(entries),
            "entries": [
                {
                    key: entry[key]
                    for key in (
                        "segment_id",
                        "line_id",
                        "speaker_entity_id",
                        "speaker_name",
                        "source_exact_text",
                        "submitted_text",
                        "language_code",
                        "voice_id",
                        "voice_name",
                        "performance_direction_en",
                        "start_seconds",
                        "end_seconds",
                        "window_seconds",
                        "source_plan",
                        "source_plan_sha256",
                        "request_body_sha256",
                    )
                }
                for entry in entries
            ],
            "results": results,
            "retime_required_line_ids": [
                result["line_id"]
                for result in results
                if result["cue_window_fit"] != "PASS"
            ],
        }
        manifest_path = output_dir / MANIFEST_FILENAME
        write_json(manifest_path, manifest)
        print(
            json.dumps(
                {
                    "status": manifest["status"],
                    "cue_count": len(entries),
                    "prompt_path": str(prompt_path),
                    "manifest_path": str(manifest_path),
                    "retime_required_line_ids": manifest[
                        "retime_required_line_ids"
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {"status": "FAIL", "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
