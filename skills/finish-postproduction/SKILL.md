---
name: finish-postproduction
description: Act as the editing and restoration master for accepted 16:9 Seedance media after mandatory generated-speech replacement and exact ElevenLabs Arabic mixing; perform the unified final edit, preserve dialogue/mouth synchronization, compile subtitles, and render verified masters.
---

# Finish Postproduction

Read the [Narrated Fable Drama Production Standard](../../references/narrated-fable-drama-production-standard.md),
[Human-in-the-Loop Guided Workflow](../../references/human-in-the-loop-guided-workflow.md),
[Editor and Restoration Master Decision Prompt](references/editor-restoration-master-prompt.md),
[Model-Authored Repair Plan Contract](references/repair-plan-contract.md),
[Finishing Contract](references/finishing-contract.md), and
[Boundary QC Contract](references/boundary-qc-contract.md).

Adopt the Editor and Restoration Master role before inspecting or rendering media.
The model owns every actual edit and repair decision. Treat Python and other scripts
only as measurement, evidence, validation, and exact rendering tools. Never accept
a script default, threshold, automatic routing result, or fallback as a creative
repair decision.

## Entry

Start only after every current Segment has one accepted `video.mp4` and matching
technical `production-record.json`, and the human confirms the assembly plan.
Creative authority remains screenplay, Storyboard, and Segment Prompts.

Probe the actual media before deciding the assembly. Generate boundary picture and
sound evidence from the outgoing final 3 seconds and incoming first 3 seconds.
Choose the smallest necessary modification interval inside that evidence window,
author it in an explicit repair plan, render short candidates when the best choice
is not visually or sonically certain, and inspect those candidates before
rendering the full master. Escalate beyond the boundary window only through an
explicit model-authored Segment-scope decision. Stop on missing, stale, failed,
corrupt, unexplained-silent, reordered, or unaccepted coverage.

Generate the real-media evidence before writing any edit:

```bash
python3 skills/finish-postproduction/scripts/inspect_finish_media.py \
  --task-dir TASK_DIR
```

Read the emitted manifest and every picture-and-sound artifact. Author
`.pending/finish-postproduction/llm-repair-plan.json`; then validate that complete
plan against the same evidence and source media:

```bash
python3 skills/finish-postproduction/scripts/validate_repair_plan.py \
  --task-dir TASK_DIR \
  --evidence-manifest TASK_DIR/.pending/finish-postproduction/llm-evidence/evidence-manifest.json \
  --repair-plan TASK_DIR/.pending/finish-postproduction/llm-repair-plan.json
```

When a picture cut, action phase, dissolve, color repair, or audio handoff is not
certain, author separate candidate plans and render each requested seam:

```bash
python3 skills/finish-postproduction/scripts/render_repair_candidate.py \
  --task-dir TASK_DIR \
  --evidence-manifest EVIDENCE_MANIFEST \
  --repair-plan CANDIDATE_PLAN \
  --boundary segment-NNN--segment-NNN \
  --output CANDIDATE.mp4
```

The model inspects and selects candidates. The tool never ranks them.

## Picture and sound

- assemble exactly one accepted clip per Storyboard Generation Segment;
- preserve 16:9 delivery at the screenplay-selected resolution and synchronized
  ElevenLabs Arabic dialogue plus Seedance-native full-duration ambience and
  authored action effects on the accepted picture;
- keep an established character storyteller's voice continuous across on-camera
  dialogue, on-camera storytelling, off-camera storytelling, and return to the
  framing scene;
- never revoice, paraphrase, replace ElevenLabs speech, move lip sync, invent a
  transition, admit Seedance character speech, or conceal a generation defect;
  validated Seedance non-dialogue audio may remain only outside recorded
  replacement intervals;
- decide trim points, picture transitions, audio handoffs, ambience bridges,
  loudness adjustments, and bounded visual repairs from actual media evidence;
- preserve the authored few-character, explicit-eyeline-axis, close-up-led
  grammar; retain the complete required movement inside a
  `position-change exception:` but trim any evidence-proven dead wide hold after
  the landing and prefer existing tight reaction/performance coverage;
- never manufacture a close-up with an unapproved digital crop or hide crowded
  staging, an axis reversal, or an unearned wide view with a dissolve; return an
  unfixable coverage defect for regeneration;
- delete model-identified internal dead holds, repeated action, frozen intervals,
  or extra generated picture through explicit retained source ranges, while
  separately deciding the synchronized audio splice;
- keep picture and audio transition decisions independent;
- require every execution value explicitly; never let code supply semantic
  durations, handles, gains, fades, repair strengths, or fallback operations;
- execute authored hard cuts, J/L audio handoffs, dissolves, fades, and safe trims;
- run reversible boundary QC before and after assembly;
- apply only bounded technical normalization; do not redesign composition,
  identity, world state, or color intent;
- keep final runtime at or below 240 seconds.

Run:

```bash
python3 skills/finish-postproduction/scripts/finish_postproduction.py \
  --task-dir TASK_DIR \
  --evidence-manifest TASK_DIR/.pending/finish-postproduction/llm-evidence/evidence-manifest.json \
  --repair-plan TASK_DIR/.pending/finish-postproduction/llm-repair-plan.json
```

## Subtitles

`load_segment_handoff` derives exact line text and speaker order directly from
Storyboard Ordered Shots. The final clean master's ElevenLabs-dubbed audio is the mandatory
timing source: align every authoritative line to measured word timestamps after
all picture and audio edits are complete. ASR is timing evidence only and is never
text authority.

Each line appears once, in order, under the correct speaker. Wrapping may change
whitespace only. A long cue may split into ordered display events only if normalized
concatenation recreates the exact text. Caption timing may extend into adjacent
silence inside the same Segment but may not overlap another line or change audio.
Missing final audio, an unavailable alignment model, low token coverage, or an
alignment outside the owning Segment blocks delivery. Never fall back to
Storyboard speech windows or editorial timing overrides.

This branch's subtitle gate is Arabic-only. It requires
`Target Language=Arabic`, forces multilingual ASR with `language=ar`, rejects
English-only `.en` models, rejects Latin letters in authoritative or observed
speech, and records `language_code=ar`. Arabic line length and reading speed use
the Arabic-specific style keys; legacy Latin/English subtitle limits are not
valid gate inputs.

Hard-subtitle rendering uses the SHA-256-pinned
`assets/fonts/NotoSansArabic-Variable.ttf` file under this Skill and selects its
named `SemiBold` instance. Never resolve or silently substitute a system font.
Require the declared Pillow dependency and verify RAQM/FriBiDi shaping support
before rendering; missing shaping support or a missing/mismatched bundled font is
a delivery blocker.

## Deliver

```text
finish-postproduction/final-clean-master.mp4
finish-postproduction/final-captioned-master.mp4
finish-postproduction/final-delivery-manifest.json
finish-postproduction/subtitles/subtitle-cues.json
finish-postproduction/subtitles/master.srt
finish-postproduction/subtitles/master.vtt
```

Both masters must match in duration and synchronized dubbed audio. The captioned
master adds subtitle pixels only. Report `FINAL_MASTER_READY`, present the actual
files and checks, then wait for human acceptance.
