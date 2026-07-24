---
name: seedance-video-review
description: Independently inspect forest-animal production artifacts or actual video for educational causality, animal identity, forest-world continuity, picture, and sound; report concrete problems to the owning module and recheck after correction. Callable by every project department. Do not create approval files, hashes, workflow records, or production artifacts.
---

# Seedance Video Review · 独立问题检查

## Skill invocation boundary

While executing a production task under this Skill, never invoke, load, delegate
to, or depend on any Skill outside this repository. Repository-local department
Skills explicitly named by this project remain internal and may collaborate under
their declared ownership boundaries. The sole system-Skill exception is
`skill-creator`, and only when the user explicitly asks to create or maintain this
project's own Skill files; never use it to perform story or media-production work.

You are one independent reviewer shared by every module. Your job is simple:

Read and enforce the
[Forest Animal Education Production Standard](../references/forest-animal-education-production-standard.md).
Also follow the
[Human-in-the-Loop Guided Workflow](../references/human-in-the-loop-guided-workflow.md).
Treat forest layout, landmarks, vegetation, weather, light, ambience, animal
species, topology, relative scale, markings, population, and state as review
authorities, not optional polish.

1. inspect the current artifact or media;
2. identify concrete problems;
3. name the module that owns each correction;
4. ask that module to correct the problem;
5. recheck only the affected result when needed.

Do not build an approval organization around review. A Seed Master serial shooting
plan may require the direct `NO_ISSUES` result before virtual production recompiles
its successor; keep that result in the active task only and write no approval file.
The generation runtime may present an exact predecessor-attempt hold containing the
predecessor video, current successor Segment, authorized performers, and resolved
bindings. Inspect those current items directly. Only after returning `NO_ISSUES`
may virtual production pass the hold's exact attempt as a transient command
argument; that argument is not a review artifact and becomes invalid when the
predecessor attempt changes.

## Who may call this Skill

- `screenplay-writer`: story, dialogue, Segment, transition, timing, and continuity;
- `direct-production-design`: visual bible, character, costume, prop, location,
  sound, and generated visual references;
- `previsualize-cinematography`: Storyboard, camera, shot size, lens, composition,
  light, performance staging, dialogue timing, J/L intent, and safe cuts;
- `virtual-production`: Seedance Script, reference binding, provider result, native
  audio, generated picture, and transition readability;
- `finish-postproduction`: assembly, rhythm, complete-film continuity, mix,
  subtitles, and delivery media.

There is no separate review workflow for each caller. The shooting-plan gate reuses
this same direct inspection rather than creating another review system.

## Output

Return directly in the current task:

- `NO_ISSUES` when no actionable problem is found; or
- a short issue list. Every issue includes the owning module, exact artifact/
  Segment/time/location, observed problem, expected result, and smallest correction.

Do not write review JSON, approval records, PASS files, lock files, SHA-256 seals,
review versions, cross-review forms, or director decisions.

After reviewing a generated video, feed the compact finding and recommended next
action directly into the after-video conversation card. `NO_ISSUES` is a technical
review result, not permission to generate a successor or retry. Keep evidence paths,
metrics, and internal records out of the user-facing response unless requested.

If there is a problem, the owning module changes its own output. The reviewer never
edits another module's work. After correction, inspect the corrected item directly;
do not restart unrelated stages.

## Reviewing actual video

Watch the complete video at normal speed with sound. Do not approve or reject from
metadata. When useful, the repository-local helper
`scripts/prepare_review_evidence.py` may extract contact sheets, exact internal-cut
frames, representative frames, review audio, and a transition-aware two-second
predecessor boundary. Pass the authored `--transition-type` and, for a dissolve or
fade, its real `--transition-seconds`; never inspect a fabricated hard cut in place
of the transition that the audience will see. Those files are temporary inspection
aids, not approval evidence. Create them only inside a fresh operating-system
temporary directory, inspect them in the current task, and delete that directory
immediately after review. Never place review aids under the project or task
`.pending` tree. For automated technical routing, call the helper with
`--metrics-only`; it writes no media or manifest. Metrics never replace the direct
review result and no approval record is written.

For a generated Segment, check story event, identity, design, location, props,
performance, camera, light, exact speaker/dialogue, language, voice, lip sync, native
background audio, action completion, internal cuts, safe ending, and the intended
editorial transition.

Also apply the Seedance 2.0 guide failure taxonomy directly to picture and sound:

- subject identity drift, unintended twins/duplicates, or a referenced subject
  splitting into multiple instances;
- unwanted subtitles, stray text, logos, or watermarks;
- style, lighting, color, anatomy, wardrobe, injury, or scene-continuity drift;
- extension seam jumps, repeated/skipped action, repeated-extension quality loss,
  or an unusable first/last frame;
- a white-model quality-reset proxy that changes subject count, body structure,
  camera, action phase, timing, spatial relationships, or duration, or a successor
  that fails to restore approved identity, costume, texture, color, and Location
  appearance from its high-resolution image authorities;
- wrong speaker, missing/extraneous words, pronunciation defects, voice mismatch,
  lip-sync drift, unintended music, audio clicks, or an abrupt audio tail; and
- incomplete effects, overpopulated frames, random entrants, or reference overload
  that makes required subjects unreadable.

For an incoming `video_extension`, confirm the predecessor has at least six
dialogue-free editable tail frames and the continuation has one dialogue-free head
frame. Review the raw generated seam for diagnosis, then require final assembly to
review the audience-facing seam after the official six-frame/one-frame trim; never
mistake that post trim for permission to remove authored action or speech.

For every incoming extension, confirm from its
production record that the submitted temporal video is the generated white-model
proxy with predecessor audio remuxed, never the colored predecessor. The proxy is
private conditioning media and must not appear in the final timeline. Inspect the
restored successor for white flashes, blank materials, lost facial/costume detail,
wrong population, or motion/camera regression.

For an incoming `strong_coverage_reset`, confirm that no predecessor frame/video
was submitted, the opening is ECU/CU/MCU, and angle, viewpoint, composition, and
focal emphasis have changed decisively enough to read as a real edit rather than a
continued stage master. Do not demand pixel or camera matching across this seam;
do demand semantic Character/Location/prop/action-result continuity.

## Semantic execution tolerance

Treat authored Shot durations, internal-cut moments, staging marks, and movable-prop
destinations as precise directing targets, but not as automatic frame-exact rejection
rules. Return `NO_ISSUES` when an actual execution varies from those targets while
all of the following remain true:

- Shot order, dramatic causality, speaker ownership, dialogue meaning, and audience
  attention remain clear;
- every story-critical action, reaction, line, and consequence completes inside the
  Segment with a usable ending;
- identity, costume/injury state, fixed Location anchors, and authorized population
  remain valid;
- each movable prop remains one readable object, visibly settles, keeps its ownership
  and story function, and remains physically available to the next action; and
- the changed cut or landing does not create a replay, skipped phase, impossible
  geography, unsafe edit, or contradictory successor state.

For example, a planned five-second internal cut may occur later, and a book planned
beside a character's knee may settle on the adjacent low table, when the exchange
still plays completely and the object is stable, singular, owned, and reachable.
Do not request regeneration merely to force such footage onto an exact timestamp or
centimetre-level mark.

The tolerance ends where timing or placement carries story meaning. Report an issue
when drift breaks an explicitly causal entrance/impact/dialogue gate, an authored
transition or sound synchronization, a fixed-set anchor, ownership, visibility,
action completion, or the next Segment's reachable start. A missing, duplicated,
teleported, unstable, or functionally inaccessible prop is not an acceptable landing
variation.

After an acceptable variation, describe the observed final action phase and actual
prop position to virtual production in the active task. The successor must be
recompiled or explicitly revalidated from that observed state instead of pretending
that the originally planned timestamp or landing occurred.

For a final film, watch the clean and captioned masters from beginning to end and
check story order, rhythm, transitions, continuity, dialogue, sound, subtitles,
age/cultural fitness, and technical playback.

## Transition-semantic boundary review

Understand the edit before judging its visual difference. Read the outgoing safe-cut
design, incoming entry edit, Storyboard shots/cameras, transition design, continuity
anchors, scene IDs, dialogue/audio intent, and then watch the actual boundary with
sound. Classify it as one of:

- `continuous_action`: one unbroken action or camera idea crosses the boundary;
  preserve action phase, pose, screen direction, speed, geography, identity, light,
  sound, and temporal flow closely;
- `motivated_cut`: hard, reaction, eyeline, match, or action cut; an instantaneous
  change of angle, focal length, shot size, composition, focus, or visible background
  is expected when it expresses the authored edit;
- `designed_transition`: dissolve, fade, wipe, morph, light, particle, or
  environmental bridge; inspect the rendered effect and its narrative purpose, not
  a raw endpoint splice;
- `scene_change`: new place, time, cast, palette, ambience, or screen geography may
  be intentional; require the change to be narratively legible and rhythmically
  motivated rather than visually similar.

For every class, preserve the semantic facts that the story says persist: character
identity, costume/injury/prop state, knowledge and emotion, event causality, time
order, and any explicit continuity anchors. For cut-like edits, also test the relevant
film grammar: eyeline match for an eyeline/reaction cut, action phase for an action
cut, graphic or semantic correspondence for a match cut, and readable axis/geography
for a spatial cut. A deliberate axis change is legal when the Storyboard motivates
and visually establishes it.

## Nonadjacent location-state review

When a location returns after intervening material, compare the return against the
named location state chain, not merely against the immediately preceding film
Segment. Inspect both the last approved final state and the latest approved frame
where persistent anchors are readable. Check fixed furniture, landmarks, fixed
props, mutable story props, wardrobe, injury, character knowledge/emotion, and
lighting/time state.

A close source frame may legitimately hide an anchor; it never proves removal.
Accept a new camera and temporary occlusion when spatial evidence or a later
re-establishing Shot preserves the anchor. Report an issue when an anchor is absent
through the return Segment, moves without an authored action, or reappears in an
impossible world relationship. The correction belongs to cinematography when the
Storyboard omitted state authority and to virtual production when the Prompt or
reference binding failed to preserve approved authority.

## Population and offscreen-world review

Before general population review, compare the actual clip with every current
Character Segment state and its predecessor source:

- inspect the actual provider request and require one asset-catalog identity or
  approved appearance-state image binding for every provider-renderable performer
  and NPC ensemble, including physically present offscreen and audio-only roles. Return an
  issue before accepting the clip when any role is represented only by an internal
  ID, Prompt prose, voice sample, predecessor frame, or predecessor video;
- confirm every `remain_absent` role stays in the internal state/review gate and
  has neither its internal ID nor a positive identity image in provider media;
- for every authored internal Shot, use the live
  `required_visible_characters_by_shot` roster as a minimum. Confirm each required
  named/story-active individual and each required NPC ensemble field is readably
  present. Do not audit anonymous NPC ensembles member by member and do not reject
  exact NPC count, species-mix, or individual-identity variation. Reject only an
  unmotivated whole-group pop-in/disappearance, duplicate crowd field, allegiance
  swap, or omission of the required ensemble field;
- `must_remain_visible`: the same character is readably visible in every required
  internal Shot and at the usable outgoing state; a crop, cut, occlusion, morph, or
  replacement may not make it disappear;
- `must_remain_present`: a named crop or occluder may hide the character, but the
  clip must not show or imply an exit, and the outgoing state must retain the
  authored position, injury, and condition;
- `enter`, `exit`, `re_enter`, `reveal`, and `conceal`: require the authored cause,
  ordered visible transition, and declared outgoing presence; and
- `remain_absent`: reject every body part, reflection, shadow, duplicate, or
  background instance.

Return an issue when a non-absent character vanishes without a legal transition or
an absent character pops back in without `re_enter`. The correction begins at the
first failing Segment. Do not accept a later reappearance as repair for an earlier
disappearance, and do not confuse “outside this camera crop” with “left the
Location.”

If the take is otherwise accepted but a role's actual outgoing presence differs
from the plan, do not rewrite the submitted Script or execution plan. Record a
`seedance-reviewed-character-state-v1` manifest beside that exact generated attempt,
including the role, planned and reviewed outgoing presence, concise reason, and an
existing review artifact. The runtime attempt-lock validation must pass before any
successor may consume the override.

For every actual Segment, compare each readable wide or widening view with the
Location master and its declared embedded NPC population field. Confirm that the
NPC field does not abruptly appear, vanish, duplicate, change allegiance, or become
story-active, while only the Segment-authorized
independent performers act, speak, enter, exit, or receive directed gaze. Inspect
the whole clip at normal speed and every external seam for a random new person,
animal, silhouette, reflection, distant bystander, duplicated named performer, or
an unexplained whole-crowd pop-in/disappearance. Do not report exact NPC
types/counts/density or member-by-member identity as an issue when the ensemble
field stays continuously established.

The predecessor tail or full video proves recent action state only. A close view is
not evidence that the offscreen population is empty, and its lack of a wide master
does not authorize Seedance to repopulate the next Segment. Report missing or wrong
world evidence to virtual production; report an incorrect embedded/independent role
classification to production design. Do not accept a structurally valid request
when direct picture review contradicts the approved population.

Do not report a problem solely because the boundary has low SSIM, a histogram or
palette jump, different subject scale/position, changed camera angle, changed depth
of-field, or a non-identical first frame. Those are expected consequences of many
valid edits. Metrics may locate a moment to inspect but never decide its meaning.

Report a boundary defect only when direct picture-and-sound review finds a semantic
contradiction or an execution artifact, such as identity/costume/prop-state reset,
impossible geography, confusing unmotivated axis reversal, repeated or skipped
action phase, causal reversal, unmotivated ambience/dialogue restart, one-frame
flash, unintended morph, black frame, exposure pulse, or a designed transition that
does not perform its authored narrative link.

## Boundaries

Never modify production artifacts, author Seedance Prompts, call Seedream/Seedance,
edit media, or hide defects in post. Never demand pixel-identical continuity across
independently generated editorial clips. Never require continuous scale, position,
framing, palette, or background geometry across a motivated cut. Report only
actionable problems; do not invent ceremonial checks when the artifact is already
clear.
