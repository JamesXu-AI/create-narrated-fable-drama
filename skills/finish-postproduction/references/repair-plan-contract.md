# Model-Authored Repair Plan Contract

The Editor and Restoration Master model writes one
`llm-postproduction-repair-plan/v1` JSON object after inspecting the current
`finish-postproduction-evidence/v1` manifest and its media artifacts. The plan is
creative authority. Python validates and executes it but never fills a missing
field.

## Root

Every root field is required:

```text
contract
evidence_manifest_sha256
source_set_sha256
decision_authority
observation_window
segments
boundaries
audio_bridges
terminal_audio
delivery
overall_reason
```

`decision_authority` is exactly `editor-restoration-master-model`.
`observation_window` explicitly states `outgoing_tail_seconds: 3.0` and
`incoming_head_seconds: 3.0`.

## Segment plan

Every accepted Segment appears once and in source order:

```json
{
  "segment_id": "segment-NNN",
  "source_sha256": "evidence source hash",
  "provider_attempt_id": "semantic provider attempt",
  "picture": {
    "source_in_seconds": 0.0,
    "source_out_seconds": 0.0,
    "removed_intervals": [],
    "color_adjustments": []
  },
  "audio": {
    "source_in_seconds": 0.0,
    "source_out_seconds": 0.0,
    "removed_intervals": [],
    "timeline_offset_from_picture_in_seconds": 0.0,
    "gain_db": 0.0,
    "fade_in_seconds": 0.0,
    "fade_out_seconds": 0.0,
    "gain_adjustments": []
  },
  "protected_dialogue_line_ids": [],
  "reason": "model-authored evidence-based reason"
}
```

The numeric zeros above are structural examples, not defaults. The model must
replace every time, gain, and duration with its actual decision. A color
adjustment requires exact source start/end, brightness, contrast, saturation,
gamma, and reason. A local gain adjustment requires exact source start/end,
gain dB, and reason.

Picture `source_in_seconds` and `source_out_seconds` are real edit points. Use them
to remove only the model-identified frozen tail, repeated frames, action restart,
or unusable boundary material. Every removed picture interval must also appear in
one boundary's `modification_intervals`; the validator rejects undeclared trims.

Use picture `removed_intervals` to delete a proven unnecessary hold, duplicate
action, frozen section, or extra generated material inside a Segment while
retaining valid material on both sides. Each entry requires exact source start,
source end, and reason. Use audio `removed_intervals` independently: delete the
matching audio only when that is the model's explicit synchronization decision;
otherwise author a J/L Cut or evidence-backed bridge. Dialogue may not intersect
any removed interval. The renderer converts the remaining ranges into ordered
splices and the subtitle compiler remaps later cue times across those deletions.

## Boundary plan

Every evidence boundary appears once and in order:

```json
{
  "boundary_id": "segment-NNN--segment-NNN",
  "from": "segment-NNN",
  "to": "segment-NNN",
  "evidence_boundary_id": "segment-NNN--segment-NNN",
  "decision": "no_op | repair | regenerate",
  "scope": "boundary_local | segment_scope_review",
  "picture": {
    "operation": "hard_cut | dissolve | fade | baked_effect",
    "overlap_seconds": 0.0
  },
  "audio": {
    "operation": "native_cut | soft_cut | crossfade | j_cut | l_cut | ambient_bridge | no_op",
    "outgoing_fade_out_seconds": 0.0,
    "incoming_fade_in_seconds": 0.0
  },
  "modification_intervals": [],
  "protected_dialogue_line_ids": [],
  "protected_events": [],
  "reason": "model-authored narrative and technical reason",
  "candidates": []
}
```

Each modification interval has `media`, `segment_id`, `start_seconds`,
`end_seconds`, and `reason`. `boundary_local` intervals must remain inside the
outgoing final 3 seconds or incoming first 3 seconds. An interval beyond that
range requires the model to choose `segment_scope_review`; the tool never widens
scope itself.

`soft_cut` is the zero-overlap repair for a baked Seedance-native track whose
music is audibly forced to stop at the video boundary. It keeps both native audio
events aligned with their pictures and requires at least one explicit outgoing
or incoming fade. Use only measured dialogue-free edge intervals and declare
each fade in `modification_intervals`. It is not a crossfade and creates no
invented audio handle. Prefer `crossfade`, J/L Cut, or `ambient_bridge` only when
real, safe source handles support that operation. An incomplete musical phrase
alone is not a `regenerate` reason once normal-speed listening finds no obvious
jump.

## Audio bridge

Each optional bridge declares `bridge_id`, `boundary_id`, `source_segment_id`,
exact source in/out, exact timeline-in, gain, fade-in, fade-out,
`dialogue_free_evidence_ref`, and reason. The source is read only. There is no
automatic ambience loop or silence padding.

## Terminal and delivery

The plan explicitly names the final Segment, terminal fade duration, and reason.
It also explicitly supplies video codec, preset, CRF, pixel format, audio codec,
audio bitrate, sample rate, and channel layout. Current renderer support is
`libx264`, `yuv420p`, `aac`, and `stereo`; unsupported explicit choices fail.
Segment and terminal fades may not overlap protected dialogue.

## Validation

The validator rejects missing or unknown fields, stale evidence, changed source
hashes, provider-attempt mismatch, incomplete Segment or boundary coverage,
removed dialogue, invalid source windows, out-of-scope local modification,
audio fades over protected dialogue, unsupported operations, and implicit audio
padding. A `regenerate` decision is a valid model conclusion but blocks
rendering.
