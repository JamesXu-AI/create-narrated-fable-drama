---
name: virtual-production
description: Compile an approved AI narrated drama or fable Storyboard into exact 16:9 Seedance Segment Prompts and generate native audiovisual clips. Use when authoring, validating, preflighting, or executing Seedance prompts. Creative truth remains only in screenplay.md, storyboard.md, and segment-NNN.md; never create a private narrative JSON plan.
---

# Virtual Production

Read the repository [Narrated Fable Drama Production Standard](../../references/narrated-fable-drama-production-standard.md), the [Storyboard Contract](../previsualize-cinematography/references/storyboard-contract.md), [Free-Form Prompt Guidance](references/natural-language-seedance-prompt.md), and [Seedance Prompting Contract](references/seedance-2-prompt-guide-contract.md).

## Authority

Compile each approved `Generation Segment` in:

```text
TASK_DIR/previsualize-cinematography/storyboard.md
```

to exactly one model-facing file:

```text
TASK_DIR/.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

Do not create a companion creative JSON file. Provider requests, attempt records,
hashes, QC manifests, and delivery manifests may be JSON because they record
runtime facts rather than story meaning.

## Prompt compilation

The Segment Prompt is the complete instruction Seedance sees. It must:

- declare every Storyboard reference token before first use and give each token one
  readable responsibility;
- reproduce the Storyboard operation, ordered internal shots, framing, action,
  blocking, gaze, light, sound, and landing state;
- before Shot 1, copy the Storyboard direction under the exact labels
  `Visible-character economy:`, `Eyeline axis and screen direction:`, and
  `Close-up-led coverage:`; keep the actual frame to the fewest story-active
  subjects and preserve A/B screen sides, opposed looks, axis line, and camera
  side;
- begin each beat `Shot N: <exact Storyboard shot_size>.`; ECU/CU/MCU must dominate,
  and any MWS/WS/EWS beat must repeat the literal
  `position-change exception:` with its start mark, path, landing mark, changed
  relation, and tight return;
- name the exact speaker for each line and put the exact words once in `{braces}`;
- state whether the speaker is visible and lip-synced, visible as a storyteller,
  off camera with the same established voice, an external voiceover, or an
  embedded-scene character;
- carry the Storyboard transition trigger: phrase or breath boundary, listener
  reaction, mouth behavior, J-cut/L-cut or visual handoff, voice continuity, and
  ambience bridge;
- when an on-screen character becomes the off-screen storyteller, explicitly say
  it is the same person and same voice, with no new narrator introduced;
- when that storyteller is absent from an embedded-story image, state the
  positive visible composition and that the established voice continues off
  camera; do not submit a positive storyteller image for that Segment;
- preserve exact 16:9 composition and Seedance-native synchronized dialogue,
  narration, effects, ambience, and restrained music;
- state the screenplay's exact approved Visual Style; resolution is supplied as
  the selected provider parameter and defaults to 1080p only when not overridden;
- forbid generated captions, paraphrased speech, duplicate characters, identity
  drift, decorative bystanders, unauthorized full-cast composition, reversed or
  ambiguous eyelines, unmotivated widening, unexplained
  appearance/disappearance, logos, and watermarks.

Use natural event order, not provider-facing second ranges. Internal timing remains
derived from the Storyboard for subtitle and edit math.

## Validate and execute

Author every Segment Prompt before opening the human loop. Then validate the
complete Prompt set:

```bash
scripts/run_python.sh skills/virtual-production/scripts/validate_segment_scripts.py validate \
  --task-dir TASK_DIR
```

Require `first_full_prompt_gate=PASS` and the full Segment-Prompt
`speech_rate_gate.status=PASS`. Partial validation never opens generation.

Preflight one Segment:

```bash
scripts/run_python.sh skills/virtual-production/scripts/preflight_segment.py \
  --task-dir TASK_DIR --segment segment-NNN
```

Only after that first full gate passes, begin the human-in-the-loop phase and
generate after the human approves that exact Segment Prompt:

```bash
scripts/run_python.sh skills/virtual-production/scripts/generate_segment_videos.py \
  --task-dir TASK_DIR --segments segment-NNN
```

Generate one Segment per approval. After generation, review the complete clip with
sound and its incoming seam. Before the Segment can be accepted or used by a
successor, run the approved-reference voice-identity gate for every dialogue cue,
then explicitly listen for the same timbre, register, age, texture, accent, pace,
and energy. Missing evidence or any voice-identity failure blocks downstream work.
A failed clip gets a new provider attempt; never rewrite the approved story
silently during generation.

## Stop conditions

Stop and return upstream when Storyboard and screenplay disagree, reference media
cannot represent the required visible cast, a narrator transition lacks a concrete
performance bridge, exact speech cannot fit naturally, the prompt would need to
invent story information, the eyeline axis or position-change exception is
ambiguous, close-up dominance would be lost, or a predecessor attempt has not
passed review.
