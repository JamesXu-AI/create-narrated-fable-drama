"""Schedule confirmed Segment attempts and enforce dependency/review gates."""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from preflight_segment import (
    parse_predecessor_observations,
    predecessor_observation_requirement,
)

from narrated_fable_drama.contracts.segment import storyboard_segment_rows

from .attempts import generate_one
from .boundary_precheck import prepare_adjacent_boundary_prechecks
from .common import (
    DEPARTMENT_DIRNAME,
    EXECUTION_LOCK_FILENAME,
    GENERATION_DIRNAME,
    PENDING_DIRNAME,
    SegmentGenerationError,
    announce,
    read_json,
)
from .requests import (
    _task_contract,
    discover_segments,
)
from .voice_precheck import (
    prepare_voice_identity_precheck,
    recorded_voice_gate_allows_downstream,
)


def _published_segment_ready(task_dir: Path, segment_id: str) -> bool:
    directory = (
        task_dir
        / PENDING_DIRNAME
        / DEPARTMENT_DIRNAME
        / GENERATION_DIRNAME
        / segment_id
    )
    record_path = directory / "production-record.json"
    if not record_path.is_file():
        return False
    try:
        record = read_json(record_path)
    except SegmentGenerationError:
        return False
    return (
        record.get("status") == "GENERATED"
        and record.get("segment_id") == segment_id
        and (directory / "video.mp4").is_file()
        and (directory / "last-frame.png").is_file()
    )


def _enforce_human_confirmation(
    *,
    task_dir: Path,
    selected_segment_ids: list[str],
    human_confirmed_segment: str | None,
) -> list[str]:
    new_segment_ids = [
        segment_id
        for segment_id in selected_segment_ids
        if not _published_segment_ready(task_dir, segment_id)
    ]
    if len(new_segment_ids) > 1:
        raise SegmentGenerationError(
            "Human-in-the-loop generation permits only one not-yet-generated "
            "Segment per run; select and confirm exactly one."
        )
    if not new_segment_ids:
        if human_confirmed_segment is not None:
            raise SegmentGenerationError(
                "--human-confirmed-segment names no not-yet-generated Segment in "
                "this run."
            )
        return new_segment_ids
    expected = new_segment_ids[0]
    if human_confirmed_segment != expected:
        raise SegmentGenerationError(
            f"{expected} requires a fresh conversational before-video confirmation "
            f"and --human-confirmed-segment {expected}."
        )
    return new_segment_ids


def _storyboard_topological_waves(
    segments: list[dict[str, Any]], *, task_dir: Path
) -> list[list[str]]:
    """Execute the exact Seed Master planned waves and dependency edges."""

    order = [segment["generation_task_id"] for segment in segments]
    segment_by_id = {
        segment["generation_task_id"]: segment for segment in segments
    }
    selected = set(order)
    dependencies = {
        segment["generation_task_id"]: set(segment["depends_on_segment_ids"])
        for segment in segments
    }
    external = {
        dependency
        for values in dependencies.values()
        for dependency in values
        if dependency not in selected
    }
    missing_external = sorted(
        dependency
        for dependency in external
        if not _published_segment_ready(task_dir, dependency)
    )
    if missing_external:
        raise SegmentGenerationError(
            "Selected serial Segments require generated continuity sources: "
            + ", ".join(missing_external)
        )
    completed = set(external)
    if any(
        isinstance(segment.get("planned_wave"), bool)
        or not isinstance(segment.get("planned_wave"), int)
        or segment["planned_wave"] < 0
        for segment in segments
    ):
        raise SegmentGenerationError(
            "Every Segment requires one non-negative planned_wave"
        )
    waves: list[list[str]] = []
    for planned_wave in sorted({segment["planned_wave"] for segment in segments}):
        ready = [
            segment_id
            for segment_id in order
            if segment_by_id[segment_id]["planned_wave"] == planned_wave
        ]
        blocked = [
            segment_id
            for segment_id in ready
            if not dependencies[segment_id] <= completed
        ]
        if blocked:
            raise SegmentGenerationError(
                f"Seed Master planned wave {planned_wave} has unresolved dependencies: "
                + ", ".join(blocked)
            )
        waves.append(ready)
        completed.update(ready)
    return waves


def run(args: argparse.Namespace) -> int:
    if args.max_concurrency != 1:
        raise SegmentGenerationError(
            "Guided human-in-the-loop generation requires --max-concurrency 1."
        )
    if args.poll_interval <= 0 or args.wait_timeout <= 0 or args.timeout <= 0:
        raise SegmentGenerationError("Provider timing values must be positive.")
    task_dir = args.task_dir.expanduser().resolve()
    if not task_dir.is_dir():
        raise SegmentGenerationError(f"Task directory does not exist: {task_dir}")
    task = _task_contract(task_dir)
    predecessor_observations = parse_predecessor_observations(
        getattr(args, "observed_predecessor", None)
    )
    all_segment_ids = [
        str(item["segment_id"])
        for item in storyboard_segment_rows(task_dir)
    ]
    if args.segments:
        unknown = sorted(set(args.segments) - set(all_segment_ids))
        if unknown:
            raise SegmentGenerationError(
                f"Unknown --segments values: {', '.join(unknown)}"
            )
    segments = discover_segments(task_dir, segment_ids=args.segments)
    selected_order = [
        segment["generation_task_id"] for segment in segments
    ]
    blocked_voice_predecessors: list[str] = []
    for segment_id in selected_order:
        segment_index = all_segment_ids.index(segment_id)
        if segment_index == 0:
            continue
        predecessor_id = all_segment_ids[segment_index - 1]
        if (
            _published_segment_ready(task_dir, predecessor_id)
            and not recorded_voice_gate_allows_downstream(
                task_dir,
                predecessor_id,
            )
        ):
            blocked_voice_predecessors.append(predecessor_id)
    if blocked_voice_predecessors:
        raise SegmentGenerationError(
            "Successor generation is blocked by failed predecessor voice-identity "
            "gates: "
            + ", ".join(sorted(set(blocked_voice_predecessors)))
        )
    selected_ids = set(selected_order)
    _enforce_human_confirmation(
        task_dir=task_dir,
        selected_segment_ids=selected_order,
        human_confirmed_segment=getattr(args, "human_confirmed_segment", None),
    )
    unexpected_observations = sorted(
        set(predecessor_observations) - selected_ids
    )
    if unexpected_observations:
        raise SegmentGenerationError(
            "Predecessor observations name unselected Segments: "
            + ", ".join(unexpected_observations)
        )
    unnecessary_observations = sorted(
        segment["generation_task_id"]
        for segment in segments
        if segment["generation_task_id"] in predecessor_observations
        and segment["execution_plan"]["shooting_plan"].get(
            "predecessor_review_required"
        )
        is not True
    )
    if unnecessary_observations:
        raise SegmentGenerationError(
            "Predecessor observations are valid only for serial reviewed Segments: "
            + ", ".join(unnecessary_observations)
        )
    waves = _storyboard_topological_waves(segments, task_dir=task_dir)
    announce(
        f"START segments={len(segments)} resolution={task['resolution']} "
        f"ratio={task['ratio']} "
        f"audio_mode={task.get('seedance_audio_mode', 'native_sync')} "
        "scheduler=storyboard_shooting_plan_waves"
    )
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    boundary_precheck_failures: list[dict[str, str]] = []
    boundary_prechecks: dict[str, dict[str, Any]] = {}
    boundary_review_holds: dict[str, dict[str, Any]] = {}
    voice_precheck_failures: list[dict[str, str]] = []
    voice_identity_gates: dict[str, dict[str, Any]] = {}
    voice_identity_holds: dict[str, dict[str, Any]] = {}
    predecessor_observation_holds: dict[str, dict[str, Any]] = {}
    segment_by_id = {
        segment["generation_task_id"]: segment for segment in segments
    }
    for wave_number, wave_ids in enumerate(waves, start=1):
        for segment_id in wave_ids:
            requirement = predecessor_observation_requirement(
                task_dir=task_dir,
                segment_id=segment_id,
                plan=segment_by_id[segment_id]["execution_plan"],
            )
            if (
                requirement is not None
                and predecessor_observations.get(segment_id)
                != requirement["source_provider_attempt_id"]
            ):
                predecessor_observation_holds[segment_id] = requirement
        if predecessor_observation_holds:
            announce(
                "STOP before Seedance submission: virtual production must review "
                "the actual predecessor, current Segment, and resolved character/"
                "location bindings, adapt and rematerialize if needed, then receive "
                "video-review NO_ISSUES"
            )
            for segment_id in sorted(predecessor_observation_holds):
                requirement = predecessor_observation_holds[segment_id]
                announce(
                    "PREDECESSOR_OBSERVATION_REQUIRED "
                    f"segment={segment_id} "
                    f"attempt={requirement['source_provider_attempt_id']} "
                    f"segment_script={requirement['segment_script_path']} "
                    f"predecessor_video={requirement['predecessor_video_path']}"
                )
            break
        announce(f"WAVE {wave_number} segments={','.join(wave_ids)}")
        with ThreadPoolExecutor(max_workers=args.max_concurrency) as executor:
            futures = {
                executor.submit(
                    generate_one,
                    segment_by_id[segment_id],
                    task_dir=task_dir,
                    resolution=task["resolution"],
                    ratio=task["ratio"],
                    poll_interval=args.poll_interval,
                    wait_timeout=args.wait_timeout,
                    request_timeout=args.timeout,
                    predecessor_observations=predecessor_observations,
                ): segment_id
                for segment_id in wave_ids
            }
            for future in as_completed(futures):
                segment_id = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    failures.append({"segment_id": segment_id, "error": str(exc)})
                    announce(f"FAIL {segment_id} error={exc}")
                    continue
                results.append(result)
                try:
                    voice_gate = prepare_voice_identity_precheck(
                        task_dir,
                        segment_id,
                    )
                    voice_identity_gates[segment_id] = voice_gate
                    announce(
                        "VOICE_IDENTITY_GATE "
                        f"segment={segment_id} status={voice_gate['status']} "
                        f"human_listening_review_required="
                        f"{voice_gate['human_listening_review_required']}"
                    )
                    if voice_gate["blocks_acceptance"] is True:
                        voice_identity_holds[segment_id] = {
                            "segment_id": segment_id,
                            "status": str(voice_gate["status"]),
                            "failed_cue_ids": list(
                                voice_gate.get("failed_cue_ids") or []
                            ),
                            "reason": (
                                "Generated voice differs materially from the "
                                "approved character reference."
                            ),
                            "recommended_owner": "virtual-production",
                        }
                except Exception as exc:
                    voice_precheck_failures.append(
                        {"segment_id": segment_id, "error": str(exc)}
                    )
                    announce(f"VOICE_IDENTITY_GATE_FAIL {segment_id} error={exc}")
                try:
                    checks = prepare_adjacent_boundary_prechecks(
                        task_dir,
                        segment_id,
                        all_segment_ids,
                    )
                    for check in checks:
                        boundary_id = str(check["boundary_id"])
                        boundary_prechecks[boundary_id] = check
                        announce(
                            "BOUNDARY_REVIEW_READY "
                            f"boundary={boundary_id} "
                            f"technical_status={check['technical_status']}"
                        )
                        if check.get("blocks_downstream") is True:
                            boundary_review_holds[boundary_id] = {
                                "boundary_id": boundary_id,
                                "segment_id": str(check["to"]),
                                "technical_status": str(check["technical_status"]),
                                "reason": str(check.get("technical_reason") or ""),
                                "recommended_owner": str(
                                    check.get("recommended_owner")
                                    or "virtual-production"
                                ),
                            }
                except Exception as exc:
                    boundary_precheck_failures.append(
                        {"segment_id": segment_id, "error": str(exc)}
                    )
                    announce(f"BOUNDARY_PRECHECK_FAIL {segment_id} error={exc}")
        if (
            failures
            or voice_precheck_failures
            or voice_identity_holds
            or boundary_precheck_failures
            or boundary_review_holds
        ):
            if failures or voice_precheck_failures or boundary_precheck_failures:
                announce("STOP downstream waves because an upstream wave failed")
            elif voice_identity_holds:
                announce(
                    "STOP downstream waves because a generated character voice "
                    "failed its approved-reference identity gate"
                )
            else:
                announce(
                    "STOP downstream waves because an incremental boundary needs "
                    "direct picture-and-sound review"
                )
            break
    results.sort(key=lambda item: item["segment_id"])
    failures.sort(key=lambda item: item["segment_id"])
    voice_precheck_failures.sort(key=lambda item: item["segment_id"])
    boundary_precheck_failures.sort(key=lambda item: item["segment_id"])
    summary_status = (
        "failed"
        if failures or voice_precheck_failures or boundary_precheck_failures
        else "voice_identity_failed"
        if voice_identity_holds
        else "boundary_review_required"
        if boundary_review_holds
        else "predecessor_observation_required"
        if predecessor_observation_holds
        else "succeeded"
    )
    summary = {
        "status": summary_status,
        "segment_count": len(segments),
        "project_segment_count": len(all_segment_ids),
        "succeeded_count": len(results),
        "failed_count": len(failures),
        "generate_audio": True,
        "seedance_audio_mode": task.get("seedance_audio_mode", "native_sync"),
        "dialogue_source": task.get("dialogue_source", "seedance"),
        "results": results,
        "failures": failures,
        "voice_identity_gate_count": len(voice_identity_gates),
        "voice_identity_gates": [
            {
                "segment_id": segment_id,
                "status": gate["status"],
                "blocks_acceptance": gate["blocks_acceptance"],
                "human_listening_review_required": gate[
                    "human_listening_review_required"
                ],
                "failed_cue_ids": gate.get("failed_cue_ids", []),
            }
            for segment_id, gate in sorted(voice_identity_gates.items())
        ],
        "voice_precheck_failed_count": len(voice_precheck_failures),
        "voice_precheck_failures": voice_precheck_failures,
        "voice_identity_hold_count": len(voice_identity_holds),
        "voice_identity_holds": [
            voice_identity_holds[key] for key in sorted(voice_identity_holds)
        ],
        "boundary_precheck_failed_count": len(boundary_precheck_failures),
        "boundary_precheck_failures": boundary_precheck_failures,
        "incremental_boundary_precheck_count": len(boundary_prechecks),
        "incremental_boundary_prechecks": [
            {
                "boundary_id": boundary_id,
                "from": check.get("from"),
                "to": check.get("to"),
                "technical_status": check.get("technical_status"),
                "blocks_downstream": check.get("blocks_downstream"),
                "recommended_owner": check.get("recommended_owner"),
                "evidence_storage": check.get("evidence_storage"),
            }
            for boundary_id, check in sorted(boundary_prechecks.items())
        ],
        "boundary_review_hold_count": len(boundary_review_holds),
        "boundary_review_holds": [
            boundary_review_holds[key] for key in sorted(boundary_review_holds)
        ],
        "predecessor_observation_hold_count": len(predecessor_observation_holds),
        "predecessor_observation_holds": [
            predecessor_observation_holds[key]
            for key in sorted(predecessor_observation_holds)
        ],
    }
    if (
        not failures
        and not voice_precheck_failures
        and not voice_identity_holds
        and not boundary_precheck_failures
        and not boundary_review_holds
        and not predecessor_observation_holds
    ):
        full_generation = all(
            _published_segment_ready(task_dir, segment_id)
            and recorded_voice_gate_allows_downstream(task_dir, segment_id)
            for segment_id in all_segment_ids
        )
        summary["state"] = "GENERATED" if full_generation else "CANARY_GENERATED"
    announce(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return (
        0
        if not failures
        and not voice_precheck_failures
        and not voice_identity_holds
        and not boundary_precheck_failures
        and not boundary_review_holds
        and not predecessor_observation_holds
        else 1
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True, type=Path)
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--poll-interval", type=float, default=10.0)
    parser.add_argument("--wait-timeout", type=float, default=3600.0)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument(
        "--observed-predecessor",
        action="append",
        metavar="SEGMENT_ID=PROVIDER_ATTEMPT_ID",
        help=(
            "Transient exact-attempt acknowledgement; pass only after virtual "
            "production reviews the predecessor video, current Segment and resolved "
            "character/location inputs, video-review returns NO_ISSUES, and "
            "the successor has been adjusted/rematerialized when needed."
        ),
    )
    parser.add_argument(
        "--human-confirmed-segment",
        metavar="SEGMENT_ID",
        help=(
            "Ephemeral assertion for the one Segment explicitly confirmed in the "
            "current conversation. It is not persisted and never authorizes a retry "
            "or another Segment."
        ),
    )
    parser.add_argument(
        "--segments",
        nargs="+",
        metavar="SEGMENT_ID",
        help=(
            "Generate only these Segment IDs in current plan order. Partial runs "
            "write CANARY_GENERATED and cannot enter postproduction."
        ),
    )
    return parser


@contextmanager
def task_execution_lock(task_dir: Path):
    pending_root = task_dir / PENDING_DIRNAME / DEPARTMENT_DIRNAME
    pending_root.mkdir(parents=True, exist_ok=True)
    lock_path = pending_root / EXECUTION_LOCK_FILENAME
    handle = lock_path.open("a+", encoding="utf-8")
    acquired = False
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError as exc:
            raise SegmentGenerationError(
                "Another Seedance generation process already owns this task: "
                f"{task_dir}"
            ) from exc
        yield
    finally:
        try:
            if acquired:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            if acquired:
                lock_path.unlink(missing_ok=True)


def main() -> int:
    try:
        args = build_parser().parse_args()
        task_dir = args.task_dir.expanduser().resolve()
        with task_execution_lock(task_dir):
            return run(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
