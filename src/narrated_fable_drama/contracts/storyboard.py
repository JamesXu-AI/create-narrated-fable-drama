"""Authoritative Markdown parsing for the cinematic Storyboard contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


STORYBOARD_RELATIVE = Path("previsualize-cinematography/storyboard.md")
SEGMENT_HEADING_RE = re.compile(
    r"^## Generation Segment ([1-9][0-9]*) — .+$",
    re.MULTILINE,
)


class StoryboardContractError(RuntimeError):
    """Raised when Storyboard Markdown cannot be parsed as the shared contract."""


def markdown_cells(
    line: str,
    *,
    error_type: type[RuntimeError] = StoryboardContractError,
) -> list[str]:
    """Parse one escaped pipe-table row without losing literal pipes."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        raise error_type("Markdown table row must start and end with |")
    body = stripped[1:-1]
    cells: list[str] = []
    current: list[str] = []
    cursor = 0
    while cursor < len(body):
        char = body[cursor]
        if (
            char == "\\"
            and cursor + 1 < len(body)
            and body[cursor + 1] in {"|", "\\"}
        ):
            current.append(body[cursor + 1])
            cursor += 2
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        cursor += 1
    cells.append("".join(current).strip())
    return cells


def table_after_heading(
    text: str,
    heading: str,
    *,
    stop_at_level_two: bool = True,
    error_type: type[RuntimeError] = StoryboardContractError,
) -> tuple[list[str], list[list[str]]]:
    """Return the first Markdown table in a named section."""
    start = text.find(heading)
    if start < 0:
        raise error_type(f"Missing {heading}")
    section = text[start + len(heading) :]
    if stop_at_level_two:
        next_heading = re.search(r"^## ", section, re.MULTILINE)
        if next_heading:
            section = section[: next_heading.start()]
    lines = section.splitlines()
    table_start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().startswith("|")
        ),
        None,
    )
    if table_start is None or table_start + 1 >= len(lines):
        raise error_type(f"{heading} must contain a Markdown table")
    headers = markdown_cells(lines[table_start], error_type=error_type)
    separator = markdown_cells(lines[table_start + 1], error_type=error_type)
    if len(separator) != len(headers) or any(
        not re.fullmatch(r":?-{3,}:?", item) for item in separator
    ):
        raise error_type(f"{heading} has an invalid separator")
    rows: list[list[str]] = []
    for line in lines[table_start + 2 :]:
        if not line.strip().startswith("|"):
            if rows:
                break
            continue
        row = markdown_cells(line, error_type=error_type)
        if len(row) != len(headers):
            raise error_type(f"{heading} has an invalid row")
        rows.append(row)
    if not rows:
        raise error_type(f"{heading} table must not be empty")
    return headers, rows


def comma_values(value: str) -> list[str]:
    """Parse an authored comma list while preserving the explicit ``none`` token."""
    if value.strip().casefold() == "none":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def segment_sections(text: str) -> dict[str, str]:
    """Return ordered Generation Segment bodies keyed by canonical Segment ID."""
    matches = list(SEGMENT_HEADING_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        segment_id = f"segment-{int(match.group(1)):03d}"
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else text.find("## Continuity Review", match.end())
        )
        if end < 0:
            end = len(text)
        sections[segment_id] = text[match.end() : end]
    return sections


@dataclass(frozen=True)
class StoryboardDocument:
    """Loaded Storyboard source plus its authoritative structural views."""

    path: Path
    text: str
    error_type: type[RuntimeError] = StoryboardContractError

    @classmethod
    def load(
        cls,
        task_dir: Path,
        *,
        error_type: type[RuntimeError] = StoryboardContractError,
    ) -> "StoryboardDocument":
        path = task_dir.expanduser().resolve(strict=True) / STORYBOARD_RELATIVE
        try:
            text = path.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError) as exc:
            raise error_type(f"Missing or invalid Storyboard: {path}") from exc
        return cls(path=path, text=text, error_type=error_type)

    def table(
        self,
        heading: str,
        *,
        section: str | None = None,
        stop_at_level_two: bool = True,
    ) -> tuple[list[str], list[list[str]]]:
        return table_after_heading(
            self.text if section is None else section,
            heading,
            stop_at_level_two=stop_at_level_two,
            error_type=self.error_type,
        )

    @property
    def segments(self) -> dict[str, str]:
        return segment_sections(self.text)
