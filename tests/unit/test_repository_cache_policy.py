from __future__ import annotations

import os
import runpy
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch

from narrated_fable_drama import cli

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_syntax_check_does_not_create_bytecode(tmp_path: Path) -> None:
    validator = runpy.run_path(
        str(REPOSITORY_ROOT / "scripts" / "validate_repository.py")
    )
    source_root = tmp_path / "src"
    source_root.mkdir()
    (source_root / "valid.py").write_text("answer = 42\n", encoding="utf-8")

    errors = validator["python_syntax_errors"](source_root)

    assert errors == []
    assert list(tmp_path.rglob("*.pyc")) == []
    assert list(tmp_path.rglob("__pycache__")) == []


def test_syntax_check_reports_invalid_source(tmp_path: Path) -> None:
    validator = runpy.run_path(
        str(REPOSITORY_ROOT / "scripts" / "validate_repository.py")
    )
    source_root = tmp_path / "src"
    source_root.mkdir()
    invalid = source_root / "invalid.py"
    invalid.write_text("def broken(:\n", encoding="utf-8")

    errors = validator["python_syntax_errors"](source_root)

    assert len(errors) == 1
    assert str(invalid) in errors[0]


def test_python_runner_respects_an_explicit_cache_prefix(tmp_path: Path) -> None:
    cache_prefix = tmp_path / "python-cache"
    environment = os.environ.copy()
    environment["PYTHONPYCACHEPREFIX"] = str(cache_prefix)
    completed = subprocess.run(
        [
            str(REPOSITORY_ROOT / "scripts" / "run_python.sh"),
            "-c",
            "import sys; print(sys.pycache_prefix)",
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == str(cache_prefix)


def test_python_runner_defaults_to_canonical_cache_prefix() -> None:
    environment = os.environ.copy()
    environment.pop("PYTHONPYCACHEPREFIX", None)
    environment["PYTHON_BIN"] = sys.executable
    completed = subprocess.run(
        [
            str(REPOSITORY_ROOT / "scripts" / "run_python.sh"),
            "-c",
            "import sys; print(sys.pycache_prefix)",
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == str(
        REPOSITORY_ROOT / ".cache" / "pycache"
    )


def test_python_runner_prefers_repository_virtual_environment(
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository"
    scripts_dir = repository_root / "scripts"
    virtualenv_bin = repository_root / ".venv" / "bin"
    scripts_dir.mkdir(parents=True)
    virtualenv_bin.mkdir(parents=True)
    runner = scripts_dir / "run_python.sh"
    shutil.copy2(REPOSITORY_ROOT / "scripts" / "run_python.sh", runner)
    virtualenv_python = virtualenv_bin / "python"
    virtualenv_python.write_text(
        "#!/bin/sh\nprintf '%s\\n' repository-virtualenv\n",
        encoding="utf-8",
    )
    virtualenv_python.chmod(0o755)
    environment = os.environ.copy()
    environment.pop("PYTHON_BIN", None)
    environment.pop("VIRTUAL_ENV", None)

    completed = subprocess.run(
        [str(runner), "-c", "ignored"],
        cwd=repository_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "repository-virtualenv"


def test_tool_caches_live_under_canonical_cache_directory() -> None:
    configuration = tomllib.loads(
        (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert configuration["tool"]["pytest"]["ini_options"]["cache_dir"] == (
        ".cache/pytest"
    )
    assert configuration["tool"]["ruff"]["cache-dir"] == ".cache/ruff"


def test_cli_propagates_the_cache_prefix_to_validation_child() -> None:
    with patch.object(cli.subprocess, "run") as run:
        run.return_value.returncode = 0

        assert cli._validate_repository() == 0

    environment = run.call_args.kwargs["env"]
    expected = os.environ.get(
        "PYTHONPYCACHEPREFIX",
        str(REPOSITORY_ROOT / ".cache" / "pycache"),
    )
    assert environment["PYTHONPYCACHEPREFIX"] == expected


def test_pytest_collection_redirects_bytecode_to_canonical_cache() -> None:
    expected = os.environ.get(
        "PYTHONPYCACHEPREFIX",
        str(REPOSITORY_ROOT / ".cache" / "pycache"),
    )
    assert sys.pycache_prefix == expected
