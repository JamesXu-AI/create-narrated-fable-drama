# Frame Occupancy, Entrances, and Exits

Treat presence, absence, negative space, occlusion, entrance, exit, and re-entry as explicit production states. Motion continuity does not repair a subject that is already visible before its authored entrance.
Keep the frame to the primary event subject and the minimum witness/listener set.
Other still-present roles remain outside the crop unless the causal event requires
their simultaneous reaction. An entrance or exit may briefly widen only as a
`position-change exception:` from first boundary contact through the landing or
edge release, then coverage returns tight.

## Contents

- [Distinguish motion from appearance](#distinguish-motion-from-appearance)
- [Choose when the appearance happens](#choose-when-the-appearance-happens)
- [Occupancy state contract](#occupancy-state-contract)
- [Entrance and exit state machine](#entrance-and-exit-state-machine)
- [Reference and mode compatibility](#reference-and-mode-compatibility)
- [Compile the event](#compile-the-event)
- [Timing and dialogue gates](#timing-and-dialogue-gates)
- [Background and ensemble locks](#background-and-ensemble-locks)
- [Local repair workflow](#local-repair-workflow)
- [Acceptance and blockers](#acceptance-and-blockers)

## Distinguish motion from appearance

Validate two separate continuities:

1. **Motion continuity:** pose, gesture, travel direction, speed, weight, and action phase continue plausibly.
2. **Appearance continuity:** the subject is absent, occluded, partly visible, or fully visible at the authored time and frame region.

Do not accept a continued gesture as a repair for a premature appearance. If a character is meant to enter from off-screen, the first frame must not already show that character. If a subject is present but hidden, call the event a reveal from occlusion rather than an entrance.

## Choose when the appearance happens

Do not let a new subject appear merely because a new shot or generation segment begins. Before directing the path, answer:

```text
why now -> what cues or causes the entrance -> what the audience sees/hears before it ->
the earliest permitted first-visible beat -> who notices -> what changes after arrival
```

Use one or more motivated triggers:

- A prior line calls, threatens, introduces, or makes space for the entrant.
- A door, footstep, engine, shadow, off-screen voice, or environmental reaction prepares the arrival.
- An on-screen character looks, pauses, clears the path, or reacts toward the entry source.
- A causal action completes: a door opens, a signal occurs, a vehicle stops, or an obstacle moves.
- Motion is already underway in the preceding segment and the next segment continues it.
- A deliberate surprise cut reveals the subject instantly for shock, comedy, or reversal.

Distinguish **authored surprise** from **accidental pop-in**. An authored surprise states its dramatic purpose, exact cut/reveal beat, viewer knowledge, and reaction. If surprise is not intended, establish a readable cue and empty/occupied frame before first contact.

Record the first-visible moment relative to story beats, not only a vague clock value: `after L11 completes`, `on the second knock`, `after CHARACTER_A looks to the doorway`, or `not before the door is fully open`. The subject must remain fully off-screen or correctly occluded until that gate.

## Occupancy state contract

For every shot with an appearance or disappearance event, record:

```yaml
appearance_event: none | enter | exit | re_enter | reveal | conceal
appearance_timing:
  why_now:
  trigger_or_cue:
  audience_preparation: prepared | intentionally_unprepared
  first_visible_not_before:
  first_visible_beat_or_range:
  witness_and_reaction:
first_frame_occupancy:
  visible_entities:
  fully_offscreen_entities:
  intentionally_occluded_entities:
  reserved_empty_regions:
  forbidden_occupants:
entry_or_exit_contract:
  subject:
  source_or_destination: frame_left | frame_right | foreground | background | doorway | occluder | other
  direction_and_path:
  ordered_reveal_or_conceal:
  arrival_or_departure_mark:
  settle_state:
  dialogue_or_action_gate:
background_lock:
last_frame_occupancy:
source_frame_verdict: compatible | incompatible | not_applicable
```

Use stable frame-region names such as `left third`, `doorway`, `foreground-right`, or a marked zone from the location bible. `Reserved empty` means no part of the forbidden subject may occupy that region, including limbs, clothing, reflection, shadow, duplicate, or background version when those would spoil the event.

Track each relevant entity with one state:

```text
offscreen -> edge_contact -> partial_entry -> full_entry -> settled_on_mark
settled_on_mark -> partial_exit -> edge_release -> offscreen
occluded -> partial_reveal -> fully_revealed
```

Do not skip states that the audience must read.

## Entrance and exit state machine

Build an entrance as an ordered causal event:

```text
empty or occupied establishing frame
-> authored cue/trigger or declared surprise cut
-> first boundary contact
-> ordered body/object reveal
-> travel across the declared path
-> arrival and weight settle
-> eye-line/listener recognition
-> dialogue or next action unlocks
```

Build an exit as:

```text
decision or cue
-> turn/weight shift
-> travel toward declared edge, doorway, or occluder
-> ordered disappearance
-> full edge release or complete concealment
-> remaining characters/space react
-> next beat unlocks
```

Specify whether the camera is fixed, pans with the subject, or reframes after the event. Use one primary camera idea. If a static frame and visible traversal are essential, forbid anticipatory reframing that reveals the subject early or hides the entry edge.

## Reference and mode compatibility

Inspect every supplied or planned opening image/video state before compiling:

- If the event is an entrance, the subject must be fully absent from the required first-frame region.
- If the event is a reveal, the subject may exist only behind the declared occluder and must not be visibly duplicated elsewhere.
- If the event is an exit, the source must start from the declared visible pose and mark.
- If the starting reference contradicts the occupancy contract, mark `BLOCKER`; do not rely on negative prompting to erase, relocate, or delay the subject.

Choose the planned mode by the non-negotiable property:

- Use video extension when the preceding moving clip already ends in the correct occupancy and the event continues from that state.
- Use multimodal reference or an independent clip when identity/voice references matter more, but label first-frame composition as a soft requirement and plan regeneration or a clean editorial cut if occupancy fails.
- Split the setup and entrance into separate segments when one request carries too many high-risk tasks.
- When pixel-exact first-frame occupancy is essential and neither allowed mode can protect it, mark a downstream mode blocker. Do not invent a strict API mode or claim exact endpoint control in this Storyboard.

Never describe a contradictory starting frame as compatible merely because the text says `enters later`.

## Compile the event

Place the occupancy contract in Segment Direction and Reference Plan before the
Ordered Shots. Give the entrance, exit, or reveal its own readable Shot or beat.
Repeat only measurable landing and continuity conditions in the owning Shot and
Continuity Review; do not create a companion prompt or ledger.

Generic entrance example:

```text
First frame: CHARACTER_A remains at the center mark. The left third is empty; CHARACTER_B is fully
off-screen left with no visible body part, reflection, shadow, or duplicate. Camera holds the entry edge.

After CHARACTER_A hears the second knock and looks toward frame-left, CHARACTER_B crosses in from
frame-left; CHARACTER_B must remain fully off-screen before that look. The authored reveal order is head/upper body, torso, then lead
foot; the lead foot lands on the speaking mark and body weight settles. Only after settling does
CHARACTER_B make eye contact and begin line L12. Background figures remain on their established marks
and do not follow, approach, duplicate, or enter the reserved left third.
```

Adapt the reveal order to the subject: face/shoulder/feet, vehicle nose/body/rear wheels, hand/prop/arm, or another readable sequence. Do not reuse an anatomically inappropriate order.

## Timing and dialogue gates

Allocate time for sequential actions rather than hiding them under the line:

```text
entrance_minimum = first readable boundary contact
                 + authored cue/audience preparation when required
                 + traversal/reveal
                 + arrival and weight settle
                 + recognition or breath when needed
                 + dialogue start
```

Allow dialogue during travel only when the story explicitly wants a moving entrance and lip-sync remains readable. Otherwise bind the first line to a visible gate such as `lead foot planted`, `door closed`, `body settled on mark`, or `eye contact established`.

Do not compress a required progressive reveal into a duration that can only produce
a pop, dissolve, teleport, or already-present first frame. Shorten the path,
briefly widen only the authored position-change interval, simplify the reveal,
delay the line, or extend/split the Segment. The widened interval ends at the
arrival/departure landing and does not become a lingering master.

## Background and ensemble locks

Separate the primary subject from companions, crowds, animals, vehicles, reflections, screens, and distant versions. Record for each group:

```yaml
primary_event_subject:
followers_allowed: yes | no
background_positions:
background_motion_limit:
reserved_region_exclusions:
duplicate_and_reflection_policy:
```

Do not write `background remains natural`. State whether background entities hold, continue small ambient motion, react in place, follow, stop at a threshold, or remain absent. A background duplicate of the entering subject is an occupancy failure even when the foreground entrance is correct.

## Local repair workflow

When generated footage shows a premature appearance, disappearance, pop, or teleport:

1. Inspect the previous last usable frame and the failed segment's actual first usable frame.
2. Identify whether the intended event is entrance, reveal, re-entry, exit, concealment, or an editorial cut.
3. Diagnose the first failing state: missing dramatic trigger, premature first-visible beat, contradictory source frame, occupied negative space, missing edge contact, skipped partial state, early dialogue, camera reframing, or background duplication.
4. Repair only the affected segment when the prior outgoing state is valid; include adjacent boundary context without redesigning unrelated scenes.
5. Replace or reject any incompatible starting reference before rewriting motion language.
6. Regenerate and verify the actual first frame, ordered event, gate, and last frame. Keep status `planned` until footage is reviewed.

Do not report `the entrance is fixed` merely because the new prompt says `enters`. State the exact occupancy and timing conditions that the result must pass.

## Acceptance and blockers

Mark `BLOCKER` when:

- A subject meant to enter later is already partly or fully visible at the first usable frame.
- A new subject appears only because a shot/segment begins, with no `why now`, cue/trigger, first-visible gate, or declared surprise purpose.
- A subject becomes visible before its authored line, sound, eyeline, action, or cut trigger.
- A required empty region contains the subject, its duplicate, reflection, shadow, or an unauthorized follower.
- A subject appears without boundary contact, visible reveal, motivated cut, or declared ellipsis.
- Entry, exit, or reveal order skips a required readable state or teleports between marks.
- Dialogue or a dependent action starts before the arrival/reveal gate.
- A background group follows, enters, exits, or duplicates without authorization.
- The camera reframes so the declared entry edge or reserved region is not testable.
- A reference image/video contradicts the occupancy contract.
- The duration cannot contain the required traversal, settle, reaction, and line at natural speed.

Approve only when actual footage, if supplied, confirms:

```text
t0 occupancy -> cue/trigger -> first-visible gate -> ordered entrance/exit/reveal -> arrival gate -> dialogue/action -> final occupancy
```

and every state is compatible with the adjacent segment or an explicit editorial transition.
