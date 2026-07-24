# Virtual-Production Contract

The sole creative input is `previsualize-cinematography/storyboard.md`. For each
Generation Segment, virtual production directly authors one exact natural-language
provider Prompt and one private execution plan. The Prompt is creative prose; the
plan is machine-readable transport authority. Neither may substitute for the other.

The exact provider Prompt is stored at:

```text
.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

It follows the free-form authorship boundary in
`natural-language-seedance-prompt.md`. No general heading, section, total Shot,
camera, word, wording, or timing syntax is prescribed. Matching `Shot N:` labels
are required only for dialogue cues whose exact ownership must be verified.
The private plan additionally supplies the exact operation instruction, ordered
binding declarations, and global constraint block required by the Seedance 2.0
Prompting Contract. Exact dialogue uses curly braces, and model-facing precise
second ranges are forbidden.

The private plan is stored at:

```text
.pending/virtual-production/seedance-segment-plans/segment-NNN.json
```

It must hold Segment identity, Storyboard hash, duration, operation, dependency,
provider-token mappings, dialogue ownership, final continuity state, and this
model-authored continuity authority:

```text
continuity:
  location_state_chain
  relationship
  state_source_segment_id
  world_binding_ids
  temporal_binding_ids
  embedded_npc_asset_ids
  authorized_independent_performer_asset_ids
  character_segment_states
  population_lock_en
```

Each `character_segment_states[]` row uses:

```text
character_asset_id
state_source_segment_id
incoming_presence
segment_presence_rule
outgoing_presence
required_visible_shots
allowed_occlusion_en
transition_cause_en
position_and_condition_en
prompt_presence_lock_en
```

Presence is `visible`, `present_offscreen`, `occluded`, or `absent`. Rules are
`must_remain_visible`, `must_remain_present`, `enter`, `re_enter`, `reveal`,
`conceal`, `exit`, `remain_absent`, or `reset_with_reason`. Every authorized
independent performer has one non-absent row. Inside one Location state chain, a
prior non-absent outgoing character must remain tracked until an explicit exit;
current incoming presence must equal the latest row's outgoing presence. Therefore
a character cannot disappear merely because a new Segment begins, and cannot
return from `absent` without `re_enter` or a justified reset.

Each private row must also match the Storyboard Character Segment State Plan
exactly for asset, source, incoming/outgoing presence, rule, required visible
Shots, allowed occlusion, position/condition, and transition cause. Virtual production cannot
relax an individual's or closed ensemble's visibility to reduce reference count or
stabilize a foreground pair. Such a conflict returns to cinematography for layered
blocking, simpler simultaneous action, an approved closed-roster binding, or
motivated Segment repacking.

It also carries `prompt_contract` with the Prompt language, exact operation
instruction, exact global constraint block, exact reference-priority order, and
the fixed Seedance reliability flags. Every binding carries its exact readable
Prompt declaration and zero or two-to-three stable visual traits.

```text
prompt_contract:
  language: English
  operation_instruction_en: <exact model-facing sentence>
  global_constraints_en: <exact model-facing sentence>
  reference_priority_order: [B01, B02, ...]
  dialogue_delimiter: curly_braces
  music_delimiter: parentheses
  sound_effect_delimiter: angle_brackets
  subtitle_delimiter: fullwidth_square_brackets
  background_music_policy: forbidden | parentheses_only
  generated_subtitle_policy: forbidden
  avoid_precise_time_ranges: true
  single_dominant_camera_move_per_shot: true

bindings[] additions:
  prompt_declaration_en: <exact model-facing reference declaration>
  stable_identity_traits_en: [<trait 1>, <trait 2>, optional <trait 3>]
```

Every catalog-image binding requires two or three traits. Runtime continuity media,
video, and audio bindings may use an empty trait list when visible identity traits
do not apply. `reference_priority_order` exactly follows the binding array. The
project keeps generated subtitles forbidden because captions are authored in post;
the default native-audio flow uses `parentheses_only` and requires Seedance-native
background music.

The exact `population_lock_en` appears once in the provider Prompt. Other private
continuity values do not have to appear verbatim or in any fixed place, except each
character state's exact `prompt_presence_lock_en`, which appears once after the
population lock and before the global constraints. Every
Segment has one Location-master world
binding active in every Shot. A continuation/revisit additionally has temporal
binding(s) to the reviewed predecessor, except `adjacent_coverage_reset`, which
names its predecessor as semantic state source but deliberately has no temporal
provider binding. The embedded roster must exactly equal the
Location catalog; Segment-authorized independent performers must be a subset of
that Location's independent-performer treatment. The plan is never sent as Prompt
prose.

Every provider-renderable role and NPC ensemble—including physically present
offscreen and audio-only roles—must also resolve to an asset-catalog identity or approved
appearance-state reference image in the actual provider request. Internal IDs,
Prompt prose, voice samples, and temporal predecessor media do not count as visual
identity bindings. `remain_absent` roles are internal state/review obligations, not
provider subjects: never submit their ID or positive identity image.

For each serial successor, runtime stops before provider submission and exposes the
actual predecessor video, current Segment Script/private plan, authorized
performers, and resolved provider bindings. Virtual production checks the observed
ending and every character/Location input, changes and rematerializes the successor
when needed, and obtains `seedance-video-review` `NO_ISSUES`. Preflight accepts only
the exact predecessor attempt passed as a transient `--observed-predecessor`
argument in that active invocation. No approval file or review hash is written, and
a changed attempt requires a new direct review.

For every Segment, the user-facing control surface remains conversational: report
how the video starts, who is present, what happens, how it ends, and what comes
next. Exact Prompt text, transport fields, hashes, and provider JSON stay internal
unless requested. One live confirmation authorizes one attempt for one Segment;
after the completed clip is reviewed, pause again for the human's next direction.

Execution-plan materialization derives one additional deterministic transport
record, `quality_reset`, from the complete ordered Segment chain and the verified
capability profile. It is not authored Prompt meaning. The first and every permitted
extension use `white_model_video_edit`: runtime strictly edits the approved
predecessor into a pure-white 3D proxy, remuxes the predecessor's synchronized
audio, and supplies that proxy as the Segment's temporal video. Virtual production must name
that temporal binding as a white model and include high-resolution Location and
identity/appearance image bindings for every declared role. The proxy owns
structure and motion only and never enters the final timeline.

Tail-frame reference and extension share one consecutive predecessor-media budget.
After either, the next same-Scene Segment must be `strong_coverage_reset` /
`adjacent_coverage_reset`: it directly depends on and reviews its predecessor,
preserves semantic Character/Location/prop state, carries no predecessor provider
binding, and opens ECU/CU/MCU from a decisively new angle, viewpoint, and
composition. If the inherited action is unfinished, cinematography must repack or complete
it before this boundary.

Python may reject an invalid or stale private transport artifact and resolve
approved media URLs. At the Prompt text layer it checks UTF-8 readability,
non-whitespace content, provider-token set/placement, ordered exact declarations,
the operation instruction, population/global locks, curly-brace dialogue/speaker
ownership, and precise-second-range exclusion. It must never invent, fill,
summarize, translate, or repair creative Prompt content.
