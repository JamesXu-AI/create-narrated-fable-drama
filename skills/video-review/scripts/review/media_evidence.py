"""Pure calculations shared by review and boundary evidence builders."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from narrated_fable_drama.media.ffmpeg import require_binary, run


def frame_timestamps(video: Path) -> list[float]:
    completed = run(
        [
            require_binary("ffprobe"),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_frames",
            "-show_entries",
            "frame=best_effort_timestamp_time",
            "-of",
            "json",
            str(video),
        ],
        context="boundary frame timestamp probe",
    )
    try:
        frames = json.loads(completed.stdout)["frames"]
        return [float(item["best_effort_timestamp_time"]) for item in frames]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Could not read every boundary frame timestamp.") from exc


def summarize_numeric_samples(
    samples: list[dict[str, float]],
    fields: tuple[str, ...],
) -> dict[str, Any]:
    summary: dict[str, Any] = {"sample_count": len(samples)}
    for field in fields:
        values = [item[field] for item in samples if field in item]
        if values:
            summary[field] = {
                "minimum": round(min(values), 4),
                "maximum": round(max(values), 4),
                "average": round(sum(values) / len(values), 4),
            }
    return summary


def summarize_signalstats(
    samples: list[dict[str, float]],
    *,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    field_summary: dict[str, dict[str, float]] = {}
    for field in fields:
        values = [sample[field] for sample in samples]
        adjacent = [
            abs(current - previous)
            for previous, current in zip(values, values[1:])
        ]
        field_summary[field] = {
            "minimum": round(min(values), 4),
            "maximum": round(max(values), 4),
            "mean": round(sum(values) / len(values), 4),
            "max_adjacent_delta": round(max(adjacent, default=0.0), 4),
        }
    chroma_deltas = [
        math.hypot(
            current["UAVG"] - previous["UAVG"],
            current["VAVG"] - previous["VAVG"],
        )
        for previous, current in zip(samples, samples[1:])
    ]
    return {
        "sample_count": len(samples),
        "fields": field_summary,
        "max_adjacent_chroma_vector_delta": round(
            max(chroma_deltas, default=0.0),
            4,
        ),
        "samples": [
            {key: round(value, 4) for key, value in sample.items()}
            for sample in samples
        ],
    }
