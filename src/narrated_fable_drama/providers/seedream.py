#!/usr/bin/env python3
"""Repository-owned Seedream provider adapter."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from narrated_fable_drama.providers import runtime as core


SEEDREAM_ENV = ("ARK_BASE_URL", "SEEDREAM_API_KEY", "SEEDREAM_MODEL")
SEEDREAM_MODEL_ID = "dola-seedream-5-0-pro-260628"
SEEDREAM_MAX_IMAGE_SIZE = "2816x1584"


def api_key() -> str:
    value = core.env("SEEDREAM_API_KEY", required=True)
    assert value is not None
    return value


def model_id() -> str:
    value = core.env("SEEDREAM_MODEL", required=True)
    assert value is not None
    if value != SEEDREAM_MODEL_ID:
        raise core.SeedMediaError(
            "SEEDREAM_MODEL must be exactly "
            f"{SEEDREAM_MODEL_ID}; no other model ID is accepted"
        )
    return SEEDREAM_MODEL_ID


def generate_image(
    payload: dict[str, Any], *, timeout: int = core.DEFAULT_TIMEOUT
) -> dict[str, Any]:
    """Generate an image without exposing ModelArk transport details to workflows."""
    core.require_environment(*SEEDREAM_ENV)
    required_model = model_id()
    request_payload = dict(payload)
    requested_model = request_payload.get("model")
    if requested_model is not None and requested_model != required_model:
        raise core.SeedMediaError(
            f"Seedream request model must be exactly {required_model}; received "
            f"{requested_model!r}"
        )
    request_payload["model"] = required_model
    return core.request_json(
        "POST",
        "images/generations",
        key=api_key(),
        body=request_payload,
        timeout=timeout,
    )


def command_config(_: argparse.Namespace) -> dict[str, Any]:
    capabilities = {
        "seedream": SEEDREAM_ENV,
        "tos_storage": core.TOS_ENV,
    }
    missing = core.missing_environment(SEEDREAM_ENV)
    return {
        "environment_source": "host_process_environment",
        "configured": not missing,
        "missing_environment_variables": missing,
        "capabilities": {
            name: {
                "configured": not core.missing_environment(names),
                "missing_environment_variables": core.missing_environment(names),
            }
            for name, names in capabilities.items()
        },
        "ark": {
            "base_url": os.getenv("ARK_BASE_URL"),
            "model": os.getenv("SEEDREAM_MODEL"),
            "credentials": bool(os.getenv("SEEDREAM_API_KEY")),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretty", action="store_true")
    root = parser.add_subparsers(dest="command", required=True)

    config = root.add_parser("config", help="Show non-secret Seedream configuration status")
    config.set_defaults(handler=command_config)
    return parser


def main(argv: list[str] | None = None) -> int:
    return core.run_cli(build_parser(), argv)


if __name__ == "__main__":
    raise SystemExit(main())
