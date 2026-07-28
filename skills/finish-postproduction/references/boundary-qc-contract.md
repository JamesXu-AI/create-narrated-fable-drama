# Boundary QC & Repair Contract

## Position in the finishing workflow

Boundary QC runs after the current generated Segment set and authored picture EDL
are available, before the dubbed picture lock is rendered. A second deterministic
audit runs against the rendered picture lock before it is promoted to the clean
master. Caption burn-in always happens after this stage.

```text
generated Segments + screenplay/Storyboard semantics
-> real-source ±3s model-decision evidence
-> model-authored explicit picture-and-sound plan
-> pre-assembly technical measurements
-> dubbed picture-lock render
-> final-timeline boundary audit
-> clean master
-> subtitles and captioned master
```

## Decision evidence

Before a plan exists, every boundary receives the predecessor's actual final 3.0
seconds plus the successor's actual first 3.0 seconds with synchronized dubbed
audio. The evidence manifest contains source SHA, provider attempt, exact source
windows, six-second preview, contact sheet, waveform, silence intervals, loudness,
True Peak, dialogue windows, and authored boundary semantics. The model uses the
picture and sound together to choose the smallest necessary modification interval.

Each Segment also receives a read-only full-duration contact sheet, freeze
measurement, full-source audio measurement, and direct source link. This wider
scan exists to expose internal dead holds, repeated action, frozen intervals, or
extra generated material outside the boundary window. It does not authorize a
global edit; the model must name each internal deletion and use
`segment_scope_review` when it falls outside ±3 seconds.

The six-second observation window is not an automatic repair range.
`boundary_local` changes remain inside it. Only an explicit
`segment_scope_review` may authorize a wider range.

## Technical audit evidence

For every cut-like boundary, create exactly the predecessor's final 1.0 second plus
the current Segment's opening 1.0 second from the model-authored EDL source points,
with synchronized ElevenLabs-dubbed audio. At 24 fps the sample contains exactly 48 ordered
frames. For a dissolve or fade, render the explicit planned effect in a two-second
sample centered on that transition instead of substituting a raw splice.

Each boundary directory contains the strict sample, 48 readable frames, frame
manifest, contact sheet, and deterministic color/similarity measurements. The
final-timeline audit creates the same evidence from the
rendered picture lock. These measurements are detection evidence only; they never
approve picture, performance, identity, action, dialogue, or semantic continuity.

## No automatic repair

Boundary QC measures and renders evidence only. It does not classify a boundary as
safe to repair, construct color parameters, select a picture cut or candidate,
change a trim, apply a gain, add silence, or route to another strategy. All such
values come from the model-authored repair plan. Missing values stop the render.

## Artifacts and reversibility

All rebuildable artifacts live below:

```text
TASK_DIR/.pending/finish-postproduction/boundary-qc/
  boundary-qc-manifest.json
  pre-assembly/FROM--TO/
  final-timeline/FROM--TO/
```

The manifest records source paths, EDL semantics, measurements, model-plan
identity, explicit decisions, and final-timeline measurements. Rebuilding from
another validated plan always starts from the same read-only generated Segment
sources; no generated Segment media is mutated.
