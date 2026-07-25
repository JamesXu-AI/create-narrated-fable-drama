# Dialogue Coverage and Blocking

Design camera coverage around power, information, and performance. Preserve a reconstructable room and a stable eye line through every generated segment.

The default frame contains the fewest story-active characters: one expressive
subject or one speaker/listener pair. A physically present third role normally
stays outside the crop and remains continuous through its mark, gaze, off-screen
sound, foreground edge, or later reaction. Do not widen to prove presence.

## Contents

- [Establish the spatial contract](#establish-the-spatial-contract)
- [Derive action and orientation from drama](#derive-action-and-orientation-from-drama)
- [Dialogue-address blocking contract](#dialogue-address-blocking-contract)
- [Coverage building blocks](#coverage-building-blocks)
- [Shot/reverse-shot contract](#shotreverse-shot-contract)
- [Choose when to cut](#choose-when-to-cut)
- [Blocking and props](#blocking-and-props)
- [Entrances, exits, and reveals](#entrances-exits-and-reveals)
- [Motivated movement contract](#motivated-movement-contract)
- [Camera and performance pairing](#camera-and-performance-pairing)
- [Generation-aware coverage](#generation-aware-coverage)
- [Coverage acceptance](#coverage-acceptance)

## Establish the spatial contract

Before close coverage, record the spatial contract internally. This does not
require an on-screen master Shot:

```yaml
scene_director_intent_and_audience_pov:
shot_story_job_and_attention_target:
axis_line:
character_A_screen_side_and_look:
character_B_screen_side_and_look:
distance_between_characters:
doors_windows_and_exits:
first_frame_visible_offscreen_and_occluded_entities:
reserved_empty_regions_and_forbidden_occupants:
entrance_exit_paths_and_marks:
table_furniture_and_prop_positions:
camera_side_of_axis:
neutral_axis_position:
key_light_direction:
lens_family_and_camera_height:
```

Example:

```text
LIN remains screen-left looking camera-right. CHEN remains screen-right looking camera-left.
The dialogue axis runs between their eye lines across the table. All coverage stays on the
window side of the axis. The door is behind CHEN; the red folder remains by LIN's right hand.
```

Do not let a reverse shot mirror the whole world. Only the subject changes; geography, screen sides, props, light direction, and eye-line logic remain consistent.
This spatial contract is mandatory even when no master Shot appears on screen.

## Derive action and orientation from drama

Do not begin with poses, camera angles, or a motion checklist. Read the complete scene and run these creative lenses in order, then merge them into one authored choice:

1. **Screenwriter/dramaturg:** identify why the beat happens now, what source fact or prior event triggers it, what each character knows, wants, fears, conceals, and what turn or state change the beat must produce.
2. **Director:** choose whose experience governs the audience, what must be seen or withheld, where attention moves, and how distance, access, facing, thresholds, and prop control express the current relationship and power geometry.
3. **Performance director:** choose the playable verb/tactic, physical and vocal behavior, active listening task, tactic change, adjustment, and whether movement or deliberate stillness is more truthful.
4. **Blocking/action designer:** turn that intention into a reachable body path, facing or refusal to face, distance change, hand/prop use, entrance/exit, contact, settle, or controlled hold.
5. **Cinematographer/editor:** decide what the audience sees first, which action/reaction owns the frame, whether to hold or cut, and what image/sound landing makes the dramatic change readable.
6. **Continuity supervisor:** verify the action starts from the inherited body/prop/emotional phase, advances only forward, and ends in a state the next Shot can consume.

Record one integrated trace, not six role-play essays:

```yaml
beat_id:
source_fact_or_trigger:
character_knowledge:
objective_obstacle_and_tactic:
audience_pov_attention_and_withholding:
relationship_and_power_geometry:
chosen_action_or_active_stillness:
facing_distance_target_and_dramatic_function:
physical_transition_and_prop_path:
listener_and_audience_effect:
changed_state:
owning_shot_cut_and_continuity_handoff:
```

An action is story-bearing only when changing or withholding it would alter character intention, audience understanding, relationship pressure, information timing, causality, physical access, or the edit. Preserve approved script action; author missing low-risk behavior in service of the locked beat; expose any substantive rewrite. Never add a turn, walk, gesture, prop pickup, or facial tic merely because a schema contains an action field. A still body, held gaze, refused eye contact, closed hand, blocked doorway, or delayed turn can be the strongest action when it is an active tactic.

Approve the creative choice only when this sentence is true:

```text
Because [source trigger and objective/obstacle], [character] uses [tactic] through
[action or active stillness and facing], causing [listener/audience effect] and
landing on [changed state], which motivates [camera/edit handoff].
```

## Dialogue-address blocking contract

Do not rely on a speaker/addressee label to tell Seedance whom a line addresses.
For every `line_id`, author this exact spatial event in the Storyboard and preserve
all five values in the owning Shot for downstream compilation:

```yaml
speaker_mark: where the speaker holds or lands
addressee_mark: where the intended listener holds or lands
movement_before_line: the speaker's reachable travel or deliberate hold
speaker_to_addressee_orientation: chest, face, and gaze relation during delivery
speech_gate: stop, settle, eyeline, cue, or other visible event that unlocks speech
```

Express the five values as one concise blocking implementation that names both
characters. Put it in the owning Ordered Shots row immediately before the exact
line. Downstream Prompt compilation may add literal braces but must not change the
blocking authority. The line must not start while an authored approach or turn is
unfinished.
In a group scene, repeat this per line so the current speaker cannot address the
camera, the nearest bystander, or the prior line's listener by accident.

For off-screen speech or voice-over, keep a concrete `addressee_mark`; explain in
the orientation field that the speaker's body is not visible and state the audible
address relation. Never use bare `not_applicable`, `toward them`, or an ambiguous
pronoun.

## Coverage building blocks

Use each angle for a reason:

| Coverage | Primary job | Best use |
|---|---|---|
| Brief master/wide two-shot | Position change only | Entrance, exit, crossing, mark handoff, consequential distance change |
| Medium two-shot | Relationship and simultaneous listening | Fast exchange, intimacy, comedy timing |
| OTS on speaker | Keeps listener physically present | Negotiation, confrontation, unequal power |
| Clean single | Isolates inner tactic or confession | Decisive line, concealment, emotional separation |
| Reaction single | Reveals new listener state | Twist, betrayal, recognition, silent decision |
| Insert | Shows story-bearing detail | Message, key, hand, wound, clock, evidence |
| Profile two-shot | Makes distance and opposition graphic | Standoff, symmetrical choice, restrained emotion |

Use close and medium-close coverage as the dialogue baseline when the story event
lives in delivery, listening, eye line, breath, concealment, recognition, or a
small physical action. A close-up still needs a precise attention target; do not
use one as empty emphasis. A master/wide is a `position-change exception:` and may
exist only for the shortest readable portion of a story-required entrance, exit,
crossing, approach, retreat, transfer between marks, or consequential
relationship-distance change. It returns immediately to the decisive close-up.
New geography, atmosphere, scale, physical presence, and continuity alone do not
justify a full-cast master.

## Shot/reverse-shot contract

For a conventional two-person exchange:

1. Establish A and B through an existing incoming spatial contract, a brief
   relational angle, or a master only when the audience genuinely lacks the needed
   geography. Do not automatically begin every exchange with a wide two-shot.
2. Lock A screen-left looking right; lock B screen-right looking left.
3. Match camera height, eye-line angle, lens family, headroom, and look room across reverses unless a deliberate power imbalance is planned.
4. Keep the foreground shoulder consistent in OTS coverage; do not swap shoulders or duplicate the listener.
5. Preserve the same dialogue axis across all generated clips.
6. Let the speaker's shot include the listener's foreground only if identity and body continuity remain reliable.
7. Cross the axis only through a visible camera move, a neutral-on-axis shot, or a motivated disorientation followed by re-establishment.

Use asymmetric coverage deliberately. A wider, slightly higher angle may weaken one character; a closer, lower angle may give the other control. Record the reason so it is not mistaken for drift.

Do not stage performers in a frontal row or semicircle facing the camera. Place
them on playable marks across depth, let the current speaker and listener own
selective frames, and keep other physically present roles continuous through
off-screen sound, eye lines, foreground edges, or later reaction coverage. A close
crop is not a diegetic exit.

## Choose when to cut

Cut because one of these changes:

- New information becomes important.
- A tactic succeeds, fails, or changes.
- Power transfers between characters.
- The listener's reaction becomes more important than the speaker's delivery.
- A prop or action must be seen clearly.
- Geography must be re-established after movement.
- Silence becomes the scene's active event.

Do not cut mechanically on every line. Consider:

- **Hold on speaker:** when concealment, persuasion, or performance is the event.
- **Cut to listener before the final word:** when anticipation matters.
- **Cut after the line:** when the line must land first, then reveal impact.
- **Stay in two-shot:** when timing, interruption, or physical distance is the event.
- **Use off-screen speech over reaction:** when the listener's change is the story.

## Blocking and props

Track the full action chain:

```text
named subject -> relevant body part -> starting pose/facing or body-to-target relation ->
action with range/speed/force -> transition or inertia -> contact/transfer if any -> landing pose/facing
```

Make this chain explicit for every story-bearing action. Name only body parts and orientations visible or necessary to eyeline, interaction, prop access, entrance/exit, camera readability, or cut continuity; do not inventory hidden anatomy. For a static performance, state the stable facing or spatial relation and the small permitted behavior instead of inventing movement. Prefer a compatible reference image for complex spatial relationships, then use concise text to name only the required change.

Do not cut from a hand beginning to reach to a reverse angle where the object is already transferred unless the cut intentionally compresses time. For dialogue with props, record:

- Owner, hand, grip, orientation, condition, and table position.
- Whether the prop is visible during the line.
- Which word or reaction motivates the pickup, release, concealment, or handoff.
- The settled state required for the next angle.

Keep complex blocking in the master whenever possible. Use singles after characters reach stable marks.

## Entrances, exits, and reveals

Use a master, wide, or otherwise testable frame when the audience must read a subject crossing into or out of the scene. Lock:

```text
first-frame presence/absence -> edge or occluder -> reveal/conceal order -> travel path ->
arrival/departure mark -> weight settle -> listener recognition -> dialogue/action gate
```

Keep the declared entry edge and reserved negative space visible until first contact. Do not pan or reframe early in a way that hides whether the subject started off-screen. Do not cut from an empty frame directly to the subject fully on its mark unless the cut itself intentionally compresses the entrance.

Separate the primary entrant from companions and background entities. State who follows, stops, reacts in place, or remains absent. For detailed occupancy rules, use [Frame occupancy, entrances, and exits](frame-occupancy-and-entrances.md).

## Motivated movement contract

Use [Cinematography and visual design](cinematography-and-visual-design.md) for the full visual system. For every move, record:

```text
story reason -> trigger -> start composition -> path/direction -> speed change ->
actor-camera relationship -> focus behavior -> stop trigger -> landing composition -> edit handoff
```

Move to discover information, transfer point of view, change power distance, follow necessary action, or embody a realization. Keep the camera locked when movement would dilute performance, geography, tension, or reveal timing. Do not add an orbit, push-in, pan, crane, zoom, or rack focus only to make the shot feel expensive.

## Camera and performance pairing

Pair camera behavior with dramatic function:

| Dramatic beat | Coverage tendency | Camera behavior |
|---|---|---|
| Testing or casual deflection | Medium two-shot/OTS | Fixed or subtle lateral correction |
| Pressure increasing | OTS or tighter single | One slow motivated push-in |
| Confession | Clean single | Stable frame; movement only if it reveals surrender |
| Threat | Profile/OTS | Hold distance or controlled push; preserve opponent |
| Recognition | Listener close-up | Hold through breath and eye change |
| Reconciliation | Two-shot | Reduce distance or gently widen to include both |
| Comedy reversal | Master then reaction | Preserve setup geometry; cut after the reveal |

Use one primary camera idea per timed beat. Avoid close facial dialogue with wide orbiting, abrupt zoom, simultaneous rack focus, and large actor movement.

## Generation-aware coverage

- Treat the coverage plan as an ordered shot sequence first, then pack compatible master, OTS, single, reaction, and insert shots into one Seedance generation segment. Do not assign one generated file per angle or line.
- Keep an internal cut inside the same generation segment when one duration, operation/reference set, identity/space/light system, and dialogue/audio contract can govern both shots.
- Create an external generation boundary only for duration or complexity overflow, incompatible mode/assets, strict endpoint needs, high-risk isolation, or required independent editorial selection.
- Favor stable medium-close and close singles for sustained spoken lines and
  listener reactions; use medium framing when shared gesture or relationship
  distance must remain readable.
- Keep visible independent performers to one or two unless the current causal
  action truly requires more; crop other still-present roles without treating
  them as absent.
- Label any MWS/WS/EWS beat `position-change exception:` and keep only the
  movement from start mark through landing mark before returning to tight
  attention.
- Reserve extreme close-ups for short, controlled performance moments.
- Keep mouth, chin, and jaw visible when lip-sync is essential.
- Avoid foreground occlusion across the mouth during critical dialogue.
- Generate clean reaction shots with no visible speaking when voice attribution is fragile.
- Use off-screen dialogue to protect a decisive listener reaction.
- Build edit handles on stillness, breath, gaze, or room tone, not arbitrary dead time.
- Separate high-risk mouth performance from high-risk hand interaction or large camera travel.
- Give a required entrance, exit, re-entry, or reveal its own readable beat; do not bury it under the first line or a simultaneous complex camera move.

## Coverage acceptance

Mark `BLOCKER` when:

- A and B look in the same screen direction during a conventional reverse without explanation.
- The axis, shoulder, door, prop, or key light flips between angles.
- A reverse shot changes camera height or lens so much that the space appears different unintentionally.
- The visible listener lip-syncs the off-screen speaker's line.
- A line lacks either actor's mark, the speaker's movement/hold, an explicit
  speaker-to-addressee body/face/gaze relation, or a stop/eyeline speech gate; or
  its blocking instruction is absent from the owning Ordered Shots row before the
  line.
- A speaker addresses the camera, a bystander, or the previous listener instead of
  the line's declared addressee, or starts speaking before reaching the declared mark.
- A critical action begins in one angle and finishes in an incompatible body or prop state.
- A story-bearing action omits its acting subject or relevant body part, gives no usable degree/transition/landing, or changes a consequential facing or body-to-target relation without a readable turn or cut.
- An action or facing choice cannot be traced to a source beat, character knowledge, objective/obstacle/tactic, audience POV, relationship geometry, listener effect, and changed state; or it was invented only to satisfy the template.
- A formally complete movement contradicts what the character knows or wants, reveals/hides information at the wrong time, weakens the intended power geometry, or replaces a stronger active stillness with decorative busywork.
- A required entrant is already visible at the first frame, reserved negative space is occupied, or the camera hides the declared edge before first contact.
- An entrance/exit/reveal skips its partial state, starts dialogue before its gate, or causes unauthorized background figures to follow or duplicate.
- The decisive reaction is neither visible nor audible.
- The coverage plan depends on more distinct cuts than the generation segment can perform clearly.
- Compatible coverage is unnecessarily split into one generated clip per shot, producing avoidable external continuity seams.
- A camera move lacks a dramatic reason, trigger, readable path, stop, landing frame, or edit consequence.
- Dialogue is covered mainly by repeated frontal masters or full-cast wide shots
  even though delivery, listening, eye line, or small reactions own the dramatic
  changes.
- An interaction lacks a declared A/B axis, screen sides, opposing look
  directions, or camera side; a reverse mirrors or silently crosses that axis.
- A wider Shot does not show a consequential position change, lasts beyond the
  readable landing, or is followed by another wider Shot instead of a tight
  dramatic subject.
