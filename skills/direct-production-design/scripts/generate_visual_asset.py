"""Generate one Seedream image directly into its final production asset folder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit

from production_design.contract import (
    ProductionDesignPlanError,
    validate_generation_prompt_text,
)
from narrated_fable_drama.contracts.role_scope import role_asset_scope_gate
from narrated_fable_drama.core.validation import StoryVideoError
from narrated_fable_drama.core.paths import ProjectPaths
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.providers import runtime as provider_runtime
from narrated_fable_drama.providers import seedream


REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root


ASSET_KINDS = frozenset(
    {
        "character",
        "costume",
        "location_master",
        "prop",
        "ensemble_roster",
    }
)
ASSET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SIZE_RE = re.compile(r"^(?:[1-9][0-9]{2,4}x[1-9][0-9]{2,4}|[1-9][0-9]*[Kk])$")
MAX_REFERENCE_IMAGES = 10
DEFAULT_IMAGE_SIZE = seedream.SEEDREAM_MAX_IMAGE_SIZE
DEFAULT_TIMEOUT = provider_runtime.DEFAULT_TIMEOUT


class VisualAssetGenerationError(StoryVideoError):
    """Raised when direct visual-asset generation input or output is invalid."""


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VisualAssetGenerationError(f"{label} must be non-empty text.")
    return value.strip()


def _validate_asset_identity(asset_id: str, asset_kind: str) -> tuple[str, str]:
    normalized_id = _require_text(asset_id, "asset_id")
    if not ASSET_ID_RE.fullmatch(normalized_id):
        raise VisualAssetGenerationError(
            "asset_id must use lowercase letters, digits, underscores, or hyphens."
        )
    normalized_kind = _require_text(asset_kind, "asset_kind")
    if normalized_kind not in ASSET_KINDS:
        raise VisualAssetGenerationError(
            "asset_kind must be one of: " + ", ".join(sorted(ASSET_KINDS)) + "."
        )
    return normalized_id, normalized_kind


def load_visual_prompt(prompt_file: Path) -> tuple[str, Path]:
    source = prompt_file.expanduser()
    try:
        source = source.resolve(strict=True)
        prompt = source.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
        raise VisualAssetGenerationError(
            f"prompt_file must identify readable UTF-8 text: {prompt_file}"
        ) from exc
    if not source.is_file():
        raise VisualAssetGenerationError(
            f"prompt_file must identify a regular file: {prompt_file}"
        )
    return _require_text(prompt, "prompt_file content"), source


def validate_provider_prompt(
    task_root: Path, *, asset_kind: str, asset_prompt: str
) -> str:
    try:
        load_project_context(task_root)
    except Exception as exc:
        raise VisualAssetGenerationError(
            "Invalid screenplay-owned project context"
        ) from exc
    brief = _require_text(asset_prompt, "asset-specific prompt")
    try:
        return validate_generation_prompt_text(brief, asset_type=asset_kind)
    except ProductionDesignPlanError as exc:
        raise VisualAssetGenerationError(str(exc)) from exc


def _reference_values(values: Iterable[str] | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)):
        raise VisualAssetGenerationError(
            "reference_images must be an ordered array, not one string."
        )
    references = list(values)
    if len(references) > MAX_REFERENCE_IMAGES:
        raise VisualAssetGenerationError(
            "Visual asset generation accepts 0-10 ordered reference images."
        )
    return [
        _require_text(value, f"reference image {index}")
        for index, value in enumerate(references, start=1)
    ]


def _normalize_reference(
    task_root: Path, value: str, *, index: int
) -> tuple[str, str]:
    parsed = urlsplit(value)
    if parsed.scheme:
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise VisualAssetGenerationError(
                f"Reference image {index} must be a local file or absolute HTTP(S) URL."
            )
        return (
            urlunsplit(
                (
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    parsed.path or "/",
                    parsed.query,
                    "",
                )
            ),
            "http_url",
        )
    local = Path(value).expanduser()
    if not local.is_absolute():
        local = task_root / local
    try:
        local = local.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise VisualAssetGenerationError(
            f"Reference image {index} does not identify an existing local file: {value}"
        ) from exc
    if not local.is_file():
        raise VisualAssetGenerationError(
            f"Reference image {index} must identify a regular local file: {value}"
        )
    return str(local), "local_file"


def resolve_ordered_references(
    task_root: Path, values: Iterable[str] | None
) -> tuple[list[str], list[dict[str, Any]]]:
    resolved: list[str] = []
    audit: list[dict[str, Any]] = []
    for index, declared in enumerate(_reference_values(values), start=1):
        normalized, source_kind = _normalize_reference(
            task_root, declared, index=index
        )
        try:
            provider_value = provider_runtime.resolve_input(
                normalized,
                kind="image",
                upload_local=False,
            )
        except provider_runtime.SeedMediaError as exc:
            raise VisualAssetGenerationError(str(exc)) from exc
        resolved.append(provider_value)
        audit.append(
            {
                "order": index,
                "provider_image_index": index - 1,
                "declared_source": declared,
                "normalized_source": normalized,
                "source_kind": source_kind,
            }
        )
    return resolved, audit


def build_provider_request(
    *, prompt: str, reference_images: Iterable[str], size: str
) -> dict[str, Any]:
    image_size = _require_text(size, "size")
    if not SIZE_RE.fullmatch(image_size):
        raise VisualAssetGenerationError(
            "size must be WIDTHxHEIGHT or a provider-supported resolution token."
        )
    images = list(reference_images)
    request: dict[str, Any] = {
        "model": seedream.SEEDREAM_MODEL_ID,
        "prompt": _require_text(prompt, "prompt"),
        "size": image_size,
        "output_format": "png",
        "response_format": "url",
        "watermark": False,
    }
    if images:
        request["image"] = images[0] if len(images) == 1 else images
    return request


def _final_output_path(asset_root: Path, output_path: Path) -> Path:
    asset_root = asset_root.expanduser().resolve()
    value = output_path.expanduser()
    if not value.is_absolute():
        value = asset_root / value
    value = value.resolve()
    if value == asset_root or asset_root not in value.parents:
        raise VisualAssetGenerationError(
            "output_path must be a file inside the repository-owned assets directory."
        )
    return value


def _single_output_url(response: dict[str, Any]) -> str:
    data = response.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise VisualAssetGenerationError(
            "Seedream visual asset generation must return exactly one image result."
        )
    item = data[0]
    if item.get("error"):
        raise VisualAssetGenerationError("Seedream returned an image generation error.")
    url = item.get("url")
    if not isinstance(url, str) or not url.strip():
        raise VisualAssetGenerationError("Seedream response lacks the image URL.")
    url = url.strip()
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise VisualAssetGenerationError(
            "Seedream image URL must be absolute HTTP(S)."
        )
    return url


def generate_visual_asset(
    *,
    task_root: Path,
    asset_id: str,
    asset_kind: str,
    asset_prompt: str,
    output_path: Path,
    asset_root: Path,
    reference_images: Iterable[str] | None = None,
    size: str = DEFAULT_IMAGE_SIZE,
    dry_run: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Generate directly to the declared final image without duplicate sidecars."""

    try:
        root = task_root.expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise VisualAssetGenerationError(
            f"task_root must identify an existing directory: {task_root}"
        ) from exc
    normalized_id, normalized_kind = _validate_asset_identity(asset_id, asset_kind)
    provider_prompt = validate_provider_prompt(
        root, asset_kind=normalized_kind, asset_prompt=asset_prompt
    )
    references, reference_plan = resolve_ordered_references(root, reference_images)
    provider_request = build_provider_request(
        prompt=provider_prompt, reference_images=references, size=size
    )
    if not dry_run and (
        isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1
    ):
        raise VisualAssetGenerationError("timeout must be a positive integer.")

    final_path = _final_output_path(asset_root, output_path)
    result: dict[str, Any] = {
        "status": "planned" if dry_run else "ready",
        "asset_id": normalized_id,
        "asset_kind": normalized_kind,
        "output_path": str(final_path),
        "reference_count": len(reference_plan),
        "source_url": None,
        "seedream_generation_calls": 0 if dry_run else 1,
    }
    if dry_run:
        return result

    try:
        response = seedream.generate_image(provider_request, timeout=timeout)
    except provider_runtime.SeedMediaError as exc:
        raise VisualAssetGenerationError(
            f"Seedream visual asset generation failed: {exc}"
        ) from exc
    if not isinstance(response, dict):
        raise VisualAssetGenerationError(
            "Seedream visual asset response must be a JSON object."
        )
    source_download_url = _single_output_url(response)
    with tempfile.TemporaryDirectory(
        prefix=f"visual-asset-{normalized_id}-"
    ) as temporary_dir:
        try:
            downloaded = Path(
                provider_runtime.download_url(
                    source_download_url,
                    Path(temporary_dir) / final_path.name,
                    timeout=max(timeout, 300),
                )
            )
            if not downloaded.is_file() or downloaded.stat().st_size <= 0:
                raise VisualAssetGenerationError(
                    "Downloaded Seedream visual asset is missing or empty."
                )
            stored = provider_runtime.tos_upload_path(
                downloaded,
                key=provider_runtime.production_asset_key(
                    normalized_kind, normalized_id, final_path.name
                ),
            )
            source_url = stored["public_url"]
            final_path.parent.mkdir(parents=True, exist_ok=True)
            ready = final_path.with_name(f".{final_path.name}.ready")
            ready.unlink(missing_ok=True)
            shutil.copyfile(downloaded, ready)
            ready.replace(final_path)
        except Exception as exc:
            if "ready" in locals():
                ready.unlink(missing_ok=True)
            if isinstance(exc, VisualAssetGenerationError):
                raise
            raise VisualAssetGenerationError(
                f"Failed to finalize Seedream visual asset: {exc}"
            ) from exc
    result["source_url"] = source_url
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--asset-kind", required=True, choices=sorted(ASSET_KINDS))
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--output-path", required=True, type=Path)
    parser.add_argument("--reference-image", action="append")
    parser.add_argument("--size", default=DEFAULT_IMAGE_SIZE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        role_asset_scope_gate(args.task_dir)
        prompt_file = args.prompt_file.expanduser()
        if not prompt_file.is_absolute():
            prompt_file = args.task_dir.expanduser().resolve() / prompt_file
        prompt, _ = load_visual_prompt(prompt_file)
        result = generate_visual_asset(
            task_root=args.task_dir,
            asset_id=args.asset_id,
            asset_kind=args.asset_kind,
            asset_prompt=prompt,
            output_path=args.output_path,
            asset_root=REPOSITORY_ROOT / "assets",
            reference_images=args.reference_image,
            size=args.size,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    except StoryVideoError as exc:
        print(
            json.dumps(
                {"status": "failed", "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
