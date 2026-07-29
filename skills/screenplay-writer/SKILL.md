---
name: screenplay-writer
description: Adapt one user-supplied Story into a 16:9 AI-narrated drama or fable screenplay with a known target country, exact dialogue, character storytellers, framing and embedded story worlds, natural dialogue-to-narration transitions, playable action, native sound, timing, and continuity.
---

# Narrated Fable Drama Screenplay Writer

Use only repository-local references, scripts, providers, and ordinary tools.
Follow
[Narrated Fable Drama Production Standard](../../references/narrated-fable-drama-production-standard.md)
and
[Human-in-the-Loop Guided Workflow](../../references/human-in-the-loop-guided-workflow.md).

## Input and output

Read:

```text
TASK_DIR/story.md
```

The user supplies the Story. The target country is mandatory and must already be
known from the conversation; if it is missing, return to the top-level orchestrator
to ask once and do not author the screenplay.
The Story and known country are the complete intake; create no separate intake
form.

Write exactly:

```text
TASK_DIR/screenplay-writer/screenplay.md
```

Read
[story-to-screenplay prompt](references/prompts/story_to_screenplay_gen.md) and
[production-script contract](references/screenplay-segment-contract.md) completely
before authoring.

## Ownership

Own story-faithful dramatic adaptation, exact speech, delivery mode, natural speech
transition, character objectives, visible action and reaction, staging, gaze,
framing/embedded-world separation, sound events, timing, continuity, and the
story-object facts that may require downstream visual authority.

Do not choose asset IDs, appearance design, detailed cinematography, provider
parameters, Storyboard implementation, or Seedance Prompt wording.

## Visual writing doctrine

Write for few-character, explicit-axis, close-up-led execution:

- retain every story-required character, but keep each Shot's active visible
  performers to the minimum needed for its dramatic change—normally one character
  or one speaker/listener pair;
- do not invent decorative bystanders, gather the cast into a frontal master, or
  mark every physically present character `visible_every_shot`; a crop is not an
  exit;
- for every interaction, make `Gaze / Addressee` and `Blocking / Movement`
  sufficient for cinematography to lock A/B screen sides, opposed look directions,
  marks, and a stable eyeline axis;
- default `Scale / View` to `close_up`, `extreme_close_up`, `reaction`, `insert`,
  or `pov`; use `medium` only for an indispensable small shared action; and
- use `establishing` or `wide` only for the shortest beat that must show a
  story-required entrance, exit, crossing, approach, retreat, transfer between
  marks, or other consequential position change. Prefix its `Blocking / Movement`
  with `position-change exception:` and return the next dramatic attention to a
  tight view.

## Storyteller rules

Do not assume an external narrator. A character may speak on camera and continue as
the same off-camera storyteller. Give that character one Entity ID and one
storytelling authority.

Every spoken line uses:

```text
L-NNN; speaker=<entity>; mode=<delivery-mode>; gate=<visible/audible trigger>;
transition=<breath/reaction/J-cut/L-cut/action/silence handoff>;
delivery=<performance>; text="<exact target-language words>"
```

Valid modes:

```text
on_camera_dialogue
on_camera_storytelling
off_camera_storytelling
external_voiceover
embedded_character_dialogue
```

Every transition must be playable and natural. Finish a phrase before a visual
world change unless the authored J/L cut deliberately carries the same voice.
Give the listener a readable reaction. State whose mouth is active and keep every
other visible character in listening or reaction behavior.

Split Scene Units at a motivated boundary when one character changes between
on-camera and off-camera storytelling. This prevents one provider request from
needing the same positive character image both present and absent.

## Workflow

1. Read the complete Story and determine premise, relationships, knowledge flow,
   causal turns, climax, consequence, ending, and implied fable meaning.
2. Preserve the source. Improve only performance, pacing, legibility, and
   filmability unless the user authorizes a rewrite.
3. Record target country, target language, `16:9`, conversational Visual Style
   (default `3D Healing Animation`), conversational resolution (default `1080p`),
   and `seedance_native` speech in Production Information.
4. Define every character once. Use `storyteller` or `both` only for a character
   who truly owns narration.
5. Separate framing and embedded story locations and population.
6. Author Scene-wide character lifecycles before Shot rows. A crop is not an exit.
7. Write only Shots that create or reveal a dramatic change, using the
   few-character, explicit-axis, close-up-led doctrine above.
8. Give every spoken line a trigger, delivery mode, natural transition, exact text,
   listener response, and changed state.
9. Use Continuity Boundary `Audio Handoff` cells to carry exact J/L cuts, breaths,
   ambience crossfades, and returns between narrative layers.
10. Register only story-relevant objects that are causal, recurring,
    state-changing, interaction-sensitive, detail-bearing, or identity-critical.
    Record their physical owner, exact visual-control triggers, authority Shots,
    state facts, and identity facts without choosing downstream asset IDs.
11. Keep project-wide visual role types at eight or fewer.
12. Run:

```text
scripts/run_python.sh skills/screenplay-writer/scripts/build_screenplay.py build --task-dir TASK_DIR
scripts/run_python.sh skills/screenplay-writer/scripts/build_screenplay.py check --task-dir TASK_DIR
scripts/run_python.sh skills/screenplay-writer/scripts/character_performance_map.py role-asset-scope \
  --task-dir TASK_DIR
```

13. Require `speech_rate_gate.status=PASS` for the complete screenplay. A fast
    line must be shortened or given more Shot time before downstream work.
14. Reread the screenplay as one film. Validator success does not prove that a
    speech transition feels natural.

Release only after all checks pass and the screenplay has no filler, speaker
confusion, voice reset, unmotivated overlap, narration mouth error, or unexplained
world-state reset; no wide Shot lacks a position-change exception and tight
attention remains the dominant coverage.
