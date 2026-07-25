---
name: create-narrated-fable-drama
description: Produce a complete 16:9 AI-narrated drama or fable from a user-supplied Story, including a target-country question when missing, screenplay, production design, storyboard, self-contained Seedance prompts, guided one-at-a-time generation, audiovisual review, subtitles, and final masters. Use for external narration, character storytellers, framing conversations, embedded tales, or mixed character-dialogue and narration.
---

# Narrated Fable Drama

Run the complete repository-local production workflow. Treat the conversation as
the director's control surface and follow
[Narrated Fable Drama Production Standard](references/narrated-fable-drama-production-standard.md)
and
[Human-in-the-Loop Guided Workflow](references/human-in-the-loop-guided-workflow.md).

## Repository-only boundary

Use only these repository-local production departments:

- `skills/screenplay-writer/SKILL.md`
- `skills/direct-production-design/SKILL.md`
- `skills/previsualize-cinematography/SKILL.md`
- `skills/virtual-production/SKILL.md`
- `skills/video-review/SKILL.md`
- `skills/finish-postproduction/SKILL.md`

Do not use an external story, image, video, audio, review, or postproduction Skill.
The sole system-Skill exception is `skill-creator`, and only when the user asks to
maintain this repository's Skill files.

All remote media and storage access goes through the shared
`narrated_fable_drama.providers` package.

## Intake

The user supplies the Story in ordinary language. Persist it as the current
`TASK_DIR/story.md` without inventing a task form.
The fable/drama may center humans, animals, fantasy beings, living objects, or a
mixed cast; do not force an animal-only domain.

Before writing the screenplay:

1. Look for the target country in the current conversation.
2. If absent, ask exactly one concise country question and stop; country is
   mandatory and has no default.
3. If already supplied, do not ask again.
4. Use the latest conversational Visual Style, defaulting to
   `3D Healing Animation`.
5. Use the latest conversational resolution, defaulting to `1080p`.
6. Record country, target language, style, resolution, and `16:9` format in
   `screenplay-writer/screenplay.md`.

The Story and country conversation are the complete intake; create no separate
intake form.

## Authority chain

Use exactly this creative chain:

```text
story.md
-> screenplay-writer/screenplay.md
-> direct-production-design/production-design-plan.json + workspace/assets/assets.json
-> previsualize-cinematography/storyboard.md
-> one exact Seedance Prompt per Generation Segment
-> accepted Segment media
-> final masters and subtitles
```

The two production-design JSON files are asset planning and lookup authority only.
They may describe what a reusable image or voice asset is. They may not own
storytelling mode, speaker changes, narration transitions, character presence,
blocking, camera, edit, or dialogue.

Do not create companion creative ledgers for screenplay, Storyboard, narration,
voice timing, Segment direction, compilation, or translation. Any runtime JSON is
technical state only.

## Project-wide visual doctrine

Carry this unchanged through screenplay, Storyboard, every Seedance Prompt, video
review, and final edit:

- keep each frame to the fewest story-active characters, normally one subject or
  one speaker/listener pair; never add decorative bystanders or default to a
  full-cast composition;
- declare the interaction eyeline axis, A/B screen sides and look directions, and
  camera side before coverage; preserve them across reverses;
- make ECU/CU/MCU the dominant grammar for speech, listening, recognition,
  decision, emotion, and story-bearing detail;
- widen only for the shortest readable part of a story-required entrance, exit,
  crossing, approach, retreat, handoff between marks, or other consequential
  position change, then cut directly back to tight attention; and
- never widen merely to establish a Scene/Segment, show scenery or scale, prove
  physical presence, include everyone, or add visual variety.

## Production order

1. Require `story.md` and known target country.
2. Execute `screenplay-writer`. Require a valid complete `screenplay.md` and a
   full speech-rate PASS with exact speech, delivery modes, natural transitions,
   and separate framing/embedded story worlds.
3. Run the role/asset scope gate, then execute `direct-production-design`.
   Before generating any visual, require its asset-library discovery gate to
   inspect repository-root `workspace/assets/assets.json` and
   `workspace/assets/`; a missing catalog ID never proves that media is absent.
4. Execute `previsualize-cinematography`. Release only `storyboard.md` and require
   its complete speech-window rate and close-up/eyeline visual-grammar gates to
   pass.
5. Execute `virtual-production`. Author every first-pass `segment-NNN.md` directly
   from the Storyboard, then require the complete Prompt-set and speech-rate gate
   to pass, including copied visible-character economy, eyeline axis, per-Shot
   size, close-up dominance, and every position-change exception; derive runtime
   transport in memory.
6. Begin the Segment human loop only now. Before every Seedance call, present the
   compact plan and wait for confirmation.
   One confirmation authorizes one attempt for one Segment.
7. After every attempt, inspect the complete video with sound, report the result,
   including visible-character economy, eyeline-axis continuity, close-up
   dominance, and every position-change widening exception, then wait for the
   user's accept/revise/retry/stop decision.
8. After every Segment is individually accepted, present the assembly plan and
   wait for final-render confirmation.
9. Execute `finish-postproduction` and wait for final human acceptance.

## Speech and narrator authority

Do not assume the narrator is an invisible announcer. A grandfather, parent,
teacher, protagonist, or other on-screen character may begin in dialogue and
continue as the same off-screen storyteller.

Require the screenplay, Storyboard, and final Prompt to state:

- exact speaker and exact words;
- on-camera dialogue, on-camera storytelling, off-camera storytelling, external
  voiceover, or embedded-character dialogue;
- physical trigger, preparation, delivery, listener reaction, mouth state, changed
  state, and edit handoff;
- whether a J-cut, L-cut, completed phrase, breath, action result, or silence makes
  the switch natural;
- whether the speaker is visually present, cropped but present, or absent; and
- which image and voice references are included or deliberately omitted.

When a storyteller becomes voice-only over an embedded tale, do not bind that
character's positive image reference to the embedded Segment. Bind the approved
voice reference, state that the same voice continues, and explicitly forbid the
storyteller's body, portrait, reflection, silhouette, or duplicate.

## Human gates

Before the complete Segment Prompt gate, pause only for missing mandatory country,
a material creative choice that cannot be inferred, or destructive overwrite.
After that gate, pause:

- before each video generation or destructive overwrite;
- after each generated video;
- when a material story commitment cannot be inferred safely; and
- before final assembly.

Never retry automatically.

## Completion

Technical completion requires valid clean and captioned masters, SRT, VTT, and a
delivery manifest. Actual completion requires human acceptance.
