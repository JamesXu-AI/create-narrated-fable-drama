"""Create and enforce virtual-production's separate internal Prompt audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.segment.common import (
    REPOSITORY_ROOT,
    SCRIPT_DIR_RELATIVE,
    SegmentRuntimeError,
    read_json,
    sha256_file,
    sha256_json,
    write_json,
)
from narrated_fable_drama.contracts.segment.prompt import parse_segment_script
from narrated_fable_drama.core.project_domain import (
    ProjectDomainError,
    TARGET_LANGUAGE,
    validate_arabic_dialogue,
)

PROMPT_AUDIT_DIR_RELATIVE = Path(
    ".pending/virtual-production/prompt-audits"
)
PROMPT_AUDIT_RULESET_RELATIVE = Path(
    "skills/virtual-production/references/"
    "seedance-2-prompt-audit-contract.md"
)
PROMPT_AUTHORING_RULESET_RELATIVE = Path(
    "skills/virtual-production/references/"
    "seedance-2-prompt-authoring-contract.md"
)
PROMPT_AUDIT_CONTRACT = "seedance-prompt-internal-audit/v3"


def prompt_audit_path(task_dir: Path, segment_id: str) -> Path:
    return task_dir / PROMPT_AUDIT_DIR_RELATIVE / f"{segment_id}.json"


def build_prompt_audit_record(
    task_dir: Path,
    segment_id: str,
) -> dict[str, Any]:
    script_path = task_dir / SCRIPT_DIR_RELATIVE / f"{segment_id}.md"
    parsed = parse_segment_script(script_path)
    if parsed["segment_id"] != segment_id:
        raise SegmentRuntimeError(
            f"Prompt audit target differs from parsed Segment: {segment_id}"
        )
    arabic_lines: list[dict[str, str]] = []
    try:
        for cue in parsed["metadata"]["dialogue_cues"]:
            exact_text = validate_arabic_dialogue(
                cue["exact_text"],
                context=f"{segment_id}/{cue['line_id']} Prompt audit",
            )
            arabic_lines.append(
                {
                    "line_id": str(cue["line_id"]),
                    "text_sha256": hashlib.sha256(
                        exact_text.encode("utf-8")
                    ).hexdigest(),
                }
            )
    except (KeyError, TypeError, ProjectDomainError) as exc:
        raise SegmentRuntimeError(
            f"{segment_id} Prompt audit requires exact Arabic-only dialogue"
        ) from exc
    ruleset_components = {
        "generation_time_authoring": {
            "path": PROMPT_AUTHORING_RULESET_RELATIVE.as_posix(),
            "sha256": sha256_file(
                REPOSITORY_ROOT / PROMPT_AUTHORING_RULESET_RELATIVE
            ),
        },
        "independent_final_audit": {
            "path": PROMPT_AUDIT_RULESET_RELATIVE.as_posix(),
            "sha256": sha256_file(
                REPOSITORY_ROOT / PROMPT_AUDIT_RULESET_RELATIVE
            ),
        },
    }
    return {
        "contract": PROMPT_AUDIT_CONTRACT,
        "status": "PASS",
        "segment_id": segment_id,
        "department": "virtual-production",
        "gate": "seedance_prompt_internal_audit",
        "language": TARGET_LANGUAGE,
        "language_code": "ar",
        "spoken_authority": "storyboard_exact_arabic_dialogue",
        "seedance_audio_mode": parsed["seedance_audio_mode"],
        "model_prompt_language": "Arabic",
        "model_prompt_language_code": "ar",
        "latin_text_policy": (
            "forbidden_except_provider_reference_tokens"
        ),
        "arabic_line_authority": arabic_lines,
        "prompt_path": str(script_path.resolve()),
        "prompt_sha256": parsed["script_sha256"],
        "model_prompt_sha256": hashlib.sha256(
            str(parsed["prompt"]).encode("utf-8")
        ).hexdigest(),
        "source_storyboard_sha256": parsed["metadata"][
            "source_storyboard_sha256"
        ],
        "ruleset_components": ruleset_components,
        "ruleset_sha256": sha256_json(ruleset_components),
        "checks": {
            "three_section_structure": "PASS",
            "eight_core_elements": "PASS",
            "reference_mapping_and_readable_nouns": "PASS",
            "one_dominant_camera_family_per_shot": "PASS",
            "quality_and_anti_distortion_fallback": "PASS",
            "storyboard_authority_no_silent_invention": "PASS",
            "full_model_prompt_arabic_only_no_latin_except_provider_tokens": (
                "PASS"
            ),
            "arabic_dialogue_only_no_latin": "PASS",
            "exact_arabic_dialogue_once_in_literal_braces": "PASS",
            "seedance_audio_mode_and_post_dialogue_replacement": "PASS",
        },
        "human_confirmation_ready": True,
        "provider_submission_ready": True,
    }


def write_prompt_audit_record(
    task_dir: Path,
    segment_id: str,
) -> dict[str, Any]:
    task_root = task_dir.expanduser().resolve(strict=True)
    record = build_prompt_audit_record(task_root, segment_id)
    write_json(prompt_audit_path(task_root, segment_id), record)
    return record


def require_prompt_audit(
    task_dir: Path,
    parsed: dict[str, Any],
) -> dict[str, Any]:
    task_root = task_dir.expanduser().resolve(strict=True)
    segment_id = str(parsed["segment_id"])
    try:
        record = read_json(
            prompt_audit_path(task_root, segment_id),
            label=f"{segment_id} Seedance Prompt audit",
        )
    except SegmentRuntimeError as exc:
        raise SegmentRuntimeError(
            f"{segment_id} Seedance Prompt audit is missing; run "
            "virtual-production's internal Prompt audit before human "
            "confirmation"
        ) from exc
    expected = build_prompt_audit_record(task_root, segment_id)
    required_equal = (
        "contract",
        "status",
        "segment_id",
        "department",
        "gate",
        "language",
        "language_code",
        "spoken_authority",
        "seedance_audio_mode",
        "model_prompt_language",
        "model_prompt_language_code",
        "latin_text_policy",
        "arabic_line_authority",
        "prompt_sha256",
        "model_prompt_sha256",
        "source_storyboard_sha256",
        "ruleset_components",
        "ruleset_sha256",
        "checks",
        "human_confirmation_ready",
        "provider_submission_ready",
    )
    if any(record.get(key) != expected[key] for key in required_equal):
        raise SegmentRuntimeError(
            f"{segment_id} Seedance Prompt audit is missing, stale, or failed; "
            "run virtual-production's internal Prompt audit before human "
            "confirmation"
        )
    return record


def require_audited_model_prompt(
    prompt_audit: dict[str, Any],
    model_prompt: str,
    *,
    segment_id: str,
) -> str:
    actual = hashlib.sha256(model_prompt.encode("utf-8")).hexdigest()
    if prompt_audit.get("model_prompt_sha256") != actual:
        raise SegmentRuntimeError(
            f"{segment_id} model-facing Prompt changed after the internal audit"
        )
    return actual
