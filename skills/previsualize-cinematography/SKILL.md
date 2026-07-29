---
name: previsualize-cinematography
description: Turn an approved 16:9 AI-narrated fable screenplay into one executable storyboard.md that preserves exact speech, character storytellers, framing and embedded worlds, natural dialogue-to-narration transitions, performance, camera, reference inclusion and omission, native audio, Segment packing, and continuity.
---

# Narrated Fable Drama Previsualization

Follow
[Narrated Fable Drama Production Standard](../../references/narrated-fable-drama-production-standard.md)
and
[Human-in-the-Loop Guided Workflow](../../references/human-in-the-loop-guided-workflow.md).
Use the bundled `video-cinematography` subskill for shot size and camera movement.

## Inputs and output

Read `TASK_DIR/story.md`, the approved screenplay, current production-design plan,
and `workspace/assets/assets.json`. Release exactly:

```text
TASK_DIR/previsualize-cinematography/storyboard.md
```

Do not create Storyboard JSON, compile manifests, narration plans, voice plans,
translation traces, or a second Storyboard representation.

## Authority

Preserve every screenplay event, Shot, exact line, speaker, delivery mode, natural
speech transition, listener reaction, mouth behavior, framing/embedded-world
boundary, character state, sound cue, and ending.

The Storyboard owns final direction, performance, camera, lighting, edit,
Generation Segment packing, reference inclusion/omission, and continuity. It does
not rewrite story meaning.

## Project visual doctrine

Direct the complete Storyboard around three linked priorities:

1. **Few visible characters:** normally isolate one story-active subject or one
   speaker/listener pair. Keep other physically present roles continuous outside
   the crop; never widen just to display the roster.
2. **Explicit eyeline axis:** every interaction Segment states A/B screen sides,
   opposed look directions, the axis line, and the camera side. Preserve them in
   every reverse; cross only through a visible neutral move or motivated
   re-establishment.
3. **Close-up-led coverage:** ECU/CU/MCU must dominate. Medium is secondary.
   MWS/WS/EWS is legal only during the shortest readable portion of a
   story-required entrance, exit, crossing, approach, retreat, transfer between
   marks, or other consequential position change, and must be labeled
   `position-change exception:` before returning tight.

## Speech transition design

Author `## Speech Transition Plan` in `storyboard.md`. Cover every screenplay line
once and state:

- speaker and exact delivery mode;
- physical or audible trigger and phrase/breath boundary;
- listener reaction and every visible mouth state;
- J-cut, L-cut, action cut, reaction cut, or silence handoff;
- voice identity, acoustic perspective, ambience crossfade, and music behavior;
- framing-world/embedded-world visual handoff; and
- the exact Segment and Ordered Shot that execute the transition.

Keep the same character voice across on-camera dialogue, on-camera storytelling,
off-camera storytelling, and return to the framing scene. Do not turn a character
storyteller into a separate announcer.

When the storyteller becomes voice-only over an embedded tale, place a motivated
Generation Segment boundary when necessary. The framing Segment may bind
storyteller/listener images and voice. The embedded Segment omits their positive
images, binds only the storyteller voice when required, and explicitly forbids
their visual appearance. The return Segment restores the framing Location and
character references. References apply to an entire provider request; Shot prose
cannot deactivate a positive image reference.

## Workflow

1. Read all upstream authorities and build one semantic model of the finished film.
2. Compile screenplay Character Scene States before choosing coverage.
3. Direct every spoken line as
   `trigger -> preparation -> exact line -> listener response -> changed state ->
   edit/audio handoff`.
4. Apply the project visual doctrine and keep tight attention dominant; wide Shots
   are only brief, labeled position-change exceptions.
5. Keep one dominant camera move per Shot.
6. Separate framing and embedded Location state chains.
7. Pack Shots into 4–15 second Generation Segments. Split when visible and absent
   reference requirements conflict or a natural speech boundary improves execution.
8. Bind every visible performer and needed voice while omitting positive images for
   visually absent storytellers.
9. Resolve every Segment boundary, audio bridge, ambience handoff, predecessor
   dependency, and return to a prior Location.
10. Validate:

```text
scripts/run_python.sh skills/previsualize-cinematography/scripts/validate_storyboard.py \
  --task-dir TASK_DIR
```

11. Reread the complete Storyboard as director, performer, editor, sound designer,
    continuity supervisor, and Seedance prompt author.

Require the returned full `speech_rate_gate.status=PASS`. It covers every
screenplay Line exactly once using the actual Segment-local speech window.

## Hard rules

- Fixed aspect ratio is `16:9`.
- Exact speech appears once in its owning Ordered Shot.
- Only the active on-camera speaker receives speaking mouth movement.
- Off-camera storytelling never drives an embedded character's mouth.
- Every speaker/mode switch has a playable trigger, phrase boundary, reaction, and
  sound/edit handoff.
- A framing storyteller's voice may cross worlds; their positive image may not.
- Frames use the fewest story-active visible characters; physical presence alone
  never forces full-cast coverage.
- Every interaction Segment declares and preserves one eyeline axis.
- ECU/CU/MCU dominate; every MWS/WS/EWS is a brief labeled
  `position-change exception:` and never decorative coverage.
- Every final Prompt requirement must already be legible in `storyboard.md`.
- Plans are not observations. Review generated video separately.

Stop after releasing and validating `storyboard.md`.
