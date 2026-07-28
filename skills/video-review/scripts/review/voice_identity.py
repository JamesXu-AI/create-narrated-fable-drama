"""Measure generated character voices against their approved audio references."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from narrated_fable_drama.contracts.asset_catalog import load_asset_catalog
from narrated_fable_drama.contracts.segment.handoff import load_segment_handoff
from narrated_fable_drama.core.arabic_pronunciation import (
    ACCENT_PROFILE_ID,
    GRAMMATICAL_GENDER_POLICY,
    PRONUNCIATION_CONTRACT,
    TTS_MODEL_ID,
    compile_arabic_tts_text,
)
from narrated_fable_drama.core.json_io import load_json_object
from narrated_fable_drama.core.paths import ProjectPaths
from narrated_fable_drama.core.project_context import load_project_context
from narrated_fable_drama.core.project_domain import (
    SOUND_EFFECTS_AUDIO_SOURCE,
    SPEECH_AUDIO_SOURCE,
    TARGET_LANGUAGE,
    ProjectDomainError,
    validate_arabic_dialogue,
)
from narrated_fable_drama.media.ffmpeg import MediaCommandError, require_binary, run
from narrated_fable_drama.media.probe import probe_json

REPOSITORY_ROOT = ProjectPaths.resolve(Path(__file__)).repository_root
DEFAULT_CONFIG = (
    REPOSITORY_ROOT
    / "skills"
    / "video-review"
    / "assets"
    / "voice-identity-gate.json"
)


class VoiceIdentityGateError(RuntimeError):
    """Raised when mandatory voice-identity evidence cannot be measured."""


VOICE_GATE_CONTRACT = "video-review-voice-identity-gate/v2"
ARABIC_EMBEDDING_CONTRACT = (
    "seedance-original-audio-dialogue-replacement/v2"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _positive_number(value: Any, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value <= 0
    ):
        raise VoiceIdentityGateError(f"{label} must be positive.")
    return float(value)


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = load_json_object(
        path.expanduser().resolve(),
        label="voice identity gate config",
        error_type=VoiceIdentityGateError,
    )
    expected = {
        "contract",
        "sample_rate_hz",
        "frame_duration_seconds",
        "frame_hop_seconds",
        "vad_energy_quantile",
        "minimum_pitch_autocorrelation",
        "minimum_voiced_frame_count",
        "minimum_candidate_duration_seconds",
        "minimum_pitch_hz",
        "maximum_pitch_hz",
        "maximum_median_pitch_ratio",
        "maximum_spectral_centroid_ratio",
        "maximum_spectral_centroid_ratio_with_strong_envelope",
        "maximum_pitch_ratio_with_strong_envelope",
        "strong_spectral_envelope_similarity",
        "minimum_spectral_envelope_similarity",
    }
    if set(config) != expected:
        raise VoiceIdentityGateError(
            f"Voice identity gate config must use exact keys: {sorted(expected)}"
        )
    if config["contract"] != "video-review-voice-identity-gate-config/v2":
        raise VoiceIdentityGateError("Unsupported voice identity gate config.")
    for field in expected - {"contract"}:
        _positive_number(config[field], field)
    for field in (
        "vad_energy_quantile",
        "minimum_pitch_autocorrelation",
        "strong_spectral_envelope_similarity",
        "minimum_spectral_envelope_similarity",
    ):
        if float(config[field]) >= 1:
            raise VoiceIdentityGateError(f"{field} must be less than 1.")
    if float(config["minimum_pitch_hz"]) >= float(config["maximum_pitch_hz"]):
        raise VoiceIdentityGateError(
            "minimum_pitch_hz must be below maximum_pitch_hz."
        )
    if int(config["minimum_voiced_frame_count"]) != config[
        "minimum_voiced_frame_count"
    ]:
        raise VoiceIdentityGateError(
            "minimum_voiced_frame_count must be an integer."
        )
    return config


def _decode_audio(
    media_path: Path,
    *,
    sample_rate_hz: int,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
) -> np.ndarray:
    if not media_path.is_file() or media_path.stat().st_size <= 0:
        raise VoiceIdentityGateError(f"Voice media is missing: {media_path}")
    command: list[str | Path] = [require_binary("ffmpeg"), "-v", "error"]
    if start_seconds is not None:
        command.extend(("-ss", f"{start_seconds:.6f}"))
    if end_seconds is not None:
        if start_seconds is not None and end_seconds <= start_seconds:
            raise VoiceIdentityGateError("Voice sample interval must be positive.")
        command.extend(("-to", f"{end_seconds:.6f}"))
    command.extend(
        (
            "-i",
            media_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate_hz),
            "-af",
            "highpass=f=70,lowpass=f=7500",
            "-f",
            "f32le",
            "-",
        )
    )
    try:
        completed = run(
            command,
            context=f"decode voice evidence from {media_path.name}",
            text=False,
            timeout=120,
        )
    except MediaCommandError as exc:
        raise VoiceIdentityGateError(str(exc)) from exc
    samples = np.frombuffer(completed.stdout, dtype="<f4").astype(
        np.float64,
        copy=False,
    )
    if samples.size == 0 or not np.all(np.isfinite(samples)):
        raise VoiceIdentityGateError(
            f"Voice evidence contains no finite samples: {media_path}"
        )
    return samples


def acoustic_profile(
    samples: np.ndarray,
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build a conservative voice profile from high-energy speech-like frames."""

    sample_rate = int(config["sample_rate_hz"])
    minimum_duration = float(config["minimum_candidate_duration_seconds"])
    duration = samples.size / sample_rate
    if duration < minimum_duration:
        raise VoiceIdentityGateError(
            f"Voice evidence is too short: {duration:.3f}s < "
            f"{minimum_duration:.3f}s."
        )
    centered = samples - float(np.mean(samples))
    peak = float(np.max(np.abs(centered)))
    if peak <= 1e-7:
        raise VoiceIdentityGateError("Voice evidence is effectively silent.")
    centered = centered / peak
    frame_size = max(
        16,
        round(sample_rate * float(config["frame_duration_seconds"])),
    )
    frame_hop = max(
        1,
        round(sample_rate * float(config["frame_hop_seconds"])),
    )
    starts = range(0, centered.size - frame_size + 1, frame_hop)
    frames = np.stack(
        [centered[start : start + frame_size] for start in starts]
    )
    windowed = frames * np.hanning(frame_size)
    energies = np.sqrt(np.mean(windowed**2, axis=1) + 1e-12)
    threshold = float(
        np.quantile(energies, float(config["vad_energy_quantile"]))
    )
    selected = windowed[energies >= threshold]
    if selected.size == 0:
        raise VoiceIdentityGateError("Voice activity selection produced no frames.")

    fft_size = 1
    while fft_size < frame_size:
        fft_size *= 2
    magnitudes = np.abs(np.fft.rfft(selected, n=fft_size)) + 1e-8
    powers = magnitudes**2
    frequencies = np.fft.rfftfreq(fft_size, d=1.0 / sample_rate)
    spectral_centroids = (
        np.sum(powers * frequencies, axis=1) / np.sum(powers, axis=1)
    )
    mel_count = 26
    mel_edges = np.linspace(
        2595.0 * np.log10(1.0 + 80.0 / 700.0),
        2595.0 * np.log10(1.0 + 7600.0 / 700.0),
        mel_count + 2,
    )
    edge_hz = 700.0 * (10.0 ** (mel_edges / 2595.0) - 1.0)
    edge_bins = np.floor((fft_size + 1) * edge_hz / sample_rate).astype(int)
    mel_filters = np.zeros((mel_count, powers.shape[1]))
    for index in range(1, mel_count + 1):
        left, center, right = edge_bins[index - 1 : index + 2]
        if center > left:
            mel_filters[index - 1, left:center] = (
                np.arange(left, center) - left
            ) / (center - left)
        if right > center:
            mel_filters[index - 1, center:right] = (
                right - np.arange(center, right)
            ) / (right - center)
    log_mel = np.log(powers @ mel_filters.T + 1e-8)
    spectral_envelope = np.mean(log_mel, axis=0)

    minimum_lag = max(
        1,
        int(sample_rate / float(config["maximum_pitch_hz"])),
    )
    maximum_lag = min(
        frame_size - 2,
        int(sample_rate / float(config["minimum_pitch_hz"])),
    )
    pitch_values: list[float] = []
    pitch_correlations: list[float] = []
    for frame in selected:
        autocorrelation = np.correlate(frame, frame, mode="full")[
            frame_size - 1 :
        ]
        zero_lag = float(autocorrelation[0])
        if zero_lag <= 1e-10:
            continue
        normalized = autocorrelation / zero_lag
        local = normalized[minimum_lag : maximum_lag + 1]
        lag = minimum_lag + int(np.argmax(local))
        correlation = float(normalized[lag])
        if correlation < float(config["minimum_pitch_autocorrelation"]):
            continue
        pitch_values.append(sample_rate / lag)
        pitch_correlations.append(correlation)
    minimum_voiced = int(config["minimum_voiced_frame_count"])
    if len(pitch_values) < minimum_voiced:
        raise VoiceIdentityGateError(
            "Voice evidence has too few stable voiced frames: "
            f"{len(pitch_values)} < {minimum_voiced}."
        )
    return {
        "duration_seconds": round(duration, 6),
        "selected_frame_count": int(selected.shape[0]),
        "voiced_frame_count": len(pitch_values),
        "median_pitch_hz": round(float(np.median(pitch_values)), 6),
        "pitch_q25_hz": round(float(np.quantile(pitch_values, 0.25)), 6),
        "pitch_q75_hz": round(float(np.quantile(pitch_values, 0.75)), 6),
        "median_pitch_autocorrelation": round(
            float(np.median(pitch_correlations)),
            6,
        ),
        "median_spectral_centroid_hz": round(
            float(np.median(spectral_centroids)),
            6,
        ),
        "mean_log_mel_spectral_envelope": [
            round(float(value), 6) for value in spectral_envelope
        ],
    }


def _symmetric_ratio(left: float, right: float) -> float:
    if left <= 0 or right <= 0:
        raise VoiceIdentityGateError("Voice comparison values must be positive.")
    return max(left / right, right / left)


def compare_profiles(
    reference: dict[str, Any],
    candidate: dict[str, Any],
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    pitch_ratio = _symmetric_ratio(
        float(reference["median_pitch_hz"]),
        float(candidate["median_pitch_hz"]),
    )
    centroid_ratio = _symmetric_ratio(
        float(reference["median_spectral_centroid_hz"]),
        float(candidate["median_spectral_centroid_hz"]),
    )
    reference_envelope = np.asarray(
        reference["mean_log_mel_spectral_envelope"],
        dtype=np.float64,
    )
    candidate_envelope = np.asarray(
        candidate["mean_log_mel_spectral_envelope"],
        dtype=np.float64,
    )
    if reference_envelope.shape != candidate_envelope.shape:
        raise VoiceIdentityGateError(
            "Voice spectral-envelope dimensions do not match."
        )
    reference_envelope -= float(np.mean(reference_envelope))
    candidate_envelope -= float(np.mean(candidate_envelope))
    denominator = float(
        np.linalg.norm(reference_envelope) * np.linalg.norm(candidate_envelope)
    )
    if denominator <= 1e-10:
        raise VoiceIdentityGateError(
            "Voice spectral envelope cannot be normalized."
        )
    envelope_similarity = float(
        np.dot(reference_envelope, candidate_envelope) / denominator
    )
    strong_envelope_centroid_variance = (
        centroid_ratio
        <= float(
            config[
                "maximum_spectral_centroid_ratio_with_strong_envelope"
            ]
        )
        and pitch_ratio
        <= float(config["maximum_pitch_ratio_with_strong_envelope"])
        and envelope_similarity
        >= float(config["strong_spectral_envelope_similarity"])
    )
    failures: list[str] = []
    if pitch_ratio > float(config["maximum_median_pitch_ratio"]):
        failures.append(
            "median_pitch_ratio exceeds the approved-reference limit"
        )
    if (
        centroid_ratio > float(config["maximum_spectral_centroid_ratio"])
        and not strong_envelope_centroid_variance
    ):
        failures.append(
            "spectral_centroid_ratio exceeds the approved-reference limit"
        )
    if envelope_similarity < float(
        config["minimum_spectral_envelope_similarity"]
    ):
        failures.append(
            "spectral_envelope_similarity is below the approved-reference limit"
        )
    return {
        "status": "FAIL" if failures else "PASS",
        "median_pitch_ratio": round(pitch_ratio, 6),
        "maximum_median_pitch_ratio": float(
            config["maximum_median_pitch_ratio"]
        ),
        "spectral_centroid_ratio": round(centroid_ratio, 6),
        "maximum_spectral_centroid_ratio": float(
            config["maximum_spectral_centroid_ratio"]
        ),
        "strong_envelope_centroid_variance": (
            strong_envelope_centroid_variance
        ),
        "maximum_spectral_centroid_ratio_with_strong_envelope": float(
            config[
                "maximum_spectral_centroid_ratio_with_strong_envelope"
            ]
        ),
        "maximum_pitch_ratio_with_strong_envelope": float(
            config["maximum_pitch_ratio_with_strong_envelope"]
        ),
        "spectral_envelope_similarity": round(envelope_similarity, 6),
        "strong_spectral_envelope_similarity": float(
            config["strong_spectral_envelope_similarity"]
        ),
        "minimum_spectral_envelope_similarity": float(
            config["minimum_spectral_envelope_similarity"]
        ),
        "failure_reasons": failures,
    }


def _media_duration(path: Path) -> float:
    try:
        payload = probe_json(path)
        duration = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, MediaCommandError) as exc:
        raise VoiceIdentityGateError(f"Cannot read Segment duration: {path}") from exc
    if duration <= 0:
        raise VoiceIdentityGateError(f"Segment duration is invalid: {path}")
    return duration


def _reviewed_window_within_visual_authority(
    *,
    storyboard_start: float,
    storyboard_end: float,
    detected_start: float | None,
    reviewed_start: float,
    reviewed_end: float,
) -> bool:
    """Allow frame review to retain an earlier detected mouth onset."""

    earliest_reviewable_start = storyboard_start
    if detected_start is not None:
        earliest_reviewable_start = min(
            earliest_reviewable_start,
            detected_start,
        )
    return (
        reviewed_start >= earliest_reviewable_start - 0.001
        and reviewed_end <= storyboard_end + 0.001
        and reviewed_end > reviewed_start
    )


def _arabic_embedding_authority(
    task_dir: Path,
    segment_id: str,
    video_path: Path,
    cues: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bind reviewed audio to exact Arabic cue hashes and role voice IDs."""

    project = load_project_context(task_dir)
    if (
        project.get("target_language") != TARGET_LANGUAGE
        or project.get("speech_audio_source") != SPEECH_AUDIO_SOURCE
        or project.get("sound_effects_audio_source")
        != SOUND_EFFECTS_AUDIO_SOURCE
    ):
        raise VoiceIdentityGateError(
            f"{segment_id} must use ElevenLabs only for Arabic dialogue and "
            "Seedance native audio for all non-dialogue sound."
        )
    authoritative: list[dict[str, Any]] = []
    try:
        for cue in cues:
            exact = validate_arabic_dialogue(
                cue["exact_text"],
                context=f"{segment_id}/{cue['cue_id']} voice review",
            )
            pronunciation = compile_arabic_tts_text(
                exact,
                grammatical_gender=GRAMMATICAL_GENDER_POLICY,
                context=f"{segment_id}/{cue['cue_id']} voice review",
            )
            authoritative.append(
                {
                    "line_id": str(cue["cue_id"]),
                    "speaker_entity_id": str(cue["speaker_entity_id"]),
                    "text_sha256": hashlib.sha256(
                        exact.encode("utf-8")
                    ).hexdigest(),
                    "tts_text_sha256": pronunciation["tts_text_sha256"],
                    "tts_text_diacritic_count": pronunciation[
                        "tts_text_diacritic_count"
                    ],
                    "pronunciation_rules": pronunciation["applied_rules"],
                    "storyboard_start_seconds": float(cue["start_seconds"]),
                    "storyboard_end_seconds": float(cue["end_seconds"]),
                }
            )
    except (KeyError, TypeError, ProjectDomainError) as exc:
        raise VoiceIdentityGateError(
            f"{segment_id} voice review requires exact Arabic-only cues."
        ) from exc

    embedding_path = video_path.parent / "arabic-embedding-record.json"
    embedding = load_json_object(
        embedding_path,
        label=f"{segment_id} Arabic embedding record",
        error_type=VoiceIdentityGateError,
    )
    cleaned_gate = embedding.get("seedance_clean_background_speech_gate")
    audio_edit = embedding.get("seedance_audio_edit")
    valid_seedance_audio_policy = (
        embedding.get("seedance_generate_audio") is True
        and embedding.get("seedance_audio_in_delivery") is True
        and embedding.get("seedance_background_audio_retained") is True
        and embedding.get("seedance_speech_in_delivery") is False
        and isinstance(cleaned_gate, dict)
        and cleaned_gate.get("status") == "PASS"
        and isinstance(audio_edit, dict)
        and audio_edit.get("status") in {"APPLIED", "NOT_REQUIRED"}
    )
    if (
        embedding.get("contract") != ARABIC_EMBEDDING_CONTRACT
        or embedding.get("language") != TARGET_LANGUAGE
        or embedding.get("language_code") != "ar"
        or embedding.get("language_code_sent") is not False
        or embedding.get("tts_model_id") != TTS_MODEL_ID
        or embedding.get("accent_profile_id") != ACCENT_PROFILE_ID
        or embedding.get("grammatical_gender_policy")
        != GRAMMATICAL_GENDER_POLICY
        or embedding.get("pronunciation_contract")
        != PRONUNCIATION_CONTRACT
        or embedding.get("speech_audio_source") != SPEECH_AUDIO_SOURCE
        or embedding.get("sound_effects_audio_source")
        != SOUND_EFFECTS_AUDIO_SOURCE
        or embedding.get("native_audio_full_duration") is not True
        or embedding.get("elevenlabs_usage_scope") != "arabic_dialogue_only"
        or embedding.get("elevenlabs_non_dialogue_request_count") != 0
        or embedding.get("dialogue_gap_fill_source")
        not in {
            "digital_silence",
            "not_required",
        }
        or not valid_seedance_audio_policy
        or not isinstance(embedding.get("cues"), list)
    ):
        raise VoiceIdentityGateError(
            f"{segment_id} Arabic dialogue-replacement record is invalid."
        )
    voice_map_path = (
        task_dir
        / "direct-production-design"
        / "elevenlabs-voice-map.json"
    )
    voice_map = load_json_object(
        voice_map_path,
        label="ElevenLabs role voice map",
        error_type=VoiceIdentityGateError,
    )
    embedded_cues = embedding["cues"]
    if len(embedded_cues) != len(authoritative):
        raise VoiceIdentityGateError(
            f"{segment_id} Arabic embedding cue coverage differs from Storyboard."
        )
    bindings: list[dict[str, Any]] = []
    for expected, observed in zip(authoritative, embedded_cues):
        speaker_id = expected["speaker_entity_id"]
        expected_voice_id = voice_map.get(speaker_id)
        if not isinstance(observed, dict):
            raise VoiceIdentityGateError(
                f"{segment_id}/{expected['line_id']} Arabic cue record is invalid."
            )
        try:
            storyboard_start = float(
                observed["storyboard_speech_start_seconds"]
            )
            storyboard_end = float(observed["storyboard_speech_end_seconds"])
            target_start = float(observed["target_speech_start_seconds"])
            target_end = float(observed["target_speech_end_seconds"])
            rendered_end = float(observed["rendered_speech_end_seconds"])
            detected_start_raw = observed.get(
                "seedance_detected_speech_start_seconds"
            )
            detected_end_raw = observed.get(
                "seedance_detected_speech_end_seconds"
            )
            detected_start = (
                float(detected_start_raw)
                if detected_start_raw is not None
                else None
            )
            detected_end = (
                float(detected_end_raw)
                if detected_end_raw is not None
                else None
            )
            visual_onset_guard = float(
                observed.get("visual_mouth_onset_guard_seconds") or 0.0
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise VoiceIdentityGateError(
                f"{segment_id}/{expected['line_id']} Arabic cue timing evidence "
                "is missing or invalid."
            ) from exc
        timing_source = observed.get("timing_source")
        expected_target_start = float(expected["storyboard_start_seconds"])
        expected_target_end = float(expected["storyboard_end_seconds"])
        if timing_source == (
            "seedance_detected_speech_onset_within_storyboard_window"
        ):
            if detected_start is None:
                raise VoiceIdentityGateError(
                    f"{segment_id}/{expected['line_id']} lacks detected "
                    "Seedance speech-onset evidence."
                )
            expected_target_start = max(expected_target_start, detected_start)
        elif timing_source == (
            "seedance_detected_speech_onset_plus_visual_guard_"
            "within_storyboard_window"
        ):
            if (
                detected_start is None
                or visual_onset_guard <= 0
                or visual_onset_guard > 1.5
            ):
                raise VoiceIdentityGateError(
                    f"{segment_id}/{expected['line_id']} lacks valid visual "
                    "mouth-onset guard evidence."
                )
            expected_target_start = max(
                expected_target_start,
                detected_start + visual_onset_guard,
            )
        elif timing_source == "seedance_detected_speech_window":
            if (
                detected_start is None
                or detected_end is None
                or detected_end <= detected_start
            ):
                raise VoiceIdentityGateError(
                    f"{segment_id}/{expected['line_id']} lacks a valid detected "
                    "Seedance speech window."
                )
            expected_target_start = detected_start
        elif timing_source == "model_reviewed_visual_mouth_window":
            reviewed = observed.get("reviewed_timing_adjustment")
            target_windows = observed.get("alignment_target_windows_seconds")
            if (
                not isinstance(reviewed, dict)
                or reviewed.get("authority")
                != "human_direction_plus_frame_review"
                or not isinstance(target_windows, list)
                or target_windows != [[target_start, target_end]]
            ):
                raise VoiceIdentityGateError(
                    f"{segment_id}/{expected['line_id']} lacks valid reviewed "
                    "mouth-performance timing evidence."
                )
            try:
                reviewed_start = float(
                    reviewed["reviewed_target_start_seconds"]
                )
                reviewed_end = float(
                    reviewed["reviewed_target_end_seconds"]
                )
                source_start = float(
                    reviewed["source_target_start_seconds"]
                )
                source_end = float(
                    reviewed["source_target_end_seconds"]
                )
                start_adjustment = float(
                    reviewed["start_adjustment_seconds"]
                )
                end_adjustment = float(
                    reviewed["end_adjustment_seconds"]
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise VoiceIdentityGateError(
                    f"{segment_id}/{expected['line_id']} reviewed mouth timing "
                    "evidence is invalid."
                ) from exc
            if (
                not _reviewed_window_within_visual_authority(
                    storyboard_start=expected_target_start,
                    storyboard_end=expected_target_end,
                    detected_start=detected_start,
                    reviewed_start=reviewed_start,
                    reviewed_end=reviewed_end,
                )
                or abs(reviewed_start - target_start) > 0.001
                or abs(reviewed_end - target_end) > 0.001
                or abs(
                    reviewed_start - source_start - start_adjustment
                )
                > 0.001
                or abs(reviewed_end - source_end - end_adjustment) > 0.001
            ):
                raise VoiceIdentityGateError(
                    f"{segment_id}/{expected['line_id']} reviewed mouth timing "
                    "falls outside its Storyboard authority."
                )
            expected_target_start = reviewed_start
            expected_target_end = reviewed_end
        elif timing_source != "storyboard_window_fallback":
            raise VoiceIdentityGateError(
                f"{segment_id}/{expected['line_id']} uses unknown Arabic cue "
                "timing authority."
            )
        if (
            detected_end is not None
            and timing_source != "model_reviewed_visual_mouth_window"
        ):
            expected_target_end = (
                detected_end
                if timing_source == "seedance_detected_speech_window"
                else min(expected_target_end, detected_end)
            )
        timing_is_valid = (
            abs(
                storyboard_start
                - float(expected["storyboard_start_seconds"])
            )
            <= 0.05
            and abs(
                storyboard_end
                - float(expected["storyboard_end_seconds"])
            )
            <= 0.05
            and abs(target_start - expected_target_start) <= 0.05
            and abs(target_end - expected_target_end) <= 0.05
            and 0.0 <= target_start < rendered_end <= target_end
        )
        if (
            observed.get("line_id") != expected["line_id"]
            or observed.get("speaker_entity_id") != speaker_id
            or observed.get("language_code") != "ar"
            or observed.get("language_code_sent") is not False
            or observed.get("model_id") != TTS_MODEL_ID
            or observed.get("accent_profile_id") != ACCENT_PROFILE_ID
            or observed.get("grammatical_gender")
            != GRAMMATICAL_GENDER_POLICY
            or observed.get("pronunciation_contract")
            != PRONUNCIATION_CONTRACT
            or observed.get("text_sha256") != expected["text_sha256"]
            or observed.get("tts_text_sha256")
            != expected["tts_text_sha256"]
            or observed.get("tts_text_diacritic_count")
            != expected["tts_text_diacritic_count"]
            or observed.get("pronunciation_rules")
            != expected["pronunciation_rules"]
            or not isinstance(expected_voice_id, str)
            or not expected_voice_id
            or observed.get("voice_id") != expected_voice_id
            or not timing_is_valid
        ):
            raise VoiceIdentityGateError(
                f"{segment_id}/{expected['line_id']} Arabic text, language, "
                "speaker, ElevenLabs voice, or performance timing binding is "
                "stale."
            )
        bindings.append(
            {
                **expected,
                "language_code": "ar",
                "voice_id": expected_voice_id,
                "target_speech_start_seconds": target_start,
                "rendered_speech_end_seconds": rendered_end,
                "timing_source": timing_source,
                "visual_mouth_onset_guard_seconds": visual_onset_guard,
            }
        )
    return {
        "status": "PASS",
        "language": TARGET_LANGUAGE,
        "language_code": "ar",
        "language_code_sent": False,
        "tts_model_id": TTS_MODEL_ID,
        "accent_profile_id": ACCENT_PROFILE_ID,
        "grammatical_gender_policy": GRAMMATICAL_GENDER_POLICY,
        "pronunciation_contract": PRONUNCIATION_CONTRACT,
        "arabic_only_no_latin": "PASS",
        "speech_audio_source": SPEECH_AUDIO_SOURCE,
        "sound_effects_audio_source": SOUND_EFFECTS_AUDIO_SOURCE,
        "elevenlabs_usage_scope": "arabic_dialogue_only",
        "elevenlabs_non_dialogue_request_count": 0,
        "dialogue_gap_fill_source": embedding["dialogue_gap_fill_source"],
        "seedance_generate_audio": True,
        "seedance_audio_in_delivery": True,
        "seedance_speech_in_delivery": False,
        "embedding_record_path": str(embedding_path),
        "embedding_record_sha256": _sha256(embedding_path),
        "voice_map_path": str(voice_map_path),
        "voice_map_sha256": _sha256(voice_map_path),
        "cue_bindings": bindings,
    }


def prepare_segment_voice_identity_gate(
    task_dir: Path,
    segment_id: str,
    *,
    video_path: Path | None = None,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Measure every speaking character in one generated Segment."""

    task_dir = task_dir.expanduser().resolve()
    config_path = config_path.expanduser().resolve()
    config = load_config(config_path)
    handoff = load_segment_handoff(task_dir)
    if segment_id not in handoff:
        raise VoiceIdentityGateError(f"Unknown Segment: {segment_id}")
    if video_path is None:
        video_path = (
            task_dir
            / ".pending"
            / "virtual-production"
            / "generation-segments"
            / segment_id
            / "video.mp4"
        )
    video_path = video_path.expanduser().resolve()
    duration = _media_duration(video_path)
    catalog = load_asset_catalog(
        task_dir,
        repository_root=REPOSITORY_ROOT,
    )
    assets = catalog["assets"]
    cues = [
        cue
        for block in handoff[segment_id]["timeline_blocks"]
        for cue in block["dialogue_cues"]
    ]
    arabic_authority = (
        _arabic_embedding_authority(
            task_dir,
            segment_id,
            video_path,
            cues,
        )
        if cues
        else {
            "status": "NOT_APPLICABLE",
            "language": TARGET_LANGUAGE,
            "language_code": "ar",
            "arabic_only_no_latin": "PASS",
            "speech_audio_source": SPEECH_AUDIO_SOURCE,
            "cue_bindings": [],
        }
    )
    if not cues:
        return {
            "contract": VOICE_GATE_CONTRACT,
            "segment_id": segment_id,
            "language": TARGET_LANGUAGE,
            "language_code": "ar",
            "status": "NOT_APPLICABLE",
            "blocks_acceptance": False,
            "human_listening_review_required": False,
            "video_path": str(video_path),
            "video_sha256": _sha256(video_path),
            "config_path": str(config_path),
            "config_sha256": _sha256(config_path),
            "arabic_dialogue_authority": arabic_authority,
            "checks": [],
        }

    reference_profiles: dict[Path, dict[str, Any]] = {}
    checks: list[dict[str, Any]] = []
    for cue in cues:
        arabic_binding = next(
            item
            for item in arabic_authority["cue_bindings"]
            if item["line_id"] == cue["cue_id"]
        )
        speaker_id = str(cue["speaker_entity_id"])
        asset = assets.get(speaker_id)
        voice = asset.get("voice") if isinstance(asset, dict) else None
        reference = voice.get("reference") if isinstance(voice, dict) else None
        reference_path_value = (
            reference.get("path") if isinstance(reference, dict) else None
        )
        if not isinstance(reference_path_value, str) or not reference_path_value:
            raise VoiceIdentityGateError(
                f"{segment_id} speaker {speaker_id} has no approved voice reference."
            )
        reference_path = (REPOSITORY_ROOT / reference_path_value).resolve()
        if reference_path not in reference_profiles:
            reference_profiles[reference_path] = acoustic_profile(
                _decode_audio(
                    reference_path,
                    sample_rate_hz=int(config["sample_rate_hz"]),
                ),
                config=config,
            )
        start = max(
            0.0,
            float(arabic_binding["target_speech_start_seconds"]),
        )
        end = min(
            duration,
            float(arabic_binding["rendered_speech_end_seconds"]),
        )
        candidate_profile = acoustic_profile(
            _decode_audio(
                video_path,
                sample_rate_hz=int(config["sample_rate_hz"]),
                start_seconds=start,
                end_seconds=end,
            ),
            config=config,
        )
        comparison = compare_profiles(
            reference_profiles[reference_path],
            candidate_profile,
            config=config,
        )
        checks.append(
            {
                "cue_id": cue["cue_id"],
                "speaker_entity_id": speaker_id,
                "speaker_screenplay_identity": cue[
                    "speaker_screenplay_identity_en"
                ],
                "exact_text": cue["exact_text"],
                "language": TARGET_LANGUAGE,
                "language_code": "ar",
                "exact_text_sha256": arabic_binding["text_sha256"],
                "elevenlabs_voice_id": arabic_binding["voice_id"],
                "candidate_window_seconds": [
                    round(start, 6),
                    round(end, 6),
                ],
                "approved_voice_description": voice["description_en"],
                "reference_path": str(reference_path),
                "reference_sha256": _sha256(reference_path),
                "reference_profile": reference_profiles[reference_path],
                "candidate_profile": candidate_profile,
                "comparison": comparison,
            }
        )
    failed = [check for check in checks if check["comparison"]["status"] == "FAIL"]
    return {
        "contract": VOICE_GATE_CONTRACT,
        "segment_id": segment_id,
        "language": TARGET_LANGUAGE,
        "language_code": "ar",
        "arabic_only_no_latin": "PASS",
        "status": "FAIL" if failed else "PASS",
        "blocks_acceptance": bool(failed),
        "human_listening_review_required": True,
        "review_policy": (
            "Acoustic ratios are a conservative technical hold for severe pitch/"
            "timbre drift. The video reviewer must still hear the complete Segment "
            "at normal speed and compare each speaker with the approved reference."
        ),
        "video_path": str(video_path),
        "video_sha256": _sha256(video_path),
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "arabic_dialogue_authority": arabic_authority,
        "failed_cue_ids": [check["cue_id"] for check in failed],
        "checks": checks,
    }
