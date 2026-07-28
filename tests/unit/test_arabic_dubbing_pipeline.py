from __future__ import annotations

import array
import base64
import json
import math
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from narrated_fable_drama.core.project_domain import (  # noqa: E402
    SOUND_EFFECTS_AUDIO_SOURCE,
    SPEECH_AUDIO_SOURCE,
    ProjectDomainError,
    validate_arabic_dialogue,
    validate_project_context,
)
from narrated_fable_drama.dubbing.arabic_segment import (  # noqa: E402
    ArabicSegmentEmbeddingError,
    _apply_reviewed_cue_window,
    _approved_voice_profiles,
    _cue_phrase_plans,
    _forbidden_speech_intervals,
    _phrase_groups,
    _render_embedded_video,
    _render_seedance_speech_cut,
    _resolved_cue_timing,
)
from narrated_fable_drama.dubbing.seedance_speech_gate import (  # noqa: E402
    audit_seedance_character_speech,
)
from narrated_fable_drama.media.probe import probe_json  # noqa: E402
from narrated_fable_drama.providers.elevenlabs import (  # noqa: E402
    create_voice_from_preview,
    design_voice_previews,
    synthesize_arabic_speech,
    voice_map,
)


class ArabicProjectContractTests(unittest.TestCase):
    def test_project_context_splits_seedance_sound_and_elevenlabs_dialogue(
        self,
    ) -> None:
        payload = {
            "production_type": "ai_narrated_fable_drama",
            "aspect_ratio": "16:9",
            "resolution": "1080p",
            "visual_style": "3D Healing Animation",
            "target_country": "Saudi Arabia",
            "target_language": "Arabic",
            "speech_audio_source": SPEECH_AUDIO_SOURCE,
            "sound_effects_audio_source": SOUND_EFFECTS_AUDIO_SOURCE,
        }
        self.assertIs(validate_project_context(payload), payload)

        payload["target_language"] = "English"
        with self.assertRaisesRegex(ProjectDomainError, "target_language"):
            validate_project_context(payload)
        payload["target_language"] = "Arabic"
        payload["target_country"] = "Egypt"
        with self.assertRaisesRegex(ProjectDomainError, "target_country"):
            validate_project_context(payload)

    def test_dialogue_requires_arabic_without_latin_letters(self) -> None:
        self.assertEqual(
            validate_arabic_dialogue("مرحبًا يا صديقي!", context="L-001"),
            "مرحبًا يا صديقي!",
        )
        with self.assertRaisesRegex(ProjectDomainError, "Arabic-script"):
            validate_arabic_dialogue("Hello", context="L-001")
        with self.assertRaisesRegex(ProjectDomainError, "Latin"):
            validate_arabic_dialogue("مرحبًا Bob", context="L-001")

    def test_voice_map_uses_screenplay_entity_ids(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"ELEVENLABS_VOICE_MAP": '{"grandfather":"voice-123"}'},
            clear=False,
        ):
            self.assertEqual(voice_map(), {"grandfather": "voice-123"})

    def test_voice_map_can_load_asset_department_mapping_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            mapping = Path(temp) / "voices.json"
            mapping.write_text(
                '{"uthman":"voice-boy","grandfather":"voice-elder"}',
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {"ELEVENLABS_VOICE_MAP": f"@{mapping}"},
                clear=False,
            ):
                self.assertEqual(
                    voice_map(),
                    {
                        "uthman": "voice-boy",
                        "grandfather": "voice-elder",
                    },
                )

    def test_voice_design_and_creation_preserve_selected_preview(self) -> None:
        class _Response:
            def __init__(self, payload: dict[str, object]) -> None:
                self._payload = json.dumps(payload).encode("utf-8")
                self.headers: dict[str, str] = {}

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return self._payload

        preview_audio = base64.b64encode(b"ID3-preview").decode("ascii")
        responses = [
            _Response(
                {
                    "previews": [
                        {
                            "generated_voice_id": f"generated-{index}",
                            "audio_base_64": preview_audio,
                            "media_type": "audio/mpeg",
                            "duration_secs": 4.0,
                            "language": "ar",
                        }
                        for index in range(3)
                    ],
                    "text": "ا" * 100,
                }
            ),
            _Response({"voice_id": "saved-role-voice", "name": "Role"}),
        ]
        with (
            mock.patch.dict(
                os.environ,
                {"ELEVENLABS_API_KEY": "test-key"},
                clear=False,
            ),
            mock.patch(
                "narrated_fable_drama.providers.elevenlabs.urllib.request.urlopen",
                side_effect=responses,
            ) as urlopen,
        ):
            designed = design_voice_previews(
                voice_description="A distinct native Saudi Arabic role voice.",
                text="ا" * 100,
                seed=17,
            )
            created = create_voice_from_preview(
                voice_name="Role",
                voice_description="A distinct native Saudi Arabic role voice.",
                generated_voice_id=designed["previews"][2]["generated_voice_id"],
                labels={"language": "ar-SA", "role": "role"},
            )

        self.assertEqual(len(designed["previews"]), 3)
        self.assertEqual(created["voice_id"], "saved-role-voice")
        create_body = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertEqual(
            create_body["generated_voice_id"],
            "generated-2",
        )

class ArabicDubbingMuxTests(unittest.TestCase):
    def test_phrase_mix_applies_consistent_dialogue_loudness(self) -> None:
        captured: dict[str, list[str]] = {}

        def _run(command: list[object], **_kwargs: object) -> None:
            captured["command"] = [str(item) for item in command]
            Path(command[-1]).write_bytes(b"rendered")

        with (
            tempfile.TemporaryDirectory() as temporary_directory,
            mock.patch(
                "narrated_fable_drama.dubbing.arabic_segment.require_binary",
                return_value="ffmpeg",
            ),
            mock.patch(
                "narrated_fable_drama.dubbing.arabic_segment.run_media_command",
                side_effect=_run,
            ),
        ):
            root = Path(temporary_directory)
            output = root / "video.mp4"
            _render_embedded_video(
                seedance_background_video=root / "background.mp4",
                cue_files=[root / "cue.mp3"],
                phrase_plans=[
                    {
                        "phrase_id": "L-004__phrase-01",
                        "input_index": 1,
                        "source_start_seconds": 0.0,
                        "source_end_seconds": 1.0,
                        "target_start_seconds": 1.0,
                        "target_end_seconds": 2.0,
                        "tempo_factor": 1.0,
                    }
                ],
                duration_seconds=3.0,
                output=output,
            )

        command = captured["command"]
        filter_graph = command[command.index("-filter_complex") + 1]
        self.assertIn(
            "acompressor=threshold=-24.0dB:ratio=4.0:"
            "attack=5.0:release=50.0:makeup=12.0dB",
            filter_graph,
        )
        self.assertIn("loudnorm=I=-18.0:LRA=7.0:TP=-3.0", filter_graph)

    def test_tts_request_uses_approved_settings_and_fresh_seed(self) -> None:
        class _Response:
            headers = {
                "request-id": "tts-request",
                "content-type": "application/json",
            }

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                payload = {
                    "audio_base64": base64.b64encode(b"ID3-speech").decode(
                        "ascii"
                    ),
                    "alignment": {
                        "characters": ["م"],
                        "character_start_times_seconds": [0.0],
                        "character_end_times_seconds": [0.2],
                    },
                }
                return json.dumps(payload).encode("utf-8")

        with (
            mock.patch.dict(
                os.environ,
                {
                    "ELEVENLABS_API_KEY": "test-key",
                    "ELEVENLABS_MODEL_ID": "eleven_multilingual_v2",
                },
                clear=False,
            ),
            mock.patch(
                "narrated_fable_drama.providers.elevenlabs.urllib.request.urlopen",
                return_value=_Response(),
            ) as urlopen,
            mock.patch(
                "narrated_fable_drama.providers.elevenlabs.secrets.randbits",
                return_value=123456789,
            ) as randbits,
        ):
            result = synthesize_arabic_speech(
                exact_text="م",
                voice_id="voice-123",
                speed=0.7,
                voice_settings={
                    "stability": 0.72,
                    "similarity_boost": 0.86,
                    "style": 0.0,
                    "use_speaker_boost": True,
                    "speed": 0.98,
                },
            )
            replay = synthesize_arabic_speech(
                exact_text="م",
                voice_id="voice-123",
                speed=0.7,
                seed=17,
            )

        body = json.loads(urlopen.call_args_list[0].args[0].data)
        self.assertEqual(body["voice_settings"]["speed"], 0.7)
        self.assertEqual(body["voice_settings"]["stability"], 0.72)
        self.assertEqual(body["voice_settings"]["similarity_boost"], 0.86)
        self.assertEqual(body["model_id"], "eleven_multilingual_v2")
        self.assertEqual(body["seed"], 123456789)
        self.assertNotIn("language_code", body)
        self.assertFalse(result["language_code_sent"])
        self.assertEqual(result["speed"], 0.7)
        self.assertEqual(result["seed_source"], "fresh_random")
        replay_body = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertEqual(replay_body["seed"], 17)
        self.assertEqual(replay["seed_source"], "explicit")
        randbits.assert_called_once_with(32)

    def test_voice_profile_comes_from_approved_asset_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository_root = Path(temporary_directory)
            task_dir = repository_root / "workspace" / "tasks" / "story"
            brief_path = (
                repository_root
                / "workspace"
                / "assets"
                / "characters"
                / "lion"
                / "voice.brief.json"
            )
            task_dir.mkdir(parents=True)
            brief_path.parent.mkdir(parents=True)
            brief_path.write_text(
                json.dumps(
                    {
                        "elevenlabs": {
                            "voice_id": "lion-voice",
                            "voice_settings": {
                                "stability": 0.72,
                                "similarity_boost": 0.86,
                                "style": 0.0,
                                "use_speaker_boost": True,
                                "speed": 1.0,
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            profiles = _approved_voice_profiles(
                task_dir=task_dir,
                voices={"lion": "lion-voice"},
            )

        self.assertEqual(profiles["lion"]["approved_speed"], 1.0)
        self.assertEqual(
            profiles["lion"]["source"],
            "workspace/assets/characters/lion/voice.brief.json",
        )
        self.assertEqual(
            profiles["lion"]["voice_settings"]["stability"],
            0.72,
        )

    def test_dialogue_replacement_detects_seedance_speech_in_any_language(
        self,
    ) -> None:
        class _Model:
            def transcribe(self, *_args: object, **kwargs: object) -> tuple:
                self.kwargs = kwargs
                words = [
                    SimpleNamespace(
                        word=text,
                        probability=0.9,
                        start=0.2 + index * 0.4,
                        end=0.5 + index * 0.4,
                    )
                    for index, text in enumerate(
                        ("wrong", "spoken", "guide")
                    )
                ]
                return (
                    iter(
                        [
                            SimpleNamespace(
                                start=0.2,
                                end=1.4,
                                text="wrong spoken guide",
                                words=words,
                            )
                        ]
                    ),
                    SimpleNamespace(
                        language="en",
                        language_probability=0.99,
                    ),
                )

        model = _Model()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.mp4"
            source.write_bytes(b"provider-media")
            result = audit_seedance_character_speech(
                source,
                model=model,
            )
        self.assertNotIn("language", model.kwargs)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["requires_replacement"])
        self.assertEqual(result["detected_language"], "en")
        self.assertEqual(
            result["segments"][0]["detected_speech_word_windows"],
            [
                {
                    "start_seconds": 0.2,
                    "end_seconds": 0.5,
                    "probability": 0.9,
                },
                {
                    "start_seconds": 0.6,
                    "end_seconds": 0.9,
                    "probability": 0.9,
                },
                {
                    "start_seconds": 1.0,
                    "end_seconds": 1.3,
                    "probability": 0.9,
                },
            ],
        )

    def test_phrase_groups_use_arabic_punctuation_and_five_word_cap(self) -> None:
        words = [
            {"text": text, "start": index * 0.2, "end": index * 0.2 + 0.15}
            for index, text in enumerate(
                ["هذا", "اختبار،", "ثم", "خمس", "كلمات", "من", "هنا"]
            )
        ]
        self.assertEqual(_phrase_groups(words), [(0, 2), (2, 7)])

    def test_locked_mouth_windows_ignore_stochastic_tts_alignment_gap(
        self,
    ) -> None:
        words = [
            {"text": "يحكى", "start": 0.0, "end": 0.5},
            {"text": "أنه", "start": 0.9, "end": 1.2},
            {"text": "العيد،", "start": 1.3, "end": 1.8},
            {"text": "خرج", "start": 2.2, "end": 2.6},
            {"text": "عرينه.", "start": 2.7, "end": 3.2},
        ]
        self.assertEqual(len(_phrase_groups(words)), 3)
        self.assertEqual(
            _phrase_groups(words, break_on_alignment_gap=False),
            [(0, 3), (3, 5)],
        )

    def test_more_arabic_phrase_groups_coalesce_to_detected_mouth_windows(
        self,
    ) -> None:
        plans = _cue_phrase_plans(
            cue={
                "line_id": "L-008",
                "start_seconds": 8.0,
                "end_seconds": 14.8,
            },
            cue_index=2,
            source_words=[
                {"text": "نعم،", "start": 0.0, "end": 0.4},
                {"text": "أنت", "start": 0.45, "end": 0.8},
                {"text": "محق...", "start": 0.85, "end": 1.3},
                {"text": "يا", "start": 1.4, "end": 1.7},
                {"text": "وجبتي", "start": 1.75, "end": 2.2},
                {"text": "الشهية.", "start": 2.25, "end": 2.8},
            ],
            source_duration=2.8,
            picture_duration=15.0,
            fill_target_window=True,
            target_windows=[(10.39, 12.23), (13.0, 14.69)],
        )
        self.assertEqual(len(plans), 2)
        self.assertEqual(plans[0]["word_start_index"], 0)
        self.assertEqual(plans[0]["word_end_index"], 3)
        self.assertEqual(plans[1]["word_start_index"], 3)
        self.assertEqual(plans[1]["word_end_index"], 6)

    def test_phrase_plan_rejects_unnatural_tempo(self) -> None:
        cue = {
            "line_id": "L-001",
            "start_seconds": 0.0,
            "end_seconds": 0.4,
        }
        source = [{"text": "مرحبًا", "start": 0.0, "end": 1.0}]
        with self.assertRaisesRegex(
            ArabicSegmentEmbeddingError,
            "allowed natural range",
        ):
            _cue_phrase_plans(
                cue=cue,
                cue_index=1,
                source_words=source,
                source_duration=1.0,
                picture_duration=2.0,
            )

    def test_short_speech_uses_natural_lower_bound_inside_window(self) -> None:
        cue = {
            "line_id": "L-001",
            "start_seconds": 0.0,
            "end_seconds": 2.0,
        }
        plans = _cue_phrase_plans(
            cue=cue,
            cue_index=1,
            source_words=[{"text": "مرحبًا", "start": 0.0, "end": 0.5}],
            source_duration=0.5,
            picture_duration=2.0,
        )
        self.assertEqual(plans[0]["tempo_factor"], 0.75)
        self.assertLess(plans[0]["target_end_seconds"], cue["end_seconds"])

    def test_detected_mouth_window_is_filled_to_its_exact_end(self) -> None:
        cue = {
            "line_id": "L-002",
            "start_seconds": 8.0,
            "end_seconds": 14.27,
        }
        plans = _cue_phrase_plans(
            cue=cue,
            cue_index=1,
            source_words=[
                {"text": "لا", "start": 0.0, "end": 2.0},
                {"text": "تبكِ", "start": 2.1, "end": 4.2},
            ],
            source_duration=4.2,
            picture_duration=14.88,
            fill_target_window=True,
        )
        self.assertAlmostEqual(plans[-1]["target_end_seconds"], 14.27)

    def test_long_mouth_window_uses_phrase_hold_instead_of_unnatural_tempo(
        self,
    ) -> None:
        plans = _cue_phrase_plans(
            cue={
                "line_id": "L-002",
                "start_seconds": 8.0,
                "end_seconds": 14.27,
            },
            cue_index=1,
            source_words=[
                {"text": "لا،", "start": 0.0, "end": 1.5},
                {"text": "تبكِ", "start": 1.6, "end": 3.3},
            ],
            source_duration=3.3,
            picture_duration=14.88,
            fill_target_window=True,
        )
        self.assertEqual(len(plans), 2)
        self.assertEqual(plans[0]["tempo_factor"], 1.0)
        self.assertGreater(plans[1]["phrase_hold_offset_seconds"], 1.0)
        self.assertAlmostEqual(plans[-1]["target_end_seconds"], 14.27)

    def test_phrase_holds_preserve_native_tempo_and_create_real_pauses(
        self,
    ) -> None:
        plans = _cue_phrase_plans(
            cue={
                "line_id": "L-005",
                "start_seconds": 0.0,
                "end_seconds": 5.6,
            },
            cue_index=1,
            source_words=[
                {"text": "خذ", "start": 0.0, "end": 0.3},
                {"text": "شيئًا.", "start": 0.35, "end": 1.435},
                {"text": "لكنها", "start": 1.828, "end": 2.2},
                {"text": "أمانة،", "start": 2.25, "end": 3.118},
                {"text": "فاحفظها.", "start": 3.198, "end": 5.24771},
            ],
            source_duration=5.24771,
            picture_duration=15.0,
            fill_target_window=True,
        )
        self.assertEqual(len(plans), 3)
        self.assertTrue(all(plan["tempo_factor"] == 1.0 for plan in plans))
        self.assertAlmostEqual(
            plans[1]["target_start_seconds"]
            - plans[0]["target_end_seconds"],
            0.509145,
        )
        self.assertAlmostEqual(
            plans[2]["target_start_seconds"]
            - plans[1]["target_end_seconds"],
            0.196145,
        )
        self.assertAlmostEqual(plans[-1]["target_end_seconds"], 5.6)

    def test_large_detected_visual_lead_overrides_storyboard_start(self) -> None:
        timing = _resolved_cue_timing(
            {
                "line_id": "L-001",
                "start_seconds": 0.6,
                "end_seconds": 7.0,
            },
            {
                "segments": [
                    {
                        "start_seconds": 0.0,
                        "end_seconds": 5.38,
                        "forbidden_speech": True,
                    }
                ]
            },
            visual_onset_guard_seconds=0.0,
            use_detected_end=True,
            use_full_detected_window=True,
        )
        self.assertAlmostEqual(timing["target_start_seconds"], 0.0)
        self.assertAlmostEqual(timing["target_end_seconds"], 5.38)

    def test_seedance_speech_intervals_are_padded_and_merged(self) -> None:
        intervals = _forbidden_speech_intervals(
            {
                "segments": [
                    {
                        "start_seconds": 0.1,
                        "end_seconds": 0.5,
                        "forbidden_speech": True,
                    },
                    {
                        "start_seconds": 0.52,
                        "end_seconds": 0.9,
                        "forbidden_speech": True,
                    },
                    {
                        "start_seconds": 1.5,
                        "end_seconds": 1.8,
                        "forbidden_speech": False,
                    },
                ]
            },
            duration_seconds=2.0,
        )
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0][0], 0.02)
        self.assertAlmostEqual(intervals[0][1], 0.98)

    def test_dialogue_replacement_cuts_only_detected_speech(self) -> None:
        intervals = _forbidden_speech_intervals(
            {
                "segments": [
                    {
                        "start_seconds": 1.6,
                        "end_seconds": 1.8,
                        "forbidden_speech": True,
                    }
                ]
            },
            duration_seconds=2.0,
        )
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0][0], 1.52)
        self.assertAlmostEqual(intervals[0][1], 1.88)

    def test_word_windows_preserve_long_native_action_audio_gap(self) -> None:
        intervals = _forbidden_speech_intervals(
            {
                "segments": [
                    {
                        "start_seconds": 3.43,
                        "end_seconds": 13.93,
                        "forbidden_speech": True,
                        "detected_speech_word_windows": [
                            {
                                "start_seconds": 3.43,
                                "end_seconds": 3.75,
                            },
                            {
                                "start_seconds": 11.27,
                                "end_seconds": 12.43,
                            },
                            {
                                "start_seconds": 12.43,
                                "end_seconds": 13.93,
                            },
                        ],
                    }
                ]
            },
            duration_seconds=15.0,
        )
        self.assertEqual(intervals, [(3.35, 3.83), (11.19, 14.01)])

    def test_speech_cut_unions_words_with_final_dialogue_windows(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp,
            mock.patch(
                "narrated_fable_drama.dubbing.arabic_segment."
                "run_media_command"
            ),
        ):
            root = Path(temp)
            source = root / "source.mp4"
            output = root / "output.mp4"
            source.write_bytes(b"source")

            def _publish_output(*_args: object, **_kwargs: object) -> None:
                output.with_name(
                    f".{output.name}.speech-cut.tmp.mp4"
                ).write_bytes(b"clean")

            with mock.patch(
                "narrated_fable_drama.dubbing.arabic_segment."
                "run_media_command",
                side_effect=_publish_output,
            ):
                result = _render_seedance_speech_cut(
                    source_video=source,
                    output_video=output,
                    speech_gate={
                        "segments": [
                            {
                                "start_seconds": 3.43,
                                "end_seconds": 13.93,
                                "forbidden_speech": True,
                                "detected_speech_word_windows": [
                                    {
                                        "start_seconds": 3.43,
                                        "end_seconds": 3.75,
                                    },
                                    {
                                        "start_seconds": 11.27,
                                        "end_seconds": 13.93,
                                    },
                                ],
                            }
                        ]
                    },
                    duration_seconds=15.0,
                    final_dialogue_intervals=[(10.25, 14.5)],
                )
        self.assertEqual(
            result["cut_intervals_seconds"],
            [[3.35, 3.83], [10.25, 14.5]],
        )
        self.assertEqual(
            result["preserved_source_audio_intervals_seconds"],
            [[0.0, 3.35], [3.83, 10.25], [14.5, 15.0]],
        )

    def test_seedance_speech_cut_includes_short_middle_asr_fragment(self) -> None:
        intervals = _forbidden_speech_intervals(
            {
                "segments": [
                    {
                        "start_seconds": 5.74,
                        "end_seconds": 7.84,
                        "arabic_token_count": 3,
                        "mean_word_probability": 0.83,
                        "forbidden_speech": True,
                    },
                    {
                        "start_seconds": 7.84,
                        "end_seconds": 8.92,
                        "arabic_token_count": 2,
                        "mean_word_probability": 0.86,
                        "forbidden_speech": False,
                    },
                    {
                        "start_seconds": 8.92,
                        "end_seconds": 11.14,
                        "arabic_token_count": 4,
                        "mean_word_probability": 0.84,
                        "forbidden_speech": True,
                    },
                ]
            },
            duration_seconds=15.0,
        )
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0][0], 5.66)
        self.assertAlmostEqual(intervals[0][1], 11.22)

    def test_detected_provider_speech_delays_dub_inside_storyboard_window(
        self,
    ) -> None:
        timing = _resolved_cue_timing(
            {
                "line_id": "L-002",
                "start_seconds": 7.5,
                "end_seconds": 14.5,
            },
            {
                "segments": [
                    {
                        "start_seconds": 9.18,
                        "end_seconds": 11.96,
                        "forbidden_speech": True,
                    },
                    {
                        "start_seconds": 11.96,
                        "end_seconds": 14.54,
                        "forbidden_speech": True,
                    },
                ]
            },
        )
        self.assertEqual(
            timing["timing_source"],
            (
                "seedance_detected_speech_onset_plus_visual_guard_"
                "within_storyboard_window"
            ),
        )
        self.assertAlmostEqual(timing["target_start_seconds"], 9.73)
        self.assertAlmostEqual(timing["target_end_seconds"], 14.5)
        self.assertAlmostEqual(
            timing["visual_mouth_onset_guard_seconds"],
            0.55,
        )

    def test_replacement_uses_complete_detected_seedance_speech_window(
        self,
    ) -> None:
        timing = _resolved_cue_timing(
            {
                "line_id": "L-007",
                "start_seconds": 4.0,
                "end_seconds": 9.25,
            },
            {
                "segments": [
                    {
                        "start_seconds": 7.15,
                        "end_seconds": 8.19,
                        "speech_token_count": 2,
                        "mean_word_probability": 0.85,
                        "forbidden_speech": False,
                    },
                    {
                        "start_seconds": 8.19,
                        "end_seconds": 10.87,
                        "speech_token_count": 5,
                        "mean_word_probability": 0.76,
                        "forbidden_speech": True,
                    },
                ]
            },
            visual_onset_guard_seconds=0.0,
            use_detected_end=True,
            use_full_detected_window=True,
        )
        self.assertEqual(
            timing["timing_source"],
            "seedance_detected_speech_window",
        )
        self.assertAlmostEqual(timing["target_start_seconds"], 7.15)
        self.assertAlmostEqual(timing["target_end_seconds"], 10.87)
        self.assertEqual(
            timing["seedance_detected_speech_windows_seconds"],
            [[7.15, 10.87]],
        )

    def test_frame_reviewed_window_overrides_alignment_but_preserves_detection(
        self,
    ) -> None:
        timing = {
            "storyboard_start_seconds": 7.5,
            "storyboard_end_seconds": 14.8,
            "target_start_seconds": 8.38,
            "target_end_seconds": 14.82,
            "timing_source": "seedance_detected_speech_window",
            "seedance_detected_speech_start_seconds": 8.38,
            "seedance_detected_speech_end_seconds": 14.82,
            "seedance_detected_speech_windows_seconds": [[8.38, 14.82]],
            "visual_mouth_onset_guard_seconds": 0.0,
        }
        adjusted, target_windows = _apply_reviewed_cue_window(
            {
                "line_id": "L-004",
                "start_seconds": 7.5,
                "end_seconds": 14.8,
            },
            timing,
            (8.75, 14.55),
            picture_duration=15.069,
        )
        self.assertEqual(
            adjusted["timing_source"],
            "model_reviewed_visual_mouth_window",
        )
        self.assertAlmostEqual(adjusted["target_start_seconds"], 8.75)
        self.assertAlmostEqual(adjusted["target_end_seconds"], 14.55)
        self.assertEqual(
            adjusted["seedance_detected_speech_windows_seconds"],
            [[8.38, 14.82]],
        )
        self.assertEqual(target_windows, [(8.75, 14.55)])
        self.assertAlmostEqual(
            adjusted["reviewed_timing_adjustment"][
                "start_adjustment_seconds"
            ],
            0.37,
        )
        self.assertAlmostEqual(
            adjusted["reviewed_timing_adjustment"][
                "end_adjustment_seconds"
            ],
            -0.27,
        )

    def test_frame_reviewed_window_must_stay_inside_storyboard_window(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ArabicSegmentEmbeddingError,
            "Storyboard dialogue window",
        ):
            _apply_reviewed_cue_window(
                {
                    "line_id": "L-004",
                    "start_seconds": 7.5,
                    "end_seconds": 14.8,
                },
                {
                    "target_start_seconds": 8.38,
                    "target_end_seconds": 14.82,
                    "seedance_detected_speech_start_seconds": 8.38,
                },
                (7.4, 14.55),
                picture_duration=15.069,
            )

    def test_frame_reviewed_window_can_keep_an_earlier_detected_mouth_onset(
        self,
    ) -> None:
        adjusted, target_windows = _apply_reviewed_cue_window(
            {
                "line_id": "L-001",
                "start_seconds": 0.6,
                "end_seconds": 7.0,
            },
            {
                "target_start_seconds": 0.0,
                "target_end_seconds": 5.38,
                "seedance_detected_speech_start_seconds": 0.0,
                "seedance_detected_speech_end_seconds": 5.38,
            },
            (0.0, 5.86),
            picture_duration=15.093,
        )
        self.assertEqual(target_windows, [(0.0, 5.86)])
        self.assertAlmostEqual(adjusted["target_start_seconds"], 0.0)
        self.assertAlmostEqual(adjusted["target_end_seconds"], 5.86)

    def test_detected_speech_pause_is_preserved_as_two_mouth_windows(
        self,
    ) -> None:
        timing = _resolved_cue_timing(
            {
                "line_id": "L-002",
                "start_seconds": 8.0,
                "end_seconds": 14.8,
            },
            {
                "segments": [
                    {
                        "start_seconds": 7.95,
                        "end_seconds": 10.75,
                        "forbidden_speech": True,
                    },
                    {
                        "start_seconds": 11.85,
                        "end_seconds": 14.27,
                        "forbidden_speech": True,
                    },
                ]
            },
            visual_onset_guard_seconds=0.0,
            use_detected_end=True,
            use_full_detected_window=True,
        )
        self.assertEqual(
            timing["seedance_detected_speech_windows_seconds"],
            [[8.0, 10.75], [11.85, 14.27]],
        )

    def test_adjacent_cue_ignores_tiny_tail_overlap_from_prior_speaker(
        self,
    ) -> None:
        timing = _resolved_cue_timing(
            {
                "line_id": "L-008",
                "start_seconds": 8.0,
                "end_seconds": 14.8,
            },
            {
                "segments": [
                    {
                        "start_seconds": 4.21,
                        "end_seconds": 8.15,
                        "forbidden_speech": True,
                    },
                    {
                        "start_seconds": 11.14,
                        "end_seconds": 14.53,
                        "forbidden_speech": True,
                    },
                ]
            },
            visual_onset_guard_seconds=0.0,
            use_detected_end=True,
            use_full_detected_window=True,
        )
        self.assertAlmostEqual(timing["target_start_seconds"], 11.14)
        self.assertAlmostEqual(timing["target_end_seconds"], 14.53)
        self.assertEqual(
            timing["seedance_detected_speech_windows_seconds"],
            [[11.14, 14.53]],
        )

    def test_two_arabic_phrases_map_to_two_detected_mouth_windows(
        self,
    ) -> None:
        plans = _cue_phrase_plans(
            cue={
                "line_id": "L-002",
                "start_seconds": 8.0,
                "end_seconds": 14.27,
            },
            cue_index=2,
            source_words=[
                {"text": "يحكى", "start": 0.0, "end": 1.0},
                {"text": "العيد،", "start": 1.1, "end": 2.1},
                {"text": "خرج", "start": 2.2, "end": 3.1},
                {"text": "عرينه.", "start": 3.2, "end": 4.2},
            ],
            source_duration=4.2,
            picture_duration=15.0,
            fill_target_window=True,
            target_windows=[(8.0, 10.75), (11.85, 14.27)],
        )
        self.assertEqual(len(plans), 2)
        self.assertAlmostEqual(plans[0]["target_end_seconds"], 10.75)
        self.assertAlmostEqual(plans[1]["target_start_seconds"], 11.85)
        self.assertAlmostEqual(plans[1]["target_end_seconds"], 14.27)

    def test_non_speech_lead_before_detected_words_is_preserved(self) -> None:
        intervals = _forbidden_speech_intervals(
            {
                "segments": [
                    {
                        "start_seconds": 9.18,
                        "end_seconds": 14.54,
                        "forbidden_speech": True,
                    }
                ]
            },
            duration_seconds=15.0,
        )
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0][0], 9.10)
        self.assertAlmostEqual(intervals[0][1], 14.62)

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "ffmpeg and ffprobe are required",
    )
    def test_seedance_speech_cut_mutes_mixed_audio_only_inside_cut(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.mp4"
            output = root / "speech-cut.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=320x180:r=24:d=2",
                    "-f",
                    "lavfi",
                    "-i",
                    (
                        "aevalsrc="
                        "0.15*sin(2*PI*220*t)+0.08*sin(2*PI*660*t)|"
                        "0.15*sin(2*PI*220*t)-0.08*sin(2*PI*660*t)"
                        ":s=48000:d=2"
                    ),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-pix_fmt",
                    "yuv420p",
                    source,
                ],
                check=True,
            )
            record = _render_seedance_speech_cut(
                source_video=source,
                output_video=output,
                speech_gate={
                    "segments": [
                        {
                            "start_seconds": 0.4,
                            "end_seconds": 0.8,
                            "forbidden_speech": True,
                        }
                    ]
                },
                duration_seconds=2.0,
            )
            self.assertEqual(record["status"], "APPLIED")
            self.assertEqual(record["cut_intervals_seconds"], [[0.32, 0.88]])
            self.assertEqual(
                record["dialogue_gap_fill_source"],
                "digital_silence",
            )
            self.assertEqual(record["elevenlabs_non_dialogue_request_count"], 0)
            self.assertEqual(record["native_audio_loop_count"], 0)
            self.assertFalse(record["center_suppression_applied"])

            def rms(start: float) -> float:
                pcm = subprocess.check_output(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-ss",
                        str(start),
                        "-t",
                        "0.2",
                        "-i",
                        output,
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        "8000",
                        "-f",
                        "s16le",
                        "-",
                    ]
                )
                samples = array.array("h")
                samples.frombytes(pcm)
                return math.sqrt(
                    sum(sample * sample for sample in samples)
                    / max(1, len(samples))
                )

            self.assertLess(rms(0.5), 10.0)
            self.assertGreater(rms(1.2), 100.0)

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"),
        "ffmpeg and ffprobe are required",
    )
    def test_dialogue_replacement_preserves_original_audio_outside_cut(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.mp4"
            speech_cut = root / "speech-cut.mp4"
            cue = root / "cue.mp3"
            output = root / "video.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=320x180:r=24:d=2",
                    "-f",
                    "lavfi",
                    "-i",
                    (
                        "aevalsrc="
                        "0.15*sin(2*PI*220*t)+0.08*sin(2*PI*660*t)|"
                        "0.15*sin(2*PI*220*t)-0.08*sin(2*PI*660*t)"
                        ":s=48000:d=2"
                    ),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-pix_fmt",
                    "yuv420p",
                    source,
                ],
                check=True,
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=0.5",
                    "-c:a",
                    "libmp3lame",
                    cue,
                ],
                check=True,
            )
            edit = _render_seedance_speech_cut(
                source_video=source,
                output_video=speech_cut,
                speech_gate={
                    "segments": [
                        {
                            "start_seconds": 0.5,
                            "end_seconds": 1.1,
                            "forbidden_speech": True,
                        }
                    ]
                },
                duration_seconds=2.0,
            )
            _render_embedded_video(
                seedance_background_video=speech_cut,
                cue_files=[cue],
                phrase_plans=[
                    {
                        "input_index": 1,
                        "source_start_seconds": 0.0,
                        "source_end_seconds": 0.5,
                        "target_start_seconds": 0.55,
                        "target_end_seconds": 1.05,
                        "tempo_factor": 1.0,
                    }
                ],
                duration_seconds=2.0,
                output=output,
            )

            def amplitude(start: float, frequency: float) -> float:
                pcm = subprocess.check_output(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-ss",
                        str(start),
                        "-t",
                        "0.2",
                        "-i",
                        output,
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        "8000",
                        "-f",
                        "s16le",
                        "-",
                    ]
                )
                samples = array.array("h")
                samples.frombytes(pcm)
                cosine = 0.0
                sine = 0.0
                for index, sample in enumerate(samples):
                    phase = 2 * math.pi * frequency * index / 8000
                    cosine += sample * math.cos(phase)
                    sine += sample * math.sin(phase)
                return (
                    2
                    * math.hypot(cosine, sine)
                    / max(1, len(samples))
                    / 32768
                )

            self.assertGreater(amplitude(0.1, 220), 0.01)
            self.assertLess(amplitude(0.65, 220), 0.005)
            self.assertLess(amplitude(0.65, 660), 0.005)
            self.assertGreater(amplitude(0.65, 440), 0.01)
            self.assertGreater(amplitude(1.5, 220), 0.01)


if __name__ == "__main__":
    unittest.main()
