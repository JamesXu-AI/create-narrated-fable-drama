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
    r"(?:\b(?:from\s+)?[0-9]+(?:\.[0-9]+)?\s*(?:-|–|—|to)\s*"
    r"[0-9]+(?:\.[0-9]+)?\s*(?:s|sec(?:ond)?s?)\b|"
    r"(?<![\w@])[0-9٠-٩]+(?:[.,٫][0-9٠-٩]+)?\s*(?:-|–|—|إلى)\s*"
    r"[0-9٠-٩]+(?:[.,٫][0-9٠-٩]+)?\s*"
    r"(?:ثانية|ثانيتين|ثوان|ثوانٍ))",
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
    "Dialogue and Dubbing Audio",
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

ARABIC_ENGINEERED_SECTION_LABELS = (
    "الإعداد العام وخريطة المراجع:",
    "الجودة والقيود:",
)
ARABIC_SHOT_ELEMENT_LABELS = (
    "سلوك الكاميرا المهيمن:",
    "الشخصية والفعل:",
    "المكان والبيئة:",
    "الإضاءة والنبرة:",
)
ARABIC_SHOT_AUTHORITY_LABELS = (
    "مرجعية الانتقال والكاميرا من لوحة القصة:",
    "المرتكزات الثابتة:",
    "الهبوط والتحرير:",
)
ARABIC_VISUAL_DOCTRINE_LABELS = (
    "اقتصاد الشخصيات الظاهرة:",
    "محور النظرات واتجاه الشاشة:",
    "تغطية تقودها اللقطات القريبة:",
)
ARABIC_SHOT_SIZE_BY_ENUM = {
    "extreme_close_up": "لقطة شديدة القرب",
    "close_up": "لقطة قريبة",
    "medium_close_up": "لقطة متوسطة قريبة",
    "medium": "لقطة متوسطة",
    "medium_wide": "لقطة متوسطة واسعة",
    "wide": "لقطة واسعة",
    "extreme_wide": "لقطة شديدة الاتساع",
}
ARABIC_OPERATION_BY_ENUM = {
    "multimodal_reference": "توليد بالمرجع متعدد الوسائط",
    "video_extension": "تمديد الفيديو",
    "text_to_video": "تحويل النص إلى فيديو",
}
ARABIC_VISUAL_STYLE_BY_NAME = {
    "3D Healing Animation": "رسوم متحركة علاجية ثلاثية الأبعاد",
}
ARABIC_POSITION_CHANGE_EXCEPTION_PREFIX = "استثناء تغيير الموضع:"
ARABIC_SEEDANCE_DIALOGUE_REPLACEMENT_DIRECTIVE = (
    "صوت سيدانس: ينشئ المسار الصوتي الأصلي الكامل للأجواء والحركة، "
    "وتنطق الشخصية المرئية الحوار العربي لتوجيه حركة الفم؛ بعد التوليد "
    "يُحذف كل صوت شخصيات ويُستبدل بالحوار العربي الدقيق من إليفن لابز، "
    "وتُمنع الموسيقى والترجمات."
)
ARABIC_QUALITY_FALLBACK_DIRECTIVE = (
    "وضوح سينمائي عالي التفاصيل؛ ثبات هوية الشخصية ووجهها وملابسها "
    "وتشريحها؛ ملامح وجه واضحة؛ من دون قفزات في الوجه أو أطراف زائدة أو "
    "اختراق للأجسام أو قصّ أو تشوه أو شعارات أو علامات مائية."
)
ARABIC_LETTER_RE = re.compile(
    r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]"
)
LATIN_LETTER_RE = re.compile(r"[A-Za-z]")


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
