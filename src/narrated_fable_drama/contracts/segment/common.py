"""Shared Segment contract vocabulary, paths, errors, hashes, and JSON I/O."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from narrated_fable_drama.core.json_io import load_json_object, write_json_atomic
from narrated_fable_drama.core.paths import ProjectPaths

REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root

SCRIPT_DIR_RELATIVE = Path(".pending/virtual-production/seedance-segment-scripts")
CAPABILITY_PROFILE_RELATIVE = Path("virtual-production/seedance-capability-profile.json")
WHITE_MODEL_RESET_CONTRACT_RELATIVE = Path(
    "skills/virtual-production/assets/white-model-quality-reset.json"
)

SEGMENT_RE = re.compile(r"^segment-([0-9]{3,})$")
SCRIPT_RE = re.compile(r"^segment-([0-9]{3,})\.md$")
TOKEN_RE = re.compile(r"^@(Image|Video|Audio)([1-9][0-9]*)$")
TOKEN_SCAN_RE = re.compile(r"@(Image|Video|Audio)([1-9][0-9]*)")
PRECISE_TIME_RANGE_RE = re.compile(
    r"\b(?:from\s+)?[0-9]+(?:\.[0-9]+)?\s*(?:-|–|—|to)\s*"
    r"[0-9]+(?:\.[0-9]+)?\s*(?:s|sec(?:ond)?s?)\b",
    re.I,
)
DIALOGUE_CELL_RE = re.compile(
    r'(L-[0-9]{3,}); window=([0-9]+(?:\.[0-9]+)?)-'
    r'([0-9]+(?:\.[0-9]+)?); speaker=([a-z0-9]+(?:-[a-z0-9]+)*); '
    r'mode=([a-z_]+); transition=(T-[0-9]{3,}); text="([^"]+)"'
)

GENERATION_PLAN_HEADERS = (
    "Segment",
    "Screenplay Range",
    "Scene",
    "Duration Seconds",
    "Operation",
    "Predecessor",
    "Seam",
    "Internal Shots",
    "Packing Reason",
)
REFERENCE_PLAN_HEADERS = (
    "Provider Token",
    "Provider Role",
    "Asset Namespace",
    "Readable Subject",
    "Purpose",
    "Shot Scope",
    "Forbidden Inheritance",
)
ORDERED_SHOT_HEADERS = (
    "Shot",
    "Screenplay Shot",
    "Shot Size",
    "Transition and Camera",
    "Subject Action and Expression",
    "Space, Blocking and Gaze",
    "Persistent Anchors",
    "Lighting and Color",
    "Dialogue and Native Audio",
    "Landing and Edit",
)
CHARACTER_STATE_HEADERS = (
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
)
LOCATION_STATE_HEADERS = (
    "Location State Chain",
    "Segment",
    "Relationship",
    "State Source",
    "Temporal Evidence",
    "World and Population Evidence",
    "Persistent Anchors",
    "Allowed Changes",
)
SPEECH_TRANSITION_HEADERS = (
    "Transition ID",
    "Segment",
    "Line",
    "Speaker and Mode",
    "Trigger and Phrase Boundary",
    "Listener and Mouth Behavior",
    "J/L Cut and Visual Handoff",
    "Voice and Ambience Continuity",
)
ALLOWED_OPERATIONS = {"multimodal_reference", "video_extension", "text_to_video"}
ALLOWED_PROVIDER_ROLES = {
    "reference_image": "Image",
    "reference_video": "Video",
    "reference_audio": "Audio",
}
ALLOWED_DELIVERY_MODES = {
    "on_camera_dialogue",
    "on_camera_storytelling",
    "off_camera_storytelling",
    "external_voiceover",
    "embedded_character_dialogue",
}


class SegmentRuntimeError(RuntimeError):
    """Raised when Storyboard, Prompt, assets, or runtime transport disagree."""


def read_json(path: Path, *, label: str | None = None) -> dict[str, Any]:
    return load_json_object(
        path,
        label=label or "JSON",
        error_type=SegmentRuntimeError,
    )


def write_json(path: Path, value: Any) -> None:
    write_json_atomic(path, value, sort_keys=True)


def sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise SegmentRuntimeError(f"Cannot hash required file: {path}") from exc


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def token_sort_key(token: str) -> tuple[int, int]:
    match = TOKEN_RE.fullmatch(token)
    if not match:
        raise SegmentRuntimeError(f"Invalid provider token: {token}")
    return (
        {"Image": 0, "Video": 1, "Audio": 2}[match.group(1)],
        int(match.group(2)),
    )

