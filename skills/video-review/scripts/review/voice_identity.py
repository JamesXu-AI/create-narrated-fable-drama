"""Measure generated character voices against their approved audio references."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from narrated_fable_drama.contracts.asset_catalog import load_asset_catalog
from narrated_fable_drama.contracts.segment.handoff import load_segment_handoff
from narrated_fable_drama.core.json_io import load_json_object
from narrated_fable_drama.core.paths import ProjectPaths
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
        "minimum_spectral_envelope_similarity",
        "minimum_blocking_spectral_envelope_similarity",
    }
    if set(config) != expected:
        raise VoiceIdentityGateError(
            f"Voice identity gate config must use exact keys: {sorted(expected)}"
        )
    if config["contract"] != "video-review-voice-identity-gate-config/v1":
        raise VoiceIdentityGateError("Unsupported voice identity gate config.")
    for field in expected - {"contract"}:
        _positive_number(config[field], field)
    for field in (
        "vad_energy_quantile",
        "minimum_pitch_autocorrelation",
        "minimum_spectral_envelope_similarity",
        "minimum_blocking_spectral_envelope_similarity",
    ):
        if float(config[field]) >= 1:
            raise VoiceIdentityGateError(f"{field} must be less than 1.")
    if float(config["minimum_pitch_hz"]) >= float(config["maximum_pitch_hz"]):
        raise VoiceIdentityGateError(
            "minimum_pitch_hz must be below maximum_pitch_hz."
        )
    if float(config["minimum_blocking_spectral_envelope_similarity"]) >= float(
        config["minimum_spectral_envelope_similarity"]
    ):
        raise VoiceIdentityGateError(
            "minimum_blocking_spectral_envelope_similarity must be below "
            "minimum_spectral_envelope_similarity."
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
    failures: list[str] = []
    advisories: list[str] = []
    if pitch_ratio > float(config["maximum_median_pitch_ratio"]):
        failures.append(
            "median_pitch_ratio exceeds the approved-reference limit"
        )
    if centroid_ratio > float(config["maximum_spectral_centroid_ratio"]):
        failures.append(
            "spectral_centroid_ratio exceeds the approved-reference limit"
        )
    if envelope_similarity < float(
        config["minimum_blocking_spectral_envelope_similarity"]
    ):
        failures.append(
            "spectral_envelope_similarity is below the severe "
            "approved-reference limit"
        )
    elif envelope_similarity < float(
        config["minimum_spectral_envelope_similarity"]
    ):
        advisories.append(
            "spectral_envelope_similarity is below the review threshold but "
            "above the severe blocking limit"
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
        "spectral_envelope_similarity": round(envelope_similarity, 6),
        "minimum_spectral_envelope_similarity": float(
            config["minimum_spectral_envelope_similarity"]
        ),
        "minimum_blocking_spectral_envelope_similarity": float(
            config["minimum_blocking_spectral_envelope_similarity"]
        ),
        "failure_reasons": failures,
        "advisory_reasons": advisories,
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
    if not cues:
        return {
            "contract": "video-review-voice-identity-gate/v1",
            "segment_id": segment_id,
            "status": "NOT_APPLICABLE",
            "blocks_acceptance": False,
            "human_listening_review_required": False,
            "video_path": str(video_path),
            "video_sha256": _sha256(video_path),
            "config_path": str(config_path),
            "config_sha256": _sha256(config_path),
            "checks": [],
        }

    reference_profiles: dict[Path, dict[str, Any]] = {}
    checks: list[dict[str, Any]] = []
    for cue in cues:
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
        start = max(0.0, float(cue["start_seconds"]))
        end = min(duration, float(cue["end_seconds"]))
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
                "speaker_screenplay_identity_en": cue[
                    "speaker_screenplay_identity_en"
                ],
                "exact_text": cue["exact_text"],
                "candidate_window_seconds": [
                    round(start, 6),
                    round(end, 6),
                ],
                "approved_voice_description_en": voice["description_en"],
                "reference_path": str(reference_path),
                "reference_sha256": _sha256(reference_path),
                "reference_profile": reference_profiles[reference_path],
                "candidate_profile": candidate_profile,
                "comparison": comparison,
            }
        )
    failed = [check for check in checks if check["comparison"]["status"] == "FAIL"]
    advisory = [
        check
        for check in checks
        if check["comparison"].get("advisory_reasons")
    ]
    return {
        "contract": "video-review-voice-identity-gate/v1",
        "segment_id": segment_id,
        "status": "FAIL" if failed else "PASS",
        "blocks_acceptance": bool(failed),
        "human_listening_review_required": True,
        "review_policy": (
            "Acoustic ratios block only severe pitch/timbre drift. A moderate "
            "spectral-envelope difference is advisory because native ambience, "
            "music, codec color, and resynthesis can shift it without changing the "
            "perceived speaker. The video reviewer must still hear the complete "
            "Segment at normal speed and compare each speaker with the approved "
            "reference."
        ),
        "video_path": str(video_path),
        "video_sha256": _sha256(video_path),
        "config_path": str(config_path),
        "config_sha256": _sha256(config_path),
        "failed_cue_ids": [check["cue_id"] for check in failed],
        "advisory_cue_ids": [check["cue_id"] for check in advisory],
        "checks": checks,
    }
