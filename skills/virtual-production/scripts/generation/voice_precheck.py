"""Run and persist the mandatory post-generation voice-identity gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.segment.common import (
    SCRIPT_DIR_RELATIVE,
    sha256_file,
)
from narrated_fable_drama.core.arabic_pronunciation import (
    ACCENT_PROFILE_ID,
    GRAMMATICAL_GENDER_POLICY,
    PRONUNCIATION_CONTRACT,
    TTS_MODEL_ID,
)
from narrated_fable_drama.core.paths import ProjectPaths
from narrated_fable_drama.core.project_domain import SPEECH_AUDIO_SOURCE

from .common import (
    DEPARTMENT_DIRNAME,
    GENERATION_DIRNAME,
    PENDING_DIRNAME,
    SegmentGenerationError,
    read_json,
    write_json,
)

REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root
VOICE_GATE_HELPER = (
    REPOSITORY_ROOT
    / "skills"
    / "video-review"
    / "scripts"
    / "prepare_voice_identity_gate.py"
)


def _segment_directory(task_dir: Path, segment_id: str) -> Path:
    return (
        task_dir
        / PENDING_DIRNAME
        / DEPARTMENT_DIRNAME
        / GENERATION_DIRNAME
        / segment_id
    )


def _valid_current_audio_build(dubbing: Any) -> bool:
    if not isinstance(dubbing, dict):
        return False
    cleaned_gate = dubbing.get("seedance_clean_background_speech_gate")
    audio_edit = dubbing.get("seedance_audio_edit")
    return (
        dubbing.get("contract")
        == "seedance-original-audio-dialogue-replacement/v2"
        and dubbing.get("language_code_sent") is False
        and dubbing.get("tts_model_id") == TTS_MODEL_ID
        and dubbing.get("accent_profile_id") == ACCENT_PROFILE_ID
        and dubbing.get("grammatical_gender_policy")
        == GRAMMATICAL_GENDER_POLICY
        and dubbing.get("pronunciation_contract")
        == PRONUNCIATION_CONTRACT
        and dubbing.get("speech_audio_source") == SPEECH_AUDIO_SOURCE
        and dubbing.get("sound_effects_audio_source")
        == "seedance_native"
        and dubbing.get("native_audio_full_duration") is True
        and dubbing.get("elevenlabs_usage_scope") == "arabic_dialogue_only"
        and dubbing.get("elevenlabs_non_dialogue_request_count") == 0
        and dubbing.get("dialogue_gap_fill_source")
        in {
            "digital_silence",
            "not_required",
        }
        and dubbing.get("seedance_speech_forbidden") is True
        and dubbing.get("seedance_speech_in_delivery") is False
        and dubbing.get("seedance_generate_audio") is True
        and dubbing.get("seedance_audio_in_delivery") is True
        and dubbing.get("seedance_background_audio_retained") is True
        and isinstance(cleaned_gate, dict)
        and cleaned_gate.get("status") == "PASS"
        and isinstance(audio_edit, dict)
        and audio_edit.get("status") in {"APPLIED", "NOT_REQUIRED"}
    )


def prepare_voice_identity_precheck(
    task_dir: Path,
    segment_id: str,
) -> dict[str, Any]:
    """Measure one generated Segment and attach technical facts to its record."""

    task_dir = task_dir.expanduser().resolve()
    directory = _segment_directory(task_dir, segment_id)
    video_path = directory / "video.mp4"
    record_path = directory / "production-record.json"
    if not video_path.is_file() or not record_path.is_file():
        raise SegmentGenerationError(
            f"{segment_id} lacks media required for voice-identity review."
        )
    record = read_json(record_path)
    current_prompt_path = (
        task_dir / SCRIPT_DIR_RELATIVE / f"{segment_id}.md"
    )
    dubbing = record.get("dubbing")
    if (
        record.get("contract") != "generated-segment-production-record"
        or record.get("segment_id") != segment_id
        or record.get("status") != "GENERATED"
        or not current_prompt_path.is_file()
        or record.get("segment_prompt_sha256")
        != sha256_file(current_prompt_path)
        or not _valid_current_audio_build(dubbing)
    ):
        raise SegmentGenerationError(
            f"{segment_id} has a stale Prompt hash or no valid Seedance-native "
            "plus ElevenLabs-dialogue audio build."
        )
    if not VOICE_GATE_HELPER.is_file():
        raise SegmentGenerationError(
            f"Voice-identity helper is missing: {VOICE_GATE_HELPER}"
        )
    command = [
        sys.executable,
        str(VOICE_GATE_HELPER),
        "--task-dir",
        str(task_dir),
        "--segment",
        segment_id,
        "--video",
        str(video_path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        gate = json.loads(completed.stdout)
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        detail = (
            completed.stderr.strip()
            if "completed" in locals() and completed.stderr
            else str(exc)
        )
        raise SegmentGenerationError(
            f"{segment_id} voice-identity gate could not run: {detail}"
        ) from exc
    if (
        not isinstance(gate, dict)
        or gate.get("contract") != "video-review-voice-identity-gate/v2"
        or gate.get("segment_id") != segment_id
        or gate.get("language") != "Arabic"
        or gate.get("language_code") != "ar"
        or gate.get("status") not in {"PASS", "FAIL", "NOT_APPLICABLE"}
        or not isinstance(gate.get("blocks_acceptance"), bool)
    ):
        raise SegmentGenerationError(
            f"{segment_id} voice-identity helper returned an invalid result."
        )
    record["voice_identity_gate"] = gate
    write_json(record_path, record)
    return gate


def recorded_voice_gate_allows_downstream(
    task_dir: Path,
    segment_id: str,
) -> bool:
    """Require Seedance-native sound, ElevenLabs dialogue, and voice identity."""

    record_path = _segment_directory(task_dir, segment_id) / "production-record.json"
    if not record_path.is_file():
        return False
    record = read_json(record_path)
    current_prompt_path = (
        task_dir / SCRIPT_DIR_RELATIVE / f"{segment_id}.md"
    )
    current_prompt_matches = (
        current_prompt_path.is_file()
        and record.get("segment_prompt_sha256")
        == sha256_file(current_prompt_path)
    )
    dubbing = record.get("dubbing")
    current_audio_build = _valid_current_audio_build(dubbing)
    if not (current_audio_build and current_prompt_matches):
        return False
    gate = record.get("voice_identity_gate")
    return (
        isinstance(gate, dict)
        and gate.get("status") in {"PASS", "NOT_APPLICABLE"}
        and gate.get("blocks_acceptance") is False
    )
