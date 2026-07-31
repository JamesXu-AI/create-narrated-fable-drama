from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "finish-postproduction"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS))

from finishing.plan import (  # noqa: E402
    RepairPlanError,
    ensure_renderable,
    load_repair_plan,
)
from assemble_segment_videos import _render_filter  # noqa: E402
from boundary.qc import _measure_master_sample  # noqa: E402
from boundary.qc_evidence import _extract_frame_evidence  # noqa: E402
from post_timeline import TimelineError, _authored_audio_handoff  # noqa: E402
from subtitles.subtitle_compile import _source_time_to_retained_time  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def _fixture(tmp_path: Path) -> tuple[list[object], Path, dict[str, object]]:
    records = []
    evidence_segments = []
    segment_plans = []
    for index in range(1, 3):
        segment_id = f"segment-{index:03d}"
        source = tmp_path / f"{segment_id}.mp4"
        source.write_bytes(f"media-{index}".encode())
        source_hash = _sha(source)
        attempt = f"{segment_id}__attempt-0001"
        records.append(
            SimpleNamespace(
                segment_name=segment_id,
                video_path=source,
                probe=SimpleNamespace(duration_seconds=10.0),
            )
        )
        line_id = f"L-{index:03d}"
        evidence_segments.append(
            {
                "segment_id": segment_id,
                "source_sha256": source_hash,
                "provider_attempt_id": attempt,
                "duration_seconds": 10.0,
                "dialogue_cues": [
                    {
                        "line_id": line_id,
                        "start_seconds": 2.0,
                        "end_seconds": 4.0,
                    }
                ],
            }
        )
        segment_plans.append(
            {
                "segment_id": segment_id,
                "source_sha256": source_hash,
                "provider_attempt_id": attempt,
                "picture": {
                    "source_in_seconds": 0.0,
                    "source_out_seconds": 10.0,
                    "removed_intervals": [],
                    "color_adjustments": [],
                },
                "audio": {
                    "source_in_seconds": 0.0,
                    "source_out_seconds": 10.0,
                    "removed_intervals": [],
                    "timeline_offset_from_picture_in_seconds": 0.0,
                    "gain_db": 0.0,
                    "fade_in_seconds": 0.0,
                    "fade_out_seconds": 0.0,
                    "gain_adjustments": [],
                },
                "protected_dialogue_line_ids": [line_id],
                "reason": "Keep the accepted source unchanged.",
            }
        )
    evidence = {
        "contract": "finish-postproduction-evidence/v1",
        "coverage": "complete_task",
        "render_authorization": True,
        "source_set_sha256": "source-set",
        "observation_window": {
            "outgoing_tail_seconds": 3.0,
            "incoming_head_seconds": 3.0,
        },
        "segments": evidence_segments,
        "boundaries": [
            {
                "boundary_id": "segment-001--segment-002",
                "from": "segment-001",
                "to": "segment-002",
            }
        ],
    }
    evidence_path = tmp_path / "evidence.json"
    _write_json(evidence_path, evidence)
    plan = {
        "contract": "llm-postproduction-repair-plan/v1",
        "evidence_manifest_sha256": _sha(evidence_path),
        "source_set_sha256": "source-set",
        "decision_authority": "editor-restoration-master-model",
        "observation_window": {
            "outgoing_tail_seconds": 3.0,
            "incoming_head_seconds": 3.0,
        },
        "segments": segment_plans,
        "boundaries": [
            {
                "boundary_id": "segment-001--segment-002",
                "from": "segment-001",
                "to": "segment-002",
                "evidence_boundary_id": "segment-001--segment-002",
                "decision": "no_op",
                "scope": "boundary_local",
                "picture": {
                    "operation": "hard_cut",
                    "overlap_seconds": 0.0,
                },
                "audio": {
                    "operation": "no_op",
                    "outgoing_fade_out_seconds": 0.0,
                    "incoming_fade_in_seconds": 0.0,
                },
                "modification_intervals": [],
                "protected_dialogue_line_ids": ["L-001", "L-002"],
                "protected_events": ["accepted action landing"],
                "reason": "Evidence supports the native cut.",
                "candidates": [],
            }
        ],
        "audio_bridges": [],
        "terminal_audio": {
            "segment_id": "segment-002",
            "fade_out_seconds": 0.0,
            "reason": "The accepted native ending already resolves cleanly.",
        },
        "delivery": {
            "video_codec": "libx264",
            "preset": "medium",
            "crf": 18,
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_bitrate": "192k",
            "sample_rate_hz": 48000,
            "channel_layout": "stereo",
        },
        "overall_reason": "Preserve the accepted edit.",
    }
    return records, evidence_path, plan


def _load(
    tmp_path: Path,
    records: list[object],
    evidence_path: Path,
    plan: dict[str, object],
) -> dict[str, object]:
    plan_path = tmp_path / "plan.json"
    _write_json(plan_path, plan)
    return load_repair_plan(plan_path, evidence_path, records)


class RepairPlanTests(unittest.TestCase):
    def test_final_boundary_audit_uses_shared_frame_metrics(self) -> None:
        frames = [
            (
                bytes([32 + index]) * 4,
                bytes([120 + index % 3]) * 4,
                bytes([132 + index % 5]) * 4,
            )
            for index in range(48)
        ]
        config = {
            "analysis": {
                "width": 2,
                "anchor_frame_count": 2,
            },
            "strict_sample": {
                "frame_rate": 24,
                "frame_count": 48,
            },
        }
        with (
            patch("boundary.qc._probe_dimensions", return_value=(2, 2)),
            patch("boundary.qc._extract_yuv_frames", return_value=frames),
        ):
            metrics = _measure_master_sample(
                Path("picture-lock-seam.mp4"),
                config,
            )
        self.assertEqual(
            metrics["analysis_role"],
            "post_assembly_technical_detection_evidence_only",
        )
        self.assertEqual(metrics["analysis_frame_count_per_side"], 2)

    def test_boundary_frame_evidence_writes_manifest_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            sample = tmp_path / "strict-sample.mp4"
            sample.write_bytes(b"sample")
            output_dir = tmp_path / "evidence"
            config = {
                "strict_sample": {
                    "frame_rate": 24,
                    "frame_count": 48,
                    "evidence_frame_width": 960,
                }
            }

            def fake_run(command: list[str], *, label: str) -> None:
                output = Path(command[-1])
                output.parent.mkdir(parents=True, exist_ok=True)
                if "%06d" in output.name:
                    for index in range(1, 49):
                        Path(str(output).replace("%06d", f"{index:06d}")).write_bytes(
                            b"frame"
                        )
                else:
                    output.write_bytes(b"contact-sheet")

            with patch(
                "boundary.qc_evidence._run",
                side_effect=fake_run,
            ):
                result = _extract_frame_evidence(
                    sample,
                    output_dir,
                    config,
                )
            manifest = json.loads(
                Path(result["frame_manifest"]).read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["frame_count"], 48)
            self.assertEqual(len(manifest["frames"]), 48)

    def test_timeline_reads_current_authored_audio_handoff_field(self) -> None:
        self.assertEqual(
            _authored_audio_handoff(
                {
                    "audio_handoff_en": (
                        "The buzz enters as a J cut before the Lion reacts."
                    )
                }
            ),
            "The buzz enters as a J cut before the Lion reacts.",
        )
        with self.assertRaisesRegex(TimelineError, "audio_handoff_en"):
            _authored_audio_handoff({"audio_handoff": "stale field"})

    def test_valid_explicit_plan_loads_without_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            loaded = _load(tmp_path, records, evidence_path, plan)
            ensure_renderable(loaded)
            self.assertEqual(loaded["boundaries"][0]["decision"], "no_op")

    def test_soft_cut_can_smooth_forced_music_stop_without_audio_overlap(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            plan["segments"][0]["audio"]["fade_out_seconds"] = 0.4
            plan["segments"][1]["audio"]["fade_in_seconds"] = 0.3
            boundary = plan["boundaries"][0]
            boundary["decision"] = "repair"
            boundary["audio"] = {
                "operation": "soft_cut",
                "outgoing_fade_out_seconds": 0.4,
                "incoming_fade_in_seconds": 0.3,
            }
            boundary["modification_intervals"] = [
                {
                    "media": "audio",
                    "segment_id": "segment-001",
                    "start_seconds": 9.6,
                    "end_seconds": 10.0,
                    "reason": "Soften the forced Seedance music stop.",
                },
                {
                    "media": "audio",
                    "segment_id": "segment-002",
                    "start_seconds": 0.0,
                    "end_seconds": 0.3,
                    "reason": "Ease into the successor native mix.",
                },
            ]
            boundary["reason"] = (
                "The unfinished musical phrase is a provider boundary artifact; "
                "short dialogue-free fades make the cut unobtrusive."
            )
            loaded = _load(tmp_path, records, evidence_path, plan)
            ensure_renderable(loaded)
            self.assertEqual(
                loaded["boundaries"][0]["audio"]["operation"],
                "soft_cut",
            )

    def test_soft_cut_requires_an_explicit_fade(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            boundary = plan["boundaries"][0]
            boundary["decision"] = "repair"
            boundary["audio"]["operation"] = "soft_cut"
            with self.assertRaisesRegex(
                RepairPlanError,
                "soft_cut requires at least one explicit audio fade",
            ):
                _load(tmp_path, records, evidence_path, plan)

    def test_soft_cut_cannot_move_native_audio_or_overlap_picture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            plan["segments"][0]["audio"]["fade_out_seconds"] = 0.4
            boundary = plan["boundaries"][0]
            boundary["decision"] = "repair"
            boundary["picture"] = {
                "operation": "dissolve",
                "overlap_seconds": 0.2,
            }
            boundary["audio"] = {
                "operation": "soft_cut",
                "outgoing_fade_out_seconds": 0.4,
                "incoming_fade_in_seconds": 0.0,
            }
            boundary["modification_intervals"] = [
                {
                    "media": "picture",
                    "segment_id": "segment-001",
                    "start_seconds": 9.8,
                    "end_seconds": 10.0,
                    "reason": "Explicit outgoing dissolve handle.",
                },
                {
                    "media": "picture",
                    "segment_id": "segment-002",
                    "start_seconds": 0.0,
                    "end_seconds": 0.2,
                    "reason": "Explicit incoming dissolve handle.",
                },
                {
                    "media": "audio",
                    "segment_id": "segment-001",
                    "start_seconds": 9.6,
                    "end_seconds": 10.0,
                    "reason": "Explicit outgoing soft fade.",
                },
            ]
            with self.assertRaisesRegex(
                RepairPlanError,
                "soft_cut must keep both native audio events aligned",
            ):
                _load(tmp_path, records, evidence_path, plan)

    def test_segment_fade_cannot_overlap_protected_dialogue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            plan["segments"][0]["audio"]["fade_out_seconds"] = 7.0
            boundary = plan["boundaries"][0]
            boundary["decision"] = "repair"
            boundary["scope"] = "segment_scope_review"
            boundary["audio"] = {
                "operation": "soft_cut",
                "outgoing_fade_out_seconds": 7.0,
                "incoming_fade_in_seconds": 0.0,
            }
            boundary["modification_intervals"] = [
                {
                    "media": "audio",
                    "segment_id": "segment-001",
                    "start_seconds": 3.0,
                    "end_seconds": 10.0,
                    "reason": "Deliberately unsafe fade.",
                }
            ]
            with self.assertRaisesRegex(
                RepairPlanError,
                "audio fade-out overlaps protected dialogue L-001",
            ):
                _load(tmp_path, records, evidence_path, plan)

    def test_terminal_fade_cannot_overlap_protected_dialogue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            plan["terminal_audio"] = {
                "segment_id": "segment-002",
                "fade_out_seconds": 7.0,
                "reason": "Deliberately unsafe terminal fade.",
            }
            with self.assertRaisesRegex(
                RepairPlanError,
                "Terminal audio fade overlaps protected dialogue L-002",
            ):
                _load(tmp_path, records, evidence_path, plan)

    def test_missing_semantic_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            del plan["boundaries"][0]["audio"]["incoming_fade_in_seconds"]
            with self.assertRaisesRegex(
                RepairPlanError,
                "missing incoming_fade_in_seconds",
            ):
                _load(tmp_path, records, evidence_path, plan)

    def test_preview_evidence_cannot_authorize_render(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["coverage"] = "preview_prefix"
            evidence["render_authorization"] = False
            _write_json(evidence_path, evidence)
            plan["evidence_manifest_sha256"] = _sha(evidence_path)
            with self.assertRaisesRegex(
                RepairPlanError,
                "Preview-prefix evidence cannot authorize",
            ):
                _load(tmp_path, records, evidence_path, plan)

    def test_boundary_local_interval_cannot_expand_past_three_seconds(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            boundary = plan["boundaries"][0]
            boundary["decision"] = "repair"
            boundary["modification_intervals"] = [
                {
                    "media": "audio",
                    "segment_id": "segment-001",
                    "start_seconds": 6.5,
                    "end_seconds": 8.0,
                    "reason": "Deliberately invalid local range.",
                }
            ]
            with self.assertRaisesRegex(
                RepairPlanError,
                "boundary-local modification scope",
            ):
                _load(tmp_path, records, evidence_path, plan)

    def test_stale_source_hash_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            records[0].video_path.write_bytes(b"changed")
            with self.assertRaisesRegex(
                RepairPlanError,
                "source media changed",
            ):
                _load(tmp_path, records, evidence_path, plan)

    def test_picture_trim_requires_explicit_local_edit_interval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            plan["segments"][0]["picture"]["source_out_seconds"] = 9.5
            plan["boundaries"][0]["decision"] = "repair"
            plan["boundaries"][0]["audio"]["operation"] = "l_cut"
            with self.assertRaisesRegex(
                RepairPlanError,
                "closing picture trim.*not covered",
            ):
                _load(tmp_path, records, evidence_path, plan)
            plan["boundaries"][0]["modification_intervals"] = [
                {
                    "media": "picture",
                    "segment_id": "segment-001",
                    "start_seconds": 9.5,
                    "end_seconds": 10.0,
                    "reason": "Remove the measured frozen tail frames.",
                }
            ]
            loaded = _load(tmp_path, records, evidence_path, plan)
            self.assertEqual(
                loaded["segments"][0]["picture"]["source_out_seconds"],
                9.5,
            )

    def test_internal_picture_and_audio_pause_can_be_explicitly_deleted(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            plan["segments"][0]["picture"]["removed_intervals"] = [
                {
                    "source_start_seconds": 4.5,
                    "source_end_seconds": 5.5,
                    "reason": "Remove an evidence-confirmed frozen pause.",
                }
            ]
            plan["segments"][0]["audio"]["removed_intervals"] = [
                {
                    "source_start_seconds": 4.5,
                    "source_end_seconds": 5.5,
                    "reason": "Keep synchronized native audio aligned to the picture edit.",
                }
            ]
            boundary = plan["boundaries"][0]
            boundary["decision"] = "repair"
            boundary["scope"] = "segment_scope_review"
            boundary["audio"]["operation"] = "native_cut"
            boundary["modification_intervals"] = [
                {
                    "media": "picture",
                    "segment_id": "segment-001",
                    "start_seconds": 4.5,
                    "end_seconds": 5.5,
                    "reason": "Delete the frozen picture pause.",
                },
                {
                    "media": "audio",
                    "segment_id": "segment-001",
                    "start_seconds": 4.5,
                    "end_seconds": 5.5,
                    "reason": "Delete the matching non-dialogue sound interval.",
                },
            ]
            loaded = _load(tmp_path, records, evidence_path, plan)
            self.assertEqual(
                loaded["segments"][0]["picture"]["removed_intervals"][0][
                    "source_start_seconds"
                ],
                4.5,
            )

    def test_regeneration_is_a_valid_decision_that_blocks_render(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            records, evidence_path, plan = _fixture(tmp_path)
            plan["boundaries"][0]["decision"] = "regenerate"
            loaded = _load(tmp_path, records, evidence_path, plan)
            with self.assertRaisesRegex(
                RepairPlanError,
                "requires source regeneration",
            ):
                ensure_renderable(loaded)

    def test_renderer_uses_explicit_independent_audio_timeline(self) -> None:
        records = [
            SimpleNamespace(
                segment_name=f"segment-{index:03d}",
                probe=SimpleNamespace(
                    frame_rate="24/1",
                    duration_seconds=10.0,
                    has_audio=True,
                ),
            )
            for index in range(1, 3)
        ]
        picture_edl = {
            "duration_seconds": 19.5,
            "picture_events": [
                {
                    "segment_id": "segment-001",
                    "source_in_seconds": 0.0,
                    "source_out_seconds": 10.0,
                    "source_ranges": [
                        {
                            "source_in_seconds": 0.0,
                            "source_out_seconds": 10.0,
                        }
                    ],
                    "color_adjustments": [],
                },
                {
                    "segment_id": "segment-002",
                    "source_in_seconds": 0.0,
                    "source_out_seconds": 10.0,
                    "source_ranges": [
                        {
                            "source_in_seconds": 0.0,
                            "source_out_seconds": 10.0,
                        }
                    ],
                    "color_adjustments": [],
                },
            ],
            "boundaries": [
                {
                    "from": "segment-001",
                    "to": "segment-002",
                    "picture_edit": "dissolve",
                    "overlap_seconds": 0.5,
                }
            ],
        }
        audio_timeline = {
            "tracks": [
                {
                    "events": [
                        {
                            "segment_id": "segment-001",
                            "source_in_seconds": 0.0,
                            "source_out_seconds": 10.0,
                            "source_ranges": [
                                {
                                    "source_in_seconds": 0.0,
                                    "source_out_seconds": 10.0,
                                }
                            ],
                            "timeline_in_seconds": 0.0,
                            "gain_db": 0.0,
                            "fade_in_seconds": 0.0,
                            "fade_out_seconds": 0.2,
                            "gain_adjustments": [],
                        },
                        {
                            "segment_id": "segment-002",
                            "source_in_seconds": 0.0,
                            "source_out_seconds": 10.0,
                            "source_ranges": [
                                {
                                    "source_in_seconds": 0.0,
                                    "source_out_seconds": 10.0,
                                }
                            ],
                            "timeline_in_seconds": 9.3,
                            "gain_db": -1.0,
                            "fade_in_seconds": 0.2,
                            "fade_out_seconds": 0.0,
                            "gain_adjustments": [],
                        },
                    ]
                }
            ],
            "audio_bridges": [],
            "native_audio_policy": {
                "terminal_audio": {
                    "segment_id": "segment-002",
                    "fade_out_seconds": 0.1,
                    "reason": "Explicit terminal protection.",
                }
            },
        }
        delivery = {
            "sample_rate_hz": 48000,
            "channel_layout": "stereo",
            "pixel_format": "yuv420p",
        }
        filter_graph = _render_filter(
            records,
            1920,
            1080,
            picture_edl,
            audio_timeline,
            delivery,
        )
        self.assertIn("xfade=transition=fade:duration=0.500000", filter_graph)
        self.assertIn(
            "afade=t=out:st=9.800000:d=0.200000",
            filter_graph,
        )
        self.assertIn("afade=t=in:st=0:d=0.200000", filter_graph)
        self.assertIn("amix=inputs=2:duration=longest:normalize=0", filter_graph)
        self.assertIn("adelay=446400S:all=1", filter_graph)
        self.assertNotIn("apad", filter_graph)
        self.assertNotIn("acrossfade", filter_graph)

    def test_subtitle_time_moves_across_internal_picture_deletion(self) -> None:
        ranges = [(0.0, 4.5), (5.5, 10.0)]
        self.assertEqual(
            _source_time_to_retained_time(
                ranges,
                6.0,
                tolerance_seconds=0.0,
            ),
            5.0,
        )
        self.assertIsNone(
            _source_time_to_retained_time(
                ranges,
                5.0,
                tolerance_seconds=0.0,
            )
        )


if __name__ == "__main__":
    unittest.main()
