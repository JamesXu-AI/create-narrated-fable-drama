# Long-Form Continuity and Dramatic Logic

Review continuity as a chain of motivated state changes. Track what the audience sees and hears, what each character knows and wants, the state carried across internal shot cuts inside one generated clip, and the exact performance phase handed across external generation seams.

## Contents

- [Dramatic continuity](#dramatic-continuity)
- [Performance continuity](#performance-continuity)
- [Spatial and shot/reverse-shot continuity](#spatial-and-shotreverse-shot-continuity)
- [Frame occupancy and appearance continuity](#frame-occupancy-and-appearance-continuity)
- [Character, wardrobe, and prop continuity](#character-wardrobe-and-prop-continuity)
- [Voice, mouth, and sound continuity](#voice-mouth-and-sound-continuity)
- [Reference bindings](#reference-bindings)
- [Boundary state ledger](#boundary-state-ledger)
- [Hard blockers](#hard-blockers)
- [Acceptance matrix](#acceptance-matrix)

## Dramatic continuity

For every scene, answer:

1. Why does this scene happen now?
2. What prior event causes it?
3. What does each character want from the other in this moment?
4. What tactic does each speaker use, and what makes the tactic change?
5. What fact, decision, danger, relationship, or physical state changes?
6. What pressure or question passes into the next scene?

Preserve who knows what and when they learned it. Require a clue before an inference, a perception before a reaction, and a decision before purposeful action. Do not let a character answer dialogue they could not hear or react to an off-screen event they could not perceive.

Track unresolved promises, threats, lies, questions, injuries, and relationship pressure until they are paid off or intentionally abandoned.

## Performance continuity

Carry emotional pressure as a phase, not a label. Record:

```text
trigger -> recognition -> tactic -> vocal/physical expression -> listener effect -> recovery or escalation
```

The next shot must inherit the correct phase. Do not cut from a character suppressing tears to a dry, relaxed neutral face unless the cut implies elapsed time or concealment. Preserve:

- Breath rate, tears, sweat, facial tension, jaw, gaze, posture, and hand behavior.
- Whether the character has started, completed, or withheld a reply.
- Whether a laugh, sob, cough, or inhale is beginning, active, or settled.
- The last tactic and whether it succeeded.
- The listener's degree of understanding, suspicion, or decision.

Let the first visible behavior in a new shot continue the prior internal pressure. A new camera angle does not reset the performance.

Enforce action-phase monotonicity across every generation boundary. A matched cut
may inherit the same result pose, gaze, hand position, expression, and emotional
pressure, but it must not replay an authored beat already completed in the outgoing
segment: no second inhale, repeated turn, repeated reach, repeated reaction,
expression reset-and-settle, duplicated pause, or repeated camera beat. Record every
recognizable beat as `started`, `active`, or `completed`. If it is completed, the new
shot consumes only its result state and begins the next story instant. If it is
unfinished, continue only the next forward phase; never rewind to an earlier phase.
Natural micro-behavior such as a different blink or ordinary breathing is not a
replay unless it clearly restages the authored beat.

## Spatial and shot/reverse-shot continuity

Establish location, doors, furniture, exits, hazards, characters, and axis before complex coverage. Preserve:

- A/B screen sides and look directions.
- 180-degree axis, neutral axis point, and camera side.
- Camera height, eye-line angle, lens family, headroom, and look room across reverses.
- Entrance/exit and travel screen direction.
- Character distance, seated/standing height, and body orientation.
- Foreground shoulder identity and side in OTS shots.

If A is screen-left looking right and B is screen-right looking left, keep that relationship across master, OTS, and singles. Cross the axis only through a visible move, neutral-on-axis shot, or deliberate disorientation followed by re-establishment.

Require every body action to begin from the preceding pose and weight distribution. Avoid teleportation, instantaneous turns, impossible reach, and silently changed seating positions.

Treat an internal editorial cut separately from an external generation seam. A
multi-shot segment may intentionally change framing or camera position at an internal
cut while preserving undeclared identity, performance, geography, prop, light/color,
voice, and sound state. When the Storyboard marks
the next segment as the same continuous camera/ensemble moment, its first usable
state must come from complete-predecessor video extension. Do not let Seedance
re-establish the camera, redistribute or resize the visible group, change person
count/occlusion, or reset exposure, white balance, palette, or saturation merely
because a new segment begins. A motivated coverage cut or hard discontinuity must be
declared before these properties may change.

Separate temporal continuity from world/population continuity. A predecessor last
frame proves only the recent visible action, pose, gaze, mutable-prop, and camera
phase; bind the Location master when a soft-cut successor needs complete set or
population evidence beyond that image. A complete-predecessor video extension is
different: audit the full source before adding images. When it already carries the
required set, population, performers, props, camera, and grade, make it the sole
visual authority; a redundant Location or identity image can trigger seam-time
reconstruction. Add an image only for a materially absent property, state that
reason, and forbid it from overriding inherited camera, geometry, population,
exposure, white balance, palette, or positions. A close frame neither deletes an
offscreen person nor authorizes Seedance to invent a new person, animal, silhouette,
reflection, or distant bystander.

## Frame occupancy and appearance continuity

Track absence as precisely as presence. For every relevant frame region, state which entities are visible, fully off-screen, intentionally occluded, or forbidden from appearing. Reserve negative space when an entrance, exit, re-entry, or reveal depends on it.

Distinguish:

- **Entrance:** the subject begins fully outside the frame and crosses a declared edge or threshold.
- **Reveal:** the subject is present but hidden, then becomes visible from behind a declared occluder.
- **Re-entry:** a previously established subject returns through a declared path after a legible absence.
- **Exit/concealment:** the subject leaves the frame or becomes fully hidden through an ordered, readable action.

Require the sequence `why now -> cue/trigger or declared surprise -> first-frame occupancy -> first-visible gate -> boundary contact or reveal source -> partial state -> full state -> settled mark -> dialogue/action gate`. Motion continuity alone does not fix premature appearance. If a subject is meant to enter later, showing it in the first usable frame is a failure even when its pose or gesture matches.

For detailed schemas and repair rules, use [Frame occupancy, entrances, and exits](frame-occupancy-and-entrances.md).

## Character, wardrobe, and prop continuity

Use one permanent ID per character. Track:

- Face, apparent age, hair, body, wardrobe layers, accessories, dirt, sweat, wetness, wounds, and fatigue.
- Prop owner, hand, grip, position, orientation, open/closed state, damage, liquid level, and visibility.
- Doors, windows, screens, practical lights, furniture, vehicles, smoke, rain,
  embedded NPC roster, authorized independent performers, and crowd density.

Require visible pickups, handoffs, drops, damage, wardrobe changes, or an explicit ellipsis. Do not use `unchanged` unless the prior value is known.

For dialogue props, tie changes to a word or reaction. Example: `CHEN stops turning the key after LIN says “一直”; the key remains in CHEN's right hand through the reverse.`

## Voice, mouth, and sound continuity

Track each speaker's:

- Language, accent, pitch family, timbre, age impression, cadence, articulation, volume, and breath texture.
- Temporary vocal state such as whisper, exhaustion, crying, distance, phone filter, or room echo.
- Current line, whether it is complete, mouth open/closed state, and whether the speaker is on-screen or off-screen.
- Relationship to room tone, music, and sound effects.

Keep visible non-speakers' lips closed unless timed overlap is intentional. A cut to a listener may carry the speaker's voice off-screen, but the listener must not inherit the lip-sync.

Preserve sound perspective: room size, reverberation, source direction, distance, ambience, music phase, and effect tails. Use J-cuts, L-cuts, sound bridges, or deliberate silence rather than allowing every generated segment to restart its sound world.

## Reference bindings

For every asset, record:

```text
reference ID -> bound character/object/function -> adopted property -> active segment/beat -> forbidden inheritance
```

Examples:

```text
@Image1 -> LIN -> face and hair only -> Shot 1, Shot 2 -> do not inherit clothing/background
@Audio1 -> LIN -> low warm grainy voice only -> Shot 2 -> do not inherit music/room noise
@Video1 -> prior generated segment -> image, motion, and room-tone continuation -> Shot 1 boundary -> do not add its subtitles
```

Do not bind one mixed audio conversation to several characters. Do not rely on numerical character names near numerical asset IDs. Use stable names or letter IDs.

## Boundary state ledger

Record this at the last usable image and sound of every generation segment:

```yaml
story_time_and_elapsed_time:
location_and_zone:
visible_characters:
fully_offscreen_and_intentionally_occluded_entities:
reserved_empty_regions_and_forbidden_occupants:
entrance_exit_reveal_phase_and_gate:
appearance_why_now_trigger_and_first_visible_status:
character_positions_and_screen_sides:
body_head_gaze_and_weight:
left_right_hands:
wardrobe_hair_injury_wetness:
prop_owner_position_orientation_condition:
axis_camera_side_shot_size_height_lens:
key_light_direction_and_color:
line_id_speaker_and_completion:
mouth_states:
listener_reaction_phase:
last_completed_performance_beat:
unfinished_performance_phase:
next_new_performance_beat:
voice_state_and_perspective:
room_tone_music_effect_tail:
knowledge_objectives_and_emotional_pressure:
last_usable_frame:
last_usable_sound:
next_required_start:
transition:
```

Approve only:

```text
previous.outgoing_state == next.incoming_state
```

or:

```text
previous.outgoing_state --[explicit cut, elapsed event, or transition]--> next.incoming_state
```

For time/location jumps, physical matching may relax, but story causality, character knowledge, relationship pressure, wardrobe-state logic, and voice identity still carry.

## Hard blockers

Mark `BLOCKER` when:

- Effect precedes cause or a character uses impossible knowledge.
- A line changes owner, voice, addressee, or meaning between script and prompt.
- A direct cut changes screen side, gaze, hands, prop, pose, wardrobe, injury, light, or sound without explanation.
- A subject meant to enter or be revealed later is already visible in the first usable frame, or required negative space is occupied.
- A new subject appears at a shot/segment boundary without a prior cause, readable cue, first-visible gate, or declared dramatic surprise.
- A subject appears, disappears, exits, re-enters, or changes occlusion state without a readable path, motivated cut, or declared ellipsis.
- A reference frame contradicts the authored first-frame occupancy or appearance gate.
- A visible listener lip-syncs an off-screen line.
- A sentence, laugh, sob, or essential breath is cut across independent generations.
- A voice changes age, accent, timbre family, or vocal distance without cause.
- A prop appears, disappears, duplicates, changes hand, or changes condition silently.
- A new shot begins from a physical or emotional phase the prior shot could not produce.
- A compatible internal shot progression is split into separate generation segments without a duration, mode/reference, risk, endpoint, or editorial-selection reason, creating avoidable drift.
- A continuous seam is mislabeled as a new shot and re-synthesizes camera, ensemble composition/count, or color/exposure state at the join.
- A new shot replays, restarts, or restages a recognizable performance or camera
  beat already marked completed, or duplicates a preparation/settle hold so story
  time visibly rolls backward or stalls without an authored causal pause.
- A master and reverse coverage disagree on axis, shoulder, door, furniture, or light direction.
- A segment ends on unstable blur, total occlusion, unfinished action, or an unusable sound tail when exact continuation is required.

## Acceptance matrix

| Dimension | Boundary question | Pass condition |
|---|---|---|
| Story | Does the next beat follow from the prior result? | Cause, objective, and tactic are legible |
| Knowledge | Can the character know or hear this? | Perception or prior information exists |
| Performance | Does emotional pressure carry while authored action phase moves only forward? | Result pose may match; completed beats do not replay, and unfinished beats continue only to their next phase |
| Space | Can the viewer reconstruct the room? | Axis, screen sides, positions, and directions agree |
| Occupancy | Who must be present, absent, occluded, entering, or exiting, and why now? | Cause/cue, first-visible beat, first/last frames, negative space, path, reveal order, and gates agree |
| Camera | Does the reverse belong to the same setup? | Height, lens, eyeline, shoulder, and light match |
| Seam synthesis | Is this a real editorial cut or only a generation boundary? | Continuous boundaries use complete-predecessor extension and do not rebuild camera, ensemble, or color |
| Character | Is this the same person in the same state? | Identity, look, injury, fatigue, and knowledge carry |
| Prop | Where is it and who controls it? | Owner, hand, position, orientation, and condition match |
| Dialogue | Who speaks, to whom, and is the line complete? | One owner, exact text, completion, and addressee |
| Mouth | Whose lips move? | Only active visible speakers articulate |
| Voice | Does the voice remain the same identity? | Timbre, accent, cadence, and temporary state carry |
| Sound | What crosses the edit? | Room tone, music, effects, and perspective are assigned |
