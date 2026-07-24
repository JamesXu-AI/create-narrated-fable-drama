---
name: previsualize-cinematography
description: "Turn an approved forest-animal all-table screenplay into one self-contained cinematic storyboard.md for Seedance-oriented previsualization. Use for forest geography, animal identity and scale, directing, performance, exact dialogue, blocking, gaze, shot design, camera, lighting, ambience, editing, reference planning, Generation Segment packing, duration, and continuity. Use the bundled video-cinematography subskill as the specialist authority for cinematic shot size and camera movement. Work from this skill's bundled contracts; release only storyboard.md."
---

# Cinematography Previsualization

Create one coherent, executable audiovisual plan while preserving the approved
forest-animal screenplay. Read and enforce the
[Forest Animal Education Production Standard](../references/forest-animal-education-production-standard.md).
Follow the
[Human-in-the-Loop Guided Workflow](../references/human-in-the-loop-guided-workflow.md).
Story meaning, animal identity, forest geography, performance truth, audience point
of view, and causal continuity govern every production decision.

## Cinematic camera-movement specialist

Use the bundled
[video-cinematography skill](video-cinematography/SKILL.md) as this department's
specialist for cinematic shot size and camera movement.

- Read its `SKILL.md`,
  [movement reference](video-cinematography/references/movements.md), and
  [storyboard field guidance](video-cinematography/references/storyboard.md)
  completely before designing or revising camera movement.
- Within the specialist scope of shot size, camera position and angle, movement
  type, movement path, movement speed, movement height, movement radius, focal
  treatment, start frame, and landing frame, `video-cinematography` overrides
  conflicting camera-movement guidance elsewhere in this folder.
- Keep that priority scoped to cinematic camera craft. It does not own story,
  dialogue, character identity, forest geography, population, blocking,
  continuity, Segment boundaries, provider constraints, duration authority,
  release format, or the human-in-the-loop workflow.
- Convert each selected move into observable direction: dramatic reason, subject,
  start composition, path and speed, framing change, and stable landing
  composition. A movement with no story or emotional purpose is not cinematic.
- Use a close, subjective shot-size baseline. Faces, eyes, breath, paws/hands,
  wounds, clues, reactions, and educational details should normally own
  `close_up`, `extreme_close_up`, or `medium_close_up` frames. A new Scene or
  Segment does not automatically require a wide establishing view.
- Treat `medium_wide`, `wide`, and `extreme_wide` as gated spatial tools. Each one
  must reveal indispensable new geography, scale, full-body mechanics,
  entrance/exit travel, or a changed relationship that a tighter frame cannot
  communicate. Do not repeatedly reopen the whole set after it is established.
- Never stage dialogue or explanation as a frontal all-cast proscenium tableau.
  Use depth, asymmetric blocking, singles, reaction close-ups, inserts, POV, and
  off-screen sound while retaining reconstructable geography.
- A combined move authorized by `video-cinematography` is one choreographed camera
  move: name its dominant component, keep the secondary component subordinate, and
  give the combination one continuous start-to-landing path.
- Preserve forest-animal readability and child-safe visual comfort. Prefer
  animal-eye-height movement, stable horizons, controlled acceleration, and
  readable ensemble spacing. Use handheld shake, roll, rapid orbit, or aggressive
  height changes only when the approved dramatic beat specifically requires their
  emotional effect.
- Do not release the subskill's generic storyboard template or any separate
  movement document. Its decisions must be integrated into the single authorized
  `storyboard.md`.

## Release boundary

Release exactly:

```text
TASK_DIR/previsualize-cinematography/storyboard.md
```

Treat [the Storyboard contract](references/storyboard-contract.md) as the output
authority. Do not create a compile manifest, data companion, trace, ledger, review
object, provider Prompt, image, audio, video, or second storyboard representation.

## External SKILL policy

Work self-contained from this folder and ordinary tools.

- Do not invoke, delegate to, or depend on `seedance-master-skill` or any other
  external SKILL. There is no official, bundled, fallback, or convenience
  exception during production.
- Treat this currently invoked skill and all files bundled inside its folder as
  local implementation, not as an external SKILL call.
- Treat `video-cinematography` and its references as bundled local implementation
  under the specialist scope defined above, not as an external SKILL dependency.
- Pass this restriction into any delegated work. If completion would require an
  external SKILL, continue with local resources and ordinary tools or report a
  blocker; never call that SKILL.

## Authority

Apply this order:

```text
current user instruction -> approved screenplay -> approved production design and
continuity authorities -> video-cinematography for cinematic camera movement ->
this storyboard -> downstream Prompt
```

Preserve every approved Scene Unit, Shot, Line, duration, entrance, movement, gaze,
completion state, audience focus, sound cue, continuity handoff, identity,
relationship, climax mechanism, and ending. Add only the direction, performance,
camera, composition, movement, light, color, design treatment, sound, edit logic,
reference purpose, Segment packing, and continuity needed to execute them.

Do not rewrite screenplay meaning. Infer routine low-risk craft decisions. Return
missing or contradictory story authority to its owner when repair would change an
approved premise, identity, relationship outcome, climax, ending, speaker, line, or
causal event.

## Read bundled contracts

Read these files completely before authoring:

- [Forest Animal Education Production Standard](../references/forest-animal-education-production-standard.md)
- [Storyboard contract](references/storyboard-contract.md)
- [Directing, performance, and editorial craft](references/directing-performance-and-editing.md)
- [Cinematography and visual design](references/cinematography-and-visual-design.md)
- [Duration and pacing](references/duration-and-pacing.md)
- [Continuity and dramatic logic](references/continuity-and-logic.md)
- [Generation planning](references/generation-planning-contract.md)
- [Seedance planning constraints](references/seedance-planning-contract.md)
- [Video cinematography specialist](video-cinematography/SKILL.md), its
  [movement reference](video-cinematography/references/movements.md), and its
  [storyboard field guidance](video-cinematography/references/storyboard.md)

Also read, when relevant:

- [Screenwriting architecture and rewrite](references/screenwriting-architecture-and-rewrite.md)
  when the source is sparse, ambiguous, or contradictory. Use it to diagnose and
  author only permitted low-risk behavior, not to rewrite locked meaning.
- [Dialogue dramaturgy and performance](references/dialogue-dramaturgy-and-performance.md)
  and [dialogue coverage and blocking](references/dialogue-coverage-and-blocking.md)
  whenever the work contains speech, vocal reactions, active silence, or ensemble
  listening.
- [Frame occupancy, entrances, and exits](references/frame-occupancy-and-entrances.md)
  for any entrance, reveal, re-entry, exit, occlusion, reserved negative space, or
  forbidden occupant.

## Workflow

1. Read the complete approved screenplay and all upstream production-design,
   character, location, voice, and continuity authorities.
2. Build an internal semantic model of premise, theme question, point of view,
   knowledge flow, character objectives and tactics, power changes, causality,
   setup/payoff, climax, consequence, ending, and runtime. Do not release internal
   schemas or analysis as a companion artifact.
3. Lock one integrated director's system for performance, staging, camera, lens,
   composition, light, color, production design treatment, sound, pacing, and edit.
   Translate generic labels such as “cinematic”, “epic”, or “premium” into observable
   choices.
4. Compile the screenplay Character Scene States into a non-downgradable occupancy
   floor before choosing coverage or Generation packing. Plan foreground,
   midground, and background roles so every required individual and NPC ensemble
   field remains readable in its authored Shots. Apply exact identity/state locks
   only to named or story-active individuals. For anonymous NPC ensembles, direct
   group-level presence and motivated group entrances/exits without making exact
   member count, species mix, or member-by-member identity a continuity gate.
5. Write scenes and beats that preserve the screenplay and make every causal change
   playable. Treat each spoken line as:
   `trigger -> preparation -> exact line -> listener response -> changed state -> edit handoff`.
6. Design ordered Shots by dramatic event and audience attention. Keep each Shot
   locked or on one dominant motivated camera move. Declare one exact `Shot Size`
   for every Shot. Preserve or tighten every screenplay `close_up`,
   `extreme_close_up`, `insert`, and `reaction`; never widen one merely to keep all
   present characters in frame. Once geography is readable, cut closer to the
   face, reaction, point of view, or detail that changes the beat. Give every
   story-bearing action a subject, relevant body part, range, speed, force, causal
   transition or inertia, landing, and continuity handoff when those details matter.
7. Pack compatible ordered Shots into Generation Segments. When required visible
   cast exceeds the reference/action reliability budget, first simplify background
   motion, then use an approved closed-roster asset, then split at a motivated
   boundary. Moving an upstream-required role off-screen is not a packing option.
8. Resolve every Segment boundary, recurring-location state chain, temporal evidence,
   world/population evidence, persistent anchor, reference role, duration, audio
   handoff, dependency, and fallback before finalizing the plan.
9. Write one self-contained `storyboard.md` by creative judgment. Never use Python,
   a validator, or a template to invent missing creative fields.
10. Validate structure without rewriting authorship:
   ```bash
   python3 previsualize-cinematography/scripts/validate_storyboard.py --task-dir TASK_DIR
   ```
11. Reread the complete work as director, cinematographer, editor, performer, sound
    designer, continuity supervisor, and Seedance specialist. Repair the artifact,
    not merely the validation result.

## Hard execution rules

- Story drives camera, light, color, design, sound, and edit; presentation never
  changes narrative authority.
- One creative decision must have one consistent implementation across rationale,
  action, blocking, camera, sound, timing, reference planning, and edit.
- Use exact dialogue once, beside its owner, addressee, trigger, speech gate,
  delivery, active listener response, and landing. Only an active speaker receives
  speaking mouth movement unless overlap or off-screen speech is explicitly
  authored.
- Require planned native synchronized dialogue, breath, reaction, ambience, music,
  and effects. Do not describe a planned result as observed.
- Separate temporal evidence from Location-owned world/population evidence. Never
  let a close predecessor frame erase off-screen anchors or authorize new people,
  animals, silhouettes, reflections, or distant bystanders.
- Author one Character Segment state for every authorized independent performer and
  every absent, offscreen, or audio-only role referenced by the Segment; carry every
  non-absent character forward inside the same Location state chain.
  Distinguish `visible`, `present_offscreen`, `occluded`, and `absent`; a new camera
  crop is not an exit. Permit disappearance only through an authored `exit` or
  `reset_with_reason`, and permit return from absence only through `re_enter`.
  Use `must_remain_visible` with every internal Shot when a character such as an
  injured elephant must never drop out of the frame, preserving its exact position,
  injury, and condition.
- Preserve screenplay Character Scene States as non-downgradable minimum
  visibility authority for individuals and closed ensembles. Reliability may
  simplify background action but may not turn a required visible role into an
  offscreen role. Repack the Segment or use an approved closed-roster asset when
  the visible cast would exceed the performer-reference budget.
- Physical presence is not an instruction to compose a wide master. A tight crop
  may place a still-present role outside the frame under `must_remain_present`;
  only an upstream Shot-specific visibility obligation requires that role to
  remain readable in the current Shot. Satisfy a genuine simultaneous-visibility
  obligation with layered foreground/midground depth or an OTS edge when possible,
  not by defaulting the whole Scene to a frontal full-cast tableau.
- Reject three consecutive `medium_wide`/`wide`/`extreme_wide` Shots unless each
  one reveals different indispensable spatial information; revise the coverage,
  not merely the wording. Never broaden an upstream `close_up`,
  `extreme_close_up`, `insert`, or `reaction` when compiling it into Storyboard
  `Shot Size`.
- Treat predecessor evidence as temporal authority only. Bind a separate
  identity/appearance-state image for every provider-renderable role, including
  physically present offscreen and audio-only roles; internal IDs, voice samples, and predecessor
  media never own visual identity. Describe temporal and identity evidence as the
  same subject and explicitly forbid duplicates. Keep `remain_absent` roles only in
  the internal state/review plan and submit neither their IDs nor positive images.
- Give each reference one stable readable subject label and one declared purpose.
  Put identity-critical references first and normally use four or five total
  references, but treat both counts as recommendations only. If the complete
  identity/world/temporal/voice set exceeds a verified provider limit, repack the
  Segment; never omit a role image merely to hit a recommendation.
- Permit only one consecutive predecessor-media handoff, whether it is soft
  predecessor-last-frame evidence for a settled motivated cut or complete
  predecessor-video extension for an unfinished phase. The next same-Scene Segment
  must use `adjacent_coverage_reset`: retain semantic Character/Location/prop state,
  bind current Location and identity assets, submit no predecessor frame/video, and
  open with `extreme_close_up`, `close_up`, or `medium_close_up` from a decisively
  new angle, viewpoint, and composition. After that reset, one later inherited
  handoff is available again.
- Plan every permitted video extension, including the first, as a white-model
  quality reset: runtime strictly edits the predecessor into a pure-white 3D
  continuity proxy, while the successor binds the Location master and current
  high-resolution identity/appearance image for every declared role. Treat the
  proxy as motion, pose, camera, timing, and structural authority only; it is never
  final appearance or final-timeline media.
- Never use the mandatory coverage reset to interrupt unfinished action. Repack the
  current Segment, complete the action phase, or move the boundary before requiring
  the tight new angle.
- Preserve action-phase monotonicity: inherit a completed beat's result state without
  replay, and continue an unfinished beat only into its next forward phase.

## Acceptance and delivery

Accept only when every approved screenplay Shot and Line appears exactly once,
every scene and Segment changes dramatic state, all action and dialogue are
performable within duration, camera and coverage express point of view, entrances
and occupancy are testable, location/prop/identity/voice/audio continuity is
reachable, references have non-overlapping authority, and every boundary advances
without replay or unauthorized reset. Decisive faces, reactions, body details,
clues, and educational information receive tight coverage, while every wide Shot
earns its spatial function and no Scene reads as a filmed stage.

Release only `storyboard.md`. Stop before downstream Prompt compilation, provider
execution, media review, or postproduction.

After validation, present one concise video-phase plan: Segment order, how the next
video starts and ends, required characters, camera/action intent, forest continuity,
and the next proposed step. Accept natural-language edits. This is the preparation
for the first before-video confirmation, not a request to inspect Storyboard JSON
or approve every internal row.
