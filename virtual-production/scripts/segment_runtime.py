"""Transport repository-authored Seedance prompts and resolve execution plans.

``segment-NNN.md`` is the exact model-facing Prompt. Deterministic transport
authority lives in a private ``segment-NNN.json`` plan beside the Prompt
collection. Code verifies a small, authored Seedance 2.0 reliability contract,
hashes the Prompt, and resolves media. It never authors or repairs creative
Prompt prose.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR_RELATIVE = Path(".pending/virtual-production/seedance-segment-scripts")
PLAN_DIR_RELATIVE = Path(".pending/virtual-production/seedance-segment-plans")
STORYBOARD_RELATIVE = Path("previsualize-cinematography/storyboard.md")
CAPABILITY_PROFILE_RELATIVE = Path("virtual-production/seedance-capability-profile.json")
WHITE_MODEL_RESET_CONTRACT_RELATIVE = Path(
    "virtual-production/assets/white-model-quality-reset.json"
)

SEGMENT_RE = re.compile(r"^segment-([0-9]{3,})$")
SCRIPT_RE = re.compile(r"^segment-([0-9]{3,})\.md$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
TOKEN_RE = re.compile(r"^@(Image|Video|Audio)([1-9][0-9]*)$")
TOKEN_SCAN_RE = re.compile(r"@(Image|Video|Audio)([1-9][0-9]*)")
SHOT_HEADING_RE = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]+)?Shot[ \t]+([1-9][0-9]*)[ \t]*:[ \t]*",
    re.IGNORECASE | re.MULTILINE,
)
PRECISE_TIME_RANGE_RE = re.compile(
    r"\b(?:from\s+)?[0-9]+(?:\.[0-9]+)?\s*(?:-|–|—|to)\s*"
    r"[0-9]+(?:\.[0-9]+)?\s*(?:s|sec(?:ond)?s?)\b",
    re.IGNORECASE,
)

REQUIRED_PLAN_FIELDS = {
    "contract",
    "segment_id",
    "source_storyboard_sha256",
    "scene_ids",
    "target_duration",
    "shot_count",
    "operation",
    "shooting_plan_status",
    "schedule_mode",
    "planned_wave",
    "depends_on_segment_ids",
    "dependency_reason",
    "predecessor_review_required",
    "required_predecessor_evidence",
    "successor_recompile_required",
    "fallback_operation_and_story_cost",
    "seam_class",
    "seam_resynthesis_allowed",
    "seam_story_reason",
    "editorial_intent",
    "reference_video_scope",
    "reference_video_audio",
    "camera_ensemble_color_resynthesis_allowed",
    "continuity",
    "prompt_contract",
    "bindings",
    "dialogue_cues",
    "editable_hold_seconds",
    "final_visible_state",
    "final_sound_state",
}
PROMPT_CONTRACT_FIELDS = {
    "language",
    "operation_instruction_en",
    "global_constraints_en",
    "reference_priority_order",
    "dialogue_delimiter",
    "music_delimiter",
    "sound_effect_delimiter",
    "subtitle_delimiter",
    "background_music_policy",
    "generated_subtitle_policy",
    "avoid_precise_time_ranges",
    "single_dominant_camera_move_per_shot",
}

ROLE_FOR_TOKEN_KIND = {
    "Image": "reference_image",
    "Video": "reference_video",
    "Audio": "reference_audio",
}
ALLOWED_OPERATIONS = {"multimodal_reference", "video_extension", "text_to_video"}
ALLOWED_EVIDENCE = {
    "none",
    "approved_complete_predecessor",
    "approved_provider_last_frame",
}
CONTINUITY_FIELDS = {
    "location_state_chain",
    "relationship",
    "state_source_segment_id",
    "world_binding_ids",
    "temporal_binding_ids",
    "embedded_npc_asset_ids",
    "authorized_independent_performer_asset_ids",
    "character_segment_states",
    "population_lock_en",
}
CHARACTER_SEGMENT_STATE_FIELDS = {
    "character_asset_id",
    "state_source_segment_id",
    "incoming_presence",
    "segment_presence_rule",
    "outgoing_presence",
    "required_visible_shots",
    "allowed_occlusion_en",
    "transition_cause_en",
    "position_and_condition_en",
    "prompt_presence_lock_en",
}
CHARACTER_PRESENCE_STATES = {
    "absent",
    "present_offscreen",
    "occluded",
    "visible",
}
CHARACTER_PRESENCE_RULES = {
    "must_remain_visible",
    "must_remain_present",
    "enter",
    "re_enter",
    "reveal",
    "conceal",
    "exit",
    "remain_absent",
    "reset_with_reason",
}
LOCATION_RELATIONSHIPS = {
    "independent",
    "adjacent_continuation",
    "adjacent_coverage_reset",
    "nonadjacent_revisit",
    "reset_with_reason",
}
ALLOWED_DIALOGUE_DELIVERY = {"seedance", "external_tts"}
BACKGROUND_ONLY_AUDIO_POLICY = (
    "Audio policy: generate synchronized background audio only, preserving the authored "
    "ambience, foley, environmental effects, and instrumental music cues; generate no "
    "spoken dialogue, narration, intelligible words, singing, or humming; retain only "
    "authored nonverbal breaths, cries, and animal sounds as diegetic effects."
)


class SegmentRuntimeError(RuntimeError):
    """Raised when a local natural-language Prompt or private plan is invalid."""


def read_json(path: Path, *, label: str | None = None) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SegmentRuntimeError(f"Missing or invalid {label or 'JSON'}: {path}") from exc
    if not isinstance(value, dict):
        raise SegmentRuntimeError(f"{label or 'JSON'} must contain one object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise SegmentRuntimeError(f"Cannot hash required file: {path}") from exc


def sha256_json(value: Any) -> str:
    """Hash one deterministic runtime object without persisting a derived file."""

    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SegmentRuntimeError(f"{label} must be a non-empty string")
    return value.strip()


def _unique_string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        raise SegmentRuntimeError(f"{label} must be a unique string array")
    return [item.strip() for item in value]


def extension_quality_reset_schedule(
    rows: list[dict[str, Any]], maximum_direct_hops: int
) -> dict[str, dict[str, Any]]:
    """Derive direct-extension depth and deterministic white-model reset points."""

    if (
        isinstance(maximum_direct_hops, bool)
        or not isinstance(maximum_direct_hops, int)
        or maximum_direct_hops < 0
    ):
        raise SegmentRuntimeError(
            "maximum_direct_extension_hops_without_quality_reset must be a "
            "non-negative integer"
        )
    schedule: dict[str, dict[str, Any]] = {}
    direct_hops_after: dict[str, int] = {}
    for row in rows:
        segment_id = _nonempty_string(row.get("segment_id"), "segment_id")
        operation = row.get("operation")
        if operation != "video_extension":
            direct_hops_after[segment_id] = 0
            schedule[segment_id] = {
                "required": False,
                "strategy": "none",
                "source_segment_id": "none",
                "direct_extension_hops_before_current": 0,
                "direct_extension_hops_after_current": 0,
                "maximum_direct_extension_hops_without_quality_reset": maximum_direct_hops,
            }
            continue
        dependencies = row.get("depends_on_segment_ids")
        if not isinstance(dependencies, list) or len(dependencies) != 1:
            raise SegmentRuntimeError(
                f"{segment_id} video extension requires exactly one predecessor"
            )
        source_segment_id = str(dependencies[0])
        if source_segment_id not in direct_hops_after:
            raise SegmentRuntimeError(
                f"{segment_id} extension predecessor must be an earlier Segment"
            )
        inherited_hops = direct_hops_after[source_segment_id]
        reset_required = inherited_hops >= maximum_direct_hops
        current_hops = 0 if reset_required else inherited_hops + 1
        direct_hops_after[segment_id] = current_hops
        schedule[segment_id] = {
            "required": reset_required,
            "strategy": "white_model_video_edit" if reset_required else "none",
            "source_segment_id": source_segment_id,
            "direct_extension_hops_before_current": inherited_hops,
            "direct_extension_hops_after_current": current_hops,
            "maximum_direct_extension_hops_without_quality_reset": maximum_direct_hops,
        }
    return schedule


def _validate_single_predecessor_inheritance_hop(
    rows: list[dict[str, Any]],
) -> None:
    """Require a reference-free strong camera reset after one inherited boundary."""

    inherited_evidence = {
        "approved_complete_predecessor",
        "approved_provider_last_frame",
    }
    for predecessor, successor in zip(rows, rows[1:]):
        shared_scene = bool(
            set(predecessor.get("scene_ids", []))
            & set(successor.get("scene_ids", []))
        )
        if not shared_scene:
            continue
        predecessor_inherited = (
            predecessor.get("required_predecessor_evidence") in inherited_evidence
        )
        successor_inherited = (
            successor.get("required_predecessor_evidence") in inherited_evidence
        )
        if predecessor_inherited and successor_inherited:
            raise SegmentRuntimeError(
                f"{successor.get('segment_id')} attempts a second consecutive "
                "predecessor-media inheritance; use a strong coverage reset"
            )
        if predecessor.get("operation") == "video_extension" and successor.get(
            "operation"
        ) == "video_extension":
            raise SegmentRuntimeError(
                f"{successor.get('segment_id')} cannot extend an extension; only "
                "one video extension is allowed before a strong coverage reset"
            )


def _target_duration(value: Any, segment_id: str) -> int:
    if isinstance(value, bool):
        raise SegmentRuntimeError(f"{segment_id} target duration must be 4-15 seconds")
    if isinstance(value, int):
        duration = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+s", value.strip()):
        duration = int(value.strip()[:-1])
    else:
        raise SegmentRuntimeError(f"{segment_id} target duration must be an integer or Ns")
    if not 4 <= duration <= 15:
        raise SegmentRuntimeError(f"{segment_id} target duration must be 4-15 seconds")
    return duration


def _private_plan_path(path: Path) -> Path:
    if path.parent.name == "seedance-segment-scripts":
        return path.parent.parent / "seedance-segment-plans" / f"{path.stem}.json"
    return path.with_suffix(".plan.json")


def _validate_prompt(text: str, path: Path, plan: dict[str, Any]) -> str:
    """Validate the authored reliability layer without templating creative prose."""

    prompt = text.strip()
    if not prompt:
        raise SegmentRuntimeError(f"{path.name} Seedance Prompt must not be empty")
    contract = plan["prompt_contract"]

    shot_matches = list(SHOT_HEADING_RE.finditer(prompt))
    shot_sections: dict[int, str] = {}
    for index, match in enumerate(shot_matches):
        shot_number = int(match.group(1))
        if shot_number in shot_sections:
            raise SegmentRuntimeError(
                f"{path.name} repeats Shot {shot_number}, so dialogue ownership is ambiguous"
            )
        end = shot_matches[index + 1].start() if index + 1 < len(shot_matches) else len(prompt)
        shot_sections[shot_number] = prompt[match.end() : end].strip()

    prompt_tokens = sorted(
        {match.group(0) for match in TOKEN_SCAN_RE.finditer(prompt)},
        key=token_sort_key,
    )
    plan_tokens = sorted(
        {item["provider_token"] for item in plan["bindings"]},
        key=token_sort_key,
    )
    if prompt_tokens != plan_tokens:
        raise SegmentRuntimeError(
            f"{path.name} provider tokens differ from the private plan"
        )
    pre_shot = prompt[: shot_matches[0].start()] if shot_matches else prompt
    if any(token not in pre_shot for token in plan_tokens):
        raise SegmentRuntimeError(
            f"{path.name} must introduce every provider token before its first Shot section"
        )

    required_preamble = [contract["operation_instruction_en"]]
    required_preamble.extend(item["prompt_declaration_en"] for item in plan["bindings"])
    required_preamble.append(plan["continuity"]["population_lock_en"])
    required_preamble.extend(
        item["prompt_presence_lock_en"]
        for item in plan["continuity"]["character_segment_states"]
    )
    required_preamble.append(contract["global_constraints_en"])
    positions: list[int] = []
    for sentence in required_preamble:
        if prompt.count(sentence) != 1 or sentence not in pre_shot:
            raise SegmentRuntimeError(
                f"{path.name} must place each exact Prompt-contract sentence once "
                "before its first Shot"
            )
        positions.append(pre_shot.index(sentence))
    if positions != sorted(positions):
        raise SegmentRuntimeError(
            f"{path.name} Prompt-contract preamble is not in authored priority order"
        )

    for binding in plan["bindings"]:
        declaration = binding["prompt_declaration_en"]
        required_terms = [
            binding["provider_token"],
            binding["readable_subject"],
            *binding["stable_identity_traits_en"],
        ]
        if any(term.lower() not in declaration.lower() for term in required_terms):
            raise SegmentRuntimeError(
                f"{path.name} binding {binding['binding_id']} declaration omits its "
                "token, readable subject, or stable traits"
            )

    if PRECISE_TIME_RANGE_RE.search(prompt):
        raise SegmentRuntimeError(
            f"{path.name} must describe event order instead of precise provider time ranges"
        )

    if prompt.count("<") != prompt.count(">") or re.search(r"<>|<\s+>", prompt):
        raise SegmentRuntimeError(
            f"{path.name} sound effects must use balanced non-empty <...> notation"
        )
    if prompt.count("【") != prompt.count("】"):
        raise SegmentRuntimeError(
            f"{path.name} generated subtitles must use balanced 【...】 notation"
        )
    if contract["generated_subtitle_policy"] == "forbidden" and re.search(
        r"【[^】]+】", prompt
    ):
        raise SegmentRuntimeError(
            f"{path.name} generated subtitles are forbidden; captions belong to postproduction"
        )
    music_markers = re.findall(r"\([^()]+\)", prompt)
    if contract["background_music_policy"] == "forbidden" and music_markers:
        raise SegmentRuntimeError(
            f"{path.name} background music is forbidden; remove (...) music cues"
        )
    if contract["background_music_policy"] == "parentheses_only" and not music_markers:
        raise SegmentRuntimeError(
            f"{path.name} default main flow requires at least one (...) background-music cue"
        )
    brace_groups = re.findall(r"\{([^{}]+)\}", prompt)
    if prompt.count("{") != prompt.count("}"):
        raise SegmentRuntimeError(
            f"{path.name} dialogue must use balanced {{...}} notation"
        )
    expected_dialogue = (
        [str(cue.get("exact_text") or "").strip() for cue in plan["dialogue_cues"]]
        if str(plan.get("dialogue_delivery") or "seedance") == "seedance"
        else []
    )
    if sorted(brace_groups) != sorted(expected_dialogue):
        raise SegmentRuntimeError(
            f"{path.name} curly-brace groups must exactly equal the authored dialogue cues"
        )

    operation_text = contract["operation_instruction_en"].lower()
    if plan["seam_class"] == "strong_coverage_reset":
        has_tight_opening = bool(
            re.search(
                r"\b(?:extreme[-_ ]+close[-_ ]?up|"
                r"medium[-_ ]+close[-_ ]?up|close[-_ ]?up|ecu|cu|mcu)\b",
                operation_text,
            )
        )
        has_no_predecessor_media = bool(
            re.search(
                r"(?:\bno\b|\bwithout\b|\bdo\s+not\b).{0,64}"
                r"\bpredecessor\b.{0,48}"
                r"\b(?:media|frame|image|video)\b",
                operation_text,
            )
        )
        has_camera_break = all(
            term in operation_text
            for term in ("angle", "viewpoint", "composition")
        )
        if not (
            has_tight_opening
            and has_no_predecessor_media
            and has_camera_break
        ):
            raise SegmentRuntimeError(
                f"{path.name} strong coverage-reset instruction must state no "
                "predecessor media, an ECU/CU/MCU opening, and a new angle, "
                "viewpoint, and composition"
            )
    if plan["operation"] == "video_extension":
        if not re.search(r"\b(?:extend|continue)\b", operation_text):
            raise SegmentRuntimeError(
                f"{path.name} video extension must directly instruct Seedance to extend/continue"
            )
        extension_tokens = [token for token in plan_tokens if token.startswith("@Video")]
        if not extension_tokens or any(
            token.lower() not in operation_text for token in extension_tokens
        ):
            raise SegmentRuntimeError(
                f"{path.name} video extension instruction must directly name its @Video token"
            )
        for token in extension_tokens:
            if re.search(
                rf"(?:reference\s+{re.escape(token.lower())}|"
                rf"{re.escape(token.lower())}\s+as\s+(?:a\s+)?reference)",
                prompt.lower(),
            ):
                raise SegmentRuntimeError(
                    f"{path.name} must name {token} as the video to extend, not a reference video"
                )
    elif plan["operation"] == "multimodal_reference" and "reference" not in operation_text:
        raise SegmentRuntimeError(
            f"{path.name} multimodal operation instruction must state reference use"
        )

    dialogue_delivery = str(plan.get("dialogue_delivery") or "seedance")
    if dialogue_delivery not in ALLOWED_DIALOGUE_DELIVERY:
        raise SegmentRuntimeError(
            f"{path.name} has unsupported dialogue_delivery {dialogue_delivery!r}"
        )
    if dialogue_delivery == "external_tts":
        if prompt.count(BACKGROUND_ONLY_AUDIO_POLICY) != 1:
            raise SegmentRuntimeError(
                f"{path.name} must contain the background-only audio policy exactly once"
            )
    for cue in plan["dialogue_cues"]:
        if not isinstance(cue, dict):
            raise SegmentRuntimeError(f"{path.name} has an invalid dialogue cue")
        line_id = _nonempty_string(cue.get("line_id"), "dialogue line_id")
        speaker = _nonempty_string(cue.get("speaker_name"), "dialogue speaker_name")
        exact_text = _nonempty_string(cue.get("exact_text"), "dialogue exact_text")
        shot_number = cue.get("shot_number")
        if not isinstance(shot_number, int) or shot_number not in shot_sections:
            raise SegmentRuntimeError(
                f"{path.name} dialogue cue has no matching Shot section"
            )
        section = shot_sections[shot_number]
        if dialogue_delivery == "seedance":
            if f"{{{exact_text}}}" not in section or speaker not in section:
                raise SegmentRuntimeError(
                    f"{path.name} must place exact curly-brace dialogue beside its readable speaker "
                    f"inside Shot {shot_number}"
                )
        else:
            marker = f"external TTS cue {line_id}"
            if (
                marker not in section
                or speaker not in section
                or not re.search(r"\b(?:mouth|lip|lips)\b", section, re.IGNORECASE)
            ):
                raise SegmentRuntimeError(
                    f"{path.name} must place {marker} beside {speaker} and an explicit "
                    f"silent mouth-performance instruction inside Shot {shot_number}"
                )
            if exact_text in prompt or f"{{{exact_text}}}" in prompt:
                raise SegmentRuntimeError(
                    f"{path.name} external-TTS dialogue text must live only in the dialogue file"
                )
    return prompt


def _parse_prompt_contract(
    value: Any, *, path: Path, bindings: list[dict[str, Any]]
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != PROMPT_CONTRACT_FIELDS:
        raise SegmentRuntimeError(
            f"{path.name} prompt_contract must use the exact current fields"
        )
    if value["language"] != "English":
        raise SegmentRuntimeError(f"{path.name} provider Prompt language must be English")
    operation = _nonempty_string(
        value["operation_instruction_en"], f"{path.name} operation_instruction_en"
    )
    constraints = _nonempty_string(
        value["global_constraints_en"], f"{path.name} global_constraints_en"
    )
    priorities = _unique_string_list(
        value["reference_priority_order"],
        f"{path.name} reference_priority_order",
        allow_empty=False,
    )
    binding_ids = [item["binding_id"] for item in bindings]
    if priorities != binding_ids:
        raise SegmentRuntimeError(
            f"{path.name} reference priority must list every binding in authored order"
        )
    if value["dialogue_delimiter"] != "curly_braces":
        raise SegmentRuntimeError(
            f"{path.name} dialogue_delimiter must be curly_braces"
        )
    expected_delimiters = {
        "music_delimiter": "parentheses",
        "sound_effect_delimiter": "angle_brackets",
        "subtitle_delimiter": "fullwidth_square_brackets",
    }
    if any(value[field] != expected for field, expected in expected_delimiters.items()):
        raise SegmentRuntimeError(
            f"{path.name} must use the Seedance music/effect/subtitle delimiters"
        )
    if value["background_music_policy"] not in {"forbidden", "parentheses_only"}:
        raise SegmentRuntimeError(f"{path.name} has invalid background_music_policy")
    if value["generated_subtitle_policy"] != "forbidden":
        raise SegmentRuntimeError(
            f"{path.name} generated subtitles must remain forbidden for postproduction captions"
        )
    if (
        value["avoid_precise_time_ranges"] is not True
        or value["single_dominant_camera_move_per_shot"] is not True
    ):
        raise SegmentRuntimeError(
            f"{path.name} must enable Seedance timing and camera reliability locks"
        )
    lowered = constraints.lower()
    prohibited_groups = [
        ("subtitle", "text"),
        ("logo",),
        ("watermark",),
        ("duplicate", "twin"),
    ]
    if value["background_music_policy"] == "forbidden":
        prohibited_groups.append(("background music", "music"))
    prohibition = r"(?:\bno\b|\bwithout\b|\bdo\s+not\b|\bnever\b|\bforbid\w*|\bprohibit\w*|\bexclude\w*|\bavoid\b)"
    if any(
        not any(
            re.search(rf"{prohibition}[^.;:]{{0,100}}\b{term}\w*\b", lowered)
            for term in group
        )
        for group in prohibited_groups
    ) or any(term not in lowered for term in ("identity", "anatomy", "style", "continuity")):
        raise SegmentRuntimeError(
            f"{path.name} global constraints must forbid text/subtitles, logos, "
            "watermarks, duplicate/twin subjects, and disallowed music while locking identity, "
            "anatomy, style, and continuity"
        )
    return {
        "language": "English",
        "operation_instruction_en": operation,
        "global_constraints_en": constraints,
        "reference_priority_order": priorities,
        "dialogue_delimiter": "curly_braces",
        "music_delimiter": "parentheses",
        "sound_effect_delimiter": "angle_brackets",
        "subtitle_delimiter": "fullwidth_square_brackets",
        "background_music_policy": value["background_music_policy"],
        "generated_subtitle_policy": "forbidden",
        "avoid_precise_time_ranges": True,
        "single_dominant_camera_move_per_shot": True,
    }


def _parse_bindings(value: Any, path: Path, shot_count: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SegmentRuntimeError(f"{path.name} private bindings must be an array")
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, dict):
            raise SegmentRuntimeError(f"{path.name} has an invalid private binding")
        binding_id = raw.get("binding_id")
        token = raw.get("provider_token")
        role = raw.get("provider_role")
        namespace = raw.get("asset_namespace")
        subject = raw.get("readable_subject")
        purpose = raw.get("purpose")
        scope = raw.get("shot_scope")
        forbidden = raw.get("forbidden_inheritance")
        declaration = raw.get("prompt_declaration_en")
        traits = raw.get("stable_identity_traits_en")
        match = TOKEN_RE.fullmatch(str(token or ""))
        if (
            binding_id != f"B{index:02d}"
            or binding_id in seen_ids
            or match is None
            or role != ROLE_FOR_TOKEN_KIND[match.group(1)]
            or not isinstance(scope, list)
            or not scope
            or any(not isinstance(item, int) or not 1 <= item <= shot_count for item in scope)
        ):
            raise SegmentRuntimeError(f"{path.name} private binding {index} is invalid")
        for label, item in (
            ("asset_namespace", namespace),
            ("readable_subject", subject),
            ("purpose", purpose),
            ("forbidden_inheritance", forbidden),
            ("prompt_declaration_en", declaration),
        ):
            _nonempty_string(item, f"{path.name} binding {index} {label}")
        if subject == namespace:
            raise SegmentRuntimeError(
                f"{path.name} binding {index} uses internal asset ID {namespace!r} "
                "as its model-facing subject name"
            )
        parsed_traits = _unique_string_list(
            traits, f"{path.name} binding {index} stable_identity_traits_en"
        )
        if (
            role == "reference_image"
            and namespace != "continuity"
            and not 2 <= len(parsed_traits) <= 3
        ):
            raise SegmentRuntimeError(
                f"{path.name} catalog image binding {index} needs two or three stable traits"
            )
        seen_ids.add(binding_id)
        result.append(
            {
                "binding_id": binding_id,
                "provider_token": token,
                "provider_role": role,
                "asset_namespace": namespace,
                "readable_subject": subject,
                "purpose": purpose,
                "shot_scope": [f"Shot {item}" for item in scope],
                "element": f"{namespace}.{purpose}",
                "authority": purpose,
                "forbidden": forbidden,
                "prompt_declaration_en": declaration,
                "stable_identity_traits_en": parsed_traits,
            }
        )
    _validate_token_sequence(result, path)
    return result


def _validate_token_sequence(bindings: list[dict[str, Any]], path: Path) -> None:
    tokens = list(dict.fromkeys(item["provider_token"] for item in bindings))
    for kind in ("Image", "Video", "Audio"):
        numbers = sorted(
            int(match.group(2))
            for token in tokens
            if (match := TOKEN_RE.fullmatch(token)) and match.group(1) == kind
        )
        if numbers != list(range(1, len(numbers) + 1)):
            raise SegmentRuntimeError(f"{path.name} @{kind} tokens must be contiguous from 1")


def _validate_shooting_plan(plan: dict[str, Any], segment_id: str) -> None:
    if plan["operation"] not in ALLOWED_OPERATIONS:
        raise SegmentRuntimeError(f"{segment_id} has unsupported operation")
    evidence = plan["required_predecessor_evidence"]
    if evidence not in ALLOWED_EVIDENCE:
        raise SegmentRuntimeError(f"{segment_id} has unsupported predecessor evidence")
    dependencies = _unique_string_list(plan["depends_on_segment_ids"], f"{segment_id} dependencies")
    if any(not SEGMENT_RE.fullmatch(item) for item in dependencies):
        raise SegmentRuntimeError(f"{segment_id} has an invalid dependency")
    schedule = plan["schedule_mode"]
    strong_reset = (
        plan["operation"] == "multimodal_reference"
        and evidence == "none"
        and plan["seam_class"] == "strong_coverage_reset"
        and plan["reference_video_scope"] == "none"
        and plan["reference_video_audio"] == "none"
        and plan["camera_ensemble_color_resynthesis_allowed"] is True
    )
    if schedule == "parallel":
        if dependencies or plan["planned_wave"] != 0 or plan["predecessor_review_required"] is not False or evidence != "none" or plan["shooting_plan_status"] != "planned":
            raise SegmentRuntimeError(f"{segment_id} parallel plan is contradictory")
    elif schedule == "serial_after_predecessor_review":
        if (
            len(dependencies) != 1
            or not isinstance(plan["planned_wave"], int)
            or plan["planned_wave"] < 1
            or plan["predecessor_review_required"] is not True
            or plan["successor_recompile_required"] is not True
            or plan["shooting_plan_status"] != "observed_adapted"
            or (evidence == "none" and not strong_reset)
        ):
            raise SegmentRuntimeError(f"{segment_id} serial plan is contradictory")
    else:
        raise SegmentRuntimeError(f"{segment_id} has unsupported schedule mode")
    if plan["operation"] == "video_extension" and not (
        evidence == "approved_complete_predecessor"
        and plan["reference_video_scope"] == "full_predecessor_for_extension"
        and plan["reference_video_audio"] == "preserved_for_extension"
        and plan["seam_class"] == "continuous_extension"
    ):
        raise SegmentRuntimeError(f"{segment_id} video-extension plan is contradictory")
    if evidence == "approved_provider_last_frame" and not (
        plan["operation"] == "multimodal_reference"
        and schedule == "serial_after_predecessor_review"
        and plan["reference_video_scope"] == "none"
        and plan["reference_video_audio"] == "none"
    ):
        raise SegmentRuntimeError(f"{segment_id} soft last-frame plan is contradictory")
    if plan["seam_class"] == "strong_coverage_reset" and not (
        strong_reset and schedule == "serial_after_predecessor_review"
    ):
        raise SegmentRuntimeError(
            f"{segment_id} strong coverage reset plan is contradictory"
        )


def _parse_character_segment_states(
    value: Any,
    *,
    segment_id: str,
    shot_count: int,
    authorized_independent_performer_asset_ids: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SegmentRuntimeError(
            f"{segment_id} character_segment_states must be an array"
        )
    result: list[dict[str, Any]] = []
    seen_characters: set[str] = set()
    all_shots = list(range(1, shot_count + 1))
    visible_event_rules = {"enter", "re_enter", "reveal", "exit"}
    no_transition_rules = {
        "must_remain_visible",
        "must_remain_present",
        "remain_absent",
    }
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, dict) or set(raw) != CHARACTER_SEGMENT_STATE_FIELDS:
            raise SegmentRuntimeError(
                f"{segment_id} character state {index} must use the exact current fields"
            )
        character_id = _nonempty_string(
            raw["character_asset_id"],
            f"{segment_id} character state {index} character_asset_id",
        )
        if character_id in seen_characters:
            raise SegmentRuntimeError(
                f"{segment_id} repeats character state for {character_id}"
            )
        seen_characters.add(character_id)
        source = raw["state_source_segment_id"]
        if source != "none" and (
            not isinstance(source, str) or not SEGMENT_RE.fullmatch(source)
        ):
            raise SegmentRuntimeError(
                f"{segment_id} character {character_id} has invalid state source"
            )
        incoming = raw["incoming_presence"]
        outgoing = raw["outgoing_presence"]
        rule = raw["segment_presence_rule"]
        if (
            incoming not in CHARACTER_PRESENCE_STATES
            or outgoing not in CHARACTER_PRESENCE_STATES
            or rule not in CHARACTER_PRESENCE_RULES
        ):
            raise SegmentRuntimeError(
                f"{segment_id} character {character_id} has an invalid presence state"
            )
        shots = raw["required_visible_shots"]
        if (
            not isinstance(shots, list)
            or any(
                isinstance(item, bool)
                or not isinstance(item, int)
                or item not in all_shots
                for item in shots
            )
            or len(shots) != len(set(shots))
            or shots != sorted(shots)
        ):
            raise SegmentRuntimeError(
                f"{segment_id} character {character_id} has invalid visible shots"
            )
        allowed_occlusion = _nonempty_string(
            raw["allowed_occlusion_en"],
            f"{segment_id} character {character_id} allowed_occlusion_en",
        )
        cause = _nonempty_string(
            raw["transition_cause_en"],
            f"{segment_id} character {character_id} transition_cause_en",
        )
        position = _nonempty_string(
            raw["position_and_condition_en"],
            f"{segment_id} character {character_id} position_and_condition_en",
        )
        prompt_lock = _nonempty_string(
            raw["prompt_presence_lock_en"],
            f"{segment_id} character {character_id} prompt_presence_lock_en",
        )

        valid_transition = {
            "must_remain_visible": incoming == outgoing == "visible",
            "must_remain_present": (
                incoming == outgoing and incoming != "absent"
            ),
            "enter": incoming == "absent" and outgoing == "visible",
            "re_enter": incoming == "absent" and outgoing == "visible",
            "reveal": (
                incoming in {"present_offscreen", "occluded"}
                and outgoing == "visible"
            ),
            "conceal": (
                incoming == "visible"
                and outgoing in {"present_offscreen", "occluded"}
            ),
            "exit": incoming != "absent" and outgoing == "absent",
            "remain_absent": incoming == outgoing == "absent",
            "reset_with_reason": True,
        }[rule]
        if not valid_transition:
            raise SegmentRuntimeError(
                f"{segment_id} character {character_id} has an illegal {rule} transition"
            )
        if rule == "must_remain_visible" and shots != all_shots:
            raise SegmentRuntimeError(
                f"{segment_id} character {character_id} must be visible in every Shot"
            )
        if rule == "remain_absent" and shots:
            raise SegmentRuntimeError(
                f"{segment_id} absent character {character_id} cannot require visible Shots"
            )
        if rule in visible_event_rules and not shots:
            raise SegmentRuntimeError(
                f"{segment_id} character {character_id} appearance event needs a visible Shot"
            )
        if rule in no_transition_rules and cause != "none":
            raise SegmentRuntimeError(
                f"{segment_id} character {character_id} has an unexplained transition cause"
            )
        if rule not in no_transition_rules and cause == "none":
            raise SegmentRuntimeError(
                f"{segment_id} character {character_id} transition requires an authored cause"
            )
        if rule == "must_remain_visible" and allowed_occlusion != "none":
            raise SegmentRuntimeError(
                f"{segment_id} character {character_id} cannot be occluded while locked visible"
            )
        if rule == "remain_absent":
            if character_id in authorized_independent_performer_asset_ids:
                raise SegmentRuntimeError(
                    f"{segment_id} absent character {character_id} cannot be authorized to appear"
                )
        elif character_id not in authorized_independent_performer_asset_ids:
            raise SegmentRuntimeError(
                f"{segment_id} present character {character_id} is not in Authorized Population"
            )
        result.append(
            {
                "character_asset_id": character_id,
                "state_source_segment_id": source,
                "incoming_presence": incoming,
                "segment_presence_rule": rule,
                "outgoing_presence": outgoing,
                "required_visible_shots": shots,
                "allowed_occlusion_en": allowed_occlusion,
                "transition_cause_en": cause,
                "position_and_condition_en": position,
                "prompt_presence_lock_en": prompt_lock,
            }
        )
    authorized = set(authorized_independent_performer_asset_ids)
    tracked_present = {
        item["character_asset_id"]
        for item in result
        if item["segment_presence_rule"] != "remain_absent"
    }
    if tracked_present != authorized:
        raise SegmentRuntimeError(
            f"{segment_id} Character Segment states must exactly cover Authorized "
            f"Population performers; missing={sorted(authorized - tracked_present)}, "
            f"extra={sorted(tracked_present - authorized)}"
        )
    prompt_locks = [item["prompt_presence_lock_en"] for item in result]
    if len(prompt_locks) != len(set(prompt_locks)):
        raise SegmentRuntimeError(
            f"{segment_id} character presence locks must be unique"
        )
    return result


def _validate_continuity_plan(
    value: Any,
    *,
    segment_id: str,
    bindings: list[dict[str, Any]],
    shot_count: int,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != CONTINUITY_FIELDS:
        raise SegmentRuntimeError(
            f"{segment_id} continuity must use the exact current fields"
        )
    chain = _nonempty_string(
        value["location_state_chain"], f"{segment_id} location_state_chain"
    )
    relationship = value["relationship"]
    if relationship not in LOCATION_RELATIONSHIPS:
        raise SegmentRuntimeError(f"{segment_id} has invalid location relationship")
    source = value["state_source_segment_id"]
    if source != "none" and (
        not isinstance(source, str)
        or not SEGMENT_RE.fullmatch(source)
        or source == segment_id
    ):
        raise SegmentRuntimeError(f"{segment_id} has invalid location state source")
    world_ids = _unique_string_list(
        value["world_binding_ids"], f"{segment_id} world_binding_ids", allow_empty=False
    )
    temporal_ids = _unique_string_list(
        value["temporal_binding_ids"], f"{segment_id} temporal_binding_ids"
    )
    if set(world_ids) & set(temporal_ids):
        raise SegmentRuntimeError(
            f"{segment_id} world and temporal binding responsibilities overlap"
        )
    binding_ids = {item["binding_id"] for item in bindings}
    unknown = (set(world_ids) | set(temporal_ids)) - binding_ids
    if unknown:
        raise SegmentRuntimeError(
            f"{segment_id} continuity names unknown bindings: {sorted(unknown)}"
        )
    embedded = _unique_string_list(
        value["embedded_npc_asset_ids"],
        f"{segment_id} embedded_npc_asset_ids",
    )
    independent = _unique_string_list(
        value["authorized_independent_performer_asset_ids"],
        f"{segment_id} authorized_independent_performer_asset_ids",
    )
    if set(embedded) & set(independent):
        raise SegmentRuntimeError(
            f"{segment_id} embeds and independently directs the same role"
        )
    population_lock = _nonempty_string(
        value["population_lock_en"], f"{segment_id} population_lock_en"
    )
    character_states = _parse_character_segment_states(
        value["character_segment_states"],
        segment_id=segment_id,
        shot_count=shot_count,
        authorized_independent_performer_asset_ids=independent,
    )
    if relationship in {"independent", "reset_with_reason"}:
        if source != "none" or temporal_ids:
            raise SegmentRuntimeError(
                f"{segment_id} independent/reset state cannot inherit temporal evidence"
            )
    elif relationship == "adjacent_coverage_reset":
        if source == "none" or temporal_ids:
            raise SegmentRuntimeError(
                f"{segment_id} adjacent coverage reset requires a state source "
                "but no predecessor-media binding"
            )
    elif source == "none" or not temporal_ids:
        raise SegmentRuntimeError(
            f"{segment_id} continuation/revisit requires a state source and temporal evidence"
        )
    return {
        "location_state_chain": chain,
        "relationship": relationship,
        "state_source_segment_id": source,
        "world_binding_ids": world_ids,
        "temporal_binding_ids": temporal_ids,
        "embedded_npc_asset_ids": embedded,
        "authorized_independent_performer_asset_ids": independent,
        "character_segment_states": character_states,
        "population_lock_en": population_lock,
    }


def parse_segment_script(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError) as exc:
        raise SegmentRuntimeError(f"Unreadable Seedance Prompt: {path}") from exc
    filename_match = SCRIPT_RE.fullmatch(path.name)
    if filename_match is None:
        raise SegmentRuntimeError(f"Invalid Seedance Prompt filename: {path.name}")
    segment_id = f"segment-{int(filename_match.group(1)):03d}"
    plan_path = _private_plan_path(path)
    plan = read_json(plan_path, label="private Seedance Segment plan")
    missing = sorted(REQUIRED_PLAN_FIELDS - set(plan))
    if missing:
        raise SegmentRuntimeError(f"{plan_path.name} is missing: {', '.join(missing)}")
    if plan.get("contract") != "seedance-natural-language-plan-v1" or plan.get("segment_id") != segment_id:
        raise SegmentRuntimeError(f"{plan_path.name} has invalid Segment identity")
    if not HASH_RE.fullmatch(str(plan.get("source_storyboard_sha256") or "")):
        raise SegmentRuntimeError(f"{plan_path.name} has invalid Storyboard hash")
    _unique_string_list(plan["scene_ids"], f"{segment_id} scene_ids", allow_empty=False)
    _validate_shooting_plan(plan, segment_id)
    duration = _target_duration(plan["target_duration"], segment_id)
    if isinstance(plan["shot_count"], bool) or not isinstance(plan["shot_count"], int) or plan["shot_count"] < 1:
        raise SegmentRuntimeError(f"{plan_path.name} shot_count must be positive")
    bindings = _parse_bindings(plan["bindings"], plan_path, plan["shot_count"])
    prompt_contract = _parse_prompt_contract(
        plan["prompt_contract"], path=plan_path, bindings=bindings
    )
    continuity = _validate_continuity_plan(
        plan["continuity"],
        segment_id=segment_id,
        bindings=bindings,
        shot_count=plan["shot_count"],
    )
    dialogue_delivery = str(plan.get("dialogue_delivery") or "seedance")
    if dialogue_delivery not in ALLOWED_DIALOGUE_DELIVERY:
        raise SegmentRuntimeError(
            f"{plan_path.name} has unsupported dialogue_delivery {dialogue_delivery!r}"
        )
    normalized_plan = {
        **plan,
        "dialogue_delivery": dialogue_delivery,
        "bindings": bindings,
        "prompt_contract": prompt_contract,
        "continuity": continuity,
    }
    prompt = _validate_prompt(text, path, normalized_plan)
    return {
        "segment_id": segment_id,
        "number": int(filename_match.group(1)),
        "path": path,
        "plan_path": plan_path,
        "text": text,
        "script_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "private_plan_sha256": sha256_file(plan_path),
        "metadata": normalized_plan,
        "duration": duration,
        "prompt": prompt,
        "bindings": bindings,
    }


def token_sort_key(token: str) -> tuple[int, int]:
    match = TOKEN_RE.fullmatch(token)
    if not match:
        raise SegmentRuntimeError(f"Invalid provider token: {token}")
    return ({"Image": 0, "Video": 1, "Audio": 2}[match.group(1)], int(match.group(2)))


def _asset_namespace(bindings: list[dict[str, Any]], token: str) -> str:
    namespaces = {item["asset_namespace"] for item in bindings if item["provider_token"] == token}
    if len(namespaces) != 1:
        raise SegmentRuntimeError(f"{token} must resolve to one private asset namespace")
    return next(iter(namespaces))


def _require_http_uri(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise SegmentRuntimeError(f"{label} has no concrete HTTP(S) URI")
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise SegmentRuntimeError(f"{label} has no concrete HTTP(S) URI")
    return value


def _resolve_roster_visual(namespace: str, assets: dict[str, Any]) -> tuple[str, str, str] | None:
    if "--" not in namespace:
        return None
    roster_id, member_type_id = namespace.split("--", 1)
    roster = assets.get(roster_id)
    if not isinstance(roster, dict) or roster.get("type") != "ensemble_roster":
        return None
    matches = [item for item in roster.get("members", []) if isinstance(item, dict) and item.get("member_type_id") == member_type_id]
    if len(matches) != 1:
        raise SegmentRuntimeError(f"Ambiguous ensemble asset namespace: {namespace}")
    media = matches[0].get("roster_asset")
    uri = media.get("uri") if isinstance(media, dict) else None
    return namespace, "ensemble_roster_member", _require_http_uri(uri, namespace)


def resolve_catalog_media(*, namespace: str, provider_role: str, catalog: dict[str, Any]) -> dict[str, Any]:
    assets = catalog.get("assets") if isinstance(catalog, dict) else None
    if not isinstance(assets, dict):
        raise SegmentRuntimeError("Asset catalog has no assets object")
    if provider_role == "reference_image":
        roster = _resolve_roster_visual(namespace, assets)
        if roster is not None:
            asset_id, asset_type, uri = roster
            return {"asset_id": asset_id, "asset_type": asset_type, "uri": uri}
        asset = assets.get(namespace)
        if not isinstance(asset, dict) or asset.get("type") in {"sound", "ensemble_roster"}:
            raise SegmentRuntimeError(f"Image token cannot resolve asset {namespace!r}")
        visual = asset.get("visual")
        uri = visual.get("uri") if isinstance(visual, dict) else None
        return {"asset_id": namespace, "asset_type": str(asset.get("type")), "uri": _require_http_uri(uri, namespace)}
    if provider_role == "reference_audio":
        asset = assets.get(namespace)
        if not isinstance(asset, dict):
            raise SegmentRuntimeError(f"Audio token cannot resolve asset {namespace!r}")
        if asset.get("type") == "character":
            voice = asset.get("voice")
            reference = voice.get("reference") if isinstance(voice, dict) else None
            uri = reference.get("uri") if isinstance(reference, dict) else None
            asset_type = "character_voice"
        elif asset.get("type") == "sound":
            audio = asset.get("audio")
            uri = audio.get("uri") if isinstance(audio, dict) else None
            asset_type = "sound"
        else:
            raise SegmentRuntimeError(f"Audio token {namespace!r} is not a voice/sound asset")
        return {"asset_id": namespace, "asset_type": asset_type, "uri": _require_http_uri(uri, namespace)}
    raise SegmentRuntimeError(f"Catalog cannot resolve provider role {provider_role}")


def _source_attempt(task_dir: Path, source_segment_id: str) -> str:
    source_root = task_dir / ".pending/virtual-production/generation-segments" / source_segment_id
    record = read_json(source_root / "production-record.json", label="predecessor production record")
    attempt_id = record.get("provider_attempt_id")
    source_script = task_dir / SCRIPT_DIR_RELATIVE / f"{source_segment_id}.md"
    source_plan = load_execution_plan(task_dir, source_segment_id)
    if (
        record.get("status") != "GENERATED"
        or record.get("segment_id") != source_segment_id
        or not isinstance(attempt_id, str)
        or record.get("segment_prompt_sha256") != sha256_file(source_script)
        or record.get("seedance_execution_plan_sha256")
        != sha256_json(source_plan)
        or not (source_root / "video.mp4").is_file()
        or not (source_root / "last-frame.png").is_file()
    ):
        raise SegmentRuntimeError(f"Dependent Prompt requires the current generated attempt for {source_segment_id}")
    return attempt_id


def _runtime_binding(
    *,
    token: str,
    role: str,
    namespace: str,
    metadata: dict[str, Any],
    task_dir: Path,
    quality_reset_required: bool = False,
) -> dict[str, Any]:
    dependencies = metadata["depends_on_segment_ids"]
    if len(dependencies) != 1:
        raise SegmentRuntimeError(f"{token} continuity media requires one predecessor")
    source_segment_id = dependencies[0]
    attempt_id = _source_attempt(task_dir, source_segment_id)
    evidence = metadata["required_predecessor_evidence"]
    if role == "reference_video" and evidence == "approved_complete_predecessor":
        source_kind = (
            "white_model_predecessor_video"
            if quality_reset_required
            else "complete_predecessor_video"
        )
        audio_policy = "preserved"
    elif role == "reference_image" and evidence == "approved_provider_last_frame":
        source_kind, audio_policy = "provider_last_frame", "none"
    else:
        raise SegmentRuntimeError(f"{token} is not authorized by the private shooting plan")
    return {
        "provider_token": token,
        "provider_role": role,
        "source_kind": source_kind,
        "source_segment_id": source_segment_id,
        "source_provider_attempt_id": attempt_id,
        "namespace": namespace,
        "audio_policy": audio_policy,
    }


def _validate_continuity_bindings(
    *,
    parsed: dict[str, Any],
    catalog: dict[str, Any],
    media_bindings: list[dict[str, Any]],
    quality_reset: dict[str, Any] | None = None,
) -> None:
    segment_id = parsed["segment_id"]
    metadata = parsed["metadata"]
    continuity = metadata["continuity"]
    assets = catalog.get("assets") if isinstance(catalog, dict) else None
    if not isinstance(assets, dict):
        raise SegmentRuntimeError("Asset catalog has no assets object")
    binding_by_id = {item["binding_id"]: item for item in parsed["bindings"]}
    world_rows = [binding_by_id[item] for item in continuity["world_binding_ids"]]
    temporal_rows = [
        binding_by_id[item] for item in continuity["temporal_binding_ids"]
    ]
    complete_predecessor_extension = (
        metadata["operation"] == "video_extension"
        and metadata["required_predecessor_evidence"] == "approved_complete_predecessor"
    )
    if complete_predecessor_extension:
        if (
            len(world_rows) != 1
            or len(temporal_rows) != 1
            or world_rows[0]["provider_role"] != "reference_video"
            or temporal_rows[0]["provider_role"] != "reference_video"
            or world_rows[0]["provider_token"] != temporal_rows[0]["provider_token"]
        ):
            raise SegmentRuntimeError(
                f"{segment_id} complete-predecessor extension must use one shared "
                "video token with separate world and temporal binding responsibilities"
            )
    world_location_rows = [
        item
        for item in world_rows
        if isinstance(assets.get(item["asset_namespace"]), dict)
        and assets[item["asset_namespace"]].get("type") == "location_master"
    ]
    if not complete_predecessor_extension and (
        len(world_rows) != 1 or len(world_location_rows) != 1
    ):
        raise SegmentRuntimeError(
            f"{segment_id} world evidence must be exactly one Location master binding"
        )
    expected_scope = [f"Shot {index}" for index in range(1, metadata["shot_count"] + 1)]
    if complete_predecessor_extension:
        if world_rows[0]["shot_scope"] != expected_scope:
            raise SegmentRuntimeError(
                f"{segment_id} complete predecessor must remain authoritative in every Shot"
            )

    catalog_bound_binding_ids = {
        binding_id
        for media in media_bindings
        if media.get("source_kind") == "asset_catalog"
        for binding_id in media.get("binding_ids", [])
    }
    catalog_location_rows = [
        item
        for item in binding_by_id.values()
        if item["binding_id"] in catalog_bound_binding_ids
        and item["provider_role"] == "reference_image"
        and isinstance(assets.get(item["asset_namespace"]), dict)
        and assets[item["asset_namespace"]].get("type") == "location_master"
    ]
    if len(catalog_location_rows) != 1:
        raise SegmentRuntimeError(
            f"{segment_id} must bind exactly one current Location master image, "
            "including during video extension"
        )
    location_binding = catalog_location_rows[0]
    if location_binding["shot_scope"] != expected_scope:
        raise SegmentRuntimeError(
            f"{segment_id} Location master must remain authoritative in every Shot"
        )
    location = assets[location_binding["asset_namespace"]]
    for field, continuity_field in (
        ("embedded_npc_asset_ids", "embedded_npc_asset_ids"),
        (
            "independent_performer_asset_ids",
            "authorized_independent_performer_asset_ids",
        ),
    ):
        catalog_ids = location.get(field)
        if not isinstance(catalog_ids, list):
            raise SegmentRuntimeError(
                f"{segment_id} Location master lacks {field} authority"
            )
        authored_ids = continuity[continuity_field]
        if field == "embedded_npc_asset_ids" and authored_ids != catalog_ids:
            raise SegmentRuntimeError(
                f"{segment_id} embedded population differs from the Location master"
            )
        if field == "independent_performer_asset_ids" and not set(
            authored_ids
        ).issubset(catalog_ids):
            raise SegmentRuntimeError(
                f"{segment_id} authorizes a performer outside the Location treatment"
            )
    location_performers = location["independent_performer_asset_ids"]
    unknown_state_characters = sorted(
        {
            item["character_asset_id"]
            for item in continuity["character_segment_states"]
            if item["segment_presence_rule"] != "remain_absent"
        }
        - set(location_performers)
    )
    if unknown_state_characters:
        raise SegmentRuntimeError(
            f"{segment_id} Character Segment states name performers outside the "
            f"Location treatment: {unknown_state_characters}"
        )
    runtime_binding_ids = {
        binding_id
        for item in media_bindings
        if item["source_kind"] != "asset_catalog"
        for binding_id in item["binding_ids"]
    }
    expected_runtime_binding_ids = set(continuity["temporal_binding_ids"])
    if complete_predecessor_extension:
        expected_runtime_binding_ids.update(continuity["world_binding_ids"])
    if runtime_binding_ids != expected_runtime_binding_ids:
        raise SegmentRuntimeError(
            f"{segment_id} runtime predecessor media differs from temporal evidence"
        )

    bound_image_namespaces = {
        str(item.get("namespace") or "")
        for item in media_bindings
        if item.get("source_kind") == "asset_catalog"
        and item.get("provider_role") == "reference_image"
    }

    def covers_performer(namespace: str, performer_id: str) -> bool:
        if namespace == performer_id or namespace.startswith(f"{performer_id}--"):
            return True
        asset = assets.get(namespace)
        return (
            isinstance(asset, dict)
            and asset.get("type") == "costume"
            and asset.get("character_id") == performer_id
        )

    renderable_character_ids = [
        item["character_asset_id"]
        for item in continuity["character_segment_states"]
        if item["segment_presence_rule"] != "remain_absent"
    ]
    absent_character_ids = [
        item["character_asset_id"]
        for item in continuity["character_segment_states"]
        if item["segment_presence_rule"] == "remain_absent"
    ]
    missing_identity = [
        performer_id
        for performer_id in renderable_character_ids
        if not any(
            covers_performer(namespace, performer_id)
            for namespace in bound_image_namespaces
        )
    ]
    if missing_identity:
        raise SegmentRuntimeError(
            f"{segment_id} requires an asset-catalog identity/state reference image "
            "binding for every provider-renderable role or NPC ensemble, including "
            "roles that are offscreen, occluded, or audio-only but may appear; predecessor "
            "continuity media, prompt prose, internal IDs, and voice samples do not "
            f"count as visual identity evidence: {missing_identity}"
        )
    positively_bound_absent = [
        performer_id
        for performer_id in absent_character_ids
        if any(
            covers_performer(namespace, performer_id)
            for namespace in bound_image_namespaces
        )
    ]
    if positively_bound_absent:
        raise SegmentRuntimeError(
            f"{segment_id} must not submit positive identity images for remain_absent "
            "roles because Seedance may render any referenced image; keep these roles "
            "only in the internal state machine and review gate, never as provider IDs "
            f"or media bindings: {positively_bound_absent}"
        )

    if not quality_reset or quality_reset.get("required") is not True:
        return
    temporal_rows = [
        binding_by_id[binding_id]
        for binding_id in continuity["temporal_binding_ids"]
    ]
    if len(temporal_rows) != 1 or not re.search(
        r"\b(?:white(?:[- ]3d)? model|white geometry)\b",
        str(temporal_rows[0].get("prompt_declaration_en") or ""),
        re.IGNORECASE,
    ):
        raise SegmentRuntimeError(
            f"{segment_id} white-model quality reset must declare its temporal "
            "@Video binding as a white model"
        )


def build_execution_plan(*, task_dir: Path, parsed: dict[str, Any], catalog: dict[str, Any], capability_profile: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    task_dir = task_dir.expanduser().resolve()
    metadata = parsed["metadata"]
    if capability_profile.get("contract") != "seedance-capability-profile" or capability_profile.get("profile_status") != "VERIFIED":
        raise SegmentRuntimeError("Seedance capability profile is not verified")
    project_policy = capability_profile.get("project_generation_policy")
    if not isinstance(project_policy, dict):
        raise SegmentRuntimeError(
            "Seedance capability profile lacks project_generation_policy"
        )
    maximum_direct_hops = project_policy.get(
        "maximum_direct_extension_hops_without_quality_reset"
    )
    if maximum_direct_hops != 0:
        raise SegmentRuntimeError(
            "Seedance capability profile must require a white-model quality "
            "reset on the first and every permitted video extension"
        )
    if project_policy.get("extension_quality_reset_strategy") != "white_model_video_edit":
        raise SegmentRuntimeError(
            "Seedance capability profile must select white_model_video_edit quality reset"
        )
    if (
        project_policy.get("maximum_consecutive_predecessor_media_hops") != 1
        or project_policy.get(
            "require_strong_coverage_reset_after_predecessor_media"
        )
        is not True
        or project_policy.get("strong_coverage_reset_opening_shot_sizes")
        != ["extreme_close_up", "close_up", "medium_close_up"]
    ):
        raise SegmentRuntimeError(
            "Seedance capability profile must allow one predecessor-media hop, "
            "then require a reference-free ECU/CU/MCU coverage reset"
        )
    quality_reset = extension_quality_reset_schedule(
        storyboard_segment_rows(
            task_dir,
            validation_through_segment_id=parsed["segment_id"],
        ),
        maximum_direct_hops,
    )[parsed["segment_id"]]
    reset_contract_path = REPOSITORY_ROOT / WHITE_MODEL_RESET_CONTRACT_RELATIVE
    if quality_reset["required"]:
        reset_contract = read_json(
            reset_contract_path, label="white-model quality-reset contract"
        )
        if (
            reset_contract.get("contract")
            != "seedance-white-model-quality-reset-v1"
            or reset_contract.get("operation") != "video_edit"
            or reset_contract.get("strategy") != "white_model_video_edit"
        ):
            raise SegmentRuntimeError(
                "White-model quality-reset contract is invalid"
            )
        quality_reset = {
            **quality_reset,
            "contract_path": WHITE_MODEL_RESET_CONTRACT_RELATIVE.as_posix(),
            "contract_sha256": sha256_file(reset_contract_path),
        }
    else:
        quality_reset = {
            **quality_reset,
            "contract_path": "none",
            "contract_sha256": "none",
        }
    token_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for binding in parsed["bindings"]:
        token_rows[binding["provider_token"]].append(binding)
    media_bindings: list[dict[str, Any]] = []
    for token in sorted(token_rows, key=token_sort_key):
        rows = token_rows[token]
        roles = {item["provider_role"] for item in rows}
        if len(roles) != 1:
            raise SegmentRuntimeError(f"{token} is assigned more than one provider role")
        role = next(iter(roles))
        namespace = _asset_namespace(parsed["bindings"], token)
        if role == "reference_video" or namespace == "continuity":
            media = _runtime_binding(
                token=token,
                role=role,
                namespace=namespace,
                metadata=metadata,
                task_dir=task_dir,
                quality_reset_required=quality_reset["required"],
            )
        else:
            resolved = resolve_catalog_media(namespace=namespace, provider_role=role, catalog=catalog)
            media = {"provider_token": token, "provider_role": role, "source_kind": "asset_catalog", "namespace": namespace, **resolved}
        media["binding_ids"] = [item["binding_id"] for item in rows]
        media_bindings.append(media)

    evidence = metadata["required_predecessor_evidence"]
    expected_runtime = {
        "none": set(),
        "approved_complete_predecessor": {
            "white_model_predecessor_video"
            if quality_reset["required"]
            else "complete_predecessor_video"
        },
        "approved_provider_last_frame": {"provider_last_frame"},
    }[evidence]
    actual_runtime = {item["source_kind"] for item in media_bindings} - {"asset_catalog"}
    if actual_runtime != expected_runtime:
        raise SegmentRuntimeError(f"{parsed['segment_id']} reference tokens do not match predecessor evidence")
    _validate_continuity_bindings(
        parsed=parsed,
        catalog=catalog,
        media_bindings=media_bindings,
        quality_reset=quality_reset,
    )
    model_id = _nonempty_string(capability_profile.get("model_id"), "Seedance model_id")
    task_input = task.get("input")
    if not isinstance(task_input, dict):
        raise SegmentRuntimeError("task.json input must be an object")
    resolution = _nonempty_string(task_input.get("resolution"), "task input resolution").lower()
    ratio = _nonempty_string(task_input.get("aspect_ratio"), "task input aspect_ratio")
    counts = {role: sum(item["provider_role"] == role for item in media_bindings) for role in ("reference_image", "reference_video", "reference_audio")}
    capabilities = capability_profile.get("provider_capabilities")
    if not isinstance(capabilities, dict):
        raise SegmentRuntimeError("Seedance capability profile lacks provider capabilities")
    if capabilities.get("native_background_music_generation") is not True:
        raise SegmentRuntimeError(
            "Seedance capability profile does not verify native background music"
        )
    limits = {
        "reference_image": capabilities.get("maximum_reference_images"),
        "reference_video": capabilities.get("maximum_reference_videos"),
        "reference_audio": capabilities.get("maximum_reference_audios"),
    }
    for role, count in counts.items():
        limit = limits[role]
        if isinstance(limit, bool) or not isinstance(limit, int) or count > limit:
            raise SegmentRuntimeError(f"{parsed['segment_id']} exceeds the verified {role} limit")
    assets = catalog.get("assets") if isinstance(catalog, dict) else None
    if not isinstance(assets, dict):
        raise SegmentRuntimeError("Asset catalog has no assets object")

    def binding_covers_performer(namespace: str, performer_id: str) -> bool:
        if namespace == performer_id or namespace.startswith(f"{performer_id}--"):
            return True
        asset = assets.get(namespace)
        return (
            isinstance(asset, dict)
            and asset.get("type") == "costume"
            and asset.get("character_id") == performer_id
        )

    declared_character_ids = [
        item["character_asset_id"]
        for item in metadata["continuity"]["character_segment_states"]
    ]
    renderable_character_ids = [
        item["character_asset_id"]
        for item in metadata["continuity"]["character_segment_states"]
        if item["segment_presence_rule"] != "remain_absent"
    ]
    absent_character_ids = [
        item["character_asset_id"]
        for item in metadata["continuity"]["character_segment_states"]
        if item["segment_presence_rule"] == "remain_absent"
    ]
    provider_last_frame_media = [
        item
        for item in media_bindings
        if item.get("source_kind") == "provider_last_frame"
        and item.get("provider_role") == "reference_image"
        and item.get("namespace") == "continuity"
    ]
    provider_last_frame_identity_authority = (
        metadata["operation"] == "multimodal_reference"
        and metadata["required_predecessor_evidence"]
        == "approved_provider_last_frame"
        and len(provider_last_frame_media) == 1
        and all(
            item["incoming_presence"] == "visible"
            and item["segment_presence_rule"] == "must_remain_visible"
            for item in metadata["continuity"]["character_segment_states"]
            if item["character_asset_id"] in renderable_character_ids
        )
    )
    independently_referenced_performers = sorted(
        {
            performer_id
            for performer_id in declared_character_ids
            if any(
                item.get("source_kind") == "asset_catalog"
                and item.get("provider_role") == "reference_image"
                and binding_covers_performer(
                    str(item.get("namespace") or ""), performer_id
                )
                for item in media_bindings
            )
        }
    )
    identity_reference_coverage = {
        performer_id: [
            {
                "provider_token": item["provider_token"],
                "asset_namespace": item["namespace"],
                "source_kind": item["source_kind"],
            }
            for item in media_bindings
            if item.get("provider_role") == "reference_image"
            and (
                (
                    item.get("source_kind") == "asset_catalog"
                    and binding_covers_performer(
                        str(item.get("namespace") or ""), performer_id
                    )
                )
                or (
                    provider_last_frame_identity_authority
                    and item.get("source_kind") == "provider_last_frame"
                    and item.get("namespace") == "continuity"
                )
            )
        ]
        for performer_id in renderable_character_ids
    }
    independent_recommendation = capabilities.get(
        "recommended_independently_referenced_performers_for_simple_composition"
    )
    if (
        isinstance(independent_recommendation, bool)
        or not isinstance(independent_recommendation, int)
        or independent_recommendation < 1
    ):
        raise SegmentRuntimeError(
            "Seedance capability profile lacks the independent-performer "
            "composition recommendation"
        )
    task_audio_mode = str(task.get("seedance_audio_mode") or "native_sync")
    task_dialogue_source = str(task.get("dialogue_source") or "seedance")
    task_voice_source = str(task.get("voice_audio_source") or "speaker_reference_audio")
    if metadata["prompt_contract"]["background_music_policy"] != "parentheses_only":
        raise SegmentRuntimeError(
            "The default main flow requires Seedance background music in (...) notation"
        )
    if task_audio_mode == "native_sync":
        if (
            task_dialogue_source != "seedance"
            or task_voice_source != "speaker_reference_audio"
            or metadata["dialogue_delivery"] != "seedance"
        ):
            raise SegmentRuntimeError(
                "Native-sync tasks require Seedance dialogue and speaker-reference audio"
            )
    elif task_audio_mode == "background_only":
        dialogue_file = task.get("external_dialogue_file")
        if (
            task_dialogue_source != "external_tts"
            or task_voice_source != "external_tts"
            or metadata["dialogue_delivery"] != "external_tts"
            or not isinstance(dialogue_file, str)
            or not dialogue_file.strip()
            or not (task_dir / dialogue_file).is_file()
            or any(item["provider_role"] == "reference_audio" for item in media_bindings)
        ):
            raise SegmentRuntimeError(
                "Background-only tasks require an existing external dialogue file, "
                "external-TTS delivery, and no reference-audio bindings"
            )
    else:
        raise SegmentRuntimeError(
            f"Unsupported task seedance_audio_mode: {task_audio_mode!r}"
        )
    result = {
        "contract": "seedance-segment-execution-plan-v2",
        "segment_id": parsed["segment_id"],
        "source_segment_script": parsed["path"].relative_to(task_dir).as_posix(),
        "source_script_sha256": parsed["script_sha256"],
        "source_private_plan_sha256": parsed["private_plan_sha256"],
        "source_storyboard_sha256": metadata["source_storyboard_sha256"],
        "continuity": metadata["continuity"],
        "prompt_contract": metadata["prompt_contract"],
        "quality_reset": quality_reset,
        "shooting_plan": {field: metadata[field] for field in (
            "shooting_plan_status", "schedule_mode", "planned_wave", "depends_on_segment_ids",
            "dependency_reason", "predecessor_review_required", "required_predecessor_evidence",
            "successor_recompile_required", "fallback_operation_and_story_cost", "operation",
            "seam_class", "seam_resynthesis_allowed", "seam_story_reason", "editorial_intent",
            "reference_video_scope", "reference_video_audio", "camera_ensemble_color_resynthesis_allowed",
        )},
        "seedance_parameters": {
            "model": model_id,
            "duration": parsed["duration"],
            "resolution": resolution,
            "ratio": ratio,
            "generate_audio": True,
            "watermark": False,
            "return_last_frame": True,
            "execution_expires_after": 172800,
            "priority": 0,
        },
        "media_bindings": media_bindings,
        "media_counts": counts,
        "identity_reference_coverage": identity_reference_coverage,
        "identity_non_submission_roles": absent_character_ids,
        "reference_budget": {
            "total": sum(counts.values()),
            "recommended_total": "4-5",
            "within_recommended_total": sum(counts.values()) in {4, 5},
            "independently_referenced_performer_asset_ids": (
                independently_referenced_performers
            ),
            "independently_referenced_performer_count": len(
                independently_referenced_performers
            ),
            "recommended_independent_performers_for_simple_composition": (
                independent_recommendation
            ),
            "within_simple_composition_recommendation": (
                len(independently_referenced_performers)
                <= independent_recommendation
            ),
        },
    }
    result["audio_policy"] = {
        "seedance_audio_mode": task_audio_mode,
        "dialogue_source": task_dialogue_source,
        "silent_mouth_performance": task_audio_mode == "background_only",
        "native_background_audio": True,
        "seedance_background_music": True,
        "background_music_source": "seedance_native",
    }
    if task_audio_mode == "background_only":
        result["audio_policy"]["external_dialogue_file"] = str(
            task["external_dialogue_file"]
        )
    return result


def validate_source_identity(task_dir: Path, parsed: dict[str, Any]) -> None:
    if sha256_file(task_dir / STORYBOARD_RELATIVE) != parsed["metadata"]["source_storyboard_sha256"]:
        raise SegmentRuntimeError(f"{parsed['segment_id']} Storyboard hash is stale")


def load_execution_plan(task_dir: Path, segment_id: str) -> dict[str, Any]:
    """Build the current deterministic execution plan in memory."""

    if not SEGMENT_RE.fullmatch(segment_id):
        raise SegmentRuntimeError(f"Invalid Segment ID: {segment_id}")
    root = task_dir.expanduser().resolve(strict=True)
    parsed = parse_segment_script(root / SCRIPT_DIR_RELATIVE / f"{segment_id}.md")
    validate_source_identity(root, parsed)
    catalog = read_json(
        REPOSITORY_ROOT / "assets" / "assets.json",
        label="repository asset catalog",
    )
    task = read_json(root / "task.json", label="task.json")
    capability_profile = read_json(
        root / CAPABILITY_PROFILE_RELATIVE,
        label="Seedance capability profile",
    )
    plan = build_execution_plan(
        task_dir=root,
        parsed=parsed,
        catalog=catalog,
        capability_profile=capability_profile,
        task=task,
    )
    if (
        plan.get("contract") != "seedance-segment-execution-plan-v2"
        or plan.get("segment_id") != segment_id
    ):
        raise SegmentRuntimeError(
            f"Invalid in-memory Seedance execution plan for {segment_id}"
        )
    return plan


def storyboard_segment_rows(
    task_dir: Path,
    *,
    validation_through_segment_id: str | None = None,
) -> list[dict[str, Any]]:
    plan_root = task_dir / PLAN_DIR_RELATIVE
    paths = sorted(plan_root.glob("segment-*.json"))
    if not paths:
        raise SegmentRuntimeError("No private Seedance Segment plans are available")
    rows: list[dict[str, Any]] = []
    for path in paths:
        row = read_json(path, label="private Seedance Segment plan")
        segment_id = row.get("segment_id")
        if row.get("contract") != "seedance-natural-language-plan-v1" or not isinstance(segment_id, str) or not SEGMENT_RE.fullmatch(segment_id) or path.name != f"{segment_id}.json":
            raise SegmentRuntimeError(f"Invalid private Segment plan: {path}")
        _unique_string_list(row.get("scene_ids"), f"{segment_id} scene_ids", allow_empty=False)
        rows.append(row)
    expected = [f"segment-{index:03d}" for index in range(1, len(rows) + 1)]
    if [row["segment_id"] for row in rows] != expected:
        raise SegmentRuntimeError("Private Segment plans must be consecutive from segment-001")
    validation_rows = rows
    if validation_through_segment_id is not None:
        if not SEGMENT_RE.fullmatch(validation_through_segment_id):
            raise SegmentRuntimeError(
                f"Invalid validation Segment ID: {validation_through_segment_id}"
            )
        matching_indexes = [
            index
            for index, row in enumerate(rows)
            if row["segment_id"] == validation_through_segment_id
        ]
        if not matching_indexes:
            raise SegmentRuntimeError(
                f"Unknown validation Segment ID: {validation_through_segment_id}"
            )
        validation_rows = rows[: matching_indexes[0] + 1]
    _validate_location_state_chains(validation_rows)
    _validate_character_state_chains(validation_rows, task_dir=task_dir)
    _validate_storyboard_character_state_authority(task_dir, validation_rows)
    _validate_same_scene_serial(validation_rows)
    _validate_single_predecessor_inheritance_hop(validation_rows)
    return validation_rows


def _validate_location_state_chains(rows: list[dict[str, Any]]) -> None:
    latest_by_chain: dict[str, str] = {}
    for index, row in enumerate(rows):
        segment_id = row["segment_id"]
        continuity = row.get("continuity")
        if not isinstance(continuity, dict):
            raise SegmentRuntimeError(f"{segment_id} lacks continuity authority")
        chain = continuity.get("location_state_chain")
        relationship = continuity.get("relationship")
        source = continuity.get("state_source_segment_id")
        if not isinstance(chain, str) or not chain.strip() or relationship not in LOCATION_RELATIONSHIPS:
            raise SegmentRuntimeError(f"{segment_id} has invalid continuity authority")
        previous_in_chain = latest_by_chain.get(chain)
        previous_global = rows[index - 1]["segment_id"] if index else None
        if previous_in_chain is None:
            if relationship not in {"independent", "reset_with_reason"} or source != "none":
                raise SegmentRuntimeError(
                    f"{segment_id} must originate location state chain {chain!r}"
                )
        elif relationship == "independent":
            raise SegmentRuntimeError(
                f"{segment_id} revisits location state chain {chain!r} as independent"
            )
        elif relationship in {
            "adjacent_continuation",
            "adjacent_coverage_reset",
            "nonadjacent_revisit",
        }:
            if source != previous_in_chain:
                raise SegmentRuntimeError(
                    f"{segment_id} must source the latest state in chain {chain!r}"
                )
            if source not in row.get("depends_on_segment_ids", []):
                raise SegmentRuntimeError(
                    f"{segment_id} dependency plan omits location state source {source}"
                )
            if relationship in {
                "adjacent_continuation",
                "adjacent_coverage_reset",
            } and source != previous_global:
                raise SegmentRuntimeError(f"{segment_id} is not adjacent to its state source")
            if relationship == "nonadjacent_revisit" and source == previous_global:
                raise SegmentRuntimeError(f"{segment_id} state source is adjacent, not a revisit")
        latest_by_chain[chain] = segment_id


def _reviewed_character_state_overrides(
    task_dir: Path,
    segment_id: str,
) -> dict[str, dict[str, str]]:
    """Load review-evidenced outgoing presence changes for one generated attempt."""

    generation_root = (
        task_dir
        / ".pending/virtual-production/generation-segments"
        / segment_id
    )
    override_path = generation_root / "reviewed-character-state-overrides.json"
    if not override_path.is_file():
        return {}
    value = read_json(
        override_path,
        label=f"{segment_id} reviewed Character state overrides",
    )
    expected_fields = {
        "contract",
        "segment_id",
        "provider_attempt_id",
        "review_status",
        "overrides",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise SegmentRuntimeError(
            f"{segment_id} reviewed Character state override uses stale fields"
        )
    production_record = read_json(
        generation_root / "production-record.json",
        label=f"{segment_id} production record",
    )
    provider_attempt_id = _nonempty_string(
        value.get("provider_attempt_id"),
        f"{segment_id} reviewed override provider_attempt_id",
    )
    if (
        value.get("contract") != "seedance-reviewed-character-state-v1"
        or value.get("segment_id") != segment_id
        or value.get("review_status") != "NO_ISSUES"
        or production_record.get("status") != "GENERATED"
        or production_record.get("provider_attempt_id") != provider_attempt_id
    ):
        raise SegmentRuntimeError(
            f"{segment_id} reviewed Character state override is not locked to "
            "the current approved provider attempt"
        )
    raw_overrides = value.get("overrides")
    if not isinstance(raw_overrides, list) or not raw_overrides:
        raise SegmentRuntimeError(
            f"{segment_id} reviewed Character state override must be non-empty"
        )
    item_fields = {
        "character_asset_id",
        "planned_outgoing_presence",
        "reviewed_outgoing_presence",
        "reason",
        "evidence_artifact",
    }
    result: dict[str, dict[str, str]] = {}
    for raw in raw_overrides:
        if not isinstance(raw, dict) or set(raw) != item_fields:
            raise SegmentRuntimeError(
                f"{segment_id} has an invalid reviewed Character state override"
            )
        character_id = _nonempty_string(
            raw.get("character_asset_id"),
            f"{segment_id} reviewed override character_asset_id",
        )
        planned = _nonempty_string(
            raw.get("planned_outgoing_presence"),
            f"{segment_id} reviewed override planned_outgoing_presence",
        )
        reviewed = _nonempty_string(
            raw.get("reviewed_outgoing_presence"),
            f"{segment_id} reviewed override reviewed_outgoing_presence",
        )
        reason = _nonempty_string(
            raw.get("reason"),
            f"{segment_id} reviewed override reason",
        )
        evidence_artifact = _nonempty_string(
            raw.get("evidence_artifact"),
            f"{segment_id} reviewed override evidence_artifact",
        )
        evidence_path = generation_root / evidence_artifact
        if (
            character_id in result
            or planned not in CHARACTER_PRESENCE_STATES
            or reviewed not in CHARACTER_PRESENCE_STATES
            or planned == reviewed
            or Path(evidence_artifact).is_absolute()
            or ".." in Path(evidence_artifact).parts
            or not evidence_path.is_file()
        ):
            raise SegmentRuntimeError(
                f"{segment_id} has an invalid reviewed override for {character_id}"
            )
        result[character_id] = {
            "planned_outgoing_presence": planned,
            "reviewed_outgoing_presence": reviewed,
            "reason": reason,
            "evidence_artifact": evidence_artifact,
        }
    return result


def _validate_character_state_chains(
    rows: list[dict[str, Any]],
    *,
    task_dir: Path | None = None,
) -> None:
    """Reject silent disappearance/reappearance inside each Location state chain."""

    latest: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        segment_id = str(row["segment_id"])
        continuity = row.get("continuity")
        shot_count = row.get("shot_count")
        if (
            not isinstance(continuity, dict)
            or isinstance(shot_count, bool)
            or not isinstance(shot_count, int)
            or shot_count < 1
        ):
            raise SegmentRuntimeError(
                f"{segment_id} lacks Character Segment state authority"
            )
        chain = _nonempty_string(
            continuity.get("location_state_chain"),
            f"{segment_id} location_state_chain",
        )
        independent = _unique_string_list(
            continuity.get("authorized_independent_performer_asset_ids"),
            f"{segment_id} authorized performers",
        )
        states = _parse_character_segment_states(
            continuity.get("character_segment_states"),
            segment_id=segment_id,
            shot_count=shot_count,
            authorized_independent_performer_asset_ids=independent,
        )
        current_ids = {item["character_asset_id"] for item in states}
        live_before = {
            character_id
            for (state_chain, character_id), prior in latest.items()
            if state_chain == chain and prior["outgoing_presence"] != "absent"
        }
        missing_live = sorted(live_before - current_ids)
        if missing_live:
            raise SegmentRuntimeError(
                f"{segment_id} silently drops still-present characters from Location "
                f"state chain {chain!r}: {missing_live}"
            )
        reviewed_overrides = (
            _reviewed_character_state_overrides(task_dir, segment_id)
            if task_dir is not None
            else {}
        )
        unknown_override_ids = sorted(
            set(reviewed_overrides)
            - {state["character_asset_id"] for state in states}
        )
        if unknown_override_ids:
            raise SegmentRuntimeError(
                f"{segment_id} reviewed Character state overrides name undeclared "
                f"roles: {unknown_override_ids}"
            )
        for state in states:
            character_id = state["character_asset_id"]
            key = (chain, character_id)
            prior = latest.get(key)
            source = state["state_source_segment_id"]
            rule = state["segment_presence_rule"]
            if prior is None:
                if source != "none":
                    raise SegmentRuntimeError(
                        f"{segment_id} character {character_id} has no earlier state "
                        f"in Location chain {chain!r}"
                    )
                if rule == "re_enter":
                    raise SegmentRuntimeError(
                        f"{segment_id} character {character_id} cannot re-enter before "
                        "an earlier established state"
                    )
            else:
                if source != prior["segment_id"]:
                    raise SegmentRuntimeError(
                        f"{segment_id} character {character_id} must source its latest "
                        f"state from {prior['segment_id']}"
                    )
                if state["incoming_presence"] != prior["outgoing_presence"]:
                    raise SegmentRuntimeError(
                        f"{segment_id} character {character_id} incoming presence "
                        f"{state['incoming_presence']!r} differs from prior outgoing "
                        f"{prior['outgoing_presence']!r}"
                    )
                if rule == "enter":
                    raise SegmentRuntimeError(
                        f"{segment_id} character {character_id} is already established; "
                        "use re_enter after an explicit exit"
                    )
                if rule == "re_enter" and prior["outgoing_presence"] != "absent":
                    raise SegmentRuntimeError(
                        f"{segment_id} character {character_id} may re-enter only after "
                        "an explicit absent state"
                    )
                if (
                    prior["outgoing_presence"] == "absent"
                    and rule
                    not in {"re_enter", "remain_absent", "reset_with_reason"}
                ):
                    raise SegmentRuntimeError(
                        f"{segment_id} character {character_id} cannot reappear from "
                        "absence without re_enter or an explicit reset"
                    )
            planned_outgoing = state["outgoing_presence"]
            reviewed_override = reviewed_overrides.get(character_id)
            if (
                reviewed_override is not None
                and reviewed_override["planned_outgoing_presence"]
                != planned_outgoing
            ):
                raise SegmentRuntimeError(
                    f"{segment_id} reviewed override for {character_id} no longer "
                    "matches the planned outgoing presence"
                )
            effective_outgoing = (
                reviewed_override["reviewed_outgoing_presence"]
                if reviewed_override is not None
                else planned_outgoing
            )
            latest[key] = {
                "segment_id": segment_id,
                "outgoing_presence": effective_outgoing,
            }


def _markdown_cells(line: str) -> list[str]:
    return [item.strip() for item in line.strip().strip("|").split("|")]


def _storyboard_character_state_rows(
    task_dir: Path,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Read exact Route-A character state authority from storyboard.md."""

    storyboard_path = task_dir / STORYBOARD_RELATIVE
    if not storyboard_path.is_file():
        return {}
    text = storyboard_path.read_text(encoding="utf-8")
    heading = "## Character Segment State Plan"
    start = text.find(heading)
    if start < 0:
        raise SegmentRuntimeError(
            "Storyboard lacks Character Segment State Plan"
        )
    section = text[start + len(heading):]
    next_heading = re.search(r"^## ", section, re.MULTILINE)
    if next_heading:
        section = section[:next_heading.start()]
    lines = section.splitlines()
    table_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().startswith("|")
        ),
        None,
    )
    expected_headers = [
        "Location State Chain",
        "Segment",
        "Screenplay Entity ID",
        "Character Asset ID",
        "State Source",
        "Incoming Presence",
        "Segment Presence Rule",
        "Required Visible Shots",
        "Allowed Occlusion",
        "Position, Injury and Condition",
        "Transition Cause",
        "Outgoing Presence",
    ]
    if table_index is None or _markdown_cells(lines[table_index]) != expected_headers:
        raise SegmentRuntimeError(
            "Storyboard Character Segment State Plan uses stale columns"
        )
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for line in lines[table_index + 2:]:
        if not line.strip().startswith("|"):
            if result:
                break
            continue
        cells = _markdown_cells(line)
        if len(cells) != len(expected_headers):
            raise SegmentRuntimeError(
                "Storyboard Character Segment State Plan has an invalid row"
            )
        row = dict(zip(expected_headers, cells))
        segment_id = row["Segment"]
        asset_id = row["Character Asset ID"]
        shot_labels = (
            []
            if row["Required Visible Shots"].casefold() == "none"
            else [
                item.strip()
                for item in row["Required Visible Shots"].split(",")
                if item.strip()
            ]
        )
        required_shots: list[int] = []
        for shot_label in shot_labels:
            match = re.fullmatch(r"Shot ([1-9][0-9]*)", shot_label)
            if not match:
                raise SegmentRuntimeError(
                    f"{segment_id} {asset_id} has an invalid Storyboard visible Shot"
                )
            required_shots.append(int(match.group(1)))
        segment_rows = result.setdefault(segment_id, {})
        if asset_id in segment_rows:
            raise SegmentRuntimeError(
                f"{segment_id} repeats Storyboard character state for {asset_id}"
            )
        segment_rows[asset_id] = {
            "state_source_segment_id": row["State Source"],
            "incoming_presence": row["Incoming Presence"],
            "segment_presence_rule": row["Segment Presence Rule"],
            "outgoing_presence": row["Outgoing Presence"],
            "required_visible_shots": required_shots,
            "allowed_occlusion_en": row["Allowed Occlusion"],
            "transition_cause_en": row["Transition Cause"],
            "position_and_condition_en": row[
                "Position, Injury and Condition"
            ],
        }
    return result


def _validate_storyboard_character_state_authority(
    task_dir: Path,
    rows: list[dict[str, Any]],
) -> None:
    """Prevent virtual production from relaxing storyboard visibility obligations."""

    expected_by_segment = _storyboard_character_state_rows(task_dir)
    if not expected_by_segment:
        return
    plan_segments = {str(row["segment_id"]) for row in rows}
    expected_by_segment = {
        segment_id: states
        for segment_id, states in expected_by_segment.items()
        if segment_id in plan_segments
    }
    if set(expected_by_segment) != plan_segments:
        raise SegmentRuntimeError(
            "Private Segment plans and Storyboard Character state Segments differ"
        )
    comparable_fields = {
        "state_source_segment_id",
        "incoming_presence",
        "segment_presence_rule",
        "outgoing_presence",
        "required_visible_shots",
        "allowed_occlusion_en",
        "transition_cause_en",
        "position_and_condition_en",
    }
    for plan in rows:
        segment_id = str(plan["segment_id"])
        continuity = plan["continuity"]
        actual = {
            item["character_asset_id"]: item
            for item in continuity["character_segment_states"]
        }
        expected = expected_by_segment[segment_id]
        if set(actual) != set(expected):
            raise SegmentRuntimeError(
                f"{segment_id} private Character states differ from Storyboard; "
                f"missing={sorted(set(expected) - set(actual))}, "
                f"extra={sorted(set(actual) - set(expected))}"
            )
        for asset_id, upstream in expected.items():
            downstream = actual[asset_id]
            mismatched = sorted(
                field
                for field in comparable_fields
                if downstream.get(field) != upstream[field]
            )
            if mismatched:
                raise SegmentRuntimeError(
                    f"{segment_id} {asset_id} downgrades or changes Storyboard "
                    f"Character state fields: {mismatched}"
                )


def _validate_same_scene_serial(rows: list[dict[str, Any]]) -> None:
    for predecessor, successor in zip(rows, rows[1:]):
        shared = sorted(set(predecessor["scene_ids"]) & set(successor["scene_ids"]))
        if not shared:
            continue
        predecessor_wave = predecessor.get("planned_wave")
        if not (
            successor.get("schedule_mode") == "serial_after_predecessor_review"
            and successor.get("depends_on_segment_ids") == [predecessor["segment_id"]]
            and successor.get("planned_wave") == (predecessor_wave + 1 if isinstance(predecessor_wave, int) else None)
            and successor.get("predecessor_review_required") is True
            and successor.get("successor_recompile_required") is True
        ):
            raise SegmentRuntimeError(f"{successor['segment_id']} shares a Scene with {predecessor['segment_id']} and must directly depend on it")
        soft = (
            successor.get("operation") == "multimodal_reference"
            and successor.get("required_predecessor_evidence") == "approved_provider_last_frame"
            and successor.get("reference_video_scope") == "none"
            and successor.get("reference_video_audio") == "none"
        )
        extension = (
            successor.get("operation") == "video_extension"
            and successor.get("required_predecessor_evidence") == "approved_complete_predecessor"
            and successor.get("reference_video_scope") == "full_predecessor_for_extension"
            and successor.get("reference_video_audio") == "preserved_for_extension"
        )
        strong_reset = (
            successor.get("operation") == "multimodal_reference"
            and successor.get("required_predecessor_evidence") == "none"
            and successor.get("seam_class") == "strong_coverage_reset"
            and successor.get("reference_video_scope") == "none"
            and successor.get("reference_video_audio") == "none"
            and successor.get("camera_ensemble_color_resynthesis_allowed") is True
            and successor.get("continuity", {}).get("relationship")
            == "adjacent_coverage_reset"
            and successor.get("continuity", {}).get("temporal_binding_ids") == []
        )
        if not (soft or extension or strong_reset):
            raise SegmentRuntimeError(
                f"{successor['segment_id']} must use one predecessor-media "
                "inheritance or a reference-free strong coverage reset"
            )
