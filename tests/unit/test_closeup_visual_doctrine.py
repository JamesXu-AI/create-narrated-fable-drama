from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(
    0,
    str(REPOSITORY_ROOT / "skills/previsualize-cinematography/scripts"),
)

from validate_storyboard import (  # noqa: E402
    StoryboardValidationError,
    _validate_shot_size_authority,
)

from narrated_fable_drama.contracts.screenplay.boundaries import (  # noqa: E402
    _validate_shot_scale_grammar,
)
from narrated_fable_drama.contracts.segment.common import (  # noqa: E402
    ARABIC_SEEDANCE_DIALOGUE_REPLACEMENT_DIRECTIVE,
    SegmentRuntimeError,
)
from narrated_fable_drama.contracts.segment.prompt import (  # noqa: E402
    _validate_prompt,
)
from narrated_fable_drama.core.validation import StoryVideoError  # noqa: E402


def _shot(
    shot_id: str,
    scale: str,
    blocking: str = "holds the established mark",
) -> dict:
    return {
        "shot_id": shot_id,
        "scale_view": scale,
        "blocking_movement_en": blocking,
    }


def _segments(*shots: dict) -> list[dict]:
    return [
        {
            "story_plan": {"scene_id": "scene-001"},
            "shots": list(shots),
        }
    ]


def _prompt_row() -> dict:
    economy = "يظهر الثعلب وحده، وتبقى البومة حاضرة خارج حدود القص."
    axis = (
        "يمتد محور النظرات بين الثعلب والبومة؛ يقف الثعلب يسار الشاشة وينظر "
        "يمينًا، وتقف البومة يمين الشاشة وتنظر يسارًا، وتبقى الكاميرا شمال المحور."
    )
    size_policy = (
        "تسود اللقطات شديدة القرب والقريبة والمتوسطة القريبة؛ ولا تُستخدم "
        "اللقطات الأوسع إلا لأقصر استثناء معلّم لتغيير الموضع ثم العودة إلى لقطة ضيقة."
    )
    fallback = (
        "وضوح سينمائي عالي التفاصيل؛ ثبات هوية الشخصية ووجهها وملابسها "
        "وتشريحها؛ ملامح وجه واضحة؛ من دون قفزات في الوجه أو أطراف زائدة أو "
        "اختراق للأجسام أو قصّ أو تشوه أو شعارات أو علامات مائية."
    )
    return {
        "segment_id": "segment-001",
        "operation": "multimodal_reference",
        "visual_style": "Test Style",
        "bindings": [],
        "dialogue_cues": [],
        "prompt_contract": {
            "authoring_ruleset": (
                "skills/virtual-production/references/"
                "seedance-2-prompt-authoring-contract.md"
            ),
            "missing_or_conflicting_information_policy": (
                "return_to_owning_upstream_department_without_silent_modification"
            ),
            "engineered_prompt_sections": [
                "الإعداد العام وخريطة المراجع:",
                "اللقطة N: <حجم اللقطة العربي المطابق للوحة القصة>.",
                "الجودة والقيود:",
            ],
            "single_dominant_camera_move_per_shot": True,
            "reference_noun_after_every_token": True,
            "model_prompt_language": "Arabic",
            "latin_text_policy": "forbidden_except_provider_reference_tokens",
            "shot_element_labels": [
                "سلوك الكاميرا المهيمن:",
                "الشخصية والفعل:",
                "المكان والبيئة:",
                "الإضاءة والنبرة:",
            ],
            "shot_authority_labels": [
                "مرجعية الانتقال والكاميرا من لوحة القصة:",
                "المرتكزات الثابتة:",
                "الهبوط والتحرير:",
            ],
            "visible_character_economy_ar": economy,
            "eyeline_axis_and_screen_direction_ar": axis,
            "shot_size_policy_ar": size_policy,
            "visual_style_instruction_ar": "أسلوب اختباري",
            "seedance_audio_directive": (
                ARABIC_SEEDANCE_DIALOGUE_REPLACEMENT_DIRECTIVE
            ),
            "quality_and_fallback_directive": fallback,
        },
        "ordered_shots": [
            [
                "Shot 1",
                "A-001",
                "wide",
                "locked camera",
                "Fox crosses between authored marks.",
                "Forest path with Owl outside the crop.",
                "Moonlit tree",
                "Soft moonlight with a calm dramatic tone.",
                "none; forest ambience",
                "Fox lands at the stone mark.",
            ],
            [
                "Shot 2",
                "A-002",
                "close_up",
                "locked camera",
                "Hold on Fox's eyes and settled breath.",
                "Preserve the same forest path.",
                "Moonlit tree",
                "Preserve the soft moonlight.",
                "none; soft wind",
                "Fox holds the final eyeline.",
            ],
        ],
    }


def _prompt(
    *,
    include_wide_exception: bool,
    camera_behavior: str = "كاميرا ثابتة",
) -> str:
    row = _prompt_row()
    contract = row["prompt_contract"]
    economy = contract["visible_character_economy_ar"]
    axis = contract["eyeline_axis_and_screen_direction_ar"]
    size_policy = contract["shot_size_policy_ar"]
    exception = (
        "استثناء تغيير الموضع: يعبر الثعلب من علامة الشجرة إلى علامة الحجر، "
        "ويستقر قبالة البومة، ثم يعود الانتباه إلى عيني الثعلب.\n"
        if include_wide_exception
        else "يبقى الثعلب ظاهرًا في الغابة.\n"
    )
    return (
        "الإعداد العام وخريطة المراجع:\n"
        "العملية: توليد بالمرجع متعدد الوسائط. أنشئ فيديو بنسبة ١٦:٩ "
        "وبأسلوب اختباري.\n"
        "اقتصاد الشخصيات الظاهرة: "
        f"{economy}\n"
        "محور النظرات واتجاه الشاشة: "
        f"{axis}\n"
        "تغطية تقودها اللقطات القريبة: "
        f"{size_policy}\n"
        f"{ARABIC_SEEDANCE_DIALOGUE_REPLACEMENT_DIRECTIVE}\n"
        "اللقطة 1: لقطة واسعة.\n"
        f"سلوك الكاميرا المهيمن: {camera_behavior}\n"
        "مرجعية الانتقال والكاميرا من لوحة القصة: كاميرا ثابتة.\n"
        "الشخصية والفعل: يعبر الثعلب بين العلامات المحددة.\n"
        "المكان والبيئة: ممر الغابة والبومة خارج حدود القص.\n"
        "المرتكزات الثابتة: شجرة مضاءة بضوء القمر.\n"
        "الإضاءة والنبرة: ضوء قمر ناعم ونبرة درامية هادئة.\n"
        "الهبوط والتحرير: يستقر الثعلب عند علامة الحجر.\n"
        f"{exception}"
        "اللقطة 2: لقطة قريبة.\n"
        "سلوك الكاميرا المهيمن: كاميرا ثابتة\n"
        "مرجعية الانتقال والكاميرا من لوحة القصة: كاميرا ثابتة.\n"
        "الشخصية والفعل: تثبيت على عيني الثعلب ونفَسه المستقر.\n"
        "المكان والبيئة: الحفاظ على ممر الغابة نفسه.\n"
        "المرتكزات الثابتة: شجرة مضاءة بضوء القمر.\n"
        "الإضاءة والنبرة: الحفاظ على ضوء القمر الناعم.\n"
        "الهبوط والتحرير: يحافظ الثعلب على خط النظر النهائي.\n"
        "الجودة والقيود:\n"
        f"{contract['quality_and_fallback_directive']}"
    )


def _storyboard_shot_row(
    number: int,
    screenplay_shot: str,
    size: str,
    space: str,
) -> str:
    return (
        f"| Shot {number} | {screenplay_shot} | {size} | locked camera | "
        f"readable action | {space} | tree | soft light | none; ambience | "
        "settled landing |"
    )


def _storyboard_text(*rows: str) -> str:
    separator = "| " + " | ".join(["---"] * 10) + " |"
    return "\n".join(
        [
            "## Generation Segment 1 — Test",
            "### Ordered Shots",
            (
                "| Shot | Screenplay Shot | Shot Size | Transition and Camera | "
                "Subject Action and Expression | Space, Blocking and Gaze | "
                "Persistent Anchors | Lighting and Color | Dialogue and Dubbing "
                "Audio | Landing and Edit |"
            ),
            separator,
            *rows,
        ]
    )


def _write_screenplay_shot_stub(task_dir: Path, scales: list[str]) -> None:
    screenplay_dir = task_dir / "screenplay-writer"
    screenplay_dir.mkdir()
    rows = [
        f"| A-{index:03d} | BEAT-{index:03d} | {scale} |"
        for index, scale in enumerate(scales, start=1)
    ]
    (screenplay_dir / "screenplay.md").write_text(
        "\n".join(rows),
        encoding="utf-8",
    )


class CloseupVisualDoctrineTests(unittest.TestCase):
    def test_screenplay_wide_requires_position_change_exception(self) -> None:
        with self.assertRaisesRegex(
            StoryVideoError, "position-change exception"
        ):
            _validate_shot_scale_grammar(
                _segments(
                    _shot("A-001", "wide"),
                    _shot("A-002", "close_up"),
                    _shot("A-003", "reaction"),
                )
            )

    def test_screenplay_rejects_consecutive_wide_shots(self) -> None:
        with self.assertRaisesRegex(StoryVideoError, "consecutive"):
            _validate_shot_scale_grammar(
                _segments(
                    _shot(
                        "A-001",
                        "wide",
                        "position-change exception: Fox crosses to the door mark.",
                    ),
                    _shot(
                        "A-002",
                        "establishing",
                        "position-change exception: Owl exits through the door.",
                    ),
                    _shot("A-003", "close_up"),
                    _shot("A-004", "reaction"),
                    _shot("A-005", "insert"),
                )
            )

    def test_screenplay_requires_tight_attention_majority(self) -> None:
        with self.assertRaisesRegex(StoryVideoError, "must outnumber"):
            _validate_shot_scale_grammar(
                _segments(
                    _shot("A-001", "medium"),
                    _shot("A-002", "close_up"),
                )
            )

    def test_screenplay_accepts_tight_majority_and_one_brief_wide(self) -> None:
        _validate_shot_scale_grammar(
            _segments(
                _shot(
                    "A-001",
                    "wide",
                    "position-change exception: Fox crosses and lands by Owl.",
                ),
                _shot("A-002", "close_up"),
                _shot("A-003", "reaction"),
            )
        )

    def test_segment_prompt_requires_wide_exception_inside_wide_shot(self) -> None:
        with self.assertRaisesRegex(SegmentRuntimeError, "wider framing"):
            _validate_prompt(
                _prompt(include_wide_exception=False),
                _prompt_row(),
                Path("segment-001.md"),
            )

    def test_segment_prompt_accepts_explicit_visual_doctrine(self) -> None:
        validated = _validate_prompt(
            _prompt(include_wide_exception=True),
            _prompt_row(),
            Path("segment-001.md"),
        )
        self.assertIn("اللقطة 2: لقطة قريبة.", validated)

    def test_segment_prompt_rejects_latin_prose_outside_provider_tokens(
        self,
    ) -> None:
        prompt = _prompt(include_wide_exception=True).replace(
            "أنشئ فيديو",
            "أنشئ English فيديو",
        )
        with self.assertRaisesRegex(
            SegmentRuntimeError,
            "must be Arabic-only",
        ):
            _validate_prompt(
                prompt,
                _prompt_row(),
                Path("segment-001.md"),
            )

    def test_segment_prompt_rejects_two_camera_families_in_one_shot(self) -> None:
        with self.assertRaisesRegex(
            SegmentRuntimeError,
            "exactly one dominant camera family",
        ):
            _validate_prompt(
                _prompt(
                    include_wide_exception=True,
                    camera_behavior=(
                        "حركة بانورامية أفقية مع دفع دولي إلى الداخل"
                    ),
                ),
                _prompt_row(),
                Path("segment-001.md"),
            )

    def test_segment_prompt_accepts_native_arabic_dolly_push(self) -> None:
        validated = _validate_prompt(
            _prompt(
                include_wide_exception=True,
                camera_behavior="حركة دفع خفيفة إلى الداخل",
            ),
            _prompt_row(),
            Path("segment-001.md"),
        )
        self.assertIn(
            "سلوك الكاميرا المهيمن: حركة دفع خفيفة إلى الداخل",
            validated,
        )

    def test_segment_prompt_rejects_token_without_readable_noun(self) -> None:
        row = _prompt_row()
        row["bindings"] = [
            {
                "provider_token": "@Image1",
                "readable_subject": "Fox",
            }
        ]
        prompt = _prompt(include_wide_exception=True).replace(
            "أنشئ فيديو بنسبة ١٦:٩ وبأسلوب اختباري.",
            "@Image1 (الثعلب) هو مرجع الهوية المعتمد.\n"
            "أنشئ فيديو بنسبة ١٦:٩ وبأسلوب اختباري.",
        ).replace(
            "الشخصية والفعل: تثبيت على عيني الثعلب",
            "الشخصية والفعل: @Image1 تثبيت على عيني الثعلب",
        )
        with self.assertRaisesRegex(
            SegmentRuntimeError,
            "followed immediately by the same Arabic readable noun",
        ):
            _validate_prompt(prompt, row, Path("segment-001.md"))

    def test_segment_prompt_rejects_silent_storyboard_rewrite(self) -> None:
        prompt = _prompt(include_wide_exception=True).replace(
            "الإضاءة والنبرة: الحفاظ على ضوء القمر الناعم.\n",
            "",
        )
        with self.assertRaisesRegex(
            SegmentRuntimeError,
            "must state each engineered element exactly once",
        ):
            _validate_prompt(
                prompt,
                _prompt_row(),
                Path("segment-001.md"),
            )

    def test_storyboard_wide_requires_literal_position_change_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            _write_screenplay_shot_stub(
                task_dir, ["wide", "close_up", "reaction"]
            )
            storyboard = _storyboard_text(
                _storyboard_shot_row(
                    1, "A-001", "wide", "Fox crosses to Owl."
                ),
                _storyboard_shot_row(
                    2, "A-002", "close_up", "Fox holds screen-left."
                ),
                _storyboard_shot_row(
                    3, "A-003", "medium_close_up", "Owl holds screen-right."
                ),
            )
            with self.assertRaisesRegex(
                StoryboardValidationError, "position-change exception"
            ):
                _validate_shot_size_authority(task_dir, storyboard)

    def test_storyboard_wide_returns_directly_to_tight_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            task_dir = Path(temporary)
            _write_screenplay_shot_stub(
                task_dir, ["wide", "medium", "close_up", "reaction", "insert"]
            )
            storyboard = _storyboard_text(
                _storyboard_shot_row(
                    1,
                    "A-001",
                    "wide",
                    (
                        "position-change exception: Fox crosses from tree to "
                        "stone and lands opposite Owl."
                    ),
                ),
                _storyboard_shot_row(
                    2, "A-002", "medium", "Fox and Owl hold their marks."
                ),
                _storyboard_shot_row(
                    3, "A-003", "close_up", "Fox holds screen-left."
                ),
                _storyboard_shot_row(
                    4, "A-004", "medium_close_up", "Owl holds screen-right."
                ),
                _storyboard_shot_row(
                    5, "A-005", "extreme_close_up", "Fox's eyes hold right."
                ),
            )
            with self.assertRaisesRegex(
                StoryboardValidationError, "return directly"
            ):
                _validate_shot_size_authority(task_dir, storyboard)


if __name__ == "__main__":
    unittest.main()
