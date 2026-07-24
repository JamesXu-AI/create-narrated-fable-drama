"""Orchestrate Boundary QC before assembly and audit the rendered picture lock."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

from .qc_evidence import (
    _boundary_directory,
    _extract_frame_evidence,
    _matches_selected,
    _render_comparison,
    _render_repaired_sample,
    _render_strict_sample,
)
from .qc_metrics import (
    _extract_tail_yuv_frames,
    _has_detectable_mismatch,
    _normalized_luma_correlation,
    append_segment_repair_filter,
    measure_boundary,
    triage_boundary,
)
from .qc_policy import (
    DEFAULT_CONFIG,
    BoundaryQCError,
    _load_json,
    _run,
    _write_json,
    load_config,
)
from narrated_fable_drama.media.ffmpeg import MediaCommandError
from narrated_fable_drama.media.probe import probe_json, stream_by_type


def prepare_boundary_qc(
    task_dir: Path,
    records: list[object],
    picture_edl: dict[str, Any],
    *,
    config_path: Path = DEFAULT_CONFIG,
    selected_boundary: str | None = None,
    generate_candidates: bool = True,
) -> tuple[Path, dict[str, dict[str, Any]], dict[str, Any]]:
    """Create pre-assembly evidence and return safe plans keyed by incoming Segment."""
    task_dir = task_dir.expanduser().resolve()
    config = load_config(config_path)
    root = task_dir / ".pending" / "finish-postproduction" / "boundary-qc"
    pre_root = root / "pre-assembly"
    manifest_path = root / "boundary-qc-manifest.json"
    record_by_name = {
        str(getattr(record, "segment_name")): record for record in records
    }
    manifest: dict[str, Any] = {
        "contract": "finish-boundary-qc/v1",
        "enabled": bool(config["enabled"]),
        "source_policy": "generated_segments_read_only",
        "decision_scope": "technical_detection_and_repair_candidates_only",
        "semantic_review_authority": "video-review",
        "config_path": str(config_path.expanduser().resolve()),
        "task_dir": str(task_dir),
        "picture_edl_contract": picture_edl.get("contract"),
        "pre_assembly_status": "disabled" if not config["enabled"] else "running",
        "boundaries": [],
    }
    repair_plans: dict[str, dict[str, Any]] = {}
    if not config["enabled"]:
        _write_json(manifest_path, manifest)
        return manifest_path, repair_plans, manifest
    boundaries = picture_edl.get("boundaries")
    if not isinstance(boundaries, list):
        raise BoundaryQCError("Picture EDL boundaries must be a list")
    for boundary in boundaries:
        if not isinstance(boundary, dict) or not _matches_selected(
            boundary, selected_boundary
        ):
            continue
        try:
            outgoing = record_by_name[str(boundary["from"])]
            incoming = record_by_name[str(boundary["to"])]
        except KeyError as exc:
            raise BoundaryQCError("Boundary references an unknown Segment") from exc
        directory = _boundary_directory(pre_root, boundary)
        original_sample = directory / "original-strict-seam.mp4"
        _render_strict_sample(outgoing, incoming, boundary, original_sample, config)
        evidence = _extract_frame_evidence(original_sample, directory, config)
        metrics = measure_boundary(outgoing, incoming, config, boundary)
        status, reason, plan = triage_boundary(boundary, metrics, config)
        item: dict[str, Any] = {
            "boundary_id": f"{boundary['from']}--{boundary['to']}",
            "from": boundary["from"],
            "to": boundary["to"],
            "timeline_seconds": boundary.get("timeline_seconds"),
            "authored_transition_type": boundary.get("authored_transition_type"),
            "transition_class": boundary.get("transition_class"),
            "picture_edit": boundary.get("picture_edit"),
            "overlap_seconds": boundary.get("overlap_seconds"),
            "seedance_extension_trim": boundary.get("seedance_extension_trim"),
            "source_paths": {
                "outgoing": str(Path(getattr(outgoing, "video_path")).resolve()),
                "incoming": str(Path(getattr(incoming, "video_path")).resolve()),
            },
            "pre_assembly_evidence": evidence,
            "metrics": metrics,
            "technical_triage": status,
            "technical_triage_reason": reason,
            "repair": None,
            "final_timeline_audit": None,
        }
        if plan is not None:
            plan.update(
                {
                    "boundary_id": item["boundary_id"],
                    "from": boundary["from"],
                    "to": boundary["to"],
                    "applied_to_picture_lock": status == "safe_color_match_planned",
                }
            )
            candidate_paths: dict[str, str] = {}
            if generate_candidates:
                candidates = directory / "candidates"
                for name, strength in config["repair"]["candidate_strengths"].items():
                    candidate = candidates / f"{name}.mp4"
                    _render_repaired_sample(
                        original_sample,
                        candidate,
                        plan,
                        strength=float(strength),
                    )
                    candidate_paths[str(name)] = str(candidate.resolve())
                comparison = directory / "original-vs-matched.mp4"
                _render_comparison(
                    original_sample,
                    Path(candidate_paths["matched"]),
                    comparison,
                )
                plan["comparison_preview"] = str(comparison.resolve())
            plan["candidate_previews"] = candidate_paths
            item["repair"] = plan
            if status == "safe_color_match_planned":
                repair_plans[str(boundary["to"])] = plan
        manifest["boundaries"].append(item)
        _write_json(manifest_path, manifest)
    if selected_boundary and not manifest["boundaries"]:
        raise BoundaryQCError(f"Selected boundary was not found: {selected_boundary}")
    blocking = [
        item["boundary_id"]
        for item in manifest["boundaries"]
        if item["technical_triage"]
        in {"review_required", "repair_candidate_review_required"}
    ]
    manifest["pre_assembly_status"] = (
        "review_required" if blocking else "ready_for_picture_lock"
    )
    manifest["blocking_boundaries"] = blocking
    manifest["planned_repair_count"] = len(repair_plans)
    _write_json(manifest_path, manifest)
    return manifest_path, repair_plans, manifest


def _render_master_sample(
    picture_lock: Path,
    boundary: dict[str, Any],
    output: Path,
) -> None:
    picture_edit = boundary.get("picture_edit")
    if picture_edit in {"dissolve", "fade"}:
        center = (
            float(boundary["transition_start_seconds"])
            + float(boundary["transition_end_seconds"])
        ) / 2.0
    else:
        center = float(boundary["timeline_seconds"])
    start = max(0.0, center - 1.0)
    coarse_start = max(0.0, start - 2.0)
    precise_offset = start - coarse_start
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{coarse_start:.6f}",
    ]
    if picture_edit == "hard_cut":
        command.append("-copyts")
    command.extend(["-i", str(picture_lock)])
    if picture_edit == "hard_cut":
        authored_cut = float(boundary["timeline_seconds"])
        cut = math.ceil(authored_cut * 24.0 - 1e-9) / 24.0
        left_start = max(0.0, cut - 1.0)
        right_end = cut + 1.0
        frame_pad = 1.0 / 24.0
        filters = (
            "[0:v]split=2[vleftin][vrightin];"
            f"[vleftin]trim=start={left_start:.6f}:end={cut:.6f},"
            f"setpts=PTS-STARTPTS,fps=24,tpad=stop_mode=clone:stop_duration={frame_pad:.6f},"
            "trim=end_frame=24,setpts=PTS-STARTPTS[vleft];"
            f"[vrightin]trim=start={cut:.6f}:end={right_end:.6f},"
            f"setpts=PTS-STARTPTS,fps=24,tpad=stop_mode=clone:stop_duration={frame_pad:.6f},"
            "trim=end_frame=24,setpts=PTS-STARTPTS[vright];"
            "[vleft][vright]concat=n=2:v=1:a=0[vout];"
            "[0:a]asplit=2[aleftin][arightin];"
            f"[aleftin]atrim=start={left_start:.6f}:end={cut:.6f},"
            "asetpts=PTS-STARTPTS,aresample=48000,"
            "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[aleft];"
            f"[arightin]atrim=start={cut:.6f}:end={right_end:.6f},"
            "asetpts=PTS-STARTPTS,aresample=48000,"
            "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[aright];"
            "[aleft][aright]concat=n=2:v=0:a=1[aout]"
        )
        command.extend(
            [
                "-filter_complex",
                filters,
                "-map",
                "[vout]",
                "-map",
                "[aout]",
            ]
        )
    else:
        command.extend(
            [
                "-ss",
                f"{precise_offset:.6f}",
                "-t",
                "2.000000",
                "-vf",
                "fps=24",
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
            ]
        )
    command.extend(
        [
            "-frames:v",
            "48",
            "-t",
            "2.000000",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    _run(
        command,
        label="Final timeline strict seam render",
    )


class _AuditProbe:
    def __init__(self, width: int, height: int, duration_seconds: float = 2.0):
        self.width = width
        self.height = height
        self.duration_seconds = duration_seconds


class _AuditRecord:
    def __init__(self, path: Path, width: int, height: int):
        self.video_path = path
        self.probe = _AuditProbe(width, height)


class _StandaloneProbe(_AuditProbe):
    def __init__(
        self,
        width: int,
        height: int,
        duration_seconds: float,
        has_audio: bool,
        frame_rate: str,
    ):
        super().__init__(width, height, duration_seconds)
        self.has_audio = has_audio
        self.frame_rate = frame_rate


class _StandaloneRecord(_AuditRecord):
    def __init__(
        self,
        segment_name: str,
        path: Path,
        probe: _StandaloneProbe,
    ):
        self.segment_name = segment_name
        self.video_path = path
        self.probe = probe


def _probe_dimensions(path: Path) -> tuple[int, int]:
    try:
        payload = probe_json(path)
        stream = stream_by_type(payload, "video")
        if stream is None:
            raise BoundaryQCError(f"Final seam has no video stream: {path}")
        return int(stream["width"]), int(stream["height"])
    except (MediaCommandError, KeyError, TypeError, ValueError) as exc:
        raise BoundaryQCError(f"Could not probe final seam: {path}") from exc


def _probe_standalone(path: Path) -> _StandaloneProbe:
    try:
        payload = probe_json(path)
        video = stream_by_type(payload, "video")
        if video is None:
            raise BoundaryQCError(f"Standalone Segment has no video stream: {path}")
        streams = payload.get("streams")
        streams = streams if isinstance(streams, list) else []
        return _StandaloneProbe(
            int(video["width"]),
            int(video["height"]),
            float(video.get("duration") or payload["format"]["duration"]),
            any(
                isinstance(item, dict) and item.get("codec_type") == "audio"
                for item in streams
            ),
            str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "24/1"),
        )
    except (
        MediaCommandError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise BoundaryQCError(f"Could not probe standalone Segment: {path}") from exc


def standalone_records_from_edl(
    task_dir: Path, picture_edl: dict[str, Any]
) -> list[object]:
    """Load media named by an existing EDL without requiring current project schemas."""
    records: list[object] = []
    events = picture_edl.get("picture_events")
    if not isinstance(events, list) or not events:
        raise BoundaryQCError("Standalone picture EDL has no picture events")
    for event in events:
        if not isinstance(event, dict):
            raise BoundaryQCError("Standalone picture EDL event is invalid")
        segment_name = str(event.get("segment_id") or "")
        source = Path(str(event.get("source") or "")).expanduser()
        if not source.is_file():
            source = (
                task_dir
                / ".pending"
                / "virtual-production"
                / "generation-segments"
                / segment_name
                / "video.mp4"
            )
        if not source.is_file():
            raise BoundaryQCError(
                f"Could not resolve standalone Segment source: {segment_name}"
            )
        probe = _probe_standalone(source.resolve())
        if not probe.has_audio:
            raise BoundaryQCError(f"Standalone Segment has no native audio: {source}")
        records.append(_StandaloneRecord(segment_name, source.resolve(), probe))
    return records


def _measure_master_sample(sample: Path, config: dict[str, Any]) -> dict[str, Any]:
    width, height = _probe_dimensions(sample)
    analysis_width = int(config["analysis"]["width"])
    analysis_height = max(2, round(height * analysis_width / width))
    analysis_height += analysis_height % 2
    count = int(config["analysis"]["anchor_frame_count"])
    rate = int(config["strict_sample"]["frame_rate"])
    all_frames = _extract_yuv_frames(
        sample,
        start_seconds=0.0,
        frame_count=int(config["strict_sample"]["frame_count"]),
        frame_rate=rate,
        width=analysis_width,
        height=analysis_height,
    )
    expected_incoming_index = int(config["strict_sample"]["frame_count"]) // 2
    candidate_indices = range(
        expected_incoming_index - 2,
        expected_incoming_index + 4,
    )
    pair_correlations = {
        index: _normalized_luma_correlation(
            all_frames[index - 1][0], all_frames[index][0]
        )
        for index in candidate_indices
    }
    incoming_index = min(pair_correlations, key=pair_correlations.get)
    outgoing = all_frames[incoming_index - count : incoming_index]
    incoming = all_frames[incoming_index : incoming_index + count]
    outgoing_stats = _plane_stats(outgoing)
    incoming_stats = _plane_stats(incoming)
    saturation_factor = outgoing_stats["saturation_mean"] / max(
        1e-6, incoming_stats["saturation_mean"]
    )
    delta_u = outgoing_stats["u_mean"] - incoming_stats["u_mean"]
    delta_v = outgoing_stats["v_mean"] - incoming_stats["v_mean"]
    return {
        "analysis_role": "post_assembly_technical_detection_evidence_only",
        "analysis_frame_width": analysis_width,
        "analysis_frame_height": analysis_height,
        "analysis_frame_count_per_side": count,
        "located_cut": {
            "expected_incoming_frame_index": expected_incoming_index,
            "located_incoming_frame_index": incoming_index,
            "located_pair": [incoming_index - 1, incoming_index],
            "candidate_pair_correlations": {
                f"{index - 1}-{index}": round(value, 6)
                for index, value in pair_correlations.items()
            },
        },
        "outgoing": outgoing_stats,
        "incoming": incoming_stats,
        "delta_target_minus_incoming": {
            "luma_q10": round(outgoing_stats["luma_q10"] - incoming_stats["luma_q10"], 6),
            "luma_mean": round(outgoing_stats["luma_mean"] - incoming_stats["luma_mean"], 6),
            "luma_q90": round(outgoing_stats["luma_q90"] - incoming_stats["luma_q90"], 6),
            "u_mean": round(delta_u, 6),
            "v_mean": round(delta_v, 6),
            "chroma_center_distance": round(math.hypot(delta_u, delta_v), 6),
            "saturation_factor": round(saturation_factor, 6),
            "saturation_ratio_delta": round(saturation_factor - 1.0, 6),
        },
        "luma_shape_correlation": round(
            _normalized_luma_correlation(outgoing[-1][0], incoming[0][0]), 6
        ),
    }


def audit_picture_lock(
    picture_lock: Path,
    picture_edl: dict[str, Any],
    manifest_path: Path,
    *,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Re-extract every selected seam from the rendered picture lock."""
    config = load_config(config_path)
    manifest = _load_json(manifest_path, label="boundary QC manifest")
    root = manifest_path.parent / "final-timeline"
    boundary_by_id = {
        f"{item['from']}--{item['to']}": item
        for item in picture_edl.get("boundaries", [])
        if isinstance(item, dict)
    }
    blocking: list[str] = []
    for item in manifest.get("boundaries", []):
        boundary_id = str(item["boundary_id"])
        try:
            boundary = boundary_by_id[boundary_id]
        except KeyError as exc:
            raise BoundaryQCError(
                f"Final timeline no longer contains boundary {boundary_id}"
            ) from exc
        directory = root / boundary_id
        sample = directory / "final-strict-seam.mp4"
        _render_master_sample(picture_lock, boundary, sample)
        evidence = _extract_frame_evidence(sample, directory, config)
        metrics = None
        if boundary.get("picture_edit") == "hard_cut":
            metrics = _measure_master_sample(sample, config)
            high_match = float(metrics["luma_shape_correlation"]) >= float(
                config["analysis"]["minimum_match_similarity"]
            )
            residual = high_match and _has_detectable_mismatch(metrics, config)
            if item.get("repair") and item["repair"].get("applied_to_picture_lock"):
                technical_status = (
                    "residual_review_required"
                    if residual
                    else "correction_within_detection_thresholds"
                )
            elif item.get("technical_triage") == "no_technical_correction_needed":
                technical_status = (
                    "matched_cut_review_required"
                    if residual
                    else "no_high_confidence_flash_signature"
                )
            else:
                technical_status = "authored_cut_evidence_only"
            if technical_status.endswith("review_required"):
                blocking.append(boundary_id)
        else:
            technical_status = "authored_transition_rendered_for_review"
        item["final_timeline_audit"] = {
            "evidence": evidence,
            "metrics": metrics,
            "technical_status": technical_status,
        }
    manifest["picture_lock"] = str(picture_lock.resolve())
    manifest["final_timeline_status"] = (
        "review_required" if blocking else "technical_audit_complete"
    )
    manifest["final_timeline_blocking_boundaries"] = blocking
    _write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--picture-edl",
        type=Path,
        help="Use an existing picture EDL without requiring current task schemas.",
    )
    parser.add_argument(
        "--boundary",
        help="Optional FROM:TO selector, for example segment-005:segment-006.",
    )
    parser.add_argument("--no-candidates", action="store_true")
    args = parser.parse_args()
    try:
        from post_timeline import compile_timelines, discover_segments

        task_dir = args.task_dir.expanduser().resolve()
        if args.picture_edl is not None:
            picture_edl = _load_json(
                args.picture_edl.expanduser().resolve(),
                label="standalone picture EDL",
            )
            records = standalone_records_from_edl(task_dir, picture_edl)
        else:
            records = discover_segments(task_dir)
            picture_edl, _ = compile_timelines(task_dir, records)
        manifest_path, repairs, manifest = prepare_boundary_qc(
            task_dir,
            records,
            picture_edl,
            config_path=args.config.expanduser().resolve(),
            selected_boundary=args.boundary,
            generate_candidates=not args.no_candidates,
        )
    except (BoundaryQCError, OSError, subprocess.CalledProcessError) as exc:
        print(
            json.dumps(
                {"status": "FAIL", "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "status": manifest["pre_assembly_status"],
                "manifest": str(manifest_path.resolve()),
                "boundary_count": len(manifest["boundaries"]),
                "planned_repair_count": len(repairs),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
