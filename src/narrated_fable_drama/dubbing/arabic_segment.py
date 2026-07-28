"""Replace Seedance character speech with exact ElevenLabs Arabic dialogue."""

from __future__ import annotations

import hashlib
import re
import tempfile
from pathlib import Path
from typing import Any

from narrated_fable_drama.contracts.segment import sha256_json
from narrated_fable_drama.contracts.segment.handoff import load_segment_handoff
from narrated_fable_drama.core.arabic_pronunciation import (
    ACCENT_PROFILE_ID,
    GRAMMATICAL_GENDER_POLICY,
    PRONUNCIATION_CONTRACT,
    TTS_MODEL_ID,
    strip_arabic_diacritics,
)
from narrated_fable_drama.core.json_io import load_json_object
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.core.project_domain import (
    SOUND_EFFECTS_AUDIO_SOURCE,
    SPEECH_AUDIO_SOURCE,
    TARGET_LANGUAGE,
    validate_arabic_dialogue,
)
from narrated_fable_drama.dubbing.seedance_speech_gate import (
    SeedanceSpeechGateError,
    audit_seedance_character_speech,
)
from narrated_fable_drama.media.ffmpeg import (
    MediaCommandError,
    require_binary,
)
from narrated_fable_drama.media.ffmpeg import (
    run as run_media_command,
)
from narrated_fable_drama.media.probe import probe_json, stream_by_type
from narrated_fable_drama.providers import elevenlabs

SAMPLE_RATE_HZ = 48000
PHRASE_EDGE_PADDING_SECONDS = 0.03
PHRASE_FADE_SECONDS = 0.012
PHRASE_BREAK_GAP_SECONDS = 0.18
DIALOGUE_PHRASE_LOUDNESS_LUFS = -18.0
DIALOGUE_PHRASE_LOUDNESS_RANGE_LU = 7.0
DIALOGUE_PHRASE_TRUE_PEAK_DBFS = -3.0
DIALOGUE_COMPRESSOR_THRESHOLD_DB = -24.0
DIALOGUE_COMPRESSOR_RATIO = 4.0
DIALOGUE_COMPRESSOR_ATTACK_MS = 5.0
DIALOGUE_COMPRESSOR_RELEASE_MS = 50.0
DIALOGUE_COMPRESSOR_MAKEUP_DB = 12.0
MAX_WORDS_PER_PHRASE = 5
MIN_TEMPO_FACTOR = 0.75
MIN_MOUTH_WINDOW_TEMPO_FACTOR = 0.65
MAX_TEMPO_FACTOR = 1.30
MIN_ELEVENLABS_SPEED = 0.70
SEEDANCE_SPEECH_CUT_PADDING_SECONDS = 0.08
SEEDANCE_SPEECH_CUT_FADE_SECONDS = 0.025
DETECTED_SPEECH_VISUAL_ONSET_GUARD_SECONDS = 0.55
DETECTED_SPEECH_PAUSE_SECONDS = 0.45
DETECTED_START_STORYBOARD_JITTER_SECONDS = 0.10
MAX_DETECTED_SPEECH_LEAD_SECONDS = 1.0
PHRASE_END_RE = re.compile(r"[،؛؟.!…]+[\"'»”)]*$")
WORD_RE = re.compile(r"\S+")


class ArabicSegmentEmbeddingError(RuntimeError):
    """Raised when one generated Segment cannot be safely Arabic-dubbed."""


def _approved_voice_profiles(
    *,
    task_dir: Path,
    voices: dict[str, str],
) -> dict[str, dict[str, Any]]:
    try:
        repository_root = task_dir.expanduser().resolve().parents[2]
    except IndexError as exc:
        raise ArabicSegmentEmbeddingError(
            f"Could not resolve repository root from task directory: {task_dir}"
        ) from exc
    profiles: dict[str, dict[str, Any]] = {}
    for entity_id, mapped_voice_id in sorted(voices.items()):
        if Path(entity_id).name != entity_id:
            raise ArabicSegmentEmbeddingError(
                f"Invalid speaker entity ID in ElevenLabs voice map: {entity_id!r}"
            )
        brief_path = (
            repository_root
            / "workspace"
            / "assets"
            / "characters"
            / entity_id
            / "voice.brief.json"
        )
        brief = load_json_object(
            brief_path,
            label=f"{entity_id} approved voice brief",
            error_type=ArabicSegmentEmbeddingError,
        )
        provider = brief.get("elevenlabs")
        if not isinstance(provider, dict):
            raise ArabicSegmentEmbeddingError(
                f"{entity_id} approved voice brief lacks ElevenLabs provenance"
            )
        approved_voice_id = provider.get("voice_id")
        settings = provider.get("voice_settings")
        if approved_voice_id != mapped_voice_id:
            raise ArabicSegmentEmbeddingError(
                f"{entity_id} voice map ID does not match its approved voice brief"
            )
        if not isinstance(settings, dict):
            raise ArabicSegmentEmbeddingError(
                f"{entity_id} approved voice brief lacks voice settings"
            )
        try:
            approved_speed = float(settings.get("speed", 1.0))
        except (TypeError, ValueError) as exc:
            raise ArabicSegmentEmbeddingError(
                f"{entity_id} approved ElevenLabs speed must be numeric"
            ) from exc
        if approved_speed < MIN_ELEVENLABS_SPEED or approved_speed > 1.2:
            raise ArabicSegmentEmbeddingError(
                f"{entity_id} approved ElevenLabs speed must stay between "
                f"{MIN_ELEVENLABS_SPEED} and 1.2"
            )
        profiles[entity_id] = {
            "voice_id": mapped_voice_id,
            "voice_settings": dict(settings),
            "approved_speed": approved_speed,
            "source": brief_path.relative_to(repository_root).as_posix(),
            "voice_settings_sha256": sha256_json(settings),
        }
    return profiles


def _dialogue_cues(task_dir: Path, segment_id: str) -> list[dict[str, Any]]:
    handoff = load_segment_handoff(task_dir)
    segment = handoff.get(segment_id)
    if not isinstance(segment, dict):
        raise ArabicSegmentEmbeddingError(
            f"{segment_id} has no Storyboard dubbing handoff"
        )
    result: list[dict[str, Any]] = []
    for block in segment["timeline_blocks"]:
        result.extend(block["dialogue_cues"])
    return result
def _probe_video(path: Path, *, require_audio: bool) -> dict[str, Any]:
    try:
        payload = probe_json(path, timeout=60)
        duration = float((payload.get("format") or {}).get("duration"))
    except (MediaCommandError, TypeError, ValueError) as exc:
        raise ArabicSegmentEmbeddingError(
            f"Could not probe Segment media: {path}"
        ) from exc
    video = stream_by_type(payload, "video")
    audio = stream_by_type(payload, "audio")
    if video is None or duration <= 0 or (require_audio and audio is None):
        raise ArabicSegmentEmbeddingError(
            f"Segment lacks required video/background-audio streams: {path}"
        )
    return {
        "duration_seconds": duration,
        "has_video_stream": video is not None,
        "has_audio_stream": audio is not None,
        "streams": payload.get("streams", []),
    }


def _audio_duration(path: Path) -> float:
    try:
        payload = probe_json(path, timeout=60)
        stream = stream_by_type(payload, "audio")
        if stream is None:
            raise ValueError("missing audio stream")
        value = stream.get("duration") or (payload.get("format") or {}).get("duration")
        duration = float(value)
    except (MediaCommandError, TypeError, ValueError) as exc:
        raise ArabicSegmentEmbeddingError(
            f"Could not measure ElevenLabs cue: {path}"
        ) from exc
    if duration <= 0:
        raise ArabicSegmentEmbeddingError(f"ElevenLabs cue is empty: {path}")
    return duration


def _source_word_spans(
    *,
    exact_text: str,
    tts_text: str,
    alignment: dict[str, list[Any]],
    context: str,
) -> list[dict[str, Any]]:
    characters = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    if "".join(characters) != tts_text:
        raise ArabicSegmentEmbeddingError(
            f"{context} ElevenLabs timestamps changed the derived Arabic "
            "pronunciation text"
        )
    exact_matches = list(WORD_RE.finditer(exact_text))
    tts_matches = list(WORD_RE.finditer(tts_text))
    if (
        len(exact_matches) != len(tts_matches)
        or any(
            strip_arabic_diacritics(tts.group(0)) != exact.group(0)
            for exact, tts in zip(exact_matches, tts_matches, strict=True)
        )
    ):
        raise ArabicSegmentEmbeddingError(
            f"{context} ElevenLabs pronunciation text changed the locked "
            "Arabic word sequence"
        )
    spans: list[dict[str, Any]] = []
    for exact_match, tts_match in zip(
        exact_matches,
        tts_matches,
        strict=True,
    ):
        spans.append(
            {
                "text": exact_match.group(0),
                "start": float(starts[tts_match.start()]),
                "end": float(ends[tts_match.end() - 1]),
            }
        )
    return spans


def _phrase_groups(
    words: list[dict[str, Any]],
    *,
    break_on_alignment_gap: bool = True,
) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    start = 0
    for index, word in enumerate(words):
        is_last = index == len(words) - 1
        gap_after = (
            0.0 if is_last else float(words[index + 1]["start"]) - float(word["end"])
        )
        word_count = index - start + 1
        if (
            is_last
            or PHRASE_END_RE.search(str(word["text"])) is not None
            or (
                break_on_alignment_gap
                and gap_after >= PHRASE_BREAK_GAP_SECONDS
            )
            or word_count >= MAX_WORDS_PER_PHRASE
        ):
            groups.append((start, index + 1))
            start = index + 1
    return groups


def _edge_padding(
    words: list[dict[str, Any]],
    *,
    start: int,
    end: int,
    source_duration: float,
) -> tuple[float, float]:
    first = words[start]
    last = words[end - 1]
    if start == 0:
        before = min(PHRASE_EDGE_PADDING_SECONDS, float(first["start"]))
    else:
        before = min(
            PHRASE_EDGE_PADDING_SECONDS,
            max(
                0.0,
                (float(first["start"]) - float(words[start - 1]["end"])) / 2,
            ),
        )
    if end == len(words):
        after = min(
            PHRASE_EDGE_PADDING_SECONDS,
            max(0.0, source_duration - float(last["end"])),
        )
    else:
        after = min(
            PHRASE_EDGE_PADDING_SECONDS,
            max(
                0.0,
                (float(words[end]["start"]) - float(last["end"])) / 2,
            ),
        )
    return before, after


def _coalesce_phrase_groups_to_mouth_windows(
    phrase_groups: list[tuple[int, int]],
    *,
    source_words: list[dict[str, Any]],
    target_windows: list[tuple[float, float]],
) -> list[tuple[int, int]]:
    """Merge adjacent Arabic phrase groups to fit fewer mouth windows."""

    window_count = len(target_windows)
    group_count = len(phrase_groups)
    if group_count < window_count:
        raise ArabicSegmentEmbeddingError(
            f"Detected {window_count} mouth windows but only "
            f"{group_count} Arabic phrase groups."
        )
    if group_count == window_count:
        return phrase_groups

    source_total = (
        float(source_words[phrase_groups[-1][1] - 1]["end"])
        - float(source_words[phrase_groups[0][0]]["start"])
    )
    target_total = sum(end - start for start, end in target_windows)
    if source_total <= 0 or target_total <= 0:
        raise ArabicSegmentEmbeddingError(
            "Cannot coalesce Arabic phrases across invalid mouth windows."
        )

    infinity = float("inf")
    costs = [
        [infinity] * (window_count + 1)
        for _ in range(group_count + 1)
    ]
    previous = [
        [-1] * (window_count + 1)
        for _ in range(group_count + 1)
    ]
    costs[0][0] = 0.0
    for used_groups in range(1, group_count + 1):
        for used_windows in range(1, min(used_groups, window_count) + 1):
            first_group_minimum = used_windows - 1
            for first_group in range(first_group_minimum, used_groups):
                if costs[first_group][used_windows - 1] == infinity:
                    continue
                source_start = float(
                    source_words[phrase_groups[first_group][0]]["start"]
                )
                source_end = float(
                    source_words[
                        phrase_groups[used_groups - 1][1] - 1
                    ]["end"]
                )
                source_share = (source_end - source_start) / source_total
                target_start, target_end = target_windows[used_windows - 1]
                target_share = (target_end - target_start) / target_total
                candidate = (
                    costs[first_group][used_windows - 1]
                    + (source_share - target_share) ** 2
                )
                if candidate < costs[used_groups][used_windows]:
                    costs[used_groups][used_windows] = candidate
                    previous[used_groups][used_windows] = first_group

    if previous[group_count][window_count] < 0:
        raise ArabicSegmentEmbeddingError(
            "Could not map Arabic phrase groups to detected mouth windows."
        )
    partitions: list[tuple[int, int]] = []
    used_groups = group_count
    used_windows = window_count
    while used_windows > 0:
        first_group = previous[used_groups][used_windows]
        partitions.append(
            (
                phrase_groups[first_group][0],
                phrase_groups[used_groups - 1][1],
            )
        )
        used_groups = first_group
        used_windows -= 1
    partitions.reverse()
    return partitions


def _cue_phrase_plans(
    *,
    cue: dict[str, Any],
    cue_index: int,
    source_words: list[dict[str, Any]],
    source_duration: float,
    picture_duration: float,
    fill_target_window: bool = False,
    target_windows: list[tuple[float, float]] | None = None,
) -> list[dict[str, Any]]:
    if not source_words:
        raise ArabicSegmentEmbeddingError(
            f"{cue['line_id']} has no ElevenLabs word timestamps"
        )
    cue_start = float(cue["start_seconds"])
    cue_end = float(cue["end_seconds"])
    if cue_start < 0 or cue_end <= cue_start or cue_end > picture_duration:
        raise ArabicSegmentEmbeddingError(
            f"{cue['line_id']} has an invalid Storyboard dubbing window"
        )
    whole_before, whole_after = _edge_padding(
        source_words,
        start=0,
        end=len(source_words),
        source_duration=source_duration,
    )
    reference_start = max(
        0.0,
        float(source_words[0]["start"]) - whole_before,
    )
    reference_end = min(
        source_duration,
        float(source_words[-1]["end"]) + whole_after,
    )
    source_span = reference_end - reference_start
    target_span = cue_end - cue_start
    required_tempo_factor = source_span / target_span
    phrase_groups = _phrase_groups(
        source_words,
        break_on_alignment_gap=not (
            target_windows and len(target_windows) > 1
        ),
    )
    if target_windows and len(target_windows) > 1:
        try:
            phrase_groups = _coalesce_phrase_groups_to_mouth_windows(
                phrase_groups,
                source_words=source_words,
                target_windows=target_windows,
            )
        except ArabicSegmentEmbeddingError as exc:
            raise ArabicSegmentEmbeddingError(
                f"{cue['line_id']} has {len(target_windows)} detected mouth "
                f"windows but {len(phrase_groups)} Arabic phrase groups: {exc}"
            ) from exc
        result: list[dict[str, Any]] = []
        for phrase_index, ((start, end), target_window) in enumerate(
            zip(phrase_groups, target_windows, strict=True),
            start=1,
        ):
            target_start, target_end = target_window
            if (
                target_start < cue_start
                or target_end <= target_start
                or target_end > cue_end
            ):
                raise ArabicSegmentEmbeddingError(
                    f"{cue['line_id']} has an invalid detected mouth window"
                )
            before, after = _edge_padding(
                source_words,
                start=start,
                end=end,
                source_duration=source_duration,
            )
            source_start = max(
                0.0,
                float(source_words[start]["start"]) - before,
            )
            source_end = min(
                source_duration,
                float(source_words[end - 1]["end"]) + after,
            )
            tempo_factor = (source_end - source_start) / (
                target_end - target_start
            )
            if (
                tempo_factor < MIN_MOUTH_WINDOW_TEMPO_FACTOR
                or tempo_factor > MAX_TEMPO_FACTOR
            ):
                raise ArabicSegmentEmbeddingError(
                    f"{cue['line_id']} phrase {phrase_index} needs "
                    f"{tempo_factor:.3f}x tempo for its detected mouth window; "
                    f"allowed natural range is "
                    f"{MIN_MOUTH_WINDOW_TEMPO_FACTOR:.2f}–"
                    f"{MAX_TEMPO_FACTOR:.2f}."
                )
            result.append(
                {
                    "phrase_id": (
                        f"{cue['line_id']}__phrase-{phrase_index:02d}"
                    ),
                    "line_id": cue["line_id"],
                    "input_index": cue_index,
                    "word_start_index": start,
                    "word_end_index": end,
                    "word_count": end - start,
                    "source_start_seconds": round(source_start, 6),
                    "source_end_seconds": round(source_end, 6),
                    "target_start_seconds": round(target_start, 6),
                    "target_end_seconds": round(target_end, 6),
                    "tempo_factor": round(tempo_factor, 8),
                    "phrase_hold_offset_seconds": 0.0,
                    "timing_source": "detected_mouth_window",
                }
            )
        return result
    can_fill_with_phrase_holds = fill_target_window and len(phrase_groups) > 1
    minimum_tempo_factor = MIN_TEMPO_FACTOR
    if fill_target_window and not can_fill_with_phrase_holds:
        minimum_tempo_factor = MIN_MOUTH_WINDOW_TEMPO_FACTOR
    if required_tempo_factor > MAX_TEMPO_FACTOR or (
        fill_target_window
        and not can_fill_with_phrase_holds
        and required_tempo_factor < minimum_tempo_factor
    ):
        raise ArabicSegmentEmbeddingError(
            f"{cue['line_id']} needs {required_tempo_factor:.3f}x tempo to fit its "
            f"target window; allowed natural range is "
            f"{minimum_tempo_factor:.2f}–{MAX_TEMPO_FACTOR:.2f}. "
            "Shorten the Arabic line or widen its window upstream."
        )
    # A dialogue window is the maximum authored envelope, not an instruction to
    # stretch short speech across every available frame. When the line already has
    # natural phrase boundaries, preserve the generated speech at native tempo and
    # turn the remaining duration into real inter-phrase holds. A single continuous
    # phrase may still slow to the natural lower bound; long speech must still fit
    # at or below the upper tempo bound.
    tempo_factor = required_tempo_factor
    if can_fill_with_phrase_holds:
        tempo_factor = max(required_tempo_factor, 1.0)
    elif not fill_target_window:
        tempo_factor = max(required_tempo_factor, MIN_TEMPO_FACTOR)
    rendered_span = source_span / tempo_factor
    phrase_hold_seconds = (
        max(0.0, target_span - rendered_span)
        if can_fill_with_phrase_holds
        else 0.0
    )

    result: list[dict[str, Any]] = []
    for phrase_index, (start, end) in enumerate(
        phrase_groups,
        start=1,
    ):
        before, after = _edge_padding(
            source_words,
            start=start,
            end=end,
            source_duration=source_duration,
        )
        source_start = max(
            0.0,
            float(source_words[start]["start"]) - before,
        )
        source_end = min(
            source_duration,
            float(source_words[end - 1]["end"]) + after,
        )
        hold_offset = (
            phrase_hold_seconds
            * (phrase_index - 1)
            / (len(phrase_groups) - 1)
            if can_fill_with_phrase_holds
            else 0.0
        )
        target_start = (
            cue_start
            + ((source_start - reference_start) / tempo_factor)
            + hold_offset
        )
        target_end = (
            cue_start
            + ((source_end - reference_start) / tempo_factor)
            + hold_offset
        )
        result.append(
            {
                "phrase_id": f"{cue['line_id']}__phrase-{phrase_index:02d}",
                "line_id": cue["line_id"],
                "input_index": cue_index,
                "word_start_index": start,
                "word_end_index": end,
                "word_count": end - start,
                "source_start_seconds": round(source_start, 6),
                "source_end_seconds": round(source_end, 6),
                "target_start_seconds": round(
                    max(cue_start, target_start),
                    6,
                ),
                "target_end_seconds": round(min(cue_end, target_end), 6),
                "tempo_factor": round(tempo_factor, 8),
                "phrase_hold_offset_seconds": round(hold_offset, 6),
            }
        )
    return result


def _render_embedded_video(
    *,
    seedance_background_video: Path,
    cue_files: list[Path],
    phrase_plans: list[dict[str, Any]],
    duration_seconds: float,
    output: Path,
) -> None:
    command: list[str | Path] = [
        require_binary("ffmpeg"),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        seedance_background_video,
    ]
    for cue_file in cue_files:
        command.extend(["-i", cue_file])
    filters = [
        "[0:a:0]"
        f"atrim=start=0:end={duration_seconds:.6f},"
        "asetpts=PTS-STARTPTS,"
        f"aresample={SAMPLE_RATE_HZ},"
        "aformat=sample_fmts=fltp:channel_layouts=stereo"
        "[seedance_base]"
    ]
    labels = ["seedance_base"]
    for index, phrase in enumerate(phrase_plans, start=1):
        target_duration = float(phrase["target_end_seconds"]) - float(
            phrase["target_start_seconds"]
        )
        if target_duration <= 0:
            raise ArabicSegmentEmbeddingError(
                f"{phrase['phrase_id']} has an invalid target duration"
            )
        fade = min(PHRASE_FADE_SECONDS, target_duration / 4)
        fade_out_start = max(0.0, target_duration - fade)
        delay_samples = round(float(phrase["target_start_seconds"]) * SAMPLE_RATE_HZ)
        label = f"phrase{index}"
        input_index = int(phrase["input_index"])
        filters.append(
            f"[{input_index}:a:0]"
            f"atrim=start={float(phrase['source_start_seconds']):.6f}:"
            f"end={float(phrase['source_end_seconds']):.6f},"
            "asetpts=PTS-STARTPTS,"
            f"aresample={SAMPLE_RATE_HZ},"
            "aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"atempo={float(phrase['tempo_factor']):.8f},"
            f"acompressor=threshold={DIALOGUE_COMPRESSOR_THRESHOLD_DB:.1f}dB:"
            f"ratio={DIALOGUE_COMPRESSOR_RATIO:.1f}:"
            f"attack={DIALOGUE_COMPRESSOR_ATTACK_MS:.1f}:"
            f"release={DIALOGUE_COMPRESSOR_RELEASE_MS:.1f}:"
            f"makeup={DIALOGUE_COMPRESSOR_MAKEUP_DB:.1f}dB,"
            f"loudnorm=I={DIALOGUE_PHRASE_LOUDNESS_LUFS:.1f}:"
            f"LRA={DIALOGUE_PHRASE_LOUDNESS_RANGE_LU:.1f}:"
            f"TP={DIALOGUE_PHRASE_TRUE_PEAK_DBFS:.1f},"
            f"atrim=start=0:end={target_duration:.6f},"
            f"afade=t=in:st=0:d={fade:.6f},"
            f"afade=t=out:st={fade_out_start:.6f}:d={fade:.6f},"
            f"adelay={delay_samples}S:all=1[{label}]"
        )
        labels.append(label)
    joined = "".join(f"[{label}]" for label in labels)
    filters.append(
        f"{joined}amix=inputs={len(labels)}:duration=first:normalize=0:"
        "dropout_transition=0,"
        f"alimiter=limit=0.95,atrim=start=0:end={duration_seconds:.6f}[mix]"
    )
    temporary = output.with_name(f".{output.name}.arabic-embed.tmp.mp4")
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "0:v:0",
            "-map",
            "[mix]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            str(SAMPLE_RATE_HZ),
            "-ac",
            "2",
            "-t",
            f"{duration_seconds:.6f}",
            "-movflags",
            "+faststart",
            temporary,
        ]
    )
    try:
        run_media_command(
            command,
            context="Seedance native audio and ElevenLabs Arabic dialogue mix",
            timeout=300,
        )
    except MediaCommandError as exc:
        temporary.unlink(missing_ok=True)
        raise ArabicSegmentEmbeddingError(
            "Could not mix Seedance native audio with ElevenLabs Arabic dialogue"
        ) from exc
    if not temporary.is_file() or temporary.stat().st_size <= 0:
        temporary.unlink(missing_ok=True)
        raise ArabicSegmentEmbeddingError("Arabic-embedded Segment output is empty")
    temporary.replace(output)


def _overlapping_seedance_speech_segments(
    cue: dict[str, Any],
    speech_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return qualifying provider-speech spans inside one authored cue window."""

    cue_start = float(cue["start_seconds"])
    cue_end = float(cue["end_seconds"])

    def belongs_to_cue(item: dict[str, Any]) -> bool:
        start = float(item["start_seconds"])
        end = float(item["end_seconds"])
        if end <= cue_start or start >= cue_end:
            return False
        if start >= cue_start:
            return True
        duration = end - start
        overlap = min(end, cue_end) - cue_start
        return (
            cue_start - start <= MAX_DETECTED_SPEECH_LEAD_SECONDS
            or (duration > 0 and overlap / duration >= 0.5)
        )

    return sorted(
        [
            item
            for item in speech_gate.get("segments", [])
            if (
                isinstance(item, dict)
                and (
                    item.get("forbidden_speech") is True
                    or (
                        int(
                            item.get(
                                "speech_token_count",
                                item.get("arabic_token_count", 0),
                            )
                        )
                        > 0
                        and float(item.get("mean_word_probability", 0.0))
                        >= 0.45
                    )
                )
                and belongs_to_cue(item)
            )
        ],
        key=lambda item: float(item["start_seconds"]),
    )


def _resolved_cue_timing(
    cue: dict[str, Any],
    speech_gate: dict[str, Any],
    *,
    visual_onset_guard_seconds: float = DETECTED_SPEECH_VISUAL_ONSET_GUARD_SECONDS,
    use_detected_end: bool = False,
    use_full_detected_window: bool = False,
) -> dict[str, Any]:
    """Delay dubbed speech to the provider performance onset inside its window."""

    storyboard_start = float(cue["start_seconds"])
    storyboard_end = float(cue["end_seconds"])
    observed = _overlapping_seedance_speech_segments(cue, speech_gate)
    if not observed:
        return {
            "storyboard_start_seconds": storyboard_start,
            "storyboard_end_seconds": storyboard_end,
            "target_start_seconds": storyboard_start,
            "target_end_seconds": storyboard_end,
            "timing_source": "storyboard_window_fallback",
            "seedance_detected_speech_start_seconds": None,
            "seedance_detected_speech_end_seconds": None,
            "seedance_detected_speech_windows_seconds": [],
        }
    detected_start = min(float(item["start_seconds"]) for item in observed)
    detected_end = max(float(item["end_seconds"]) for item in observed)
    resolved_detected_start = (
        storyboard_start
        if (
            detected_start < storyboard_start
            and storyboard_start - detected_start
            <= DETECTED_START_STORYBOARD_JITTER_SECONDS
        )
        else detected_start
    )
    detected_windows: list[tuple[float, float]] = []
    for item in observed:
        item_start = float(item["start_seconds"])
        start = (
            storyboard_start
            if (
                item_start < storyboard_start
                and storyboard_start - item_start
                <= DETECTED_START_STORYBOARD_JITTER_SECONDS
            )
            else item_start
        )
        end = float(item["end_seconds"])
        if end <= start:
            continue
        if (
            detected_windows
            and start
            <= detected_windows[-1][1] + DETECTED_SPEECH_PAUSE_SECONDS
        ):
            detected_windows[-1] = (
                detected_windows[-1][0],
                max(detected_windows[-1][1], end),
            )
        else:
            detected_windows.append((start, end))
    visual_onset_guard = (
        visual_onset_guard_seconds
        if detected_start > storyboard_start + 0.05
        else 0.0
    )
    target_start = max(
        0.0,
        resolved_detected_start
        if use_full_detected_window
        else detected_start + visual_onset_guard,
    )
    target_limit = detected_end if use_full_detected_window else storyboard_end
    if target_start >= target_limit:
        raise ArabicSegmentEmbeddingError(
            f"{cue['line_id']} detected Seedance speech window is invalid."
        )
    target_end = (
        detected_end
        if use_full_detected_window
        else min(storyboard_end, detected_end)
        if use_detected_end and detected_end > target_start
        else storyboard_end
    )
    return {
        "storyboard_start_seconds": storyboard_start,
        "storyboard_end_seconds": storyboard_end,
        "target_start_seconds": target_start,
        "target_end_seconds": target_end,
        "timing_source": (
            "seedance_detected_speech_window"
            if use_full_detected_window
            else "seedance_detected_speech_onset_plus_visual_guard_"
            "within_storyboard_window"
            if visual_onset_guard > 0
            else "seedance_detected_speech_onset_within_storyboard_window"
        ),
        "seedance_detected_speech_start_seconds": detected_start,
        "seedance_detected_speech_end_seconds": detected_end,
        "seedance_detected_speech_windows_seconds": [
            [round(start, 6), round(end, 6)]
            for start, end in detected_windows
        ],
        "visual_mouth_onset_guard_seconds": visual_onset_guard,
    }


def _apply_reviewed_cue_window(
    cue: dict[str, Any],
    timing: dict[str, Any],
    reviewed_window: tuple[float, float],
    *,
    picture_duration: float,
) -> tuple[dict[str, Any], list[tuple[float, float]]]:
    """Apply one explicitly reviewed mouth-performance window."""

    reviewed_start = float(reviewed_window[0])
    reviewed_end = float(reviewed_window[1])
    storyboard_start = float(cue["start_seconds"])
    storyboard_end = float(cue["end_seconds"])
    detected_start = timing.get("seedance_detected_speech_start_seconds")
    earliest_reviewable_start = storyboard_start
    if isinstance(detected_start, (int, float)) and not isinstance(
        detected_start,
        bool,
    ):
        earliest_reviewable_start = min(
            storyboard_start,
            float(detected_start),
        )
    if (
        reviewed_start < earliest_reviewable_start
        or reviewed_end > storyboard_end
        or reviewed_end > picture_duration
        or reviewed_end <= reviewed_start
    ):
        raise ArabicSegmentEmbeddingError(
            f"{cue['line_id']} reviewed cue window must stay inside the "
            "Storyboard dialogue window, the detected mouth-performance "
            "onset, and picture duration."
        )
    source_start = float(timing["target_start_seconds"])
    source_end = float(timing["target_end_seconds"])
    adjusted = {
        **timing,
        "target_start_seconds": reviewed_start,
        "target_end_seconds": reviewed_end,
        "timing_source": "model_reviewed_visual_mouth_window",
        "visual_mouth_onset_guard_seconds": max(
            0.0,
            reviewed_start
            - float(
                timing.get("seedance_detected_speech_start_seconds")
                or source_start
            ),
        ),
        "reviewed_timing_adjustment": {
            "authority": "human_direction_plus_frame_review",
            "source_target_start_seconds": round(source_start, 6),
            "source_target_end_seconds": round(source_end, 6),
            "reviewed_target_start_seconds": round(reviewed_start, 6),
            "reviewed_target_end_seconds": round(reviewed_end, 6),
            "start_adjustment_seconds": round(
                reviewed_start - source_start,
                6,
            ),
            "end_adjustment_seconds": round(
                reviewed_end - source_end,
                6,
            ),
        },
    }
    return adjusted, [(reviewed_start, reviewed_end)]


def _forbidden_speech_intervals(
    speech_gate: dict[str, Any],
    *,
    duration_seconds: float,
) -> list[tuple[float, float]]:
    segments = sorted(
        [
            item
            for item in speech_gate.get("segments", [])
            if isinstance(item, dict)
        ],
        key=lambda item: float(item["start_seconds"]),
    )
    cut_segment_indexes = {
        index
        for index, item in enumerate(segments)
        if item.get("forbidden_speech") is True
    }
    # Whisper may split one uninterrupted generated line into several adjacent
    # segments. A short two-token middle fragment can sit between two qualifying
    # speech segments and must not survive merely because it misses the
    # stand-alone token threshold. Expand each qualifying run through adjacent,
    # high-confidence Arabic fragments in the same continuous ASR chain.
    changed = True
    while changed:
        changed = False
        for index, item in enumerate(segments):
            if index in cut_segment_indexes:
                continue
            is_arabic_fragment = (
                int(
                    item.get(
                        "speech_token_count",
                        item.get("arabic_token_count", 0),
                    )
                )
                > 0
                and float(item.get("mean_word_probability", 0.0)) >= 0.45
            )
            if not is_arabic_fragment:
                continue
            touches_left = (
                index > 0
                and index - 1 in cut_segment_indexes
                and float(item["start_seconds"])
                <= float(segments[index - 1]["end_seconds"]) + 0.08
            )
            touches_right = (
                index + 1 < len(segments)
                and index + 1 in cut_segment_indexes
                and float(segments[index + 1]["start_seconds"])
                <= float(item["end_seconds"]) + 0.08
            )
            if touches_left or touches_right:
                cut_segment_indexes.add(index)
                changed = True
    raw: list[tuple[float, float]] = []
    used_word_windows = False
    for index, item in enumerate(segments):
        if index not in cut_segment_indexes:
            continue
        word_windows = [
            window
            for window in item.get("detected_speech_word_windows", [])
            if isinstance(window, dict)
            and window.get("start_seconds") is not None
            and window.get("end_seconds") is not None
            and float(window["end_seconds"]) > float(window["start_seconds"])
        ]
        boundaries = (
            [
                (
                    float(window["start_seconds"]),
                    float(window["end_seconds"]),
                )
                for window in word_windows
            ]
            if word_windows
            else [
                (
                    float(item["start_seconds"]),
                    float(item["end_seconds"]),
                )
            ]
        )
        used_word_windows = used_word_windows or bool(word_windows)
        raw.extend(
            (
                max(0.0, start - SEEDANCE_SPEECH_CUT_PADDING_SECONDS),
                min(
                    duration_seconds,
                    end + SEEDANCE_SPEECH_CUT_PADDING_SECONDS,
                ),
            )
            for start, end in boundaries
        )
    merged: list[tuple[float, float]] = []
    merge_gap_seconds = 0.35 if used_word_windows else 0.02
    for start, end in sorted(raw):
        if end <= start:
            continue
        if merged and start <= merged[-1][1] + merge_gap_seconds:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _preserved_audio_intervals(
    intervals: list[tuple[float, float]],
    *,
    duration_seconds: float,
) -> list[tuple[float, float]]:
    preserved: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in intervals:
        if start > cursor + 1e-6:
            preserved.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration_seconds - 1e-6:
        preserved.append((cursor, duration_seconds))
    return preserved


def _render_seedance_speech_cut(
    *,
    source_video: Path,
    output_video: Path,
    speech_gate: dict[str, Any],
    duration_seconds: float,
    final_dialogue_intervals: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Mute mixed Seedance audio in character-voice replacement intervals."""

    detected_speech_intervals = _forbidden_speech_intervals(
        speech_gate,
        duration_seconds=duration_seconds,
    )
    raw_intervals = [
        *detected_speech_intervals,
        *(final_dialogue_intervals or []),
    ]
    intervals: list[tuple[float, float]] = []
    for start, end in sorted(raw_intervals):
        start = max(0.0, float(start))
        end = min(duration_seconds, float(end))
        if end <= start:
            continue
        if intervals and start <= intervals[-1][1] + 0.02:
            intervals[-1] = (
                intervals[-1][0],
                max(intervals[-1][1], end),
            )
        else:
            intervals.append((start, end))
    if not intervals:
        raise ArabicSegmentEmbeddingError(
            "Seedance speech-cut repair has no detected speech intervals."
        )
    preserved_intervals = _preserved_audio_intervals(
        intervals,
        duration_seconds=duration_seconds,
    )
    regions: list[tuple[str, float, float]] = []
    cursor = 0.0
    for start, end in intervals:
        if start > cursor + 1e-6:
            regions.append(("source", cursor, start))
        regions.append(("muted", start, end))
        cursor = end
    if cursor < duration_seconds - 1e-6:
        regions.append(("source", cursor, duration_seconds))

    filters: list[str] = []
    labels: list[str] = []
    for index, (kind, start, end) in enumerate(regions):
        label = f"region{index}"
        region_duration = end - start
        if kind == "muted":
            chain = (
                f"anullsrc=r={SAMPLE_RATE_HZ}:cl=stereo,"
                f"atrim=duration={region_duration:.6f},"
                "asetpts=PTS-STARTPTS"
            )
            filters.append(f"{chain}[{label}]")
        else:
            chain = (
                f"[0:a:0]atrim=start={start:.6f}:end={end:.6f},"
                "asetpts=PTS-STARTPTS,"
                f"aresample={SAMPLE_RATE_HZ},"
                "aformat=sample_fmts=fltp:channel_layouts=stereo"
            )
            fade = min(
                SEEDANCE_SPEECH_CUT_FADE_SECONDS,
                region_duration / 4,
            )
            if start > 0 and fade > 0:
                chain += f",afade=t=in:st=0:d={fade:.6f}"
            if end < duration_seconds and fade > 0:
                chain += (
                    f",afade=t=out:st={max(0.0, region_duration - fade):.6f}:"
                    f"d={fade:.6f}"
                )
            filters.append(f"{chain}[{label}]")
        labels.append(label)
    joined = "".join(f"[{label}]" for label in labels)
    filters.append(
        f"{joined}concat=n={len(labels)}:v=0:a=1,"
        f"atrim=start=0:end={duration_seconds:.6f}[clean]"
    )
    temporary = output_video.with_name(
        f".{output_video.name}.speech-cut.tmp.mp4"
    )
    command: list[str | Path] = [
        require_binary("ffmpeg"),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        source_video,
        "-filter_complex",
        ";".join(filters),
        "-map",
        "0:v:0",
        "-map",
        "[clean]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        str(SAMPLE_RATE_HZ),
        "-ac",
        "2",
        "-t",
        f"{duration_seconds:.6f}",
        "-movflags",
        "+faststart",
        temporary,
    ]
    try:
        run_media_command(
            command,
            context="Seedance forbidden-speech interval removal",
            timeout=300,
        )
    except MediaCommandError as exc:
        temporary.unlink(missing_ok=True)
        raise ArabicSegmentEmbeddingError(
            "Could not remove detected Seedance speech intervals."
        ) from exc
    if not temporary.is_file() or temporary.stat().st_size <= 0:
        raise ArabicSegmentEmbeddingError(
            "Seedance speech-cut background output is empty."
        )
    temporary.replace(output_video)
    return {
        "contract": "seedance-native-dialogue-interval-replacement/v5",
        "status": "APPLIED",
        "method": (
            "mute_seedance_mixed_audio_in_character_voice_intervals"
        ),
        "dialogue_gap_fill_source": "digital_silence",
        "elevenlabs_non_dialogue_request_count": 0,
        "native_audio_loop_count": 0,
        "center_suppression_applied": False,
        "native_audio_preserved_outside_replacement_intervals": True,
        "cut_scope": (
            "detected_character_speech_words_and_final_dialogue_windows"
        ),
        "padding_seconds": SEEDANCE_SPEECH_CUT_PADDING_SECONDS,
        "edge_fade_seconds": SEEDANCE_SPEECH_CUT_FADE_SECONDS,
        "detected_speech_intervals_seconds": [
            [round(start, 6), round(end, 6)]
            for start, end in detected_speech_intervals
        ],
        "final_dialogue_intervals_seconds": [
            [round(start, 6), round(end, 6)]
            for start, end in (final_dialogue_intervals or [])
        ],
        "interval_count": len(intervals),
        "cut_intervals_seconds": [
            [round(start, 6), round(end, 6)] for start, end in intervals
        ],
        "preserved_source_audio_intervals_seconds": [
            [round(start, 6), round(end, 6)]
            for start, end in preserved_intervals
        ],
    }


def embed_arabic_segment(
    *,
    task_dir: Path,
    segment_id: str,
    seedance_background_video: Path,
    output_video: Path,
    request_timeout: int,
    reviewed_cue_windows: dict[str, tuple[float, float]] | None = None,
    reviewed_cue_speeds: dict[str, float] | None = None,
    reviewed_cue_seeds: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Replace Seedance character speech while preserving safe native audio."""

    context = load_project_context(task_dir)
    if (
        context["target_language"] != TARGET_LANGUAGE
        or context["speech_audio_source"] != SPEECH_AUDIO_SOURCE
        or context["sound_effects_audio_source"] != SOUND_EFFECTS_AUDIO_SOURCE
    ):
        raise ArabicSegmentEmbeddingError(
            "Arabic branch requires ElevenLabs only for Arabic dialogue and "
            "Seedance native audio for all ambience and action sound."
        )
    cues = _dialogue_cues(task_dir, segment_id)
    reviewed_cue_windows = reviewed_cue_windows or {}
    reviewed_cue_speeds = reviewed_cue_speeds or {}
    reviewed_cue_seeds = reviewed_cue_seeds or {}
    cue_line_ids = {str(cue["line_id"]) for cue in cues}
    unknown_reviewed_lines = sorted(
        (
            set(reviewed_cue_windows)
            | set(reviewed_cue_speeds)
            | set(reviewed_cue_seeds)
        )
        - cue_line_ids
    )
    if unknown_reviewed_lines:
        raise ArabicSegmentEmbeddingError(
            f"{segment_id} reviewed cue windows name unknown lines: "
            + ", ".join(unknown_reviewed_lines)
        )
    invalid_reviewed_speeds = sorted(
        line_id
        for line_id, speed in reviewed_cue_speeds.items()
        if float(speed) < MIN_ELEVENLABS_SPEED or float(speed) > 1.2
    )
    if invalid_reviewed_speeds:
        raise ArabicSegmentEmbeddingError(
            f"{segment_id} reviewed ElevenLabs cue speeds must stay between "
            f"{MIN_ELEVENLABS_SPEED} and 1.2: "
            + ", ".join(invalid_reviewed_speeds)
        )
    invalid_reviewed_seeds = sorted(
        line_id
        for line_id, seed in reviewed_cue_seeds.items()
        if (
            isinstance(seed, bool)
            or not isinstance(seed, int)
            or seed < 0
            or seed > 4294967295
        )
    )
    if invalid_reviewed_seeds:
        raise ArabicSegmentEmbeddingError(
            f"{segment_id} reviewed ElevenLabs cue seeds must be integers "
            "between 0 and 4294967295: "
            + ", ".join(invalid_reviewed_seeds)
        )
    source_probe = _probe_video(
        seedance_background_video,
        require_audio=True,
    )
    duration = float(source_probe["duration_seconds"])
    voices = elevenlabs.voice_map() if cues else {}
    missing_speakers = sorted(
        {
            str(cue["speaker_entity_id"])
            for cue in cues
            if str(cue["speaker_entity_id"]) not in voices
        }
    )
    if missing_speakers:
        raise ArabicSegmentEmbeddingError(
            "ELEVENLABS_VOICE_MAP lacks speakers: " + ", ".join(missing_speakers)
        )
    voice_profiles = _approved_voice_profiles(
        task_dir=task_dir,
        voices={
            speaker_id: voices[speaker_id]
            for speaker_id in sorted(
                {str(cue["speaker_entity_id"]) for cue in cues}
            )
        },
    )

    cue_records: list[dict[str, Any]] = []
    phrase_plans: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"{segment_id}-arabic-dialogue-") as temp:
        temp_root = Path(temp)
        seedance_speech_gate: dict[str, Any]
        cleaned_seedance_speech_gate: dict[str, Any]
        seedance_audio_edit: dict[str, Any] = {
            "contract": "seedance-native-dialogue-interval-replacement/v5",
            "status": "NOT_APPLICABLE",
            "cut_intervals_seconds": [],
            "dialogue_gap_fill_source": "digital_silence",
            "elevenlabs_non_dialogue_request_count": 0,
            "native_audio_loop_count": 0,
            "center_suppression_applied": False,
        }
        mix_background_video = seedance_background_video
        try:
            seedance_speech_gate = audit_seedance_character_speech(
                seedance_background_video
            )
        except SeedanceSpeechGateError as exc:
            raise ArabicSegmentEmbeddingError(str(exc)) from exc
        final_dialogue_intervals: list[tuple[float, float]] = []
        for cue in cues:
            replacement_timing = _resolved_cue_timing(
                cue,
                seedance_speech_gate,
                visual_onset_guard_seconds=0.0,
                use_detected_end=True,
                use_full_detected_window=True,
            )
            reviewed_window = reviewed_cue_windows.get(str(cue["line_id"]))
            if reviewed_window is not None:
                replacement_timing, _ = _apply_reviewed_cue_window(
                    cue,
                    replacement_timing,
                    reviewed_window,
                    picture_duration=duration,
                )
            final_dialogue_intervals.append(
                (
                    float(replacement_timing["target_start_seconds"]),
                    float(replacement_timing["target_end_seconds"]),
                )
            )
        if cues or seedance_speech_gate.get("status") == "FAIL":
            speech_cut_video = temp_root / "seedance-dialogue-cut.mp4"
            seedance_audio_edit = _render_seedance_speech_cut(
                source_video=seedance_background_video,
                output_video=speech_cut_video,
                speech_gate=seedance_speech_gate,
                duration_seconds=duration,
                final_dialogue_intervals=final_dialogue_intervals,
            )
            mix_background_video = speech_cut_video
            cleaned_seedance_speech_gate = audit_seedance_character_speech(
                speech_cut_video
            )
            if cleaned_seedance_speech_gate.get("status") != "PASS":
                raise ArabicSegmentEmbeddingError(
                    f"{segment_id} still contains detected Seedance speech "
                    "after dialogue-window replacement."
                )
        else:
            seedance_audio_edit = {
                "contract": "seedance-native-dialogue-interval-replacement/v5",
                "status": "NOT_REQUIRED",
                "cut_intervals_seconds": [],
                "dialogue_gap_fill_source": "not_required",
                "elevenlabs_non_dialogue_request_count": 0,
                "native_audio_loop_count": 0,
            }
            cleaned_seedance_speech_gate = seedance_speech_gate
        cue_files: list[Path] = []
        timing_gate = seedance_speech_gate
        for cue_index, cue in enumerate(cues, start=1):
            timing = _resolved_cue_timing(
                cue,
                timing_gate,
                visual_onset_guard_seconds=0.0,
                use_detected_end=True,
                use_full_detected_window=True,
            )
            target_windows = [
                (float(window[0]), float(window[1]))
                for window in timing[
                    "seedance_detected_speech_windows_seconds"
                ]
            ]
            reviewed_window = reviewed_cue_windows.get(str(cue["line_id"]))
            if reviewed_window is not None:
                timing, target_windows = _apply_reviewed_cue_window(
                    cue,
                    timing,
                    reviewed_window,
                    picture_duration=duration,
                )
            timed_cue = {
                **cue,
                "start_seconds": timing["target_start_seconds"],
                "end_seconds": timing["target_end_seconds"],
            }
            exact_text = validate_arabic_dialogue(
                cue["exact_text"],
                context=str(cue["line_id"]),
            )
            speaker_id = str(cue["speaker_entity_id"])
            voice_profile = voice_profiles[speaker_id]
            approved_voice_settings = voice_profile["voice_settings"]
            reviewed_tts_speed = reviewed_cue_speeds.get(
                str(cue["line_id"])
            )
            reviewed_tts_seed = reviewed_cue_seeds.get(
                str(cue["line_id"])
            )
            requested_tts_speed = (
                float(reviewed_tts_speed)
                if reviewed_tts_speed is not None
                else float(voice_profile["approved_speed"])
            )
            tts_generation_count = 1
            response = elevenlabs.synthesize_arabic_speech(
                exact_text=exact_text,
                voice_id=voices[speaker_id],
                speed=requested_tts_speed,
                seed=reviewed_tts_seed,
                voice_settings=approved_voice_settings,
                timeout=request_timeout,
            )
            cue_seed = int(response["seed"])
            cue_seed_source = (
                "frame_reviewed_override"
                if reviewed_tts_seed is not None
                else "fresh_per_audio_build"
            )
            cue_path = temp_root / f"cue-{cue_index:03d}.mp3"
            cue_path.write_bytes(response["audio"])
            source_duration = _audio_duration(cue_path)
            source_words = _source_word_spans(
                exact_text=exact_text,
                tts_text=response["tts_text"],
                alignment=response["alignment"],
                context=str(cue["line_id"]),
            )
            target_span = (
                sum(
                    float(window[1]) - float(window[0])
                    for window in target_windows
                )
                or (
                    float(timed_cue["end_seconds"])
                    - float(timed_cue["start_seconds"])
                )
            )
            source_reference_start = float(source_words[0]["start"])
            source_reference_end = float(source_words[-1]["end"])
            required_tempo_factor = (
                source_reference_end - source_reference_start
            ) / target_span
            if (
                reviewed_tts_speed is None
                and required_tempo_factor < MIN_TEMPO_FACTOR
            ):
                requested_tts_speed = max(
                    MIN_ELEVENLABS_SPEED,
                    required_tempo_factor / MIN_TEMPO_FACTOR,
                )
                response = elevenlabs.synthesize_arabic_speech(
                    exact_text=exact_text,
                    voice_id=voices[speaker_id],
                    speed=requested_tts_speed,
                    seed=cue_seed,
                    voice_settings=approved_voice_settings,
                    timeout=request_timeout,
                )
                tts_generation_count += 1
                cue_path.write_bytes(response["audio"])
                source_duration = _audio_duration(cue_path)
                source_words = _source_word_spans(
                    exact_text=exact_text,
                    tts_text=response["tts_text"],
                    alignment=response["alignment"],
                    context=str(cue["line_id"]),
                )
            try:
                cue_phrases = _cue_phrase_plans(
                    cue=timed_cue,
                    cue_index=cue_index,
                    source_words=source_words,
                    source_duration=source_duration,
                    picture_duration=duration,
                    fill_target_window=True,
                    target_windows=target_windows,
                )
            except ArabicSegmentEmbeddingError:
                if (
                    len(target_windows) <= 1
                    or requested_tts_speed <= MIN_ELEVENLABS_SPEED
                ):
                    raise
                requested_tts_speed = MIN_ELEVENLABS_SPEED
                response = elevenlabs.synthesize_arabic_speech(
                    exact_text=exact_text,
                    voice_id=voices[speaker_id],
                    speed=requested_tts_speed,
                    seed=cue_seed,
                    voice_settings=approved_voice_settings,
                    timeout=request_timeout,
                )
                tts_generation_count += 1
                cue_path.write_bytes(response["audio"])
                source_duration = _audio_duration(cue_path)
                source_words = _source_word_spans(
                    exact_text=exact_text,
                    tts_text=response["tts_text"],
                    alignment=response["alignment"],
                    context=str(cue["line_id"]),
                )
                cue_phrases = _cue_phrase_plans(
                    cue=timed_cue,
                    cue_index=cue_index,
                    source_words=source_words,
                    source_duration=source_duration,
                    picture_duration=duration,
                    fill_target_window=True,
                    target_windows=target_windows,
                )
            phrase_plans.extend(cue_phrases)
            cue_files.append(cue_path)
            rendered_speech_end = max(
                float(item["target_end_seconds"])
                for item in cue_phrases
            )
            cue_records.append(
                {
                    "line_id": cue["line_id"],
                    "speaker_entity_id": speaker_id,
                    "voice_id": response["voice_id"],
                    "request_id": response["request_id"],
                    "model_id": response["model_id"],
                    "language_code": response["language_code"],
                    "language_code_sent": response["language_code_sent"],
                    "accent_profile_id": response["accent_profile_id"],
                    "grammatical_gender": response[
                        "grammatical_gender"
                    ],
                    "pronunciation_contract": response[
                        "pronunciation_contract"
                    ],
                    "text_sha256": hashlib.sha256(
                        exact_text.encode("utf-8")
                    ).hexdigest(),
                    "tts_text_sha256": response["tts_text_sha256"],
                    "tts_text_diacritic_count": response[
                        "tts_text_diacritic_count"
                    ],
                    "pronunciation_rules": response[
                        "pronunciation_rules"
                    ],
                    "word_count": len(source_words),
                    "phrase_count": len(cue_phrases),
                    "source_duration_seconds": round(source_duration, 6),
                    "elevenlabs_speed": round(requested_tts_speed, 6),
                    "elevenlabs_seed": response["seed"],
                    "elevenlabs_seed_source": cue_seed_source,
                    "approved_voice_settings_source": voice_profile["source"],
                    "approved_voice_settings_sha256": voice_profile[
                        "voice_settings_sha256"
                    ],
                    "applied_voice_settings": response["voice_settings"],
                    "elevenlabs_generation_count": tts_generation_count,
                    "elevenlabs_speed_source": (
                        "frame_reviewed_override"
                        if reviewed_tts_speed is not None
                        else "automatic_fit"
                    ),
                    "target_speech_start_seconds": round(
                        float(timing["target_start_seconds"]), 6
                    ),
                    "target_speech_end_seconds": round(
                        float(timing["target_end_seconds"]), 6
                    ),
                    "rendered_speech_end_seconds": round(
                        rendered_speech_end, 6
                    ),
                    "storyboard_speech_start_seconds": round(
                        float(timing["storyboard_start_seconds"]), 6
                    ),
                    "storyboard_speech_end_seconds": round(
                        float(timing["storyboard_end_seconds"]), 6
                    ),
                    "timing_source": timing["timing_source"],
                    "seedance_detected_speech_start_seconds": timing[
                        "seedance_detected_speech_start_seconds"
                    ],
                    "seedance_detected_speech_end_seconds": timing[
                        "seedance_detected_speech_end_seconds"
                    ],
                    "seedance_detected_speech_windows_seconds": timing[
                        "seedance_detected_speech_windows_seconds"
                    ],
                    "alignment_target_windows_seconds": [
                        [round(start, 6), round(end, 6)]
                        for start, end in target_windows
                    ],
                    "visual_mouth_onset_guard_seconds": timing.get(
                        "visual_mouth_onset_guard_seconds",
                        0.0,
                    ),
                    **(
                        {
                            "reviewed_timing_adjustment": timing[
                                "reviewed_timing_adjustment"
                            ]
                        }
                        if "reviewed_timing_adjustment" in timing
                        else {}
                    ),
                }
            )
        _render_embedded_video(
            seedance_background_video=mix_background_video,
            cue_files=cue_files,
            phrase_plans=phrase_plans,
            duration_seconds=duration,
            output=output_video,
        )

    final_probe = _probe_video(output_video, require_audio=True)
    if abs(float(final_probe["duration_seconds"]) - duration) > 0.25:
        raise ArabicSegmentEmbeddingError(
            f"{segment_id} ElevenLabs audio build changed picture duration"
        )
    return {
        "contract": "seedance-original-audio-dialogue-replacement/v2",
        "language": TARGET_LANGUAGE,
        "language_code": elevenlabs.LANGUAGE_CODE,
        "language_code_sent": False,
        "tts_model_id": TTS_MODEL_ID,
        "accent_profile_id": ACCENT_PROFILE_ID,
        "grammatical_gender_policy": GRAMMATICAL_GENDER_POLICY,
        "pronunciation_contract": PRONUNCIATION_CONTRACT,
        "speech_audio_source": SPEECH_AUDIO_SOURCE,
        "sound_effects_audio_source": SOUND_EFFECTS_AUDIO_SOURCE,
        "elevenlabs_usage_scope": "arabic_dialogue_only",
        "elevenlabs_voice_settings_authority": (
            "workspace_role_voice_brief"
        ),
        "elevenlabs_seed_policy": (
            "fresh_per_audio_build_persisted_per_cue_with_reviewed_override"
        ),
        "dialogue_phrase_loudness_normalization": {
            "status": "APPLIED" if phrase_plans else "NOT_REQUIRED",
            "method": (
                "ffmpeg_acompressor_then_loudnorm_per_natural_phrase"
            ),
            "compressor_threshold_db": DIALOGUE_COMPRESSOR_THRESHOLD_DB,
            "compressor_ratio": DIALOGUE_COMPRESSOR_RATIO,
            "compressor_attack_ms": DIALOGUE_COMPRESSOR_ATTACK_MS,
            "compressor_release_ms": DIALOGUE_COMPRESSOR_RELEASE_MS,
            "compressor_makeup_db": DIALOGUE_COMPRESSOR_MAKEUP_DB,
            "integrated_lufs_target": DIALOGUE_PHRASE_LOUDNESS_LUFS,
            "loudness_range_lu": DIALOGUE_PHRASE_LOUDNESS_RANGE_LU,
            "true_peak_dbfs": DIALOGUE_PHRASE_TRUE_PEAK_DBFS,
        },
        "elevenlabs_non_dialogue_request_count": 0,
        "dialogue_gap_fill_source": seedance_audio_edit.get(
            "dialogue_gap_fill_source"
        ),
        "alignment_method": (
            "seedance_detected_or_storyboard_window_natural_phrase_atempo"
        ),
        "timing_authority": (
            "seedance_detected_speech_window_with_storyboard_deviation_recorded"
        ),
        "seedance_generate_audio": True,
        "seedance_audio_in_delivery": True,
        "seedance_background_audio_retained": True,
        "seedance_speech_forbidden": True,
        "seedance_speech_in_delivery": False,
        "seedance_audio_preservation_scope": (
            "original_seedance_audio_outside_replacement_intervals_and_"
            "digital_silence_inside_replacement_intervals"
        ),
        "seedance_speech_detection": seedance_speech_gate,
        "seedance_clean_background_speech_gate": cleaned_seedance_speech_gate,
        "seedance_audio_edit": seedance_audio_edit,
        "picture_frames_retimed": False,
        "native_audio_full_duration": True,
        "native_audio_delivery_scope": (
            "seedance_ambience_and_action_sound_outside_dialogue_"
            "replacement_intervals"
        ),
        "cue_count": len(cue_records),
        "phrase_count": len(phrase_plans),
        "cues": cue_records,
        "phrases": phrase_plans,
        "picture_duration_seconds": round(duration, 6),
        "source_media_probe": source_probe,
        "final_media_probe": final_probe,
    }
