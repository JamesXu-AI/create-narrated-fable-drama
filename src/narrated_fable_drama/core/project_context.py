"""Read fixed project settings from the sole screenplay Markdown authority."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.core.project_domain import (
    ProjectDomainError,
    validate_project_context,
)


SCREENPLAY_RELATIVE = Path("screenplay-writer/screenplay.md")
PRODUCTION_HEADING = "## Production Information"
REQUIRED_FIELDS = (
    "Production Type",
    "Genre",
    "Visual Style",
    "Estimated Runtime Seconds",
    "Target Country",
    "Target Language",
    "Aspect Ratio",
    "Resolution",
    "Speech Audio Source",
    "Sound Effects Audio Source",
    "Story Premise",
    "Fable Meaning",
    "Framing and Embedded Story Strategy",
    "Speech Transition Strategy",
    "Safety and Culture",
    "Opening Event",
    "Ending Event and Obligation",
)


def _cells(line: str) -> list[str]:
    return [item.strip() for item in line.strip().strip("|").split("|")]


def read_production_information(path: str | Path) -> dict[str, str]:
    screenplay = Path(path).expanduser().resolve()
    try:
        text = screenplay.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError) as exc:
        raise ProjectDomainError(f"Missing or invalid screenplay: {screenplay}") from exc
    start = text.find(PRODUCTION_HEADING)
    if start < 0:
        raise ProjectDomainError(f"{screenplay} lacks {PRODUCTION_HEADING}.")
    section = text[start + len(PRODUCTION_HEADING) :]
    next_heading = re.search(r"^## ", section, re.M)
    if next_heading:
        section = section[: next_heading.start()]
    lines = [line for line in section.splitlines() if line.strip()]
    table_start = next(
        (index for index, line in enumerate(lines) if line.strip().startswith("|")),
        None,
    )
    if table_start is None or table_start + 2 >= len(lines):
        raise ProjectDomainError(f"{screenplay} has no Production Information table.")
    if _cells(lines[table_start]) != ["Field", "Value"]:
        raise ProjectDomainError("Production Information must use Field | Value.")
    values: dict[str, str] = {}
    for line in lines[table_start + 2 :]:
        if not line.strip().startswith("|"):
            break
        cells = _cells(line)
        if len(cells) != 2 or not all(cells):
            raise ProjectDomainError("Production Information has an invalid row.")
        if cells[0] in values:
            raise ProjectDomainError(
                f"Production Information repeats {cells[0]}."
            )
        values[cells[0]] = cells[1]
    if tuple(values) != REQUIRED_FIELDS:
        raise ProjectDomainError(
            "Production Information fields differ from the current contract."
        )
    return values


def load_project_context(task_dir: str | Path) -> dict[str, Any]:
    root = Path(task_dir).expanduser().resolve()
    values = read_production_information(root / SCREENPLAY_RELATIVE)
    try:
        runtime = int(values["Estimated Runtime Seconds"])
    except ValueError as exc:
        raise ProjectDomainError(
            "Estimated Runtime Seconds must be an integer."
        ) from exc
    context: dict[str, Any] = {
        "production_type": values["Production Type"],
        "genre": values["Genre"],
        "visual_style": values["Visual Style"],
        "runtime_seconds": runtime,
        "target_country": values["Target Country"],
        "target_language": values["Target Language"],
        "aspect_ratio": values["Aspect Ratio"],
        "resolution": values["Resolution"],
        "speech_audio_source": values["Speech Audio Source"],
        "sound_effects_audio_source": values["Sound Effects Audio Source"],
    }
    validate_project_context(context, context=str(root / SCREENPLAY_RELATIVE))
    if runtime < 1 or runtime > 240:
        raise ProjectDomainError("Estimated Runtime Seconds must be 1-240.")
    return context
