"""Submit/poll identity helpers shared by Segment and reset attempts."""

from __future__ import annotations

import time
from typing import Any

from narrated_fable_drama.providers import seedance
from .common import (
    TERMINAL_STATES,
    SegmentGenerationError,
    announce,
)


def provider_task_id(response: dict[str, Any]) -> str:
    task_id = response.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise SegmentGenerationError("Seedance create response has no task ID.")
    return task_id


def wait_for_task(
    task_id: str,
    *,
    segment_id: str,
    poll_interval: float,
    wait_timeout: float,
    request_timeout: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + wait_timeout
    while True:
        result = seedance.get_video_task(task_id, timeout=request_timeout)
        status = str(result.get("status") or "unknown")
        announce(f"STATUS {segment_id} task={task_id} status={status}")
        if status in TERMINAL_STATES:
            return result
        if time.monotonic() >= deadline:
            raise SegmentGenerationError(
                f"Timed out waiting for {segment_id} provider task {task_id}."
            )
        time.sleep(poll_interval)
