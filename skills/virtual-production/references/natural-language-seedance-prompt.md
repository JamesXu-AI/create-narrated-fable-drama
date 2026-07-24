# Free-Form Seedance Prompt Guidance

`segment-NNN.md` is the exact model-facing instruction. It is plain natural
language, not JSON. Its only creative sources are the approved screenplay and
Storyboard.

## Recommended order

1. State the task operation and 16:9 cinematic style.
2. Declare each `@ImageN`, `@VideoN`, and `@AudioN` token from the Storyboard
   Reference Plan, with one readable subject and one responsibility per token.
3. State population, identity, continuity, and incoming-state constraints.
4. Write ordered `Shot N:` beats with camera, visible action, blocking, gaze,
   speech, listener behavior, ambience, effects, and landing state.
5. Close with one concise global constraint block.

The prose may otherwise be continuous, bulleted, or sectional. Use event order,
phrases such as “after his breath settles,” and relative pacing. Do not place
precise second ranges in the model-facing prompt.

## Speech is performance, not a label

For every Storyboard speech cue:

- name the readable speaker;
- include the exact line once as `{exact words}`;
- repeat its delivery mode in natural language;
- say whose mouth moves and whose mouth stays closed;
- describe the listener's reaction during or immediately after the phrase;
- express the authored trigger or phrase/breath boundary;
- express the J-cut, L-cut, cutaway, eyeline, memory transition, or visual handoff;
- preserve the established voice, room tone, and ambience bridge.

Examples of the required semantic precision:

```text
Grandfather is visible and speaks directly to his grandson, with natural lip sync:
{Have you ever wondered why the smallest lantern stayed lit?}
The grandson stops fidgeting and looks up before the final phrase lands.
```

```text
On Grandfather's soft inhale, cut from his close-up into the moonlit fable world.
Grandfather is no longer visible, but the very same established voice continues
off camera as storyteller: {Long ago, a fox guarded one last flame.}
No mouth in the fable scene moves for this narration; the fox only reacts to the
wind. Keep the room hush under the first night wind as a gentle L-cut.
```

```text
The fox now answers inside the embedded story and is the only lip-synced speaker:
{Then I will carry it through the storm.}
Grandfather's narration pauses completely; the owl listens with a closed beak.
```

Never introduce “a narrator” when the screenplay establishes a character such as
Grandfather as storyteller. Never bind a positive image for a character who must
remain visually absent in that embedded Segment.

## Visual compilation

Translate Storyboard Shot Size literally. Close coverage keeps the authored face,
eye line, hand, clue, or reaction dominant; it does not widen merely to show every
physically present character. Use off-screen sound, foreground edges, gaze, and
listener reactions to preserve space.

Every provider-renderable visible role needs an approved identity or state image.
Temporal evidence owns recent action and position, not identity. A role marked
`remain_absent` receives no positive image or video binding.

## Audio notation

- exact speech: `{spoken words}`
- effect: `<source and audible event>`
- restrained native music: `(music cue)`
- generated on-screen text: `【text】`

This production forbids generated on-screen text; subtitles are added after
picture lock. Seedance generates synchronized speech, narration, ambience,
effects, and restrained music natively.

## Final constraints

Forbid paraphrase, omission, repetition, added words, wrong speaker, wrong mouth
movement, voice replacement, captions, visible text, logos, watermarks, duplicate
people, clones, anatomy errors, identity/style/costume drift, unmotivated
appearance or disappearance, and discontinuous light, space, props, or ambience.
