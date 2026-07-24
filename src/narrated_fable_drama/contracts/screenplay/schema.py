"""Shared schema vocabulary and primitive predicates for screenplay contracts."""

from __future__ import annotations

import re
from typing import Any

from narrated_fable_drama.contracts.boundary import AUTHORING_TRANSITION_TYPES

SEGMENT_ID_RE = re.compile(r"^segment-[0-9]{3,}$")
BEAT_ID_RE = re.compile(r"^BEAT-[A-Za-z0-9_.-]+$")
SLUGLINE_RE = re.compile(r"^(INT|EXT)\. .+ - .+$")
WORD_RE = re.compile(
    r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*|"
    r"[\u3400-\u9fff]|[\u3040-\u30ff]|[\uac00-\ud7af]|"
    r"[\u0600-\u06ff]+|[^\W\d_]+",
    re.UNICODE,
)

DRAMATIC_WORKLOADS = {
    "action_led",
    "mixed_dialogue_action",
    "dialogue_led",
}
MINIMUM_ACTION_REACTION_SECONDS = 1.0

SCALE_VIEWS = {
    "establishing",
    "wide",
    "medium",
    "close_up",
    "extreme_close_up",
    "insert",
    "reaction",
    "pov",
}
WIDE_SCALE_VIEWS = {"establishing", "wide"}
TIGHT_ATTENTION_VIEWS = {
    "close_up",
    "extreme_close_up",
    "insert",
    "reaction",
    "pov",
}
CHARACTER_STORY_ROLES = {"lead", "supporting", "npc"}
NARRATION_ELIGIBILITIES = {"storyteller", "dialogue_only", "both", "none"}
SPEECH_DELIVERY_MODES = {
    "on_camera_dialogue",
    "on_camera_storytelling",
    "off_camera_storytelling",
    "external_voiceover",
    "embedded_character_dialogue",
}
ON_CAMERA_SPEECH_MODES = {
    "on_camera_dialogue",
    "on_camera_storytelling",
    "embedded_character_dialogue",
}
OFF_CAMERA_SPEECH_MODES = {
    "off_camera_storytelling",
    "external_voiceover",
}
ENTITY_KINDS = {"individual", "anonymous_ensemble"}
PRESENCE_MODES = {"on_screen", "off_screen", "voice_over"}
APPEARANCE_MODES = {"present_at_open", "enters", "not_visible"}
DIALOGUE_ADDRESSEE_SPECIALS = {"self", "narration"}
ENVIRONMENT_KINDS = {"INT", "EXT", "MIXED"}
SCENE_ENTRY_BOUNDARIES = {
    "opening",
    "time_change",
    "place_change",
    "time_and_place_change",
    "narrative_event_change",
}
INCOMING_VISUAL_REQUIREMENTS = {
    "independent",
    "state_match",
    "continuous_motion",
    "strong_coverage_reset",
}
TRANSITION_DESIGN_TYPES = AUTHORING_TRANSITION_TYPES
DIEGETIC_PRESENCE_STATES = {
    "present_in_location",
    "absent_from_location",
}
VISIBILITY_REQUIREMENTS = {
    "visible_every_shot",
    "visible_in_required_shots",
    "may_be_offscreen",
    "must_remain_absent",
}
STAGE_TABLEAU_RISK_RE = re.compile(
    r"\b(?:all\s+(?:the\s+)?(?:animals|characters|people|villagers|students|guests|"
    r"workers|soldiers|courtiers)|everyone|the\s+(?:animals|characters|group|cast|crowd))\b"
    r"[^.!?]{0,100}\b(?:stand|stands|stood|standing|line\s+up|lined\s+up|semicircle)\b|"
    r"\b(?:take|takes|took)\s+turns?\s+(?:speaking|talking|answering)\b|"
    r"\b(?:face|faces|facing|look|looks|looking)\s+(?:at|toward)?\s*(?:the\s+)?camera\b",
    re.IGNORECASE,
)
INHERITED_VISUAL_PHASE_RE = re.compile(
    r"\b(?:continue|continues|continued|continuing|resume|resumes|inherit|inherits|"
    r"preserve|preserves|match|matches)\b[^.]{0,100}\b"
    r"(?:motion|movement|action\s+phase|body\s+phase|pose|position|facing|"
    r"screen\s+direction|eyeline|blocking|performance\s+phase)\b|"
    r"\b(?:same|exact|unfinished|inherited)\b[^.]{0,80}\b"
    r"(?:motion|movement|pose|position|facing|blocking|performance\s+phase)\b",
    re.IGNORECASE,
)


def concrete(value: Any, *, allow_none: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().casefold()
    if allow_none and normalized == "none":
        return True
    if normalized in {"", "none", "n/a", "na", "same", "consistent", "tbd"}:
        return False
    return len(WORD_RE.findall(value)) >= 3


def present(value: Any, *, allow_none: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().casefold()
    if allow_none and normalized == "none":
        return True
    return normalized not in {
        "",
        "none",
        "n/a",
        "na",
        "same",
        "consistent",
        "tbd",
    }
