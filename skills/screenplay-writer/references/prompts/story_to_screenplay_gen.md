# AI-Narrated Fable Screenplay Prompt

## Task

Adapt the complete user-supplied `TASK_DIR/story.md` into one 16:9 dramatic
production screenplay for the known target country. Preserve source participants,
relationships, events, causal logic, climax, consequence, and ending.

The screenplay may use an external narrator, a framing conversation, a character
storyteller, an embedded tale, participant narration, or a deliberate hybrid.
Infer the structure from the Story. Do not add a separate announcer when an existing
character already tells the story.

## Inputs

Read only:

- `TASK_DIR/story.md`;
- the target country already supplied in the conversation;
- the latest conversational visual style, or `3D Healing Animation` by default;
- the latest conversational resolution, or `1080p` by default;
- `screenplay-writer/references/screenplay-segment-contract.md`.

Do not read or create task metadata, a narrator JSON, a voice plan, a Storyboard,
or a Seedance Prompt.

## Authoring decisions

### Preserve the story

Understand the premise, characters, wants, obstacles, beliefs, knowledge flow,
turns, climax, consequence, ending, and fable meaning before writing tables. Do not
output the analysis.

The target country controls delivery language, natural expressions, pronunciation,
and cultural safety. It does not relocate or culturally rewrite the story unless
the source or user requests that change.

### Separate narrative worlds

When the Story begins with a conversation that introduces another story, treat the
framing scene and embedded story as separate Environments and Scene chains. Preserve
the framing characters' positions, props, emotion, and ambience for the return.

A storyteller's voice may cross the visual cut. The storyteller's body does not.
End or split a Scene Unit at a motivated phrase, breath, reaction, or edit point
when the storyteller becomes off-camera.

### Author natural speech transitions

For every spoken line, author:

- exact speaker;
- delivery mode;
- visible or audible gate;
- natural transition from the preceding speech or silence;
- performance delivery;
- exact target-language text.

Valid delivery modes:

```text
on_camera_dialogue
on_camera_storytelling
off_camera_storytelling
external_voiceover
embedded_character_dialogue
```

Use a completed phrase, breath, listener reaction, object look, action result,
J-cut, L-cut, or meaningful silence to change speakers or storytelling mode. Never
cut in the middle of a word, reset the same storyteller into announcer delivery, or
let an unrelated line overlap.

Only the active on-camera speaker receives speaking mouth movement. During
off-camera storytelling, visible characters perform listening, action, or reaction
without matching the storyteller's words.

The Storyboard will later implement these decisions, so write observable behavior:

```text
The grandson finishes, closes his mouth, and looks to Grandfather. Grandfather
meets his gaze, takes one quiet breath, and begins on camera. He completes the
phrase before an L-cut carries the same voice over the embedded tale. The embedded
characters do not move their mouths until their own dialogue begins.
```

### Build executable drama

Each Scene has an objective, obstacle, tactic progression, spatial progression,
important reaction, turn, outcome, and exit impulse. Each Shot has a visible start,
action, reaction, and changed landing.

Apply one non-negotiable visual grammar to the whole screenplay:

1. **Few visible characters.** Keep the active frame to the minimum
   story-required performer set, normally one character or one speaker/listener
   pair. Preserve physically present cropped characters in lifecycle tables; do
   not crowd the Shot to prove they still exist. Do not invent decorative
   bystanders or full-cast reaction rows.
2. **Explicit eyeline axis.** For every interaction, write concrete marks,
   opposing facing/look directions, and addressee gaze so downstream direction can
   lock A/B screen sides and one camera side of the axis. The camera is never the
   addressee.
3. **Close-up-led coverage.** `close_up`, `extreme_close_up`, `reaction`, `insert`,
   and `pov` own speech, listening, recognition, hesitation, decision, emotion,
   breath, hands/paws, clues, wounds, and other story-bearing detail. Use `medium`
   only when a small shared action or two-person relationship cannot read tighter.
4. **One narrow widening exception.** `establishing` or `wide` is legal only for
   the shortest readable beat of a story-required entrance, exit, crossing,
   approach, retreat, handoff between marks, or other consequential position
   change. Prefix `Blocking / Movement` with `position-change exception:` and
   identify the start mark, path, landing mark, and the tight attention target
   that follows.

A Scene opening, new Segment, attractive environment, scale, atmosphere, number of
characters physically present, continuity proof, or desire for visual variety does
not justify a wider view.

### Timing and sound

A Scene Unit is 4–15 seconds. Total runtime is at most 240 seconds. Every exact
line must fit the strict shared speech-rate gate in its own Shot, not merely in the
total Scene Unit. Allow time for
preparation, exact speech, listener reaction, and transition.

Author Seedance-native dialogue, storytelling, breaths, ambience, effects, silence,
and music cues. Put every audio change in the Shot where it occurs. Continuity
Boundary `Audio Handoff` cells own cross-Segment voice bridges, ambience crossfades,
and the return from an embedded tale.

### Character lifecycle

Author the complete Character Scene States lifecycle before release. Separate
physical presence from current frame visibility. Carry a present character through
later Units until an explicit exit. An off-camera storyteller may remain
`absent_from_location` in an embedded world while their voice remains authoritative.

Keep all `Kind=individual` characters plus all `Kind=anonymous_ensemble` closed
roster groups within eight visual role types; one ensemble entity counts once
regardless of its member-type count. Never turn a silent individual into a group or
a speaking individual into a different class merely because of dialogue; `Kind`
alone owns that classification. Preserve source-required and speaking roles first.

### Register story objects, not nouns

Author one `Story Objects` row only for an object whose visual behavior matters to
the drama: it is causal, recurring, state-changing, interaction-sensitive,
detail-bearing, or identity-critical. Do not inventory ordinary furniture,
background decoration, generic one-off handling objects, body parts, weather,
light, or every noun in the prose.

For each registered object, state its physical owner and only the visual-control
triggers that are true:

```text
recurring_identity | detail_view | state_change |
interaction_geometry | distinctive_identity
```

Every trigger names exact screenplay Shots in which positive visual authority is
required. Multi-Segment use requires `recurring_identity`; `state_change` requires
concrete State Facts; `distinctive_identity` requires concrete Identity Facts.
Use `none` for triggers and authority Shots when a story-relevant but generic,
independent one-off object can safely remain Segment-Prompt-only.

The writer never decides whether the resulting authority is a prop image,
Location, character, costume, parent prop, or Prompt. Production design owns that
decision.

## Output

Write exactly:

```text
TASK_DIR/screenplay-writer/screenplay.md
```

Follow `screenplay-segment-contract.md` exactly. Do not emit JSON, YAML, analysis,
or a second screenplay representation.

## Release gate

Release only when:

1. every source event and ending remains true;
2. target country, target language, `16:9`, selected/default resolution,
   selected/default Visual Style, and Seedance-native speech are explicit;
3. every line has one speaker, valid delivery mode, natural transition, exact text,
   listener response, and changed state;
4. the same character storyteller retains one identity and voice across on/off
   camera speech;
5. framing and embedded worlds are spatially and causally distinct;
6. no off-camera narration drives a visible character's mouth;
7. all entrances, exits, gaze, action, sound, duration, and boundaries are
   reachable; and
8. the complete screenplay reads naturally aloud in the target language; and
9. the few-character, eyeline-axis, close-up-led grammar is explicit, tight views
   dominate, and every wide view carries a concrete position-change exception; and
10. every story-relevant visual object has exact physical ownership and
    visual-control facts without inventorying incidental nouns; and
11. the full screenplay speech-rate gate passes every Line before release.
