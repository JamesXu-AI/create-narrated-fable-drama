"""Run and persist the mandatory post-generation voice-identity gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from narrated_fable_drama.core.paths import ProjectPaths

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
        or gate.get("contract") != "video-review-voice-identity-gate/v1"
        or gate.get("segment_id") != segment_id
        or gate.get("status") not in {"PASS", "FAIL", "NOT_APPLICABLE"}
        or not isinstance(gate.get("blocks_acceptance"), bool)
    ):
        raise SegmentGenerationError(
            f"{segment_id} voice-identity helper returned an invalid result."
        )
    record = read_json(record_path)
    if (
        record.get("contract") != "generated-segment-production-record"
        or record.get("segment_id") != segment_id
        or record.get("status") != "GENERATED"
    ):
        raise SegmentGenerationError(
            f"{segment_id} production record is invalid for voice review."
        )
    record["voice_identity_gate"] = gate
    write_json(record_path, record)
    return gate


def recorded_voice_gate_allows_downstream(
    task_dir: Path,
    segment_id: str,
) -> bool:
    """Keep legacy records compatible but enforce every newly measured gate."""

    record_path = _segment_directory(task_dir, segment_id) / "production-record.json"
    if not record_path.is_file():
        return False
    record = read_json(record_path)
    gate = record.get("voice_identity_gate")
    if gate is None:
        return True
    return (
        isinstance(gate, dict)
        and gate.get("status") in {"PASS", "NOT_APPLICABLE"}
        and gate.get("blocks_acceptance") is False
    )
