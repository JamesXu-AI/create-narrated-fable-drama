# Finishing Contract

## Current picture and sound authority

`screenplay-writer/screenplay.md` defines story order and authored editorial
transitions. The local `storyboard.md` is the sole Storyboard authority; no compile
manifest or `storyboard.data.json` exists. Private Segment plans, exact Prompt
Scripts, in-memory execution plans, and generated media live below
`.pending/virtual-production/`. `load_segment_handoff` exposes a read-only view of
dialogue timing and safe-cut state without generating companion ledgers.

Postproduction scans the current private plans and requires one generated Segment
directory for each, containing only `video.mp4`, `last-frame.png`, and a compact
`production-record.json`. The record binds the output to its exact local Segment
Prompt, in-memory execution-plan hash, provider attempt, resolved media, and source
URLs. Do not create or require a separate generation-state or summary file.
Postproduction executes
the authored edit and may normalize technical delivery, but cannot recompose a
Shot, rewrite dialogue, or synthesize silence for missing native audio.

`.pending/finish-postproduction/post-production/picture-audio-edl.json` is the
final-timeline offset authority. `.pending/finish-postproduction/audio-timeline.json`
records one synchronized native event per Segment with Seedance dialogue, foley,
ambience, effects, and background music. The main flow never reads a separate music
plan or adds a SeedAudio track; Seedance-native music remains inside the accepted
synchronized source track.

Before the picture lock is rendered, every EDL boundary passes through
[boundary-qc-contract.md](boundary-qc-contract.md). High-confidence matched cuts
may receive only a bounded, decaying luma/chroma correction. Generated Segment
files remain read-only. The rendered picture lock is then scanned again at every
EDL boundary before clean-master promotion. The authoritative technical evidence
and reversible correction record is:

```text
.pending/finish-postproduction/boundary-qc/boundary-qc-manifest.json
```

Boundary measurements never approve performance, identity, action, dialogue, or
semantic continuity. Unsafe corrections and unresolved residuals stop delivery for
visual review or upstream regeneration.

When the incoming Segment is a `video_extension`, the EDL first verifies
dialogue-free safe handles and records exact source trims: predecessor tail six
frames, continuation head one frame. Boundary evidence uses those trimmed source
points. The terminal native-audio event carries a short fade-out to prevent an end
click.

## Subtitle authority

```text
private Segment-plan exact dialogue and local timing via `load_segment_handoff`
-> picture-audio-edl.json Segment offset
-> subtitle-cues.json + master.srt + master.vtt
-> final-captioned-master.mp4
```

ASR is never subtitle authority. Every private-plan dialogue cue appears once in
order. Cue times stay inside the owning Segment and Segment offsets come from the
actual EDL. Long cues may split only for layout/readability while normalized
concatenation remains exact Unicode authority text. Caption display may extend only
into adjacent silence inside the same Segment and never changes audio.

## Delivery

All rebuildable work stays under `.pending/finish-postproduction/`. Release the
clean master, captioned master, subtitle cues, SRT, VTT, and final delivery manifest
under `finish-postproduction/`. Both masters must have equal timing and synchronized
native audio; the captioned master adds only subtitle pixels. Both declare
`background_music_source: seedance_native`. Their delivery manifest also binds a completed
Boundary QC manifest whose generated sources remained read-only. Final state is
`FINAL_MASTER_READY`.
