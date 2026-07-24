---
name: virtual-production
description: "Directly compile the approved forest-animal storyboard.md into free-form Seedance prompts using this repository's bundled contracts, preserve exact forest Location and animal authorities, resolve provider media from a minimal private plan, and execute dependency-aware video generation. Use for Seedance prompt writing, prompt repair, materialization, or Segment generation without any external production Skill."
---

# Virtual Production

## Inputs and outputs

Read and enforce the
[Forest Animal Education Production Standard](../references/forest-animal-education-production-standard.md).
Read and enforce the
[Human-in-the-Loop Guided Workflow](../references/human-in-the-loop-guided-workflow.md).
Read the sole Storyboard authority:

```text
TASK_DIR/previsualize-cinematography/storyboard.md
```

Author every Seedance Prompt directly from the original request, that Storyboard,
current `assets/assets.json`, verified provider capabilities, and this folder's
bundled contracts. Do not invoke, load, delegate to, or depend on
`seedance-master-skill` or any other external Skill.

For each Generation Segment, write only:

```text
TASK_DIR/.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
TASK_DIR/.pending/virtual-production/seedance-segment-plans/segment-NNN.json
```

The Markdown file is the exact provider Prompt. The JSON file is private transport
metadata for validation, asset resolution, scheduling, and API parameters. Never
copy private-plan fields into the Prompt.

These are the minimum authored runtime pair: one model-facing Prompt and one
machine-facing plan. Do not add a Prompt draft, wrapper, compile manifest, trace,
compatibility packet, review report, or approval artifact. Derived execution state
exists in memory only, not as another file or creative authority.

## Provider Prompt contract

Read [natural-language-seedance-prompt.md](references/natural-language-seedance-prompt.md).
Then read [seedance-2-prompt-guide-contract.md](references/seedance-2-prompt-guide-contract.md).
These repository-local contracts are the complete Prompt-authoring authority.
Author the Prompt by cinematic and model-facing judgment. There is no
required heading, section order, paragraph count, total Shot count, consecutive
Shot numbering, word count, vocabulary list, or sentence pattern. A private
dialogue cue requires its owning `Shot N:` section. Use event order instead of
precise second ranges and keep each Shot locked or on one dominant camera move.
The author may use prose, bullets, numbered Shots, continuous action, cuts,
or another form when it best communicates the intended result. The Storyboard is
creative authority, not a template for Prompt paragraph count.

Preserve every Storyboard `Shot Size` as exact camera authority. Carry
`extreme_close_up`, `close_up`, and `medium_close_up` into explicit model-facing
framing; never widen a tight Shot merely to show the whole set, prove that
off-screen roles still exist, or simplify ensemble generation. A
`medium_wide`/`wide`/`extreme_wide` Shot remains legal only for the Storyboard's
authored spatial reason. Virtual production may clarify execution but may not replace
attention-led close coverage with a frontal all-cast master.

Prompt authorship still aims to communicate the intended subjects, action,
performance, space, references, continuity, dialogue/audio, visual finish, and
landing. Most are semantic directing goals evaluated by virtual production and human
review. Python searches only the small auditable layer defined below: provider
tokens, priority-ordered exact reference declarations, the exact operation
instruction, population/global locks, the official `()`/`<>`/`{}`/`【】` notation
and its music/subtitle policies, curly-brace dialogue ownership, and the absence of
precise second ranges.

For every forest Segment, including `video_extension`, bind its approved dressed
Location master together with the required
independent performer identity/state references. The Location image owns
architecture, materials, topology, every production-design-authored fixed-set
element, vegetation, landmarks, lighting state, and embedded animal population.
Express those responsibilities in the
Prompt only when and where virtual production judges useful; no sentence, placement,
or repetition rule applies. Do not bind an embedded NPC
again as a separate character, and never let a speaking or story-active performer
inherit identity from the Location image. Never rely on Seedance to invent fixed set
elements or embedded population, and never treat a close-up
crop as their removal from the set.

Never accept a provider-invented forest redesign. Preserve animal species,
topology, relative scale and markings; forest layout, screen direction, paths,
vegetation, weather, time, light, moisture and ambience; and every authored change
across the Location chain.

Also bind temporal evidence when the Segment continues or revisits state. Keep the
authorities separate: predecessor video/last frame owns only the recent action,
pose, gaze, mutable-prop, and camera phase it can prove; the Location master owns
the full set and embedded population, including what the predecessor crop does not
show. Preserve the approved embedded population and independent-performer
authority by including the private plan's exact `population_lock_en` sentence once
in the Prompt.

Permission to appear is not proof of continued presence. Compile the Storyboard's
Character Segment states into the private plan and put every exact
`prompt_presence_lock_en` after the population lock. Within one Location state
chain, carry every character whose latest outgoing presence is not `absent`.
`must_remain_visible` covers every internal Shot and forbids exit, disappearance,
full occlusion, or replacement. `must_remain_present` may allow a named crop or
occluder but never a physical exit. Only `exit` or `reset_with_reason` may produce
`absent`; only `re_enter` or a justified reset may make an absent established
character visible again. Preserve the row's position, injury, and condition. Reject
any private-plan chain that silently drops a still-present character.

The Storyboard state row is exact upstream authority, not a hint. Virtual production preserves
its asset, source, incoming/outgoing presence, rule, required visible Shots,
occlusion, condition, and transition cause exactly, including for closed-roster
ensembles at group level. Named/story-active individuals retain strict identity,
injury, position, and condition. NPC/anonymous ensembles do not receive
member-by-member audit authority: exact member count, species mix, and individual
NPC identity drift are non-blocking when the same crowd/court field remains
continuously present. It may clarify model-facing prose but may not turn a required visible
individual or group into `present_offscreen` for reliability. Reference overload
returns to cinematography for repacking; it is never repaired by deleting a
visibility obligation.

Temporal evidence never substitutes for identity evidence. Every provider-renderable
role, including a physically present audio-only role, every NPC ensemble, and every role
outside the current crop, must bind an asset-catalog identity or approved
appearance-state image in the same Seedance request. Internal IDs, Prompt prose,
and voice samples are audit/audio metadata, not visual identity inputs. The
identity image owns who the role is; temporal evidence owns recent pose, position,
action phase, camera, and continuity state.
Describe both as the same subject and forbid duplicate instances. For a closed NPC
ensemble, exact generated member counts, species mix, and member-by-member identity
drift remain non-blocking. Keep `remain_absent` roles in the internal state machine
and review gate only; submit neither their IDs nor their positive identity images.
Provider reference media is request-wide and cannot be deactivated by a later Shot.
When one closed roster must exit and another must enter with mutually exclusive
visual authority, place the completed exit at a Generation Segment boundary. The
first Segment binds only the exiting roster; the dependent successor omits that
reference and binds only the entering roster. Never claim that Shot wording can
turn off a reference that was submitted with the same provider request.

Derive extension quality policy from the complete ordered private-plan chain and the
verified project policy. Every permitted `video_extension`, including the first,
uses `white_model_video_edit`: runtime strictly edits the approved
predecessor into a pure-white 3D white-model video, replaces its generated audio
with the predecessor's original synchronized audio, and passes that white-model
video as the successor's temporal `@Video` input. The Segment operation remains
`video_extension`; the preprocessing edit is not final footage. Its temporal
binding declaration must identify the input as a white model. Because the proxy
intentionally removes appearance, bind the Location master and a current
high-resolution identity or appearance
image for every declared role. The white model owns motion,
pose, camera, timing, and structure only. Missing image authority is a preflight
blocker.

## Private execution plan

The private JSON plan may contain only deterministic execution authority:

- source Storyboard hash and Segment identity;
- duration, operation, dependency, seam, and predecessor evidence;
- location state chain and relationship, exact temporal/world binding roles,
  embedded NPC roster, Segment-authorized independent performers, and one readable
  population-lock sentence;
- one Character Segment state per authorized independent performer plus any
  explicitly absent character being held out, with latest state source, incoming
  and outgoing presence, legal transition, required visible Shots, allowed
  occlusion, position/injury condition, transition cause, and exact Prompt presence
  lock;
- provider-token to asset-namespace mapping;
- exact dialogue ownership needed for validation;
- final visible/sound state and editable hold;
- fixed provider parameters.

It also carries one authored `prompt_contract` and one exact Prompt declaration per
binding. The contract records language, operation wording, reference priority,
global constraints, the official music/effect/dialogue/subtitle delimiters,
background-music and generated-subtitle policies, no precise second ranges, and
one dominant camera move per Shot. Python never writes these strings into the Prompt;
the virtual-production author places them verbatim.

Virtual production authors this plan from `storyboard.md`. Python may parse, validate,
hash, resolve catalog URLs, and reject disagreement. Python may not invent, copy
into place, summarize, rewrite, or fill missing Prompt prose, Shots, dialogue,
references, continuity, or creative fields. The private plan may retain storyboard
Shot traceability for scheduling and media scope, but its `shot_count` does not
prescribe the Prompt's total Shot count. Python validates only the small auditable
reliability layer; it does not validate other headings, paragraphs, total Shot
numbering/count, descriptive vocabulary, or word count.

## Materialization and generation

Treat each not-yet-generated Segment as one human-confirmed production unit. Before
its provider call, present the compact before-video card: which video, how it
starts, which characters are present, what happens and is said, the forest state,
how it ends, and what follows. Keep exact Prompt text, hashes, payloads, provider
records, and execution JSON internal unless requested. Pause. Generate only that
one new Segment after explicit confirmation, and pass
`--human-confirmed-segment SEGMENT_ID`.

Do not batch two new Segments, even when both are independent or share one wave.
Existing completed Segments may be reread during a reconciliation run because that
does not call the provider. Do not automatically retry a create, moderation,
terminal, or output failure. Report it, show the repair/retry plan, and obtain a
fresh confirmation.

Run capability validation, materialization, preflight, and generation only after
the Prompt passes those binding checks and the private plan passes its transport
checks. Every provider-renderable Character Segment state receives a catalog
identity/appearance image binding, including physically present offscreen,
audio-only, and NPC ensemble roles. Never drop an identity binding merely to meet a performer-count
target. Treat four independently referenced performers and four or five total
references only as composition-planning recommendations, never as provider maxima
or rejection thresholds.
`remain_absent` states are deliberately not provider-renderable: their positive
identity images and internal IDs must not be submitted.
Materialization may resolve the
manually authored token mapping to current catalog URLs, but it must reject missing
or mistyped assets directly. It must not create compatibility packets, review
drafts, rework JSON, or Prompt text. Machine-readable catalog facts remain
transport authority and do not define a required provider-prose structure.

Do not persist a derived execution-plan file, copied Prompt, provider request,
create response, poll response, artifacts manifest, generation-state file, or
generation-summary file. During one active attempt, keep only the single mutable
submission record needed for crash recovery. On failure, replace it with one
`failure-record.json` plus any media needed to diagnose the failure. On success,
the Segment generation directory contains exactly:

```text
video.mp4
last-frame.png
production-record.json
```

The production record is the sole compact audit record for the Prompt/plan hashes,
request hash, provider attempt, source URLs, media probe, and audio policy.
Materialization and generation summaries go to standard output only.
Incremental boundary prechecks run metrics-only in memory. Any visual review aids
must live in a fresh operating-system temporary directory and be deleted after
inspection; never add them to a Segment or task directory.

Use the Storyboard's one-hop inheritance budget unchanged. One same-Scene boundary
may use a soft predecessor-last-frame image after a settled motivated cut or a
white-model complete-predecessor extension for unfinished action, performance,
blocking, gaze, entrance, or camera phase. The immediately following same-Scene
boundary must use `strong_coverage_reset`: still wait for and inspect the exact
predecessor, but submit no predecessor frame/video, keep semantic state through
current Location/identity assets, and enact the Storyboard's ECU/CU/MCU opening
from a decisively new angle, viewpoint, and composition. After that reset, one
later inherited boundary is available again. Never cut unfinished action to force
the reset; repack or complete the phase first.

The white-model quality reset changes which predecessor representation is submitted
for every extension; it is not a final-film Segment and does not reset the
one-hop inheritance budget.

That review evaluates semantic completion, not frame-exact obedience to every
planned internal-cut second or centimetre-level movable-prop mark. A Segment may be
accepted when Shot order, causality, exact speaker/dialogue, required actions,
identity, fixed set, population, and usable ending are intact even if an internal
cut lands earlier/later or a movable prop settles at an adjacent, stable, reachable
position. Do not regenerate only to force an otherwise valid take onto the planned
timestamp or prop coordinate. Timing remains hard when it controls a causal gate,
dialogue/action completion, authored transition or sound synchronization. Placement
remains hard when it changes ownership or story function, loses/duplicates the prop,
breaks a fixed anchor, creates impossible geography, or prevents the next action.

After an accepted variation, the observed predecessor tail becomes temporal
authority. Recompile or explicitly revalidate the successor Prompt so its incoming
action and mutable-prop description use the actual final state; never preserve a
planned landing in prose when the accepted video visibly landed elsewhere.

After every provider attempt, inspect the complete picture and sound, run direct
review, present the compact after-video card, and pause even when the result is
`NO_ISSUES`. Report the result, material differences, and one recommended next
action; do not dump internal JSON. Only the human may accept the attempt, request
changes, authorize a retry, or approve preparation of the named successor.
Acceptance does not authorize that successor's provider call.

Runtime enforces this as a live predecessor-observation gate rather than trusting
the planned wave. Before any serial successor, it stops and exposes the exact
predecessor video, current `segment-NNN.md`, private plan, authorized performers,
and resolved character/Location bindings. Virtual production compares the actual
ending to the incoming action, identity, appearance, roster, props, location state,
camera phase, audio phase, operation, and every Character Segment state's required
incoming/outgoing occupancy. A character locked `must_remain_visible` must be
readably present throughout the actual predecessor and at its usable tail; a
temporary crop is accepted only under `must_remain_present` with the authored
offscreen/occlusion state. It corrects and rematerializes the current
Segment when necessary. Only after `seedance-video-review` returns `NO_ISSUES` may
the same active task pass `--observed-predecessor
segment-NNN=segment-MMM__attempt-NNNN`. The argument is transient and exact-attempt
scoped; do not write approval files. Missing/stale acknowledgement blocks preflight
and occurs before either white-model preprocessing or the successor Seedance call.

Also enforce nonadjacent location-state dependencies. A Segment returning to a
continuing set after an insert, imagined sequence, flashback, or another location
must wait for the last Segment in that location state chain. Bind the approved final
state for current performance, the Location master for complete world/population
authority, and the latest approved wide state when a visible set change makes that
additional evidence necessary. Choosing the readable anchor
frame is a continuity judgment made from direct review; Python may extract an
explicitly chosen frame and validate bindings, but may not choose, infer, or fill it.

An editorial dissolve or scene change does not by itself permit a set reset. New
camera coverage is allowed; unexplained furniture, landmark, wardrobe, injury, or
mutable-prop loss is not.

## Hard failures

Stop before provider submission when:

- the Prompt is empty or unreadable as UTF-8;
- Prompt provider tokens differ from the private plan or first appear after a Shot
  section;
- the exact population lock is missing or repeated;
- exact curly-brace dialogue and its readable speaker are outside the owning `Shot N:`
  section;
- the private plan and Storyboard disagree;
- the Prompt omits, broadens, or otherwise changes a Storyboard Shot Size, or turns
  selective close coverage into a frontal stage-like master;
- a private Character Segment state relaxes or changes a Storyboard individual or
  closed-ensemble presence/visibility obligation;
- a recurring location is scheduled as independent despite an unfinished location
  state chain, or a nonadjacent revisit is submitted before its state source review;
- the Location master is missing from any Segment set there, including an
  extension, or a tight predecessor frame/video is allowed to own the offscreen
  world or complete population;
- the embedded NPC roster differs from the Location authority or the Segment
  permits an undeclared independent performer;
- an authorized performer lacks a Character Segment state, a non-absent character
  is dropped from the next Segment in the same Location chain, incoming/outgoing
  presence disagrees, a required-visible Shot is omitted, or absence/reappearance
  lacks an explicit legal transition;
- an exact Character Segment presence lock is missing, repeated, or out of order in
  the Prompt;
- an embedded NPC is also bound independently, or a dialogue/story-active performer
  is missing its separate identity/state reference;
- any provider-renderable role or NPC ensemble, including a physically present
  audio-only/offscreen role, lacks an asset-catalog
  identity/appearance-state image in the actual request; predecessor media,
  voice samples, internal IDs, and Prompt prose do not satisfy this requirement;
- a `remain_absent` role is submitted as a provider ID or positive identity image;
- an asset's identity, injury, wardrobe, group, prop, location, or voice state
  conflicts with the Storyboard.
- a serial successor lacks the live exact-attempt predecessor observation, the
  actual ending contradicts its current Prompt/bindings, or the review found an
  issue that its owning department has not corrected.
- the exact current Segment has not received a live before-video confirmation,
  more than one new Segment would be generated, or a failed attempt is about to
  retry without a fresh confirmation.

Do not add deterministic Prompt-prose validators beyond these binding checks.
Creative review may request a better Prompt, but it must judge the generated video
and authored intent rather than enforce a textual template.

Do not repair upstream story or Storyboard authority locally. Do not assemble the
final film, replace native dialogue, mix final sound, or create subtitles.
