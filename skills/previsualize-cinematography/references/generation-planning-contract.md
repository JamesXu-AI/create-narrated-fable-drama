# Generation Planning Contract

Turn the approved shot order and external seams into the `Generation Plan`,
`Location State Plan`, per-Segment records, and `Continuity Review` inside the sole
release `storyboard.md`. Do not create a manifest, dependency JSON, provider task,
or second storyboard representation.

## Contents

- [Plan after creative lock](#plan-after-creative-lock)
- [Pack Generation Segments](#pack-generation-segments)
- [Classify every boundary](#classify-every-boundary)
- [Choose operation and evidence](#choose-operation-and-evidence)
- [Preserve location state](#preserve-location-state)
- [Derive execution dependencies](#derive-execution-dependencies)
- [Review semantically](#review-semantically)
- [Blockers](#blockers)

## Plan after creative lock

Finish the screenplay interpretation, performance, blocking, shot order, light,
sound, and edit before optimizing generation. Apply this counterfactual:

```text
If parallel execution had no speed advantage, would this Segment design, operation,
reference authority, and boundary still produce the strongest finished film?
```

If not, repair the creative plan. Do not change coverage or continuity merely to
increase throughput.

Label every design state `planned`. Use `observed` only after reviewing actual
generated media. This skill does not perform that review or claim that footage
exists.

## Pack Generation Segments

Treat one Segment as one future Seedance video task that may contain several
internal Shots. Pack consecutive Shots when one duration, operation/reference set,
identity and location system, dialogue/audio contract, and continuity state can
govern them.

Prefer Segments whose visible composition can be executed with one story-active
subject or one speaker/listener pair while still preserving upstream visibility
authority. When several independently controlled performers are story-required,
split on a motivated reaction, movement landing, or speech boundary instead of
defaulting to full-cast master coverage.

Create an external Segment boundary only for:

- duration or combined-complexity overflow;
- incompatible operation or reference authority;
- a required independent editorial choice;
- an endpoint or occupancy state that must be isolated; or
- a generation risk that cannot be controlled inside the current Segment.

Do not create one Segment per Shot, line, reaction, angle, or shot-size change.

## Classify every boundary

For each adjacent pair, author one row in `Continuity Review` only after answering:

```text
outgoing dramatic change -> completed and unfinished action phases -> performance phase
-> blocking/facing/gaze -> camera phase -> light/color -> sound tail -> incoming need
```

Use exactly these same-Scene modes:

| End state | Successor plan | Evidence scope |
| --- | --- | --- |
| Action, performance, blocking, facing, eyeline, entrance/contact, and camera phase are settled; a cut is motivated | `multimodal_reference` with a soft predecessor-last-frame reference | The last frame is temporal evidence; keep the Location master as world/population authority |
| Any of those phases remains unfinished | `video_extension` of the complete predecessor | The complete predecessor is converted to the official white-model proxy before every permitted extension; current Location/identity images restore appearance |
| The immediately prior same-Scene boundary already used either predecessor-media mode | reference-free `strong_coverage_reset` / `adjacent_coverage_reset` | Preserve semantic state and direct predecessor review, but submit no predecessor image/video; bind current Location/identity assets and open ECU/CU/MCU from a decisively new angle, viewpoint, and composition |

The two predecessor-media modes share one inheritance budget. After either one, the
immediately following same-Scene boundary must be the strong coverage reset. After
that reset, one later predecessor-media boundary is available again. A matched
tail, strict first-frame claim, or new Segment ID does not make a same-Scene
successor independent.

Use an independent `multimodal_reference` or `text_to_video` Segment only for a
genuine discontinuity such as a new scene, meaningful time/location change, or
approved state reset. State the dramatic and editorial reason.

## Track character occupancy across Segments

For every Location state chain, give each authorized or still-present independent
performer one Character Segment state. Separate `visible`,
`present_offscreen`, `occluded`, and `absent`. A close crop may change `visible` to
`present_offscreen` only through `must_remain_present` or an authored concealment;
it is not an exit. A prior non-absent character remains in every following Segment
until an explicit `exit`/reset. A character with prior `absent` may become visible
only through `re_enter` or an explicit reset.

Use `must_remain_visible` when the story requires the subject to stay readably in
frame throughout every internal Shot. Carry its established mark, body side,
wardrobe, injury, fatigue, and prop state. If the generated character disappears,
repair the first failing Segment rather than authoring a later unexplained return.

Treat screenplay Character Scene States as a floor, not a suggestion. Preserve
exact required visibility for individuals and closed ensembles. Never convert
`visible_every_shot` or `visible_in_required_shots` to `present_offscreen` because
a two-character foreground composition is easier. If the exact visible cast
conflicts with the four-performer-reference ceiling, change packing or action
complexity while keeping the upstream visible roles.

## Choose operation and evidence

For a soft same-Scene cut:

- bind the approved predecessor last frame as ordinary temporal evidence;
- bind the Location master for complete set and population authority;
- inherit the settled result state without replaying the completed behavior; and
- allow the motivated new Shot to evolve without claiming pixel-identical opening.

For a complete-predecessor extension:

- continue the next forward performance and action phase without replay;
- require `white_model_video_edit` on the first and every permitted extension:
  runtime turns the approved predecessor into a pure-white 3D structural proxy and
  strips all audio from it;
- use that proxy for motion, pose, camera, timing, spatial structure, and action
  phase only; and
- bind the current Location master and one high-resolution identity/appearance
  image for every declared role to restore final face, costume, texture, and color.

The white-model proxy is private generation evidence and never enters the final
timeline. The restored extension still consumes the one predecessor-media handoff;
it does not restart the inheritance budget.

For a strong coverage reset:

- wait for and semantically inspect the direct predecessor, but bind no predecessor
  frame, last frame, colored video, or white-model video into the provider request;
- preserve Character presence, position/condition, Location, prop, action-result,
  eyeline, and dramatic state in prose and current asset bindings;
- begin with `extreme_close_up`, `close_up`, or `medium_close_up`;
- preserve the declared eyeline axis unless a visible neutral move or motivated
  re-establishment authorizes crossing it, while decisively changing angle,
  viewpoint, composition, focal subject, or shot/reverse-shot relation so the
  opening cannot read as a continued stage master;
  and
- mark `Coverage Reset Requirement` exactly as
  `required: no_predecessor_media; opening=<first Shot Size>;
  camera_break=new_angle_new_viewpoint_new_composition`.

Do not interrupt unfinished action to create this reset. Finish/repack the action
inside the predecessor Segment or move the boundary before generation.

Provider media affects the whole Segment. A later internal Shot cannot deactivate a
bound roster or identity reference. Split the Segment after visible exits when an
exiting roster and an entering roster require mutually exclusive authority.

`medium_wide`, `wide`, and `extreme_wide` are never planning conveniences. Each
must be a labeled `position-change exception:` limited to the shortest readable
entrance, exit, crossing, approach, retreat, transfer between marks, or other
consequential relocation, followed by tight coverage.

## Preserve location state

Maintain one state chain per recurring physical location across the full film. An
inserted story, flashback, imagined sequence, or visit elsewhere does not reset the
latest physical state of that location.

Separate:

- `Temporal Evidence`: latest approved action, performance, gaze, character, and
  mutable-prop state;
- `World and Population Evidence`: Location master plus any later approved readable
  wide state needed for fixed furniture, installed props, landmarks, embedded NPC
  roster, population density, and off-screen world objects.

A close predecessor frame does not erase off-screen anchors or people. Permit only
changes caused by approved visible action or an explicit reset reason.

## Derive execution dependencies

After every boundary is creatively locked, state dependencies in readable prose
and tables inside `storyboard.md`:

- an independent discontinuity has no provider-output dependency;
- every same-Scene successor waits for review of its direct predecessor output;
- a soft cut consumes the approved provider last frame;
- an extension consumes the approved predecessor only through the mandatory
  white-model proxy with preserved audio;
- a strong coverage reset consumes semantic state but no predecessor provider
  media;
- a nonadjacent location revisit waits for the latest state source in its location
  chain even when the edit is a dissolve or time/place return.

These are planning dependencies, not permission to call a provider.

## Review semantically

Review each boundary from seven perspectives without creating separate ledgers:

1. story causality, knowledge, objective, tactic, and consequence;
2. audience point of view, reveal timing, and performance truth;
3. body, facing, gaze, prop, breath, mouth, and emotional inheritance;
4. camera, ensemble, light, color, and reference compatibility;
5. editorial punctuation, handles, and audio bridge;
6. Seedance operation, duration, reference load, and first-frame feasibility; and
7. continuity of every outgoing state into the incoming state.

Integrate the result into the Generation Plan, Segment Direction, Location State
Plan, and Continuity Review. Do not add a companion review artifact.

## Blockers

Mark `BLOCKER` when the plan is missing, generic, schedule-driven, cyclic, falsely
independent, missing an adjacent boundary, uses a soft frame as strict endpoint
control, chains two predecessor-media handoffs, fails to white-model the first
extension, fails to extend/repack an unfinished same-Scene phase before a mandatory
reset, opens a reset wider than MCU, permits inherited camera or color
reconstruction, replays a completed beat, omits world/population authority, depends
on unreviewed evidence, crowds a Shot without causal necessity, leaves an
interaction axis ambiguous, uses an unlabeled/decorative wider Shot, or chooses a
fallback that changes an approved story fact.
