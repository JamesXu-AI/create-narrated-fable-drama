# Narrated Fable Drama Production Standard

## Mission

Create 16:9 narrated dramatic shorts and fables from one user-supplied `story.md`.
The story may use a framing conversation, an embedded tale, an external narrator,
or a character who becomes the storyteller. Preserve the supplied premise,
relationships, causal turns, climax, consequence, and ending unless the user asks
for a rewrite.

The user supplies the Story. If the target country is not already known from the
conversation or the current screenplay, ask for it once before screenplay
authorship. Do not ask the user to create or edit task metadata.

## Creative authority

Creative authority exists only in:

```text
story.md
-> screenplay-writer/screenplay.md
-> previsualize-cinematography/storyboard.md
-> .pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

Do not create a task JSON, narration JSON, voice plan, screenplay companion,
Storyboard companion, translation trace, prompt manifest, or private creative plan.
Runtime JSON may store only asset lookup, provider attempts, generated-media
records, technical QC, and final delivery facts. Runtime data never adds or changes
story, performance, speech, camera, or continuity authority.

## Project format

- Required aspect ratio: `16:9`.
- Visual style comes from conversation and defaults to `3D Healing Animation`.
- Delivery resolution comes from conversation and defaults to `1080p`; supported
  choices are `480p`, `720p`, `1080p`, and `4k`.
- Dialogue, storytelling, narration, breaths, reactions, ambience, effects, and
  authored music are generated as synchronized Seedance-native audio.
- Generated subtitles and on-screen transcription are forbidden. Captions belong
  to postproduction.
- Postproduction captions copy exact text and speaker order from the Storyboard,
  but derive their final appearance times from word-level alignment against the
  completed clean master's native audio. Missing or low-coverage alignment blocks
  delivery; nominal Storyboard speech windows are never a release fallback.
- Total runtime must not exceed 240 seconds.

The target country is mandatory. If it is missing from the conversation, stop and
ask for it before screenplay authoring. Style and resolution use their defaults
when absent.

## Project-wide visual doctrine

Apply this doctrine from screenplay through final review:

```text
few visible characters -> explicit eyeline axis -> close-up-led coverage ->
brief widening only for a story-required position change -> immediate return to
the tight dramatic subject
```

- Keep the visible composition economical. A Shot normally isolates one
  story-active character or a two-character speaker/listener relationship. Do not
  add decorative characters, gather the full cast, or keep every physically
  present role in frame merely to prove continuity. Cropped roles remain
  physically present and are carried by screen direction, gaze, foreground edge,
  off-screen sound, or a later reaction.
- Before any interaction coverage, state the eyeline axis, each principal's
  screen side and look direction, and the camera side of the axis. Preserve those
  facts through singles, over-shoulders, reactions, and reverses. Cross the axis
  only through a visible neutral move or a motivated re-establishment.
- `extreme_close_up`, `close_up`, and `medium_close_up` are the baseline and must
  dominate the finished coverage. `medium` is secondary and exists only when a
  small shared action or two-person relation cannot read tighter.
- `medium_wide`, `wide`, and `extreme_wide` are exceptions. Use one only while the
  audience must see a story-required entrance, exit, crossing, approach, retreat,
  transfer between marks, or other consequential position change. Keep it to the
  shortest readable beat and return immediately to the decisive face, eyes,
  mouth, hand/paw, clue, or reaction.
- A new Scene, a new Segment, scenic atmosphere, scale, the existence of a
  Location, several characters being present, or a desire for “cinematic variety”
  never independently justifies widening.

## Three full release gates

1. After screenplay generation, validate the complete screenplay and every exact
   line against its owning Shot duration.
2. After Storyboard generation, validate the complete Storyboard, few-character
   composition, eyeline axes, close-up dominance, all position-change exceptions,
   and every exact line against its Segment-local speech window.
3. After all first-pass Segment Prompts are authored, validate the complete Prompt
   set, copied visual-doctrine declarations, exact per-Shot sizes, references,
   exact speech, and all speech windows again.

The shared maximum is 4.0 CJK characters per second or 2.6 non-CJK words per
second, plus 0.25 seconds of line start/end allowance. Failure blocks downstream
work.

The Segment human-in-the-loop phase starts only after Gate 3 passes.

## Storytelling and speech

A narrator may be:

- an external voice;
- an on-screen character speaking to another character;
- a diegetic storyteller whose same voice continues off-screen over an embedded
  tale;
- a participant narrating personal experience; or
- a deliberate hybrid of these forms.

Never create a second narrator when an existing character owns the storytelling.
The same character keeps one identity and one voice across on-camera dialogue,
on-camera storytelling, off-camera storytelling, and return to the framing scene.

Every spoken line must state in the screenplay:

1. speaker;
2. delivery mode;
3. visible or audible trigger;
4. natural speech transition;
5. delivery;
6. exact words.

Valid delivery modes are:

```text
on_camera_dialogue
on_camera_storytelling
off_camera_storytelling
external_voiceover
embedded_character_dialogue
```

Every speaker or delivery-mode change must be motivated by performance and edit.
Use a completed phrase, breath, listener reaction, action result, J-cut, L-cut, or
authored silence. Do not cut mid-word, reset the voice into announcer delivery,
overlap unrelated speech, or give narration mouth movement to a visible character.
Only the active on-camera speaker receives speaking mouth movement. An off-camera
storyteller remains visually absent unless the Storyboard explicitly returns to the
framing scene.

## Framing and embedded worlds

Treat a framing scene and an embedded story as separate location and population
chains. A storyteller's voice may cross between them; the storyteller's positive
image reference may not.

When an on-screen storyteller hands off to an embedded tale:

- finish a speakable phrase on camera;
- give the listener a readable reaction;
- carry the outgoing voice naturally across the visual cut when authored;
- omit the storyteller and listener image references from an embedded-story
  Segment in which they must remain absent;
- bind only the storyteller's voice reference when that voice continues; and
- state in the Prompt that no storyteller body, portrait, reflection, silhouette,
  or extra observer may appear.

Return through an authored sound or reaction bridge. Restore the original framing
location, cast positions, props, ambience, and voice without unexplained reset.

## World and identity continuity

Production design owns reusable visual identities and dressed Location masters.
The screenplay and Storyboard own how those identities participate in the story.
Preserve each recurring character's face, body topology, scale, wardrobe,
accessories, voice, and temporary state. Preserve each Location's layout,
landmarks, fixed dressing, population, time, weather, light, and ambience.

References are positive conditioning. Never bind a character image merely because
the character is speaking off-screen when that image could cause an unwanted
appearance. Use a voice reference alone for an absent storyteller. Split a
Generation Segment at a motivated speech or scene boundary when visible and absent
reference requirements conflict.

## Department obligations

- `screenplay-writer` authors the complete drama, exact speech, delivery modes,
  natural speech transitions, framing/embedded-world separation, and state changes.
- `direct-production-design` supplies reusable character, voice, prop, costume, and
  Location assets without inventing narrative functions.
- `previsualize-cinematography` turns the screenplay into one executable
  `storyboard.md`, including every speech handoff, mouth state, listener reaction,
  audio bridge, reference inclusion, and reference omission.
- `virtual-production` writes one self-contained Seedance Prompt per Generation
  Segment directly from the Storyboard. The Prompt must say everything Seedance
  needs to perform the speech, picture, sound, and transition.
- `video-review` watches picture and sound and rejects unnatural speech
  switches, voice drift, wrong mouth movement, unwanted storyteller appearances,
  missing reactions, crowded or full-cast staging, ambiguous/reversed eyelines,
  unearned wide coverage, or abrupt ambience changes.
- `finish-postproduction` assembles accepted native audiovisual Segments, executes
  authored J/L audio bridges and transitions, and builds exact captions.

## Release gates

Release a phase only when:

1. `story.md` exists and the target country is stated in `screenplay.md`;
2. the screenplay and Storyboard both state `16:9`;
3. every spoken line is exact and has a delivery mode and natural transition;
4. a character storyteller keeps one identity and voice across narrative layers;
5. framing and embedded worlds have separate visual-population authority;
6. every Seedance Prompt contains the Storyboard's exact speech, speaker,
   visibility, mouth, reaction, audio-bridge, and exclusion instructions;
7. every interaction declares a stable eyeline axis, tight Shots dominate, and
   every wider Shot is the shortest readable coverage of a story-required
   position change;
8. adjacent Segments preserve character, prop, environment, voice, and ambience
   state without replay or unexplained reset; and
9. generated video has been reviewed with sound before acceptance.
