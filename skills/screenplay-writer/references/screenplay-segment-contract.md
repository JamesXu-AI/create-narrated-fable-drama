# AI-Narrated Fable Production Script Contract

This file owns the exact `screenplay.md` table syntax. Creative decisions belong
to `references/prompts/story_to_screenplay_gen.md`.

The writer releases exactly one UTF-8 file:

```text
screenplay-writer/screenplay.md
```

Apart from the title and section headings, all content is in Markdown tables.
This screenplay is the only creative authority between the Story and Storyboard.
Do not create a task JSON, narration JSON, or screenplay companion.

## Authorship Boundary

The writer authors every cell. Code may map authored values into validation records
and calculate pass/fail facts; it may not add, copy, compose, infer, default, or
alter creative content.

## Required order

1. title;
2. `## Production Information` table;
3. `## Characters` table;
4. `## Script` with consecutive Scene Unit sections;
5. `## Continuity Appendix` tables.

Use globally consecutive IDs: `segment-001`, `scene-001`, `state-001`,
`boundary-001`, `A-001`, and `L-001`.

## Title

Begin with:

```markdown
# Cinematic Widescreen Production Script: <title>
```

## Production Information

Use a two-column table with the exact header `Field | Value` and these exact rows:

```text
Production Type
Genre
Visual Style
Estimated Runtime Seconds
Target Country
Target Language
Aspect Ratio
Resolution
Speech Audio Source
Story Premise
Fable Meaning
Framing and Embedded Story Strategy
Speech Transition Strategy
Safety and Culture
Opening Event
Ending Event and Obligation
```

`Production Type` is `ai_narrated_fable_drama`; `Aspect Ratio` is `16:9`; and
`Speech Audio Source` is `seedance_native`. `Visual Style` uses the latest
conversation choice, or `3D Healing Animation` by default. `Resolution` uses the
latest conversation choice from `480p`, `720p`, `1080p`, or `4k`, defaulting to
`1080p`.
`Target Country` and `Target Language` are concrete authored values.
Opening and ending rows describe authored screen events, not promotional slogans.

## Characters

Use these exact columns:

```text
Entity ID | Character | Story Role | Narrative Function | Kind | Recurring | Group Role | Member Types | Narration | Description
```

`Story Role` is `lead`, `supporting`, or `npc`. `Kind` is `individual` or
`anonymous_ensemble`. `Recurring` is `yes` or `no`. `Narration` is `storyteller`,
`dialogue_only`, `both`, or `none`. Use `both` for a character such as a
grandfather who participates in the framing dialogue and tells the embedded story.
`Kind`, never dialogue ownership, decides visual treatment. Every
`individual`—speaking or silent—uses `none` for Group Role and Member Types and
receives one standalone character asset. An `anonymous_ensemble` is always silent,
uses one concrete Group Role, and uses a
semicolon-separated intended member-type list. This list is a writing/design
description, not a downstream frame-exact NPC audit. The screenplay tracks an
`anonymous_ensemble` as one group-presence field: its authored arrival, persistence,
visibility minimum, allegiance, and exit remain authoritative, while exact generated
NPC member counts, species mix, and member-by-member identity do not.
The art gate counts each `individual` as one standalone role visual type and each
`anonymous_ensemble` entity as one closed-roster group visual type, regardless of
how many ordered Member Types the group contains.
The project-wide default maximum is eight. An over-limit draft blocks image
generation and requires a story-judged keep/prune decision. Prune nonessential
ensemble groups, report the exact kept/pruned groups, remove every affected group
reference consistently, and rerun the gate. Require human confirmation only if the
cut would alter a dialogue role or story-required action.
One character storyteller uses one Entity ID across on-camera dialogue,
on-camera storytelling, off-camera storytelling, and the return to the framing
scene. Never add a second narrator row for the same voice.
Entity IDs and Group Role labels are project trace keys only. They never act as
model-facing identity evidence. Downstream Storyboard/Prompt compilation must
resolve every provider-renderable individual or ensemble—including physically
present offscreen and audio-only roles—to an actual identity or approved
appearance-state reference image. A `must_remain_absent` entity stays in the
internal state/review chain and must not be sent to the provider as an ID or
positive image.

## Script

After `## Script`, write consecutive units:

```markdown
## Scene Unit 1 — <dramatic label>
```

A Scene Unit is a 4–15 second screenplay planning unit. Cinematography may pack or refine
it for generation, and its Shot rows do not prescribe the number or formatting of
future Seedance Prompt passages. Several adjacent units may share one `Scene ID`;
a new unit does not imply a change of scene, place, or time.

### Scene Unit Information

Use a two-column `Field | Value` table with these exact rows:

```text
Segment ID
Scene ID
Slugline
Duration Seconds
Workload
Environment
Dramatic Purpose
Start State
End State
Incoming Boundary
```

`Slugline` uses `INT.` or `EXT.` plus a specific place and time. `Workload` is
`action_led`, `mixed_dialogue_action`, or `dialogue_led`. `Duration Seconds` is an
integer from 4 through 15.

### Shot Execution

Use these exact columns:

```text
Shot ID | Beat ID | Scale / View | Duration Seconds | Performers | Dramatic Change | Objective / Tactic | Visual Action | Important Reaction | Blocking / Movement | Gaze / Addressee | Completion State | Audience Focus | BGM / SFX / Ambience | Dialogue
```

One row is one story-facing shot.

#### Shot ID and duration

- `Shot ID` uses the globally consecutive Action ID sequence: `A-001`, `A-002`, …
- `Beat ID` is a globally unique ID such as `BEAT-001A`; it identifies the same
  row's dramatic change.
- `Duration Seconds` is a positive editorial estimate. It need not sum exactly to
  the Scene Unit duration and is not compiled into mandatory Prompt time windows.

#### Scale / View

Use one of:

```text
establishing | wide | medium | close_up | extreme_close_up | insert | reaction | pov
```

Choose the scale or viewpoint only when it serves spatial understanding, action,
reaction, revelation, concealment, emotional emphasis, or story legibility.
Do not write lens, focal length, camera height, coordinates, equipment, lighting,
routine camera movement, or edit implementation. The repository-local
cinematography and virtual-production departments own those.

The default grammar is attention-led and intimate:

- `close_up`, `extreme_close_up`, `reaction`, `insert`, and `pov` isolate the face,
  eye line, breath, wound, active body part, clue, or story-critical detail that owns
  the beat and must dominate the screenplay;
- `medium` is secondary and supports only a small shared action or two-person
  relation that cannot read in a tighter view;
- `establishing` and `wide` are position-change exceptions only. They may cover
  the shortest readable portion of a story-required entrance, exit, crossing,
  approach, retreat, transfer between marks, or other consequential relocation.

Do not use `establishing` or `wide` as an automatic Scene opener, continuity proof,
scenic/scale reveal, atmosphere beat, or frontal all-cast dialogue master. Every
`establishing`/`wide` row prefixes `Blocking / Movement` with
`position-change exception:` and names the start mark, path, landing mark, and
consequential relationship change. Do not author consecutive
`establishing`/`wide` rows. The next Shot returns to
`close_up`/`extreme_close_up`/`reaction`/`insert`/`pov` on the decisive face,
eyes, hand/paw, clue, or reaction. Across the complete screenplay, those tight
attention views outnumber `medium`, `establishing`, and `wide` combined.

#### Performers, action, reaction, and movement

- `Performers` is a comma-separated list of declared Entity IDs, or `none` for a
  pure environment/object shot.
- `Dramatic Change` states what becomes different in story knowledge, pressure,
  relationship, expectation, decision, or result during this shot.
- `Objective / Tactic` states what the active performer is trying to achieve and
  the playable tactic used now.
- `Visual Action` contains only visible, filmable present-tense behavior.
- `Important Reaction` identifies the reacting entity and its readable response;
  use `none` only when the shot genuinely contains no important reaction.
- `Blocking / Movement` states origins, destinations, screen-space relationships,
  crossings, stops, turns, and resulting positions. `none` is valid only for a
  truly static object/environment shot.
- A Shot normally names one visible dramatic subject or one speaker/listener pair.
  Additional physically present roles remain continuous through gaze, foreground
  edge, off-screen sound, or later reaction rather than forcing a full-cast frame.
  Any larger visible group must be indispensable to the current causal action.

#### Gaze / Addressee

Declare every visible performer's meaningful gaze as:

```text
<entity-id> -> <entity-id|object|place|self|narration> (<facing and gaze behavior>)
```

Write each relation exactly as
`owl -> rabbit (facing=across the table toward Rabbit, gaze=holds Rabbit's eyes)`.
Separate multiple relations with `<br>`. The camera is never an addressee.
For O.S./V.O. dialogue use `not_visible` facing/gaze language. The dialogue
speaker's target here is the authoritative addressee for that Line.
Across interactive Shot rows, preserve opposed look directions that can compile to
one stable A/B eyeline axis. Do not alternate screen direction, mirror marks, or
silently cross the axis.

#### Completion State

Use exactly one prefix:

```text
completed: <observable settled result>
open: <unfinished action phase that must continue>
```

This cell answers whether the shot action has completed. The final shot of a unit
may use `open:` only when the outgoing boundary requires `continuous_motion`.

#### Audience Focus

State the one action, reaction, clue, relationship change, or consequence the
audience must register now. Do not restate the Scale / View cell.

#### BGM / SFX / Ambience

Use `none` or one or more authored cues separated with `<br>`:

```text
BGM ENTERS: <character and dramatic function>
BGM EVOLVES: <audible change and reason>
BGM STOPS: <dramatic stop point>
BGM STING: <brief accent and event>
SFX: <source and exact audible event>
AMBIENCE: <specific environmental bed or change>
SILENCE: <what drops out and why the silence matters>
```

Every Scene Unit contains at least one non-`none` audio cell.

#### Dialogue

Use `none` or exactly:

```text
L-001; speaker=<entity-id>; mode=<delivery-mode>; gate=<visible or audible trigger inside this shot>; transition=<breath, reaction, J-cut, L-cut, action result, or silence handoff>; delivery=<playable cue or none>; text="<exact target-language words>"
```

Valid delivery modes are:

```text
on_camera_dialogue | on_camera_storytelling | off_camera_storytelling |
external_voiceover | embedded_character_dialogue
```

Each shot holds at most one Line. Every line must pass the shared strict
speech-rate gate in its owning Shot: at most 4.0 CJK characters per second and at
most 2.6 non-CJK words per second, plus 0.25 seconds of line start/end allowance.
A fast line blocks screenplay release; shorten it or give the Shot more time.
The `gate` states why speech begins. The
`transition` states how the current voice enters naturally from the prior voice,
silence, or narrative layer. The speaker must be a Performer for on-camera speech
or have an off-screen/voice-over staging declaration. Its addressee comes from the
same row's `Gaze / Addressee` cell. Dialogue is exact production authority.

An on-camera mode requires `Presence=on_screen`. An off-camera storytelling mode
requires `Presence=off_screen` or `voice_over`. Only a `storyteller` or `both`
character may use a storytelling mode. Every speaker or delivery-mode change
requires a completed phrase, breath, listener reaction, action result, J-cut,
L-cut, or authored silence. State the listener's closed-mouth behavior and
reaction in the Shot. Never cut mid-word or give an off-camera storyteller's words
to a visible character's mouth.

### Character Staging

Use these exact columns:

```text
Entity ID | Presence | Appearance | Trigger | Entry Path / Opening Position | First Visible Shot | First Visible Moment | Landing Shot | Landing Moment / Result | Speaks | Lines | State Change | Action Shots
```

Every character used by the Scene Unit appears once.

- `Presence` is `on_screen`, `off_screen`, or `voice_over`.
- `Appearance` is `present_at_open`, `enters`, or `not_visible`.
- `present_at_open` uses `opening` as Trigger, a concrete opening position, and
  points First Visible and Landing to the first shot where the character is already
  visibly settled.
- `enters` names the causal Trigger, physical entry path, First Visible Shot,
  First Visible Moment, Landing Shot, and observable Landing Moment / Result. The
  referenced shot cells must
  actually show the trigger-to-entry-to-landing chain.
- Both moment cells describe observable events. They may use exact seconds,
  relative timing, event order, or no numeric timing. Python does not require or
  interpret a timing notation.
- O.S./V.O. uses `not_visible` for Trigger, path/position, First Visible, Landing,
  both moment fields, and Landing Result.
- `Speaks` and `State Change` use `yes` or `no`. `Lines` and `Action Shots` contain
  comma-separated IDs or `none`.
- A character that changes from on-camera storytelling to off-camera storytelling
  moves at a motivated Scene Unit boundary. The outgoing `Audio Handoff` owns the
  voice bridge; the embedded-world Unit stages that character as `voice_over` and
  keeps the character visually absent.

## Continuity Appendix

The appendix contains reference mappings only. It never repeats shot descriptions,
dialogue, movement, gaze, audience focus, or audio cues.

### Environments

```text
Environment ID | Logical Environment | Scene IDs | INT/EXT | Time Context | Environment Facts | Story Function
```

### Scenes

```text
Scene ID | Segment IDs | Primary Time | Primary Place | Narrative Event | Entry Boundary | Entry Reason | Continuity Reference Segment | Continuity Reference Reason
```

### Scene Dramatic Contracts

```text
Scene ID | Purpose | Character Objective | Obstacle | Power Relationship | Turning Point | Outcome | Spatial Progression | Exit Impulse
```

### Character Scene States

```text
Scene ID | Segment ID | Entity ID | State Source Segment | Incoming Diegetic Presence | Visibility Requirement | Required Visible Shots | Position, Injury and Condition | Transition Cause | Outgoing Diegetic Presence
```

This table is the upstream character lifecycle authority. It separates whether a
character still exists in the physical Scene from whether the current camera must
show that character.

`Incoming Diegetic Presence` and `Outgoing Diegetic Presence` are
`present_in_location` or `absent_from_location`. `Visibility Requirement` is one
of:

```text
visible_every_shot | visible_in_required_shots | may_be_offscreen | must_remain_absent
```

`Required Visible Shots` is an ordered comma-separated list of exact authored
Shot IDs, or `none`. `visible_every_shot` names every Shot in the Scene Unit;
`visible_in_required_shots` names at least one. `may_be_offscreen` is not an exit
and uses `none`; the Character Staging row remains present with an off-screen
declaration. `must_remain_absent` uses absent incoming/outgoing presence and
`none`.

`visible_every_shot` is reserved for events whose causal legibility depends on
continuous simultaneous visibility. It is not the default for every role that is
physically present. Shot/reverse-shot, close-up, reaction, insert, and POV coverage
normally uses `may_be_offscreen` for the cropped but still-present roles. Do not
convert presence continuity into a reason for a wide all-cast composition.

Every performer, speaker, silent story-active individual, and closed ensemble that
is physically present has a row. A character with outgoing
`present_in_location` must have a state row in the next Scene Unit of the same
Scene even when outside the crop. Its `State Source Segment` is the latest prior
row and its incoming presence equals that source's outgoing presence. A new camera,
close-up, generation limit, reference budget, or stability preference is never an
exit. Only the screenplay or an explicit user revision may relax a required
visibility row.

### Continuity States

```text
State ID | Parent State | Changed Facts | Change Reason
```

`state-001` establishes the complete opening. Each later state names its immediate
parent and records only changed story facts and their cause.

### Continuity Boundaries

```text
Boundary ID | From Segment | To Segment | From State | To State | Handoff | Transition | Dramatic Reason | Audio Handoff | Continuity Handoff
```

`Handoff` is `independent`, `state_match`, `continuous_motion`, or
`strong_coverage_reset`. Same-Scene units are serial. Use `state_match` after one
settled motivated predecessor-media cut; use `continuous_motion` when unfinished
action, entry, movement, facing, eyeline, or performance crosses one boundary.
After either inherited handoff, the immediately following same-Scene boundary must
use `strong_coverage_reset`: the predecessor is settled, the successor preserves
semantic state but opens with an ECU/CU/MCU from a decisively new angle, viewpoint,
and composition and does not request predecessor media. If action is unfinished,
repack the units rather than forcing the cut. A Scene/time/place discontinuity may
use `independent`.

`Audio Handoff` states what continues, stops, overlaps, or changes. When dialogue
becomes storytelling, storytelling becomes embedded-character dialogue, or an
embedded tale returns to its framing scene, it names the completed phrase or breath
point, listener reaction, J/L-cut behavior, mouth state, ambience crossfade, and
same-voice continuity.
