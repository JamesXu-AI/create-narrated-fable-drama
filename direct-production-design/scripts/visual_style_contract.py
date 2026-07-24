"""Minimal visual-profile identity and prohibited shortcut validation."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_SCRIPTS_ROOT = REPOSITORY_ROOT / "scripts"
if str(PROJECT_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_SCRIPTS_ROOT))

from project_domain import VISUAL_STYLE_PROFILE  # noqa: E402

# Provider prompts carry their complete model-authored style section. This module
# intentionally contains no prose blocks that Python could prepend or append.
PROHIBITED_STYLE_SHORTCUT_RE = re.compile(
    r"\b(?:pixar|disney|dreamworks|illumination|ghibli|blender|cycles|"
    r"unreal engine|octane render)\b",
    re.IGNORECASE,
)


def contains_prohibited_style_shortcut(value: Any) -> bool:
    if isinstance(value, str):
        return bool(PROHIBITED_STYLE_SHORTCUT_RE.search(value))
    if isinstance(value, dict):
        return any(contains_prohibited_style_shortcut(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_prohibited_style_shortcut(item) for item in value)
    return False
