---
name: finish-postproduction
description: Assemble current forest-animal audiovisual Seedance Segments, preserve animal identity, forest-world picture and ambience continuity, synchronized dialogue, foley, and native background music, execute authored transitions, create exact subtitles, and render verified clean and captioned masters.
---

# Finish Postproduction · 剪辑、声音与后期

## Skill invocation boundary

While executing a production task under this Skill, never invoke, load, delegate
to, or depend on any Skill outside this repository. Repository-local department
Skills explicitly named by this project remain internal and may collaborate under
their declared ownership boundaries. The sole system-Skill exception is
`skill-creator`, and only when the user explicitly asks to create or maintain this
project's own Skill files; never use it to perform story or media-production work.

Own picture assembly, synchronized native-sound finish, exact
subtitles, clean/captioned masters, and deterministic delivery integrity. This is
the only postproduction department.

Read and enforce the
[Forest Animal Education Production Standard](../references/forest-animal-education-production-standard.md).
Also follow the
[Human-in-the-Loop Guided Workflow](../references/human-in-the-loop-guided-workflow.md).
Do not hide animal-identity or forest-layout, landmark, vegetation, weather, light,
palette, or ambience discontinuity with an edit, grade, crop, transition, or mix.

## Entry condition

Before assembly, scan the ordered current Segment plans and require exactly one
complete audiovisual output plus one compact `production-record.json` for every
Segment. Do not require or create a separate generation-state or summary file.
Require each record to match the current Segment Prompt, in-memory execution plan,
operation, provider attempt, and current resolved media bindings. Probe the actual
media and stop on missing, stale, failed, corrupt, silent, or reordered coverage.
Independent review is callable for diagnosis but never a required approval file.
Also require that the conversation contains the human's acceptance of every current
clip and explicit confirmation of the compact assembly plan. Do not encode those
decisions into another JSON or approval artifact.

## Required authorities

Read:

1. `task.json` and its format, language, voice, and dialogue source settings;
2. screenplay, its ordered Segment plans, audio timeline, and exact dialogue;
3. the sole native `previsualize-cinematography/storyboard.md` authority;
4. the current private Segment plans, read through the read-only
   `load_segment_handoff` timing/safe-cut view—never companion ledgers or reports;
5. all current Segment Prompts, in-memory execution plans, videos, and compact
   production records;
6. production-design assets.

Read [finishing-contract.md](references/finishing-contract.md),
[boundary-qc-contract.md](references/boundary-qc-contract.md),
[audio-timeline-contract.md](references/audio-timeline-contract.md), and
[seedaudio-score-contract.md](references/seedaudio-score-contract.md), and
[subtitle-style.json](assets/subtitle-style.json). Preserve the current
[Soft & Cute 3D Healing Animation Visual Standard](../direct-production-design/references/soft-cute-3d-healing-visual-standard.md).

## Audio policy

Use this fixed source separation:

```text
voice_audio_source: speaker_reference_audio
dialogue_source: seedance
native_background_audio_source: seedance_ambience_foley_and_music
seedance_background_music: true
background_music_source: seedance_native
generate_audio: true
```

Every dialogue character has one fixed, unique speaker-reference audio identity.
Seedance uses it to generate the Segment's actual synchronized words and native
dialogue, breath, reaction, room tone, ambience, foley, effects, diegetic sound,
and background music. Every submitted Segment Prompt carries the intended music in
official `(music cue)` notation.
Postproduction preserves the native track; it never substitutes the reference WAV,
shares one reference across characters, revoices a line, disables native ambience,
or replaces missing audio with silence.

## Isolated SeedAudio experiment

Do not read `music-production.json`, call SeedAudio, create a score track, select a
scored master, or promote any SeedAudio artifact while running
`finish_postproduction.py`. The main workflow always delivers native synchronized
sound with `background_music_source: seedance_native`.

Retain [music-production.json](assets/music-production.json),
`generate_seedaudio_score.py`, `evaluate_seedaudio_score_only.py`, and
[seedaudio-score-contract.md](references/seedaudio-score-contract.md) only for a
future manually requested experiment. Run them solely when the user explicitly asks
for another SeedAudio experiment. Keep every result under `.pending`, label it
experimental, and never use it as a main-flow input or final master.
Because the default source already contains Seedance music, a SeedAudio experiment
requires an explicitly requested, separately regenerated music-free source set; it
cannot remove or replace music in the default accepted Segments.
Each experimental provider call also requires the compact before/after confirmation
and never retries automatically.

## Picture and sound finish

- Assemble exactly one accepted video per Segment in screenplay order.
- Before picture-lock render, run `Boundary QC & Repair` on every external seam.
  Create the strict two-second audiovisual evidence, all 48 ordered frames at
  24 fps, deterministic technical measurements, and a reversible manifest. Apply
  only configured safe luma/chroma corrections to high-confidence matched cuts;
  never overwrite generated Segment media.
- Render Soft/Matched/Strong previews for each planned correction. A large required
  correction, identity/action/geometry issue, or unresolved final-timeline residual
  must stop delivery for visual review or upstream regeneration.
- Derive and execute the screenplay transition boundary contract exactly: motivated cuts remain
  hard cuts; dissolve/fade use their authored overlap and matching native-audio
  acrossfade; animation/effects transitions must already be completed clip-locally.
- At every incoming `video_extension` seam, verify the predecessor's editable hold
  and both sides' dialogue windows, then trim exactly six source frames from the
  predecessor tail and one source frame from the continuation head. Record the
  source points in the EDL and run pre/final boundary QC against those trimmed
  points. Stop instead of trimming authored action or dialogue.
- Do not invent a transition, reorder, repeat, or otherwise trim away authored
  action/dialogue.
- Normalize canvas, SAR, frame rate, codec, and color metadata without recomposing
  shots or redesigning assets.
- Keep every Segment native audio track sample-aligned with its picture. Never move
  dialogue or lip sync across a Segment boundary.
- Preserve the accepted synchronized native sound without adding a music layer.
- Apply a short final audio fade to the terminal Segment so the delivered stream
  cannot end on a click; keep it sample-aligned with the terminal picture.
- Keep the final runtime at or below 240 seconds.
- After picture-lock render, extract and audit every seam again from the final
  timeline. Subtitle burn-in and final promotion require
  `final_timeline_status: technical_audit_complete`.

Run:

```text
python3 finish-postproduction/scripts/finish_postproduction.py \
  --task-dir TASK_DIR
```

Rebuildable work lives only under
`TASK_DIR/.pending/finish-postproduction/`. Deliverables live under:

```text
finish-postproduction/final-clean-master.mp4
finish-postproduction/final-captioned-master.mp4
finish-postproduction/final-delivery-manifest.json
finish-postproduction/subtitles/subtitle-cues.json
finish-postproduction/subtitles/master.srt
finish-postproduction/subtitles/master.vtt
```

Boundary evidence and repair records live under:

```text
.pending/finish-postproduction/boundary-qc/boundary-qc-manifest.json
.pending/finish-postproduction/boundary-qc/pre-assembly/FROM--TO/
.pending/finish-postproduction/boundary-qc/final-timeline/FROM--TO/
```

## Subtitle authority

Build exact captions from the private Segment-plan dialogue cues exposed by
`load_segment_handoff` and actual picture-EDL offsets. Do not transcribe,
paraphrase, translate, omit, duplicate, or
reorder authority text. Whitespace wrapping is the only permitted textual change.
When one authored dialogue cue exceeds the current per-screen line limit, split it
into the fewest ordered caption events that fit, preferring sentence boundaries and
allocating the original cue interval by exact word/character share. Preserve the
source cue identity and prove that normalized concatenation reconstructs the exact
authority text; every split event must independently pass line-count, minimum-time,
and reading-speed limits.
When an authored speech window is shorter than the minimum caption display time,
extend only the caption event—prefer its following silence, then its preceding
silence—while remaining inside the owning Segment and never overlapping an adjacent
caption. Record both authored speech timing and final caption timing. If no safe
interval exists, return the timing defect upstream.
Interpret font size, outline, and bottom margin as percentages of the delivered
frame. Convert those values into the subtitle renderer's native script-resolution
coordinates before burn-in, then visually inspect at least one active-caption frame;
never allow renderer-default scaling to enlarge captions a second time.
For dissolve/fade boundaries, derive each Segment offset from the EDL's authored
overlap; never force overlapping picture events into a hard-cut-contiguous model.
If exact text does not fit its authored interval, stop and return the timing defect
to `virtual-production` for direct local Prompt/plan revision.

## Delivery check

The final delivery manifest describes all masters, subtitle files, EDL/audio timeline,
duration, resolution, streams, native audio declarations, and
`background_music_source: seedance_native`. After checking the actual files, this department
emits:

```text
FINAL_MASTER_READY
```

Present the masters, verification result, and recommended next action in the
conversation, then pause for human acceptance or revision. Do not automatically
re-render from a review problem; propose the smallest correction and wait for
direction.

Any module may ask `seedance-video-review` to watch either complete master when a
visual or sound problem needs independent diagnosis. If it finds a problem, send the
smallest correction to the owning module and rebuild only affected output. No review
file or approval record is created.

## Hard boundaries

- Do not change story, dialogue, design, performance, Storyboard, or Segment Scripts.
- Do not use postproduction to hide generation defects.
- Do not treat boundary metrics, similarity, or a successful repair render as a
  semantic picture approval. They are technical detection and routing evidence.
- Do not connect SeedAudio experiment code or artifacts to the main finishing flow.
- Do not create approval records for individual videos or the final film.
- Always deliver a clean master and external SRT/VTT in addition to the captioned
  master.
