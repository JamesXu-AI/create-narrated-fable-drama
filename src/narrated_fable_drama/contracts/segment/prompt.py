"""Parse and validate exact Seedance Segment Prompt files."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.segment.common import (
    ARABIC_ENGINEERED_SECTION_LABELS,
    ARABIC_LETTER_RE,
    ARABIC_OPERATION_BY_ENUM,
    ARABIC_POSITION_CHANGE_EXCEPTION_PREFIX,
    ARABIC_SEEDANCE_DIALOGUE_REPLACEMENT_DIRECTIVE,
    ARABIC_SHOT_AUTHORITY_LABELS,
    ARABIC_SHOT_ELEMENT_LABELS,
    ARABIC_SHOT_SIZE_BY_ENUM,
    ARABIC_VISUAL_DOCTRINE_LABELS,
    LATIN_LETTER_RE,
    PRECISE_TIME_RANGE_RE,
    SCRIPT_RE,
    TOKEN_SCAN_RE,
    SegmentRuntimeError,
    token_sort_key,
)
from narrated_fable_drama.contracts.segment.storyboard import (
    storyboard_segment_rows,
)

ENGINEERED_SECTION_LABELS = ARABIC_ENGINEERED_SECTION_LABELS
SHOT_ELEMENT_LABELS = ARABIC_SHOT_ELEMENT_LABELS
SHOT_AUTHORITY_LABELS = ARABIC_SHOT_AUTHORITY_LABELS
SHOT_HEADING_RE = re.compile(
    r"^(?:#{1,6}\s*)?اللقطة ([1-9١-٩][0-9٠-٩]*): ("
    + "|".join(
        re.escape(value)
        for value in sorted(
            ARABIC_SHOT_SIZE_BY_ENUM.values(),
            key=len,
            reverse=True,
        )
    )
    + r")\.",
    re.MULTILINE,
)
SHOT_SIZE_ENUM_BY_ARABIC = {
    value: key for key, value in ARABIC_SHOT_SIZE_BY_ENUM.items()
}
CAMERA_FAMILY_PATTERNS = {
    "locked": re.compile(r"\b(?:ثابت|ثابتة|مقفلة)\b"),
    "pan": re.compile(r"\b(?:بانورامي|بانورامية)\b|تحريك أفقي"),
    "tilt": re.compile(r"\bإمالة\b|ميل رأسي"),
    "dolly": re.compile(
        r"\bدولي\b|دفع دولي|دفع(?: خفيف(?:ة)?)? إلى (?:الداخل|الأمام)|"
        r"اقتراب محوري|ابتعاد محوري"
    ),
    "track": re.compile(r"\b(?:تتبّع|تتبع|ملاحقة)\b"),
    "pedestal": re.compile(r"رفع عمودي|خفض عمودي|بيدستال"),
    "arc": re.compile(r"\b(?:قوس|مدار)\b|دوران مداري"),
    "crane": re.compile(r"\bرافعة\b|ذراع رافعة"),
    "zoom": re.compile(r"\bزوم\b|تكبير بصري|تصغير بصري"),
}
INTERNAL_ASSET_ID_RE = re.compile(r"\basset-[a-z0-9][a-z0-9-]*\b", re.I)


def _prompt_dialogue_blocks(text: str) -> list[str]:
    if (
        text.count("{") != text.count("}")
        or "{{" in text
        or "}}" in text
    ):
        raise SegmentRuntimeError(
            "Seedance Prompt dialogue braces must be balanced, non-nested "
            "literal pairs"
        )
    return re.findall(r"\{([^{}]+)\}", text)


def _shot_matches(prompt: str) -> list[re.Match[str]]:
    return list(SHOT_HEADING_RE.finditer(prompt))


def _shot_number(value: str) -> int:
    return int(
        value.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    )


def _validate_reference_mapping(prompt: str, row: dict[str, Any]) -> None:
    if INTERNAL_ASSET_ID_RE.search(prompt):
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt exposes an internal asset ID; use only "
            "@ImageN/@VideoN plus a readable noun"
        )
    shot_matches = _shot_matches(prompt)
    if not shot_matches:
        return
    reference_map = prompt[: shot_matches[0].start()]
    for binding in row["bindings"]:
        token = str(binding["provider_token"])
        declaration = re.search(
            re.escape(token) + r"\s*\(\s*([^()\n]{1,120}?)\s*\)",
            reference_map,
        )
        if declaration is None:
            raise SegmentRuntimeError(
                f"{row['segment_id']} must declare {token} with an Arabic "
                "readable noun before Shot 1"
            )
        arabic_subject = declaration.group(1).strip()
        if (
            not ARABIC_LETTER_RE.search(arabic_subject)
            or LATIN_LETTER_RE.search(arabic_subject)
        ):
            raise SegmentRuntimeError(
                f"{row['segment_id']} {token} readable noun must be Arabic-only"
            )
        for occurrence in re.finditer(re.escape(token), prompt):
            suffix = prompt[occurrence.end() :]
            noun = re.match(r"\s*\(\s*([^()\n]{1,120}?)\s*\)", suffix)
            if noun is None:
                raise SegmentRuntimeError(
                    f"{row['segment_id']} every {token} use must be followed "
                    "immediately by the same Arabic readable noun in parentheses"
                )
            if noun.group(1).strip() != arabic_subject:
                raise SegmentRuntimeError(
                    f"{row['segment_id']} every {token} use must keep the same "
                    f"Arabic readable noun {arabic_subject!r}"
                )


def _validate_engineered_structure(prompt: str, row: dict[str, Any]) -> None:
    contract = row["prompt_contract"]
    if (
        contract.get("authoring_ruleset")
        != (
            "skills/virtual-production/references/"
            "seedance-2-prompt-authoring-contract.md"
        )
        or contract.get("engineered_prompt_sections")
        != [
            "الإعداد العام وخريطة المراجع:",
            "اللقطة N: <حجم اللقطة العربي المطابق للوحة القصة>.",
            "الجودة والقيود:",
        ]
        or contract.get("shot_element_labels") != list(SHOT_ELEMENT_LABELS)
        or contract.get("shot_authority_labels")
        != list(SHOT_AUTHORITY_LABELS)
        or contract.get("single_dominant_camera_move_per_shot") is not True
        or contract.get("reference_noun_after_every_token") is not True
        or contract.get("model_prompt_language") != "Arabic"
        or contract.get("latin_text_policy")
        != "forbidden_except_provider_reference_tokens"
        or contract.get("missing_or_conflicting_information_policy")
        != (
            "return_to_owning_upstream_department_without_silent_modification"
        )
    ):
        raise SegmentRuntimeError(
            f"{row['segment_id']} Storyboard Prompt authoring contract is stale"
        )
    folded = prompt.casefold()
    global_label, quality_label = ENGINEERED_SECTION_LABELS
    global_position = folded.find(global_label.casefold())
    quality_position = folded.find(quality_label.casefold())
    shot_matches = _shot_matches(prompt)
    if (
        global_position < 0
        or quality_position < 0
        or not shot_matches
        or global_position > shot_matches[0].start()
        or quality_position < shot_matches[-1].end()
    ):
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt must use the ordered Arabic global "
            "setup, Shot, and quality sections"
        )

    directive = row["prompt_contract"]["quality_and_fallback_directive"]
    if directive.casefold() not in folded[quality_position:]:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt lacks the approved quality and "
            "anti-distortion fallback"
        )

    for index, match in enumerate(shot_matches):
        block_end = (
            shot_matches[index + 1].start()
            if index + 1 < len(shot_matches)
            else quality_position
        )
        block = prompt[match.end() : block_end]
        block_folded = block.casefold()
        missing = [
            label
            for label in (*SHOT_ELEMENT_LABELS, *SHOT_AUTHORITY_LABELS)
            if block_folded.count(label.casefold()) != 1
        ]
        if missing:
            raise SegmentRuntimeError(
                f"{row['segment_id']} Shot {index + 1} must state each engineered "
                f"element exactly once: {', '.join(missing)}"
            )
        camera_match = re.search(
            r"^سلوك الكاميرا المهيمن:\s*(\S[^\n]*)$",
            block,
            re.MULTILINE,
        )
        if camera_match is None:
            raise SegmentRuntimeError(
                f"{row['segment_id']} Shot {index + 1} has no readable dominant "
                "camera behavior"
            )
        camera = camera_match.group(1)
        families = [
            name
            for name, pattern in CAMERA_FAMILY_PATTERNS.items()
            if pattern.search(camera)
        ]
        if len(families) != 1:
            raise SegmentRuntimeError(
                f"{row['segment_id']} Shot {index + 1} must select exactly one "
                f"dominant camera family; found {families or ['unrecognized']}"
            )
        if len(row["ordered_shots"][index]) != 10:
            raise SegmentRuntimeError(
                f"{row['segment_id']} Shot {index + 1} Storyboard authority "
                "is incomplete"
            )


def _validate_visual_doctrine(prompt: str, row: dict[str, Any]) -> None:
    for label in ARABIC_VISUAL_DOCTRINE_LABELS:
        matches = re.findall(
            rf"^{re.escape(label)}\s*(\S[^\n]*)$",
            prompt,
            re.MULTILINE,
        )
        if len(matches) != 1 or not ARABIC_LETTER_RE.search(matches[0]):
            raise SegmentRuntimeError(
                f"{row['segment_id']} Prompt must contain one complete Arabic "
                f"visual-doctrine declaration: {label}"
            )

    shot_matches = _shot_matches(prompt)
    expected_sizes = [shot[2] for shot in row["ordered_shots"]]
    actual = [
        (_shot_number(match.group(1)), SHOT_SIZE_ENUM_BY_ARABIC[match.group(2)])
        for match in shot_matches
    ]
    expected = list(enumerate(expected_sizes, start=1))
    if actual != expected:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Arabic Prompt Shot headings must preserve "
            "the exact Storyboard shot sizes in order"
        )
    wide_sizes = {"medium_wide", "wide", "extreme_wide"}
    for index, match in enumerate(shot_matches):
        if SHOT_SIZE_ENUM_BY_ARABIC[match.group(2)] not in wide_sizes:
            continue
        end = (
            shot_matches[index + 1].start()
            if index + 1 < len(shot_matches)
            else len(prompt)
        )
        shot_block = prompt[match.end() : end]
        if ARABIC_POSITION_CHANGE_EXCEPTION_PREFIX not in shot_block:
            raise SegmentRuntimeError(
                f"{row['segment_id']} Shot {index + 1} wider framing lacks the "
                "literal Arabic position-change exception"
            )


def _validate_arabic_model_text(prompt: str, row: dict[str, Any]) -> None:
    prose_without_provider_tokens = TOKEN_SCAN_RE.sub("", prompt)
    latin = sorted(set(re.findall(r"[A-Za-z]+", prose_without_provider_tokens)))
    if latin:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Seedance Prompt must be Arabic-only; Latin "
            "text is allowed only inside @ImageN/@VideoN provider tokens. "
            f"Found: {', '.join(latin[:12])}"
        )
    if not ARABIC_LETTER_RE.search(prose_without_provider_tokens):
        raise SegmentRuntimeError(
            f"{row['segment_id']} Seedance Prompt contains no Arabic directions"
        )


def _validate_prompt(text: str, row: dict[str, Any], path: Path) -> str:
    prompt = text.strip()
    if not prompt:
        raise SegmentRuntimeError(f"Seedance Prompt is empty: {path}")
    _validate_arabic_model_text(prompt, row)
    tokens = sorted(
        set(match.group(0) for match in TOKEN_SCAN_RE.finditer(prompt)),
        key=token_sort_key,
    )
    expected_tokens = sorted(
        [item["provider_token"] for item in row["bindings"]],
        key=token_sort_key,
    )
    if tokens != expected_tokens:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt provider tokens differ from Storyboard Reference Plan"
        )
    if PRECISE_TIME_RANGE_RE.search(prompt):
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt must use event order, not precise second ranges"
        )
    visual_style_ar = str(
        row["prompt_contract"].get("visual_style_instruction_ar") or ""
    )
    if not visual_style_ar or visual_style_ar not in prompt:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt must name the approved visual style "
            "in Arabic"
        )
    operation = str(row["operation"])
    operation_ar = ARABIC_OPERATION_BY_ENUM.get(operation)
    if operation_ar is None or operation_ar not in prompt:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt must name its authored operation in Arabic"
        )
    if "【" in prompt or "】" in prompt:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt requests generated subtitles or text"
        )
    audio_directive = row["prompt_contract"]["seedance_audio_directive"]
    if (
        audio_directive != ARABIC_SEEDANCE_DIALOGUE_REPLACEMENT_DIRECTIVE
        or ARABIC_SEEDANCE_DIALOGUE_REPLACEMENT_DIRECTIVE.casefold()
        not in prompt.casefold()
    ):
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt must include the mandatory native-audio "
            "dialogue-replacement Seedance directive"
        )
    _validate_reference_mapping(prompt, row)
    _validate_engineered_structure(prompt, row)
    _validate_visual_doctrine(prompt, row)
    dialogue_blocks = _prompt_dialogue_blocks(prompt)
    for cue in row["dialogue_cues"]:
        exact = cue["exact_text"]
        if dialogue_blocks.count(exact) != 1:
            raise SegmentRuntimeError(
                f"{cue['line_id']} exact speech must appear once in literal braces"
            )
        line_position = prompt.find("{" + exact + "}")
        nearby = prompt[
            max(0, line_position - 500) : line_position + len(exact) + 150
        ]
        if (
            cue["delivery_mode"] not in {
                "off_camera_storytelling",
                "external_voiceover",
            }
            and not re.search(
                r"(?:(?:مسموع|بصوت)[^.\n]{0,220}"
                r"(?:الفم|الشفاه|ينطق|توجيه)|"
                r"(?:الفم|الشفاه|ينطق|توجيه)[^.\n]{0,220}"
                r"(?:مسموع|بصوت))",
                nearby,
            )
        ):
            raise SegmentRuntimeError(
                f"{cue['line_id']} must direct one audible Arabic guide "
                "performance for mouth motion before ElevenLabs replacement"
            )
        if cue["delivery_mode"] in {
            "off_camera_storytelling",
            "external_voiceover",
        }:
            if not re.search(
                r"خارج (?:الكادر|الشاشة|الكاميرا)|تعليق صوتي",
                nearby,
            ):
                raise SegmentRuntimeError(
                    f"{cue['line_id']} off-camera storytelling is not explicit near the line"
                )
    unexpected = [item for item in dialogue_blocks if item not in {
        cue["exact_text"] for cue in row["dialogue_cues"]
    }]
    if unexpected:
        raise SegmentRuntimeError(
            f"{row['segment_id']} Prompt contains unauthorised spoken text in braces"
        )
    return prompt


def parse_segment_script(path: Path) -> dict[str, Any]:
    script_path = path.expanduser().resolve()
    try:
        text = script_path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError) as exc:
        raise SegmentRuntimeError(f"Unreadable Seedance Prompt: {script_path}") from exc
    match = SCRIPT_RE.fullmatch(script_path.name)
    if match is None:
        raise SegmentRuntimeError(f"Invalid Seedance Prompt filename: {script_path.name}")
    segment_id = f"segment-{int(match.group(1)):03d}"
    task_dir = script_path.parents[3]
    rows = storyboard_segment_rows(
        task_dir, validation_through_segment_id=segment_id
    )
    row = next(item for item in rows if item["segment_id"] == segment_id)
    prompt = _validate_prompt(text, row, script_path)
    return {
        "segment_id": segment_id,
        "number": int(match.group(1)),
        "path": script_path,
        "text": text,
        "script_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "metadata": row,
        "duration": row["target_duration"],
        "prompt": prompt,
        "bindings": row["bindings"],
        "seedance_audio_mode": "original_audio_dialogue_replacement",
        "generate_audio": True,
    }
