from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "finish-postproduction"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS))

from subtitles.subtitle_files import _write_subtitle_files  # noqa: E402
from subtitles.subtitle_render import (  # noqa: E402
    _render_cue_overlay,
    _require_raqm,
    _resolve_bundled_font_file,
)
from subtitles.subtitle_style import (  # noqa: E402
    DEFAULT_STYLE,
    SubtitleBuildError,
    _load_json,
)


class SubtitleRenderCompatibilityTests(unittest.TestCase):
    def test_external_subtitles_use_utf8_bom_for_arabic_players(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, srt_path, vtt_path = _write_subtitle_files(
                Path(temporary),
                {
                    "cues": [
                        {
                            "cue_index": 1,
                            "timeline_start_seconds": 1.0,
                            "timeline_end_seconds": 2.0,
                            "rendered_text": "الله أكبر.",
                        }
                    ]
                },
            )
            self.assertTrue(srt_path.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertTrue(vtt_path.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_bundled_arabic_font_resolves_without_fontconfig(self) -> None:
        style = _load_json(DEFAULT_STYLE)
        font_path = _resolve_bundled_font_file(
            style["font_asset"],
            style["font_sha256"],
        )
        self.assertTrue(font_path.is_file())
        self.assertEqual(font_path.name, "NotoSansArabic-Variable.ttf")

    def test_bundled_font_path_cannot_escape_skill(self) -> None:
        with self.assertRaisesRegex(
            SubtitleBuildError,
            "safe relative",
        ):
            _resolve_bundled_font_file("../../outside.ttf", "0" * 64)

    def test_bundled_font_hash_mismatch_is_rejected(self) -> None:
        style = _load_json(DEFAULT_STYLE)
        with self.assertRaisesRegex(
            SubtitleBuildError,
            "hash does not match",
        ):
            _resolve_bundled_font_file(style["font_asset"], "0" * 64)

    @patch(
        "PIL.features.check_feature",
        return_value=False,
    )
    def test_missing_raqm_fails_with_install_guidance(self, _check_mock) -> None:
        with self.assertRaisesRegex(
            SubtitleBuildError,
            "FriBiDi runtime library",
        ):
            _require_raqm()

    def test_bundled_font_renders_shaped_arabic(self) -> None:
        style = _load_json(DEFAULT_STYLE)
        font_path = _resolve_bundled_font_file(
            style["font_asset"],
            style["font_sha256"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "cue.png"
            x, y = _render_cue_overlay(
                {"rendered_text": "السَّلَامُ عَلَيْكُمْ"},
                output_path=output,
                frame_width=1920,
                frame_height=1080,
                style=style,
                font_path=font_path,
            )
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)


if __name__ == "__main__":
    unittest.main()
