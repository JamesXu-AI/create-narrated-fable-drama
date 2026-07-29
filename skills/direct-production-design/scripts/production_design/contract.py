"""Validate the model-authored production-design plan without completing it."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from narrated_fable_drama.contracts.story_objects import (
    VISUAL_AUTHORITY_MODES,
    expected_visual_authority_mode,
)
from narrated_fable_drama.core.json_io import load_json_object


PLAN_RELATIVE_PATH = Path("direct-production-design/production-design-plan.json")
ROOT_KEYS = {
    "contract",
    "characters",
    "ensemble_rosters",
    "object_authorities",
    "props",
    "costumes",
    "locations",
}
PROMPT_KEYS = {
    "intent_en",
    "subject_en",
    "background_en",
    "composition_en",
    "continuity",
    "style_en",
    "exclusions_en",
}
PROVIDER_PROMPT_KEYS = PROMPT_KEYS | {
    "style_execution_en",
    "style_medium_exclusions_en",
}
PROMPT_CONTINUITY_KEYS = {"reference_asset_ids", "locks_en"}
CHARACTER_KEYS = {
    "type",
    "entity_id",
    "actor_profile",
    "description_en",
    "body_topology",
    "voice_description_en",
    "voice_sample_text_en",
    "voice_speech_rate",
    "voice_generation_prompt",
    "media_path",
    "generation_prompt",
}
ENSEMBLE_KEYS = {
    "type",
    "asset_id",
    "group_role_type_en",
    "description_en",
    "member_type_id",
    "allowed_member_types_en",
    "subject_count",
    "variation_profile",
    "media_path",
    "generation_prompt",
}
VARIATION_PROFILE_KEYS = {"locked_traits_en", "allowed_variation_en"}
ACTOR_PROFILE_KEYS = {
    "name_en",
    "personality_en",
    "screen_presence_en",
    "acting_range_en",
}
BODY_TOPOLOGY_KEYS = {
    "body_plan_en",
    "total_limb_count",
    "limb_sets",
    "non_limb_appendages",
    "topology_lock_en",
}
LIMB_SET_KEYS = {"kind_en", "count", "function_en"}
NON_LIMB_APPENDAGE_KEYS = {"kind_en", "count"}
PROP_KEYS = {
    "type",
    "asset_id",
    "description_en",
    "media_path",
    "generation_prompt",
}
OBJECT_AUTHORITY_KEYS = {
    "object_id",
    "mode",
    "asset_ids",
}
COSTUME_KEYS = {
    "type",
    "asset_id",
    "character_id",
    "description_en",
    "appearance_state_en",
    "media_path",
    "generation_prompt",
}
LOCATION_KEYS = {
    "type",
    "location_id",
    "scene_ids",
    "description_en",
    "included_prop_ids",
    "embedded_npc_asset_ids",
    "independent_performer_asset_ids",
    "fixed_set_elements_en",
    "environment_state_en",
    "lighting_state_en",
    "palette_materials_en",
    "topology",
    "landmarks",
    "media_path",
    "generation_prompt",
}
VOICE_PROMPT_KEYS = {
    "text_en",
    "voice_direction_en",
    "delivery_en",
    "exclusions_en",
}
ASSET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
STORY_BOUND_ACTOR_PROFILE_RE = re.compile(
    r"\b(?:screenplay|segment|current story|story objective|narrative function|"
    r"plot event|scene-specific)\b",
    re.IGNORECASE,
)
STORY_BOUND_CHARACTER_PROMPT_RE = re.compile(
    r"\b(?:screenplay|segment|current story|plot event|narrative function|"
    r"first dialogue|line delivery|victory|defeat|injury state)\b",
    re.IGNORECASE,
)
PROMPT_PATCH_LANGUAGE_RE = re.compile(
    r"\b(?:append(?:ed)?|supplemental|emergency correction|ignore previous|"
    r"override previous|despite previous|additional negative block)\b",
    re.IGNORECASE,
)
MAX_GENERATION_PROMPT_CHARS = 3500
MAX_VOICE_PROMPT_CHARS = 2000
PURE_WHITE_BACKGROUND_EN = (
    "Seamless pure-white (#FFFFFF) studio backdrop; no environment, horizon, "
    "floor line, texture, gradient, tint, or background cast shadow."
)
DEFAULT_STYLE_AUTHORITY_EN = "3D Healing Animation"
DEFAULT_STYLE_EXECUTION_EN = (
    "Execute as unmistakably stylized soft 3D healing animation: rounded appealing "
    "proportions, enlarged expressive eyes, simplified clean forms, plush matte "
    "fur and materials, a warm gentle palette, soft diffuse cinematic lighting, "
    "and a polished family-friendly animated-film render."
)
DEFAULT_STYLE_MEDIUM_EXCLUSIONS_EN = [
    "No live action, wildlife photography, documentary photography, or photographed animals.",
    "No photorealism, hyperreal fur, camera-captured texture, or real-world lens artifacts.",
    "No flat 2D illustration, painterly concept art, or mixed visual medium.",
]


class ProductionDesignPlanError(ValueError):
    pass


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionDesignPlanError(f"{label} must be an object")
    missing = sorted(keys - set(value))
    unknown = sorted(set(value) - keys)
    if missing or unknown:
        raise ProductionDesignPlanError(
            f"{label} must use exact keys; missing={missing}, unknown={unknown}"
        )
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductionDesignPlanError(f"{label} must be non-empty text")
    return value.strip()


def _text_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ProductionDesignPlanError(f"{label} must be a text array")
    result = [_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len({item.casefold() for item in result}) != len(result):
        raise ProductionDesignPlanError(f"{label} must not repeat values")
    return result


def _asset_ids(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    result = _text_list(value, label, allow_empty=allow_empty)
    invalid = [item for item in result if not ASSET_ID_RE.fullmatch(item)]
    if invalid:
        raise ProductionDesignPlanError(f"{label} has invalid IDs {invalid}")
    return result


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProductionDesignPlanError(f"{label} must be a positive integer")
    return value


def _media_path(value: Any, label: str) -> str:
    raw = _text(value, label)
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or ".." in path.parts
        or len(path.parts) < 3
        or path.parts[:2] != ("workspace", "assets")
        or path.suffix.casefold() != ".png"
    ):
        raise ProductionDesignPlanError(
            f"{label} must be a repository-relative PNG path under workspace/assets/"
        )
    return path.as_posix()


def _actor_profile(value: Any, label: str) -> dict[str, str]:
    profile = _exact(value, ACTOR_PROFILE_KEYS, label)
    result: dict[str, str] = {}
    for key in sorted(ACTOR_PROFILE_KEYS):
        text = _text(profile[key], f"{label}.{key}")
        if STORY_BOUND_ACTOR_PROFILE_RE.search(text):
            raise ProductionDesignPlanError(
                f"{label}.{key} must describe a reusable actor, not one story"
            )
        result[key] = text
    return result


def _body_topology(value: Any, label: str) -> dict[str, Any]:
    topology = _exact(value, BODY_TOPOLOGY_KEYS, label)
    raw_limb_sets = topology["limb_sets"]
    if not isinstance(raw_limb_sets, list) or not raw_limb_sets:
        raise ProductionDesignPlanError(f"{label}.limb_sets must be non-empty")
    limb_sets: list[dict[str, Any]] = []
    seen_limb_kinds: set[str] = set()
    for index, raw in enumerate(raw_limb_sets):
        item = _exact(raw, LIMB_SET_KEYS, f"{label}.limb_sets[{index}]")
        kind = _text(item["kind_en"], f"{label}.limb_sets[{index}].kind_en")
        if kind.casefold() in seen_limb_kinds:
            raise ProductionDesignPlanError(f"{label}.limb_sets repeats {kind!r}")
        seen_limb_kinds.add(kind.casefold())
        limb_sets.append(
            {
                "kind_en": kind,
                "count": _positive_int(
                    item["count"], f"{label}.limb_sets[{index}].count"
                ),
                "function_en": _text(
                    item["function_en"], f"{label}.limb_sets[{index}].function_en"
                ),
            }
        )
    total = _positive_int(topology["total_limb_count"], f"{label}.total_limb_count")
    if total != sum(item["count"] for item in limb_sets):
        raise ProductionDesignPlanError(
            f"{label}.total_limb_count must equal the limb-set sum"
        )
    raw_appendages = topology["non_limb_appendages"]
    if not isinstance(raw_appendages, list):
        raise ProductionDesignPlanError(
            f"{label}.non_limb_appendages must be an array"
        )
    appendages: list[dict[str, Any]] = []
    seen_appendages: set[str] = set()
    for index, raw in enumerate(raw_appendages):
        item = _exact(
            raw,
            NON_LIMB_APPENDAGE_KEYS,
            f"{label}.non_limb_appendages[{index}]",
        )
        kind = _text(
            item["kind_en"], f"{label}.non_limb_appendages[{index}].kind_en"
        )
        if kind.casefold() in seen_appendages:
            raise ProductionDesignPlanError(
                f"{label}.non_limb_appendages repeats {kind!r}"
            )
        seen_appendages.add(kind.casefold())
        appendages.append(
            {
                "kind_en": kind,
                "count": _positive_int(
                    item["count"], f"{label}.non_limb_appendages[{index}].count"
                ),
            }
        )
    return {
        "body_plan_en": _text(topology["body_plan_en"], f"{label}.body_plan_en"),
        "total_limb_count": total,
        "limb_sets": limb_sets,
        "non_limb_appendages": appendages,
        "topology_lock_en": _text(
            topology["topology_lock_en"], f"{label}.topology_lock_en"
        ),
    }


def _generation_prompt(
    value: Any, *, label: str, asset_type: str
) -> dict[str, Any]:
    prompt = _exact(value, PROMPT_KEYS, label)
    continuity = _exact(
        prompt["continuity"], PROMPT_CONTINUITY_KEYS, f"{label}.continuity"
    )
    result = {
        "intent_en": _text(prompt["intent_en"], f"{label}.intent_en"),
        "subject_en": _text(prompt["subject_en"], f"{label}.subject_en"),
        "background_en": _text(prompt["background_en"], f"{label}.background_en"),
        "composition_en": _text(
            prompt["composition_en"], f"{label}.composition_en"
        ),
        "continuity": {
            "reference_asset_ids": _asset_ids(
                continuity["reference_asset_ids"],
                f"{label}.continuity.reference_asset_ids",
            ),
            "locks_en": _text_list(
                continuity["locks_en"], f"{label}.continuity.locks_en"
            ),
        },
        "style_en": _text(prompt["style_en"], f"{label}.style_en"),
        "exclusions_en": _text_list(
            prompt["exclusions_en"], f"{label}.exclusions_en"
        ),
    }
    if asset_type == "location_master":
        if result["background_en"] == PURE_WHITE_BACKGROUND_EN:
            raise ProductionDesignPlanError(
                f"{label}.background_en must describe the actual location"
            )
    elif result["background_en"] != PURE_WHITE_BACKGROUND_EN:
        raise ProductionDesignPlanError(
            f"{label}.background_en must exactly equal the pure-white asset backdrop"
        )
    if asset_type == "character" and STORY_BOUND_CHARACTER_PROMPT_RE.search(
        json.dumps(result, ensure_ascii=False)
    ):
        raise ProductionDesignPlanError(
            f"{label} must present a reusable actor, not a story performance state"
        )
    serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if len(serialized) > MAX_GENERATION_PROMPT_CHARS:
        raise ProductionDesignPlanError(
            f"{label} exceeds the {MAX_GENERATION_PROMPT_CHARS}-character limit"
        )
    if PROMPT_PATCH_LANGUAGE_RE.search(serialized):
        raise ProductionDesignPlanError(
            f"{label} contains patch/override language instead of one coherent Prompt"
        )
    exclusions = " ".join(result["exclusions_en"]).casefold()
    required_groups = [
        ("text", "subtitle", "typography"),
        ("logo", "brand mark"),
        ("watermark",),
        ("duplicate", "clone", "repeated subject"),
    ]
    if asset_type == "character":
        required_groups.extend(
            [
                ("anatomy", "limb"),
                ("multiview", "multi-view", "collage"),
                ("single subject", "one subject", "isolated subject"),
            ]
        )
    if any(not any(term in exclusions for term in group) for group in required_groups):
        raise ProductionDesignPlanError(
            f"{label}.exclusions_en must cover unwanted text, logos, watermarks, "
            "duplicate subjects, and character presentation/anatomy when applicable"
        )
    return result


def _fixed_set_elements(
    value: Any,
    *,
    label: str,
    topology: Any,
    prompt: dict[str, Any],
) -> list[str]:
    """Validate authored fixed-set authority without inventing prompt prose."""

    elements = _text_list(value, label, allow_empty=True)
    if not isinstance(topology, dict):
        raise ProductionDesignPlanError(f"{label} requires an authored topology")
    obstacles = topology.get("fixed_obstacles")
    placements = topology.get("fixed_prop_placements")
    if not isinstance(obstacles, list) or not isinstance(placements, list):
        raise ProductionDesignPlanError(
            f"{label} requires topology.fixed_obstacles and "
            "topology.fixed_prop_placements arrays"
        )
    if (obstacles or placements) and not elements:
        raise ProductionDesignPlanError(
            f"{label} must name every necessary fixed furniture, set piece, and "
            "installed prop visible in the location master"
        )
    locks = prompt["continuity"]["locks_en"]
    missing_locks = [element for element in elements if element not in locks]
    if missing_locks:
        raise ProductionDesignPlanError(
            f"{label} entries must appear verbatim in generation_prompt.continuity."
            f"locks_en; missing={missing_locks}"
        )
    return elements


def _voice_generation_prompt(
    value: Any,
    *,
    label: str,
    sample_text_en: str,
    voice_description_en: str,
) -> dict[str, Any]:
    prompt = _exact(value, VOICE_PROMPT_KEYS, label)
    result = {
        "text_en": _text(prompt["text_en"], f"{label}.text_en"),
        "voice_direction_en": _text(
            prompt["voice_direction_en"], f"{label}.voice_direction_en"
        ),
        "delivery_en": _text(prompt["delivery_en"], f"{label}.delivery_en"),
        "exclusions_en": _text_list(
            prompt["exclusions_en"], f"{label}.exclusions_en"
        ),
    }
    if result["text_en"] != sample_text_en:
        raise ProductionDesignPlanError(
            f"{label}.text_en must exactly equal voice_sample_text_en"
        )
    if result["voice_direction_en"] != voice_description_en:
        raise ProductionDesignPlanError(
            f"{label}.voice_direction_en must exactly equal voice_description_en"
        )
    serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if len(serialized) > MAX_VOICE_PROMPT_CHARS:
        raise ProductionDesignPlanError(
            f"{label} exceeds the {MAX_VOICE_PROMPT_CHARS}-character limit"
        )
    if PROMPT_PATCH_LANGUAGE_RE.search(serialized):
        raise ProductionDesignPlanError(
            f"{label} contains patch/override language instead of one coherent Prompt"
        )
    return result


def _provider_generation_prompt(prompt: dict[str, Any]) -> dict[str, Any]:
    provider_prompt = dict(prompt)
    if prompt["style_en"] == DEFAULT_STYLE_AUTHORITY_EN:
        provider_prompt["style_execution_en"] = DEFAULT_STYLE_EXECUTION_EN
        provider_prompt["style_medium_exclusions_en"] = list(
            DEFAULT_STYLE_MEDIUM_EXCLUSIONS_EN
        )
    else:
        provider_prompt["style_execution_en"] = (
            "Execute the authored visual style exactly as follows, without medium "
            f"drift: {prompt['style_en']}"
        )
        provider_prompt["style_medium_exclusions_en"] = [
            "Do not drift into a different visual medium or aesthetic treatment."
        ]
    return provider_prompt


def render_generation_prompt(prompt: dict[str, Any]) -> str:
    """Compile the validated plan into one provider-facing canonical Prompt."""

    return json.dumps(_provider_generation_prompt(prompt), ensure_ascii=False, indent=2)


def validate_generation_prompt_text(text: str, *, asset_type: str) -> str:
    """Accept only one canonical JSON prompt object, with no prefix or suffix."""

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProductionDesignPlanError(
            "Generation prompt must be one structured JSON object"
        ) from exc
    provider_prompt = _exact(raw, PROVIDER_PROMPT_KEYS, "generation prompt")
    base_prompt = {key: provider_prompt[key] for key in PROMPT_KEYS}
    prompt = _generation_prompt(
        base_prompt, label="generation prompt", asset_type=asset_type
    )
    expected_provider_prompt = _provider_generation_prompt(prompt)
    if provider_prompt != expected_provider_prompt:
        raise ProductionDesignPlanError(
            "Generation prompt style execution fields must exactly match the "
            "compiled screenplay-owned style authority"
        )
    canonical = render_generation_prompt(prompt)
    if text.strip() != canonical:
        raise ProductionDesignPlanError(
            "Generation prompt must use canonical JSON formatting with no appended prose"
        )
    return canonical


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProductionDesignPlanError(f"{label} must be an array")
    return value


def load_production_design_plan(
    task_root: Path,
    *,
    performance: dict[str, Any],
    screenplay: dict[str, Any],
) -> dict[str, Any]:
    """Reject missing or contradictory model fields; never infer replacements."""

    path = task_root / PLAN_RELATIVE_PATH
    payload = load_json_object(
        path,
        label="current production-design plan",
        error_type=ProductionDesignPlanError,
    )
    plan = _exact(payload, ROOT_KEYS, "production-design plan")
    if plan["contract"] != "production-design-plan/v2":
        raise ProductionDesignPlanError(
            "production-design plan contract must be production-design-plan/v2"
        )

    speaking_ids = {
        call["entity_id"]
        for segment in performance["scene_segment_calls"]
        for call in segment["calls"]
        if call["speaks"]
    }
    entities = performance["performance_entities"]
    individual_ids = {
        entity["entity_id"]
        for entity in performance["performance_entities"]
        if entity["entity_kind"] == "individual"
    }
    ensembles_by_role: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        if entity["entity_kind"] != "anonymous_ensemble":
            continue
        role_type = _text(
            entity.get("group_role_type_en"),
            f"performance entity {entity['entity_id']}.group_role_type_en",
        )
        if role_type == "none":
            raise ProductionDesignPlanError(
                f"Anonymous ensemble {entity['entity_id']} lacks a group role type"
            )
        if role_type not in ensembles_by_role:
            ensembles_by_role[role_type] = []
        ensembles_by_role[role_type].append(entity)

    characters: list[dict[str, Any]] = []
    character_ids: set[str] = set()
    for index, raw in enumerate(_list(plan["characters"], "characters")):
        item = _exact(raw, CHARACTER_KEYS, f"characters[{index}]")
        entity_id = _text(item["entity_id"], f"characters[{index}].entity_id")
        if entity_id in character_ids:
            raise ProductionDesignPlanError(f"characters repeats {entity_id}")
        character_ids.add(entity_id)
        speech_rate = item["voice_speech_rate"]
        if (
            isinstance(speech_rate, bool)
            or not isinstance(speech_rate, int)
            or not -50 <= speech_rate <= 100
        ):
            raise ProductionDesignPlanError(
                f"character {entity_id}.voice_speech_rate must be -50..100"
            )
        if item["type"] != "character":
            raise ProductionDesignPlanError(
                f"character {entity_id}.type must be character"
            )
        speaks = entity_id in speaking_ids
        if speaks:
            voice_description: str | None = _text(
                item["voice_description_en"],
                f"character {entity_id}.voice_description_en",
            )
            voice_sample_text: str | None = _text(
                item["voice_sample_text_en"],
                f"character {entity_id}.voice_sample_text_en",
            )
            voice_generation_prompt: dict[str, Any] | None = (
                _voice_generation_prompt(
                    item["voice_generation_prompt"],
                    label=f"character {entity_id}.voice_generation_prompt",
                    sample_text_en=voice_sample_text,
                    voice_description_en=voice_description,
                )
            )
        else:
            if (
                item["voice_description_en"] != "none"
                or item["voice_sample_text_en"] != "none"
                or item["voice_speech_rate"] != 0
                or item["voice_generation_prompt"] != "none"
            ):
                raise ProductionDesignPlanError(
                    f"silent Kind=individual character {entity_id} must use "
                    "voice_description_en=none, voice_sample_text_en=none, "
                    "voice_speech_rate=0, and voice_generation_prompt=none"
                )
            voice_description = None
            voice_sample_text = None
            voice_generation_prompt = None
        character = {
            "type": "character",
            "entity_id": entity_id,
            "speaks": speaks,
            "actor_profile": _actor_profile(
                item["actor_profile"], f"character {entity_id}.actor_profile"
            ),
            "description_en": _text(
                item["description_en"], f"character {entity_id}.description_en"
            ),
            "body_topology": _body_topology(
                item["body_topology"], f"character {entity_id}.body_topology"
            ),
            "media_path": _media_path(
                item["media_path"], f"character {entity_id}.media_path"
            ),
            "generation_prompt": _generation_prompt(
                item["generation_prompt"],
                label=f"character {entity_id}.generation_prompt",
                asset_type="character",
            ),
        }
        if speaks:
            character.update(
                {
                    "voice_description_en": voice_description,
                    "voice_sample_text_en": voice_sample_text,
                    "voice_speech_rate": speech_rate,
                    "voice_generation_prompt": voice_generation_prompt,
                }
            )
        characters.append(character)
    if character_ids != individual_ids:
        raise ProductionDesignPlanError(
            "characters must exactly cover Kind=individual entities, including "
            "silent individuals; "
            f"expected={sorted(individual_ids)}, actual={sorted(character_ids)}"
        )

    ensembles: list[dict[str, Any]] = []
    ensemble_ids: set[str] = set()
    ensemble_by_role: dict[str, str] = {}
    for index, raw in enumerate(
        _list(plan["ensemble_rosters"], "ensemble_rosters")
    ):
        item = _exact(raw, ENSEMBLE_KEYS, f"ensemble_rosters[{index}]")
        asset_id = _text(item["asset_id"], f"ensemble_rosters[{index}].asset_id")
        role_type = _text(
            item["group_role_type_en"],
            f"ensemble_roster {asset_id}.group_role_type_en",
        )
        if (
            not ASSET_ID_RE.fullmatch(asset_id)
            or asset_id in ensemble_ids
            or role_type in ensemble_by_role
        ):
            raise ProductionDesignPlanError(
                f"Invalid/repeated ensemble ID or role: {asset_id}/{role_type}"
            )
        ensemble_ids.add(asset_id)
        if item["type"] != "ensemble_roster":
            raise ProductionDesignPlanError(
                f"ensemble_roster {asset_id}.type must be ensemble_roster"
            )
        ensemble_by_role[role_type] = asset_id
        allowed = _text_list(
            item["allowed_member_types_en"],
            f"ensemble_roster {asset_id}.allowed_member_types_en",
        )
        if role_type not in ensembles_by_role:
            raise ProductionDesignPlanError(
                f"ensemble_roster {asset_id} names an unknown anonymous-ensemble role"
            )
        authored_allowed = [
            member
            for entity in ensembles_by_role[role_type]
            for member in entity["ensemble_member_types_en"]
        ]
        if allowed != authored_allowed:
            raise ProductionDesignPlanError(
                f"ensemble_roster {asset_id} member types differ from writer authority; "
                f"expected={authored_allowed}, actual={allowed}"
            )
        variation = _exact(
            item["variation_profile"],
            VARIATION_PROFILE_KEYS,
            f"ensemble_roster {asset_id}.variation_profile",
        )
        ensembles.append(
            {
                "type": "ensemble_roster",
                "asset_id": asset_id,
                "group_role_type_en": role_type,
                "description_en": _text(
                    item["description_en"],
                    f"ensemble_roster {asset_id}.description_en",
                ),
                "member_type_id": _text(
                    item["member_type_id"],
                    f"ensemble_roster {asset_id}.member_type_id",
                ),
                "allowed_member_types_en": allowed,
                "subject_count": _positive_int(
                    item["subject_count"],
                    f"ensemble_roster {asset_id}.subject_count",
                ),
                "variation_profile": {
                    "locked_traits_en": _text(
                        variation["locked_traits_en"],
                        f"ensemble_roster {asset_id}.variation_profile.locked_traits_en",
                    ),
                    "allowed_variation_en": _text(
                        variation["allowed_variation_en"],
                        f"ensemble_roster {asset_id}.variation_profile.allowed_variation_en",
                    ),
                },
                "media_path": _media_path(
                    item["media_path"], f"ensemble_roster {asset_id}.media_path"
                ),
                "generation_prompt": _generation_prompt(
                    item["generation_prompt"],
                    label=f"ensemble_roster {asset_id}.generation_prompt",
                    asset_type="ensemble_roster",
                ),
            }
        )
    if set(ensemble_by_role) != set(ensembles_by_role):
        raise ProductionDesignPlanError(
            "ensemble_rosters must exactly cover Kind=anonymous_ensemble roles; "
            f"expected={sorted(ensembles_by_role)}, actual={sorted(ensemble_by_role)}"
        )

    props: list[dict[str, Any]] = []
    prop_ids: set[str] = set()
    for index, raw in enumerate(_list(plan["props"], "props")):
        item = _exact(raw, PROP_KEYS, f"props[{index}]")
        asset_id = _text(item["asset_id"], f"props[{index}].asset_id")
        if not ASSET_ID_RE.fullmatch(asset_id) or asset_id in prop_ids:
            raise ProductionDesignPlanError(f"Invalid/repeated prop ID {asset_id}")
        prop_ids.add(asset_id)
        if item["type"] != "prop":
            raise ProductionDesignPlanError(f"prop {asset_id}.type must be prop")
        props.append(
            {
                "type": "prop",
                "asset_id": asset_id,
                "description_en": _text(
                    item["description_en"], f"prop {asset_id}.description_en"
                ),
                "media_path": _media_path(
                    item["media_path"], f"prop {asset_id}.media_path"
                ),
                "generation_prompt": _generation_prompt(
                    item["generation_prompt"],
                    label=f"prop {asset_id}.generation_prompt",
                    asset_type="prop",
                ),
            }
        )

    costumes: list[dict[str, Any]] = []
    costume_ids: set[str] = set()
    for index, raw in enumerate(_list(plan["costumes"], "costumes")):
        item = _exact(raw, COSTUME_KEYS, f"costumes[{index}]")
        asset_id = _text(item["asset_id"], f"costumes[{index}].asset_id")
        character_id = _text(
            item["character_id"], f"costume {asset_id}.character_id"
        )
        if (
            not ASSET_ID_RE.fullmatch(asset_id)
            or asset_id in costume_ids
            or character_id not in character_ids
        ):
            raise ProductionDesignPlanError(
                f"Invalid/repeated costume or owner for {asset_id}"
            )
        costume_ids.add(asset_id)
        if item["type"] != "costume":
            raise ProductionDesignPlanError(
                f"costume {asset_id}.type must be costume"
            )
        costumes.append(
            {
                "type": "costume",
                "asset_id": asset_id,
                "character_id": character_id,
                "description_en": _text(
                    item["description_en"], f"costume {asset_id}.description_en"
                ),
                "appearance_state_en": _text(
                    item["appearance_state_en"],
                    f"costume {asset_id}.appearance_state_en",
                ),
                "media_path": _media_path(
                    item["media_path"], f"costume {asset_id}.media_path"
                ),
                "generation_prompt": _generation_prompt(
                    item["generation_prompt"],
                    label=f"costume {asset_id}.generation_prompt",
                    asset_type="costume",
                ),
            }
        )

    role_asset_by_entity = {
        entity["entity_id"]: (
            entity["entity_id"]
            if entity["entity_kind"] == "individual"
            else ensemble_by_role[entity["group_role_type_en"]]
        )
        for entity in entities
    }
    on_screen_by_scene: dict[str, set[str]] = {}
    state_changing_by_scene: dict[str, set[str]] = {}
    for segment in performance["scene_segment_calls"]:
        scene_id = segment["scene_id"]
        if scene_id not in on_screen_by_scene:
            on_screen_by_scene[scene_id] = set()
            state_changing_by_scene[scene_id] = set()
        on_screen_by_scene[scene_id].update(
            call["entity_id"]
            for call in segment["calls"]
            if call.get("presence_mode") == "on_screen"
        )
        state_changing_by_scene[scene_id].update(
            role_asset_by_entity[call["entity_id"]]
            for call in segment["calls"]
            if call.get("presence_mode") == "on_screen"
            and call.get("state_changing_action") is True
        )
    entity_order = [entity["entity_id"] for entity in entities]

    locations: list[dict[str, Any]] = []
    location_ids: set[str] = set()
    covered_scene_ids: list[str] = []
    for index, raw in enumerate(_list(plan["locations"], "locations")):
        item = _exact(raw, LOCATION_KEYS, f"locations[{index}]")
        location_id = _text(item["location_id"], f"locations[{index}].location_id")
        if not ASSET_ID_RE.fullmatch(location_id) or location_id in location_ids:
            raise ProductionDesignPlanError(
                f"Invalid/repeated location ID {location_id}"
            )
        location_ids.add(location_id)
        if item["type"] != "location_master":
            raise ProductionDesignPlanError(
                f"location {location_id}.type must be location_master"
            )
        scene_ids = _asset_ids(
            item["scene_ids"], f"location {location_id}.scene_ids", allow_empty=False
        )
        covered_scene_ids.extend(scene_ids)
        included_props = _asset_ids(
            item["included_prop_ids"], f"location {location_id}.included_prop_ids"
        )
        if not set(included_props).issubset(prop_ids):
            raise ProductionDesignPlanError(
                f"location {location_id} contains unknown included_prop_ids"
            )
        expected_role_lists: list[list[str]] = []
        for scene_id in scene_ids:
            if scene_id not in on_screen_by_scene:
                raise ProductionDesignPlanError(
                    f"location {location_id} names Scene {scene_id} without calls"
                )
            current = on_screen_by_scene[scene_id]
            expected_role_lists.append(
                list(
                    dict.fromkeys(
                        role_asset_by_entity[entity_id]
                        for entity_id in entity_order
                        if entity_id in current
                    )
                )
            )
        expected_role_union = list(
            dict.fromkeys(
                role_asset_id
                for roles in expected_role_lists
                for role_asset_id in roles
            )
        )
        embedded_npcs = _asset_ids(
            item["embedded_npc_asset_ids"],
            f"location {location_id}.embedded_npc_asset_ids",
        )
        independent_performers = _asset_ids(
            item["independent_performer_asset_ids"],
            f"location {location_id}.independent_performer_asset_ids",
        )
        overlap = set(embedded_npcs).intersection(independent_performers)
        if overlap:
            raise ProductionDesignPlanError(
                f"location {location_id} role treatments overlap: {sorted(overlap)}"
            )
        expected_embedded_order = [
            role_asset_id
            for role_asset_id in expected_role_union
            if role_asset_id in set(embedded_npcs)
        ]
        expected_independent_order = [
            role_asset_id
            for role_asset_id in expected_role_union
            if role_asset_id not in set(embedded_npcs)
        ]
        if embedded_npcs != expected_embedded_order:
            raise ProductionDesignPlanError(
                f"location {location_id}.embedded_npc_asset_ids must be an ordered "
                f"subset of writer-owned on-screen roles; expected order="
                f"{expected_embedded_order}, actual={embedded_npcs}"
            )
        if independent_performers != expected_independent_order:
            raise ProductionDesignPlanError(
                f"location {location_id} role treatments must exactly cover writer "
                f"on-screen authority; expected independent performers="
                f"{expected_independent_order}, actual={independent_performers}"
            )
        unstable_embedded = [
            role_asset_id
            for role_asset_id in embedded_npcs
            if any(role_asset_id not in roles for roles in expected_role_lists)
        ]
        if unstable_embedded:
            raise ProductionDesignPlanError(
                f"location {location_id} embeds NPCs absent from one or more bound "
                f"Scenes: {unstable_embedded}; split the Location master or keep the "
                "role independent"
            )
        speaking_embedded = [
            role_asset_id
            for role_asset_id in embedded_npcs
            if role_asset_id in speaking_ids
        ]
        if speaking_embedded:
            raise ProductionDesignPlanError(
                f"location {location_id} embeds dialogue performers "
                f"{speaking_embedded}; every speaking role must remain independent"
            )
        active_embedded = [
            role_asset_id
            for role_asset_id in embedded_npcs
            if any(
                role_asset_id in state_changing_by_scene[scene_id]
                for scene_id in scene_ids
            )
        ]
        if active_embedded:
            raise ProductionDesignPlanError(
                f"location {location_id} embeds state-changing performers "
                f"{active_embedded}; story-active roles must remain independent"
            )
        topology = item["topology"]
        landmarks = item["landmarks"]
        if not isinstance(topology, dict) or not topology:
            raise ProductionDesignPlanError(
                f"location {location_id}.topology must be a non-empty object"
            )
        if not isinstance(landmarks, list) or not landmarks:
            raise ProductionDesignPlanError(
                f"location {location_id}.landmarks must be a non-empty array"
            )
        generation_prompt = _generation_prompt(
            item["generation_prompt"],
            label=f"location {location_id}.generation_prompt",
            asset_type="location_master",
        )
        fixed_set_elements = _fixed_set_elements(
            item["fixed_set_elements_en"],
            label=f"location {location_id}.fixed_set_elements_en",
            topology=topology,
            prompt=generation_prompt,
        )
        locations.append(
            {
                "type": "location_master",
                "location_id": location_id,
                "scene_ids": scene_ids,
                "description_en": _text(
                    item["description_en"], f"location {location_id}.description_en"
                ),
                "included_prop_ids": included_props,
                "embedded_npc_asset_ids": embedded_npcs,
                "independent_performer_asset_ids": independent_performers,
                "fixed_set_elements_en": fixed_set_elements,
                "environment_state_en": _text(
                    item["environment_state_en"],
                    f"location {location_id}.environment_state_en",
                ),
                "lighting_state_en": _text(
                    item["lighting_state_en"],
                    f"location {location_id}.lighting_state_en",
                ),
                "palette_materials_en": _text(
                    item["palette_materials_en"],
                    f"location {location_id}.palette_materials_en",
                ),
                "topology": topology,
                "landmarks": landmarks,
                "media_path": _media_path(
                    item["media_path"], f"location {location_id}.media_path"
                ),
                "generation_prompt": generation_prompt,
            }
        )
    expected_scene_ids = [scene["scene_id"] for scene in screenplay["scenes"]]
    if (
        len(covered_scene_ids) != len(set(covered_scene_ids))
        or set(covered_scene_ids) != set(expected_scene_ids)
    ):
        raise ProductionDesignPlanError(
            "locations must partition every screenplay Scene exactly once; "
            f"expected={expected_scene_ids}, actual={covered_scene_ids}"
        )

    all_assets = [*characters, *ensembles, *props, *costumes, *locations]
    expected_style = screenplay["production_information"]["Visual Style"]
    for asset in all_assets:
        actual_style = asset["generation_prompt"]["style_en"]
        if actual_style != expected_style:
            asset_id = (
                asset.get("entity_id")
                or asset.get("asset_id")
                or asset.get("location_id")
            )
            raise ProductionDesignPlanError(
                f"asset {asset_id} style_en must exactly match screenplay Visual "
                f"Style {expected_style!r}"
            )
    ids = [
        asset.get("entity_id") or asset.get("asset_id") or asset.get("location_id")
        for asset in all_assets
    ]
    if len(ids) != len(set(ids)):
        raise ProductionDesignPlanError("production-design plan repeats an asset ID")
    paths = [asset["media_path"] for asset in all_assets]
    if len(paths) != len(set(paths)):
        raise ProductionDesignPlanError("production-design plan repeats a media_path")
    known_ids = set(ids)
    for asset in all_assets:
        asset_id = asset.get("entity_id") or asset.get("asset_id") or asset.get(
            "location_id"
        )
        references = asset["generation_prompt"]["continuity"][
            "reference_asset_ids"
        ]
        if not set(references).issubset(known_ids):
            raise ProductionDesignPlanError(
                f"asset {asset_id} references unknown assets {sorted(set(references)-known_ids)}"
            )
        if asset in props or asset in ensembles:
            expected_references: list[str] = []
        elif asset in costumes:
            expected_references = [asset["character_id"]]
        elif asset in locations:
            expected_references = [
                *asset["included_prop_ids"],
                *asset["embedded_npc_asset_ids"],
            ]
        else:
            expected_references = [
                reference for reference in references if reference in prop_ids
            ]
            if references != expected_references:
                raise ProductionDesignPlanError(
                    f"character {asset_id} may reference only independent props"
                )
        if references != expected_references:
            raise ProductionDesignPlanError(
                f"asset {asset_id} reference order must be fully model-authored and "
                f"consistent; expected={expected_references}, actual={references}"
            )

    story_objects = screenplay["story_objects"]
    story_object_by_id = {
        item["object_id"]: item for item in story_objects
    }
    raw_authorities = _list(
        plan["object_authorities"], "object_authorities"
    )
    object_authorities: list[dict[str, Any]] = []
    authority_by_object: dict[str, dict[str, Any]] = {}
    asset_by_id = {
        (
            asset.get("entity_id")
            or asset.get("asset_id")
            or asset.get("location_id")
        ): asset
        for asset in all_assets
    }
    locations_by_scene = {
        scene_id: location["location_id"]
        for location in locations
        for scene_id in location["scene_ids"]
    }
    for index, raw in enumerate(raw_authorities):
        item = _exact(
            raw,
            OBJECT_AUTHORITY_KEYS,
            f"object_authorities[{index}]",
        )
        object_id = _text(
            item["object_id"],
            f"object_authorities[{index}].object_id",
        )
        if object_id in authority_by_object:
            raise ProductionDesignPlanError(
                f"object_authorities repeats {object_id}"
            )
        story_object = story_object_by_id.get(object_id)
        if story_object is None:
            raise ProductionDesignPlanError(
                f"object_authorities names unknown Story Object {object_id}"
            )
        mode = _text(item["mode"], f"{object_id}.mode")
        if mode not in VISUAL_AUTHORITY_MODES:
            raise ProductionDesignPlanError(
                f"{object_id}.mode must be a supported visual-authority mode"
            )
        authority_asset_ids = _asset_ids(
            item["asset_ids"], f"{object_id}.asset_ids"
        )
        owner_kind = story_object["physical_owner_kind"]
        owner_id = story_object["physical_owner_id"]
        parent_authority = (
            authority_by_object.get(str(owner_id))
            if owner_kind == "object"
            else None
        )
        if owner_kind == "object" and parent_authority is None:
            raise ProductionDesignPlanError(
                f"{object_id} parent object must be routed earlier"
            )
        expected_mode = expected_visual_authority_mode(
            story_object,
            parent_mode=(
                str(parent_authority["mode"])
                if parent_authority is not None
                else None
            ),
        )
        if mode != expected_mode:
            raise ProductionDesignPlanError(
                f"{object_id} visual-authority mode must be {expected_mode}; "
                f"actual={mode}"
            )
        if mode == "segment_prompt_only":
            if authority_asset_ids:
                raise ProductionDesignPlanError(
                    f"{object_id} segment_prompt_only must not name asset_ids"
                )
        else:
            if not authority_asset_ids:
                raise ProductionDesignPlanError(
                    f"{object_id} {mode} requires asset_ids"
                )
            unknown = set(authority_asset_ids) - known_ids
            if unknown:
                raise ProductionDesignPlanError(
                    f"{object_id} names unknown visual-authority assets "
                    f"{sorted(unknown)}"
                )
        if mode == "dedicated_asset":
            dedicated_assets = [
                asset_by_id[asset_id] for asset_id in authority_asset_ids
            ]
            if owner_kind == "character":
                invalid = [
                    asset_id
                    for asset_id, asset in zip(authority_asset_ids, dedicated_assets)
                    if asset["type"] not in {"prop", "costume"}
                    or (
                        asset["type"] == "costume"
                        and asset["character_id"] != owner_id
                    )
                ]
            else:
                invalid = [
                    asset_id
                    for asset_id, asset in zip(authority_asset_ids, dedicated_assets)
                    if asset["type"] != "prop"
                ]
            if invalid:
                raise ProductionDesignPlanError(
                    f"{object_id} dedicated assets have incompatible types or owners: "
                    f"{invalid}"
                )
            if owner_kind == "environment":
                expected_locations = list(
                    dict.fromkeys(
                        locations_by_scene[scene_id]
                        for scene_id in story_object["scene_ids"]
                    )
                )
                prop_assets = [
                    asset_id
                    for asset_id in authority_asset_ids
                    if asset_by_id[asset_id]["type"] == "prop"
                ]
                for location_id in expected_locations:
                    location = asset_by_id[location_id]
                    missing_props = [
                        asset_id
                        for asset_id in prop_assets
                        if asset_id not in location["included_prop_ids"]
                    ]
                    if missing_props:
                        raise ProductionDesignPlanError(
                            f"{object_id} fixed dedicated props must be included in "
                            f"{location_id}: {missing_props}"
                        )
        elif mode == "covered_by_asset":
            if owner_kind == "environment":
                expected_assets = list(
                    dict.fromkeys(
                        locations_by_scene[scene_id]
                        for scene_id in story_object["scene_ids"]
                    )
                )
            elif owner_kind == "character":
                expected_assets = [
                    asset_id
                    for asset_id, asset in asset_by_id.items()
                    if asset_id == owner_id
                    or (
                        asset.get("type") == "costume"
                        and asset.get("character_id") == owner_id
                    )
                ]
            elif owner_kind == "object":
                parent = parent_authority
                if parent is None or not parent["asset_ids"]:
                    raise ProductionDesignPlanError(
                        f"{object_id} parent object must already resolve to assets"
                    )
                expected_assets = parent["asset_ids"]
            else:
                expected_assets = []
            if not set(authority_asset_ids).issubset(expected_assets):
                raise ProductionDesignPlanError(
                    f"{object_id} covered_by_asset must use its physical owner's "
                    f"approved assets; allowed={expected_assets}, "
                    f"actual={authority_asset_ids}"
                )
        authority = {
            "object_id": object_id,
            "mode": mode,
            "asset_ids": authority_asset_ids,
        }
        object_authorities.append(authority)
        authority_by_object[object_id] = authority
    expected_object_ids = [item["object_id"] for item in story_objects]
    actual_object_ids = [item["object_id"] for item in object_authorities]
    if actual_object_ids != expected_object_ids:
        raise ProductionDesignPlanError(
            "object_authorities must cover every Story Object exactly once and in "
            f"order; expected={expected_object_ids}, actual={actual_object_ids}"
        )
    mapped_prop_ids = {
        asset_id
        for authority in object_authorities
        for asset_id in authority["asset_ids"]
        if asset_id in prop_ids
    }
    if mapped_prop_ids != prop_ids:
        raise ProductionDesignPlanError(
            "Every independent prop asset must trace to a Story Object; "
            f"unmapped={sorted(prop_ids - mapped_prop_ids)}"
        )

    return {
        "contract": "production-design-plan/v2",
        "characters": characters,
        "ensemble_rosters": ensembles,
        "object_authorities": object_authorities,
        "props": props,
        "costumes": costumes,
        "locations": locations,
    }
