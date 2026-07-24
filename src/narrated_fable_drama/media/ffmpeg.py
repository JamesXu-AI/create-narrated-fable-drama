"""Execute local media commands with one error and binary policy."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import shutil
import subprocess
from typing import Any


class MediaCommandError(RuntimeError):
    """Raised when a required media binary or command fails."""


def require_binary(name: str) -> str:
    binary = shutil.which(name)
    if binary is None:
        raise MediaCommandError(f"{name} is required on PATH.")
    return binary


def run(
    command: Sequence[str | Path],
    *,
    context: str,
    check: bool = True,
    timeout: float | None = None,
    text: bool = True,
) -> subprocess.CompletedProcess[Any]:
    try:
        completed = subprocess.run(
            [str(item) for item in command],
            text=text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise MediaCommandError(f"{context} failed: {exc}") from exc
    if check and completed.returncode != 0:
        raw_detail = completed.stderr or completed.stdout or "unknown error"
        detail = (
            raw_detail.decode("utf-8", errors="replace")
            if isinstance(raw_detail, bytes)
            else str(raw_detail)
        ).strip()
        raise MediaCommandError(f"{context} failed: {detail[:2000]}")
    return completed
