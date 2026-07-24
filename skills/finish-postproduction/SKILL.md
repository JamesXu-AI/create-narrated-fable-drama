---
name: finish-postproduction
description: Assemble accepted 16:9 AI narrated drama or fable Seedance Segments, preserve exact dialogue and character-storyteller voice continuity, execute authored transitions, build Storyboard-authoritative subtitles, and render verified clean and captioned masters.
---

# Finish Postproduction

Read the [Narrated Fable Drama Production Standard](../../references/narrated-fable-drama-production-standard.md),
[Human-in-the-Loop Guided Workflow](../../references/human-in-the-loop-guided-workflow.md),
[Finishing Contract](references/finishing-contract.md), and
[Boundary QC Contract](references/boundary-qc-contract.md).

## Entry

Start only after every current Segment has one accepted `video.mp4` and matching
technical `production-record.json`, and the human confirms the assembly plan.
Creative authority remains screenplay, Storyboard, and Segment Prompts.

Probe the actual media. Stop on missing, stale, failed, corrupt, silent, reordered,
or unaccepted coverage.

## Picture and sound

- assemble exactly one accepted clip per Storyboard Generation Segment;
- preserve 16:9 delivery at the screenplay-selected resolution and synchronized
  Seedance-native speech, narration,
  ambience, effects, and restrained music;
- keep an established character storyteller's voice continuous across on-camera
  dialogue, on-camera storytelling, off-camera storytelling, and return to the
  framing scene;
- never revoice, paraphrase, replace native speech, move lip sync, invent a
  transition, or conceal a generation defect;
- execute authored hard cuts, J/L audio handoffs, dissolves, fades, and safe trims;
- run reversible boundary QC before and after assembly;
- apply only bounded technical normalization; do not redesign composition,
  identity, world state, or color intent;
- keep final runtime at or below 240 seconds.

Run:

```bash
python3 skills/finish-postproduction/scripts/finish_postproduction.py \
  --task-dir TASK_DIR
```

## Subtitles

`load_segment_handoff` derives exact line text and Segment-local timing directly
from Storyboard Ordered Shots. ASR is never text authority.

Each line appears once, in order, under the correct speaker. Wrapping may change
whitespace only. A long cue may split into ordered display events only if normalized
concatenation recreates the exact text. Caption timing may extend into adjacent
silence inside the same Segment but may not overlap another line or change audio.

## Deliver

```text
finish-postproduction/final-clean-master.mp4
finish-postproduction/final-captioned-master.mp4
finish-postproduction/final-delivery-manifest.json
finish-postproduction/subtitles/subtitle-cues.json
finish-postproduction/subtitles/master.srt
finish-postproduction/subtitles/master.vtt
```

Both masters must match in duration and synchronized native audio. The captioned
master adds subtitle pixels only. Report `FINAL_MASTER_READY`, present the actual
files and checks, then wait for human acceptance.
