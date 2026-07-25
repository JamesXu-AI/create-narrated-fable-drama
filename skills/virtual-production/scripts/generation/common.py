"""Shared state, errors, and task paths for Segment generation."""

from __future__ import annotations

from pathlib import Path
import re
import threading
from typing import Any

from narrated_fable_drama.core.json_io import load_json_object, write_json_atomic
from narrated_fable_drama.core.paths import ProjectPaths


REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root


PENDING_DIRNAME = ".pending"
DEPARTMENT_DIRNAME = "virtual-production"
GENERATION_DIRNAME = "generation-segments"
PROVIDER_ATTEMPTS_DIRNAME = "provider-attempts"
ACTIVE_ATTEMPT_DIRNAME = "active"
EXECUTION_LOCK_FILENAME = "generation.lock"
TERMINAL_STATES = {"succeeded", "failed", "cancelled", "expired"}
MAX_WHITE_MODEL_RESET_ATTEMPTS = 3
FAILED_ATTEMPT_RE = re.compile(r"^attempt-([0-9]{4})-failed$")
PRINT_LOCK = threading.Lock()


class SegmentGenerationError(RuntimeError):
    pass


def announce(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def write_json(path: Path, value: Any) -> None:
    write_json_atomic(path, value, sort_keys=True)


def read_json(path: Path) -> dict[str, Any]:
    return load_json_object(
        path,
        label="JSON",
        error_type=SegmentGenerationError,
    )
