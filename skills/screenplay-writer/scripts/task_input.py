#!/usr/bin/env python3
"""Validate the Story-only intake used before screenplay authorship."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from narrated_fable_drama.core.validation import (
    StoryVideoError,
    normalize_video_resolution,
    require_utf8_text,
)


COUNTRY_RE = re.compile(r"^[^\n\r|]{2,80}$")


def load_story(task_dir: str | Path) -> str:
    path = Path(task_dir).expanduser().resolve() / "story.md"
    try:
        return require_utf8_text(path.read_text(encoding="utf-8"), "story.md")
    except FileNotFoundError as exc:
        raise StoryVideoError(f"Missing Story: {path}") from exc
    except UnicodeDecodeError as exc:
        raise StoryVideoError(f"Story must be valid UTF-8: {path}") from exc


def validate_country(value: str) -> str:
    country = require_utf8_text(value, "target country")
    if not COUNTRY_RE.fullmatch(country):
        raise StoryVideoError("Target country must be one concise country name.")
    return country


def extract_story_input(
    task_dir: str | Path,
    country: str,
    *,
    visual_style: str = "3D Healing Animation",
    resolution: str = "1080p",
) -> dict[str, str]:
    return {
        "story": load_story(task_dir),
        "target_country": validate_country(country),
        "aspect_ratio": "16:9",
        "visual_style": require_utf8_text(visual_style, "visual style"),
        "resolution": normalize_video_resolution(resolution),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--country", required=True)
    parser.add_argument("--visual-style", default="3D Healing Animation")
    parser.add_argument("--resolution", default="1080p")
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                extract_story_input(
                    args.task_dir,
                    args.country,
                    visual_style=args.visual_style,
                    resolution=args.resolution,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    except StoryVideoError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
