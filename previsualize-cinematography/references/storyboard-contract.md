# Single-File Cinematic Storyboard Contract

Cinematography releases exactly one UTF-8 file:

```text
previsualize-cinematography/storyboard.md
```

The Storyboard is human-readable production authority and the sole local
virtual-production source.
Do not create `storyboard-compile-manifest.json`, `storyboard.data.json`, a trace,
ledger, review object, or any second representation.

## Contents

- [Required order](#required-order)
- [Project Direction](#project-direction)
- [Generation Plan](#generation-plan)
- [Location State Plan](#location-state-plan)
- [Character Segment State Plan](#character-segment-state-plan)
- [Generation Segment](#generation-segment)
- [Continuity Review](#continuity-review)
- [Acceptance](#acceptance)

## Required order

1. `# Cinematic Storyboard: <title>`
2. `## Project Direction`
3. `## Generation Plan`
4. `## Location State Plan`
5. `## Character Segment State Plan`
6. consecutive `## Generation Segment N — <dramatic label>` sections
7. `## Continuity Review`

Use Markdown tables for exact mappings and concise prose for integrated direction.
Do not embed JSON or YAML.

## Project Direction

Use a `Field | Value` table that states runtime, aspect ratio, audience point of
view, visual progression, camera grammar, shot-size/intimacy grammar,
lighting/color grammar, production-design motifs, performance grammar, native-audio
grammar, and editorial rhythm. The shot-size/intimacy grammar must name the
project's tight-coverage baseline and the exact story conditions that permit a
wide view. Use the exact field name `Shot Size and Intimacy Grammar`. Every value
must be a chosen production decision, not a menu, slogan, or generic adjective
such as `cinematic`, `epic`, or `beautiful`.

## Generation Plan

Use one row per future Seedance video task:

```text
Segment | Screenplay Range | Scene | Duration Seconds | Operation | Predecessor | Seam | Internal Shots | Packing Reason
```

The Segment ID is internal traceability. Duration is an integer from 4 through 15.
`Operation` is `multimodal_reference`, `video_extension`, or `text_to_video`.
Several compatible internal shots may belong to one Segment. Do not create one
Segment merely because the view, speaker, reaction, or scale changes.
Choose the number of internal Shots by cinematic judgment. No fixed quota and no
downstream Prompt paragraph count follows from this table.

## Location State Plan

Use one row per Generation Segment:

```text
Location State Chain | Segment | Relationship | State Source | Temporal Evidence | World and Population Evidence | Persistent Anchors | Allowed Changes
```

`Relationship` is `independent`, `adjacent_continuation`,
`adjacent_coverage_reset`, `nonadjacent_revisit`, or `reset_with_reason`. A location returning after an
insert, flashback, imagined sequence, or another location is not independent when
its diegetic set state continues. It must name the latest prior Segment in the same
state chain as `State Source`.

The two evidence columns separate facts that one image or video may not show
together:

- `Temporal Evidence` names the latest approved final state for current action
  phase, performance, gaze, character, and mutable-prop state;
- `World and Population Evidence` names the approved Location master and, after a
  visible set-state change, any latest approved readable wide state needed for
  furniture, fixed props, landmarks, embedded NPC roster, population density, and
  offscreen world objects.

For an independent opening, temporal evidence is `none` and world evidence is the
approved Location master. Every continuation and revisit retains that world
authority in addition to its temporal source. A predecessor video or close final
frame proves only the recently visible action state; it never owns the offscreen
set or complete population and never proves that an offscreen anchor or NPC
disappeared. When a visible change makes the original Location image stale, add the
latest approved readable wide state without dropping the Location identity.
For `adjacent_coverage_reset`, `Temporal Evidence` is exactly
`semantic_state_only_no_provider_media`: name the direct predecessor as State
Source for semantic review, but do not bind its image or video into the provider
request.
`Persistent Anchors` comes directly from the current production-design plan's
Location fields: `fixed_set_elements_en`, fixed obstacles, fixed-prop placements,
landmarks, and any screenplay-owned mutable prop that has not been moved or removed
on screen. Do not create or read a second location-continuity package. `Allowed
Changes` names only changes caused by an approved visible action or an explicit
reset reason.

## Character Segment State Plan

Use one row for every independently controlled character whose presence, absence,
occlusion, entrance, exit, or re-entry matters in a Generation Segment:

```text
Location State Chain | Segment | Screenplay Entity ID | Character Asset ID | State Source | Incoming Presence | Segment Presence Rule | Required Visible Shots | Allowed Occlusion | Position, Injury and Condition | Transition Cause | Outgoing Presence
```

`Incoming Presence` and `Outgoing Presence` are `visible`,
`present_offscreen`, `occluded`, or `absent`. `Segment Presence Rule` is exactly
one of:

```text
must_remain_visible | must_remain_present | enter | re_enter | reveal |
conceal | exit | remain_absent | reset_with_reason
```

`must_remain_visible` means the same character is readably present in every
internal Shot; camera crop, foreground action, or a new Segment may not erase it.
`must_remain_present` permits an authored crop or named occluder but not a physical
exit. A character can become `absent` only through an explicit `exit` or an
authored `reset_with_reason`. A later visible return from `absent` is `re_enter`,
never a silent new appearance. A character that remains in the same Location state
chain with non-absent outgoing presence must have a state row in every later
Segment until a valid exit occurs, even when the character has no dialogue or
primary action.

`Screenplay Entity ID` traces the row to the exact upstream `Character Scene
States` authority. Cinematography must preserve that table's two axes:

- `present_in_location` remains non-absent even when the camera crops the subject;
- `visible_every_shot` compiles to `must_remain_visible` in every internal Shot;
- `visible_in_required_shots` compiles to internal Shots covering every named
  screenplay Shot;
- `may_be_offscreen` may use a named crop or occlusion but never physical absence;
  and
- `must_remain_absent` compiles to `remain_absent`.

These are minimum visibility obligations for individuals and NPC ensemble fields.
For a named/story-active individual, identity, injury, condition, and position are
strict. For an anonymous NPC ensemble, the row controls group-level presence,
visibility, allegiance, and motivated entrance/exit only. Exact generated member
count, species mix, and member-by-member identity are explicitly non-blocking so
long as the group does not abruptly pop in, vanish, duplicate as a second crowd, or
replace a story-active role.
Cinematography may show additional authorized roles, but it may not move a required role
off-screen to reduce reference load or generation risk. Every provider-renderable
role declared in the Segment state plan—including physically present offscreen and
audio-only roles—must receive its asset-catalog identity/appearance-state image in
the downstream request; an internal ID, voice sample, or predecessor image cannot
substitute. A `remain_absent` role stays internal-only and contributes neither ID
nor positive image to the provider request. If all
required identity, world, temporal, prop, and voice media exceed a verified provider
limit, repack the Generation Segment while preserving the visible composition.

`State Source` names that character's latest prior state row in the same Location
state chain. The current incoming presence must equal that source's outgoing
presence. `Required Visible Shots` names exact internal Shot numbers; for
`must_remain_visible` it contains every Shot. `Allowed Occlusion` is `none` or one
specific spatially stable occluder/crop rule. `Position, Injury and Condition`
carries identity state such as the injured elephant's bandaged leg, body side,
weight-bearing limit, and established mark. `Transition Cause` is `none` for a hold
and a concrete visible action, motivated cut, or declared ellipsis for every state
change.

## Generation Segment

Each Segment contains these sections in order.

### Segment Direction

Use a `Field | Value` table with:

```text
Segment ID
Screenplay Scene and Units
Duration Seconds
Dramatic Change
Audience Point of View
Scene and Environment
Incoming State
Outgoing State
Operation
Predecessor and Evidence
Continuity Requirement
Coverage Reset Requirement
Location State Chain
Temporal Continuity Evidence
World and Population Evidence
Authorized Population
Character Segment States
Required Presence Locks
Persistent Anchors
Anchor Visibility Requirement
Style and Image Quality
Concise Constraints
```

### Reference Plan

Use:

```text
Provider Token | Provider Role | Asset Namespace | Readable Subject | Purpose | Shot Scope | Forbidden Inheritance
```

Provider tokens use `@ImageN`, `@VideoN`, or `@AudioN`. Each token gets one clear
purpose stated in natural language. `Asset Namespace` is internal runtime mapping;
`Readable Subject` is the human-facing character, place, prop, or voice name virtual production
must use. A token may be repeated only when it has genuinely separate purposes.

The Location token owns the dressed set and its production-design-approved embedded
NPC population. Do not bind those NPC assets again. Bind every required
`independent_performer_asset_ids` character or ensemble separately for identity,
state, and performance. If an embedded NPC must speak, enter or exit on cue,
interact, change state, carry a directed gaze/reaction, or preserve individual
identity, stop and return the classification to production design.

Every Segment set in a Location binds that Location master across every internal
Shot, including a video extension. `Authorized Population` names the exact embedded
population already inside the Location plus the independent performers allowed in
this Segment. No predecessor frame or video may authorize a new person, animal,
silhouette, reflection, or distant bystander.

Every authorized independent performer has one Character Segment state row. Also
retain any prior non-absent character from the same Location state chain, even when
that character is temporarily offscreen or occluded. `Required Presence Locks`
translate those rows into readable, observable constraints: who must remain visible,
who remains physically present outside the crop, who may be hidden behind which
occluder, and which explicit event authorizes entrance, exit, reveal, concealment,
or re-entry.

For a serial successor, `Predecessor and Evidence` and `Temporal Continuity
Evidence` explicitly state that virtual production must inspect the actual approved
predecessor before submitting the successor and adapt the current Segment when its
real landing, action phase, prop position, character state, camera, or audio differs
from the plan. The successor's Reference Plan must make every character/Location
input auditable during that check. Every video extension, including the first, uses
the white-model quality reset: its `@Video` is structural/motion evidence only,
while the Location master and one current high-resolution identity/appearance image
for every declared role restores the final look.

`Coverage Reset Requirement` is `not_required` unless the immediately prior
same-Scene boundary used either a soft last-frame reference or an extension. The
next Segment uses the exact value
`required: no_predecessor_media; opening=<first Shot Size>;
camera_break=new_angle_new_viewpoint_new_composition`. Its first Ordered Shot must be
`extreme_close_up`, `close_up`, or `medium_close_up`. This is a camera/coverage
reset, not a story-state reset, and its `Transition and Camera` cell must name the
decisive new angle, viewpoint, composition, or camera side. If the predecessor
action is unfinished, repack or finish it before this boundary.

### Ordered Shots

Use one row per ordered internal shot:

```text
Shot | Screenplay Shot | Shot Size | Transition and Camera | Subject Action and Expression | Space, Blocking and Gaze | Persistent Anchors | Lighting and Color | Dialogue and Native Audio | Landing and Edit
```

For every Shot:

- set `Shot Size` to exactly one of `extreme_close_up`, `close_up`,
  `medium_close_up`, `medium`, `medium_wide`, `wide`, or `extreme_wide`;
- treat `extreme_close_up`, `close_up`, and `medium_close_up` as the normal scale
  for decisive faces, eye lines, breaths, paws/hands, wounds, clues, reactions,
  and educational details. Use insert/reaction/POV intent inside the camera and
  action fields while retaining one physical Shot Size;
- use `medium_wide`, `wide`, or `extreme_wide` only when the current Shot must
  reveal new geography, scale, full-body mechanics, entrance/exit travel, or a
  changed spatial relationship. Do not use a wide frame merely because a Scene or
  Segment begins, because several roles remain physically present, or because the
  set has not appeared recently;
- preserve or tighten screenplay `close_up`, `extreme_close_up`, `insert`, and
  `reaction` intent. Compiling any of them to `medium_wide`, `wide`, or
  `extreme_wide` is forbidden;
- do not author three consecutive `medium_wide`/`wide`/`extreme_wide` Shots unless
  each row names different indispensable spatial information. A frontal all-cast
  master, repeated set reveal, or generic continuity proof is never such an
  exception;
- author the transition and camera behavior the event needs; keep a Shot locked or
  give it one dominant move. Put a motivated camera change in the next Shot instead
  of stacking push, pull, pan, tilt, crane, and orbit instructions together;
- name the readable subject and exact visible action;
- refine story-bearing movement by body part, range, speed, force, and causal
  transition or inertia when relevant;
- preserve entrances, landing positions, gaze, addressees, listener reactions,
  wounds, props, and action completion from the screenplay;
- name which persistent set/prop anchors remain visible, which are temporarily
  outside the frame or occluded, and which later Shot re-establishes them;
- place exact dialogue verbatim beside its speaker and trigger; virtual production converts it
  to Seedance `{exact words}` notation without changing the authority text;
- state native ambience, effects, music, silence, and the settled landing;
- use editorial timing descriptions when they clarify the event. Keep exact source
  timing in planning authority, but virtual production must translate it into event order and
  natural rhythm instead of model-facing ranges such as `0-3 seconds`.

### Prompt Translation Notes

Use a short prose paragraph that states what virtual production must prioritize and what may
be compressed. It must not introduce new story action or repeat every Shot row.
It must not prescribe Prompt headings, paragraphs, Shot labels/count, movement
count, word count, vocabulary, or timing syntax.

Also state the media budget decision. Prefer four or five total provider references
when sufficient and order identity-critical references first, but treat those as
recommendations only. Bind an identity/appearance-state image for every
provider-renderable role, including physically present audio-only and offscreen
roles. Keep `remain_absent` states out of provider media. Repack only when the
complete required media set exceeds a verified provider capacity; never satisfy a
recommendation by dropping a role image.

## Continuity Review

Use one compact table covering adjacent edits and nonadjacent location revisits:

```text
Boundary or Revisit | From | To | Relationship | State Evidence | Persistent Inheritance | Audio Inheritance | Editorial Reason
```

Use a soft predecessor-last-frame image for one settled same-Scene cut or mandatory
white-model predecessor extension for one unfinished phase. After either, use
`adjacent_coverage_reset` on the next same-Scene boundary: semantic predecessor
review continues, but the provider receives no predecessor media and the new
Segment opens on strong tight coverage. Use independent generation only at a
genuine discontinuity. A nonadjacent revisit waits for its named state source
review even when the edit itself is a dissolve or a time-and-place return.
The return may choose a new camera, but it may not reset furniture, landmarks,
wardrobe, injury, mutable props, or character state without an authored cause.

## Acceptance

Accept only when:

- every approved screenplay Shot and Line appears exactly once;
- action, blocking, gaze, camera, light, sound, and landing describe one reachable
  event rather than separate checklists;
- entrances retain trigger, first visibility, path, landing, and witness response;
- injuries and consequences remain as clear as the screenplay requires;
- every camera behavior has a story reason and each Shot has at most one dominant
  camera move;
- every Ordered Shot declares one valid Shot Size; decisive faces, reactions,
  active body details, clues, and educational information receive tight coverage,
  while every medium-wide or wider Shot names indispensable spatial information;
- no screenplay `close_up`, `extreme_close_up`, `insert`, or `reaction` is widened
  to `medium_wide`, `wide`, or `extreme_wide`, and no Scene or Segment defaults to
  repeated frontal stage-tableau coverage;
- body action names the relevant part, degree, speed, force, and transition when
  those details matter, while emotion is visibly externalized;
- reference planning identifies one stable subject label and responsibility per
  token, puts the most identity-critical declaration first, normally stays within
  four or five references, and never independently references more than four
  performers;
- every Segment appears once in the Location State Plan;
- every Segment supplies Location-owned world/population evidence; every
  continuing or revisited location also names the latest earlier source in the
  same state chain and supplies temporal evidence;
- every authorized independent performer has one Character Segment state; every
  non-absent outgoing character continues into the next Segment in the same
  Location state chain until a visible exit or explicit reset, and no absent
  character reappears without `re_enter`;
- every Character Segment state traces to one screenplay Character Scene State,
  preserves diegetic presence, and meets or exceeds every upstream individual and
  closed-ensemble visibility obligation;
- no persistent anchor disappears across a revisit without a visible action,
  explicit reset reason, or a later re-establishing Shot after temporary occlusion;
- Generation packing serves the finished edit rather than bookkeeping;
- no field is mechanically filled, generic, repeated, or contradictory;
- the release directory contains only `storyboard.md`.
