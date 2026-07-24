"""Strict JSON loading and atomic JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


class JsonIOError(ValueError):
    """Raised when a JSON authority cannot be loaded or persisted."""


def load_json_object(
    path: str | Path,
    *,
    label: str,
    object_pairs_hook: Callable[[list[tuple[str, Any]]], dict[str, Any]] | None = None,
    error_type: type[Exception] = JsonIOError,
) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    try:
        text = source.read_text(encoding="utf-8")
        value = json.loads(text, object_pairs_hook=object_pairs_hook)
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise error_type(f"Missing or invalid {label}: {source}") from exc
    if not isinstance(value, dict):
        raise error_type(f"{label} must contain one JSON object: {source}")
    return value


def load_optional_json_object(path: str | Path) -> dict[str, Any] | None:
    source = Path(path).expanduser().resolve()
    try:
        return load_json_object(source, label=source.name)
    except JsonIOError:
        return None


def write_json_atomic(
    path: str | Path,
    value: Any,
    *,
    sort_keys: bool = False,
) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=sort_keys) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return target
