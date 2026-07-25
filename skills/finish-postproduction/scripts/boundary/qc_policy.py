"""Load Boundary QC policy and provide shared persistence/command adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from narrated_fable_drama.core.json_io import (
    load_json_object,
    write_json_atomic,
)
from narrated_fable_drama.core.paths import ProjectPaths
from narrated_fable_drama.media.ffmpeg import MediaCommandError, run


REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root
DEFAULT_CONFIG = (
    REPOSITORY_ROOT
    / "skills"
    / "finish-postproduction"
    / "assets"
    / "boundary-qc.json"
)


class BoundaryQCError(RuntimeError):
    """Raised when deterministic boundary evidence or repair cannot be built."""


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    return load_json_object(path, label=label, error_type=BoundaryQCError)


def _positive_number(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise BoundaryQCError(f"{label} must be a positive number")
    return float(value)


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load and validate deterministic evidence-rendering settings."""
    config = _load_json(path.expanduser().resolve(), label="boundary QC config")
    if config.get("contract") != "finish-boundary-qc-evidence-config/v2":
        raise BoundaryQCError("Unsupported boundary QC config contract")
    if not isinstance(config.get("enabled"), bool):
        raise BoundaryQCError("boundary QC config enabled must be boolean")
    strict = config.get("strict_sample")
    analysis = config.get("analysis")
    for label, value in (
        ("strict_sample", strict),
        ("analysis", analysis),
    ):
        if not isinstance(value, dict):
            raise BoundaryQCError(f"boundary QC config {label} must be an object")
    frame_rate = int(_positive_number(strict.get("frame_rate"), label="frame_rate"))
    tail = _positive_number(strict.get("tail_seconds"), label="tail_seconds")
    head = _positive_number(strict.get("head_seconds"), label="head_seconds")
    frame_count = int(_positive_number(strict.get("frame_count"), label="frame_count"))
    if abs(tail - 1.0) > 1e-9 or abs(head - 1.0) > 1e-9:
        raise BoundaryQCError("Strict cut seam must be final 1.0s plus opening 1.0s")
    if frame_rate != 24 or frame_count != 48:
        raise BoundaryQCError("Strict seam evidence must be exactly 48 frames at 24 fps")
    _positive_number(strict.get("evidence_frame_width"), label="evidence_frame_width")
    _positive_number(analysis.get("width"), label="analysis.width")
    _positive_number(analysis.get("anchor_frame_count"), label="anchor_frame_count")
    return config


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    write_json_atomic(path, payload, sort_keys=True)


def _run(command: list[str], *, label: str) -> None:
    try:
        run(command, context=label)
    except MediaCommandError as exc:
        raise BoundaryQCError(f"{label} failed") from exc
