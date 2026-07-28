---
name: create-narrated-fable-drama
description: Produce a complete Arabic 16:9 AI-narrated drama or fable from a user-supplied Story, using mandatory Seedance native audio and mouth performance, mandatory generated-speech replacement with exact ElevenLabs Arabic, guided one-at-a-time generation, audiovisual review, subtitles, and final masters.
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
6. Record country, fixed target language `Arabic`, style, resolution, and `16:9` format in
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
-> virtual-production independent internal Prompt audit PASS
-> Seedance picture, mouth performance, and mandatory native audio
-> mandatory removal of every generated character voice
-> Seedance-native dialogue-cut repair plus immediately mixed exact ElevenLabs Arabic
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
   size, close-up dominance, exact-Arabic mouth performance, one explicit
   Seedance audio mode, mandatory generated-speech replacement, and every
   position-change exception. Then run virtual-production's separate internal
   hard gate. Require every exact Prompt to pass the three-section, eight-element,
   readable-reference, single-camera-family, quality/anti-distortion,
   Storyboard-authority, and Arabic audio-ownership checks. A changed Prompt,
   Storyboard, reference, or audit ruleset invalidates the PASS record; derive
   runtime transport in memory only from that unchanged audited Prompt.
6. Begin the Segment human loop only now. Before every Seedance call, present the
   compact plan and wait for confirmation.
   One confirmation authorizes one attempt for one Segment.
7. After every successful Seedance attempt, publish the immutable provider result
   plus its last frame as `PICTURE_GENERATED`, start the current Segment's audio
   build immediately, and treat picture and audio as separate review tracks.
   Directly review the provider picture for continuity, visible-character economy,
   eyeline-axis continuity, close-up dominance, and every position-change
   widening exception. A current-attempt picture review returning `NO_ISSUES`
   releases that picture as predecessor evidence: after a separate fresh human
   confirmation, another Segment process may submit the reviewed successor while
   the current Segment's audio build continues.

   The audio track must preserve the untouched provider original as
   `seedance-source.mp4`, cut generated character speech with bounded edge
   padding, verify the cleaned background, hard-mute the complete Seedance mix
   inside dialogue intervals, preserve Seedance-native ambience and action sound
   unchanged outside them, derive a conservative masculine pronunciation-only
   tashkeel rendering from immutable Storyboard text, and insert only the
   resulting exact ElevenLabs Arabic dialogue fitted to the detected
   mouth-performance window. Use Multilingual v2 with the approved neutral urban
   Riyadh Saudi voice asset; ElevenLabs may never generate
   ambience, action sound, Foley, animal sounds, music, or any other non-dialogue
   audio. Do not defer or batch this audio work. Only after the audio and
   voice-identity gates pass may the current Segment become `GENERATED`, undergo
   complete audiovisual review, and wait for the user's
   accept/revise/retry/stop decision. An audio-only failure blocks acceptance and
   postproduction, but does not invalidate the reviewed picture or stop an already
   authorized successor Seedance job.
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
- which image references are included or deliberately omitted, and which
  ElevenLabs voice ID owns each speaking entity.

When a storyteller becomes voice-only over an embedded tale, do not bind that
character's positive image or audio reference to Seedance. Keep the established
ElevenLabs voice ID for later dubbing, state that the same voice continues, and
explicitly forbid the storyteller's body, portrait, reflection, silhouette, or
duplicate.

## Human gates

Before the complete Segment Prompt gate, pause only for missing mandatory country,
a material creative choice that cannot be inferred, or destructive overwrite.
After that gate, pause:

- before each Seedance generation or destructive overwrite;
- after picture review when requesting the fresh authorization for a successor
  Seedance attempt;
- after the current Segment's complete audiovisual review for its
  accept/revise/retry/stop decision;
- when a material story commitment cannot be inferred safely; and
- before final assembly.

Never retry automatically.

## Completion

Technical completion requires valid clean and captioned masters, SRT, VTT, and a
delivery manifest. Actual completion requires human acceptance.
