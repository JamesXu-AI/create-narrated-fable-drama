"""Resolve repository and workspace paths without fixed parent-depth assumptions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPOSITORY_ENV = "NARRATED_FABLE_DRAMA_ROOT"
WORKSPACE_ENV = "NARRATED_FABLE_DRAMA_WORKSPACE"


class ProjectPathError(ValueError):
    """Raised when the narrated-fable repository layout cannot be resolved."""


def find_repository_root(start: str | Path | None = None) -> Path:
    configured = os.environ.get(REPOSITORY_ENV)
    if configured:
        root = Path(configured).expanduser().resolve()
        if (root / "pyproject.toml").is_file() and (root / "SKILL.md").is_file():
            return root
        raise ProjectPathError(
            f"{REPOSITORY_ENV} must contain pyproject.toml and SKILL.md: {root}"
        )

    origin = Path(start or Path.cwd()).expanduser().resolve()
    candidates = (origin, *origin.parents) if origin.is_dir() else origin.parents
    for candidate in candidates:
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "SKILL.md"
        ).is_file():
            return candidate
    raise ProjectPathError(
        f"Cannot find the narrated-fable repository above {origin}."
    )


@dataclass(frozen=True)
class ProjectPaths:
    repository_root: Path
    workspace_root: Path

    @classmethod
    def resolve(cls, start: str | Path | None = None) -> "ProjectPaths":
        repository_root = find_repository_root(start)
        configured_workspace = os.environ.get(WORKSPACE_ENV)
        workspace_root = (
            Path(configured_workspace).expanduser().resolve()
            if configured_workspace
            else repository_root / "workspace"
        )
        return cls(
            repository_root=repository_root,
            workspace_root=workspace_root,
        )

    @property
    def skills_root(self) -> Path:
        return self.repository_root / "skills"

    @property
    def shared_assets_root(self) -> Path:
        return self.workspace_root / "assets"

    @property
    def tasks_root(self) -> Path:
        return self.workspace_root / "tasks"
