# Generation runtime

Provider attempts and clips live under `.pending/virtual-production/`. The
in-memory execution plan freezes the exact natural-language Prompt hash, private Segment-plan hash, Storyboard hash,
Seedance parameters, token ordering, asset URLs, dependency wave, and predecessor
attempt identity. A changed Prompt, private binding, or catalog semantic row
invalidates resume/reuse without imposing any Prompt-prose schema.

Treat the active conversation as the only human authority. Before any new Segment,
regeneration, or retry, present the compact natural-language plan and require the
matching transient `--human-confirmed-segment SEGMENT_ID`. One invocation may
contain at most one not-yet-generated Segment. Existing completed Segments may be
reconciled without another provider call. Do not persist an approval receipt or ask
the human to inspect runtime JSON.

Prepare runtime media only after preflight. A true video extension always converts
its complete predecessor to the official white-model proxy and preserves the
predecessor audio by remux. A settled matched cut uses the approved provider last
frame as an image reference. Both requests also carry the model-authored
Location-master world binding; runtime code may never infer or substitute it. A
strong coverage reset still waits for predecessor review but carries no predecessor
provider media. Reuse a predecessor's persistent provider URL directly; if it is
unavailable, upload the existing predecessor media directly. Do not copy runtime
reference inputs or write a runtime-media manifest. A white-model proxy remains
the only permitted derived runtime media and is keyed by its source attempt and
contract hashes.

Do not automatically advance from a completed predecessor to a serial successor.
At the start of each dependent wave, runtime emits a
`predecessor_observation_required` hold with the actual predecessor video, current
Segment Script/private plan, authorized performers, predecessor/current Character
Segment states, strict required-visible named characters and group-level required
NPC ensemble fields per Shot, and
resolved bindings. Virtual
production reviews the actual result, adapts and rematerializes the successor when
needed, and receives a direct `seedance-video-review` `NO_ISSUES` result. The active
generation invocation then supplies the exact predecessor attempt through
`--observed-predecessor`; no PASS file or review receipt is persisted. Preflight
rechecks that this transient value equals the execution plan's current attempt lock.

The in-memory execution plan freezes the complete Character Segment state array. Before the
hold can clear, directly confirm every required-visible named individual and every
required NPC ensemble field in each authored Shot, not only the foreground pair.
Before provider submission, confirm that every provider-renderable role and NPC
ensemble, including physically present offscreen and audio-only roles, resolves to an
asset-catalog identity or approved appearance-state reference image in the actual
request. A continuity frame/video, voice sample, internal ID, or Prompt declaration
never counts as that visual identity binding. A `remain_absent` role stays in the
internal state machine/review gate and must have neither an internal ID nor a
positive identity image submitted to Seedance.
The preflight identity audit must expose the readable model-facing subject name,
provider image token, and concrete HTTP image URI for every such role. An internal
asset ID may remain private audit metadata, but it may never be used as the
model-facing subject name or as a substitute for the image.
NPC ensembles are not checked for exact member count, species mix, or
member-by-member identity; only group-level persistence and motivated
appearance/disappearance are blocking. Confirm that every
`must_remain_visible` character appears throughout all required Shots and at the
usable outgoing state; confirm that a
`must_remain_present` character has not physically exited when a camera crop or
named occluder hides it. The next incoming state must equal the reviewed outgoing
state. Regenerate the first failing Segment instead of allowing a later Segment to
make the missing character pop back into existence.

When an otherwise accepted take ends with a different but valid presence state
than planned, preserve the submitted Script and execution-plan hashes unchanged.
The reviewer records only the actual outgoing difference in
`generation-segments/<segment>/reviewed-character-state-overrides.json` using
`seedance-reviewed-character-state-v1`. Runtime accepts that override only when it
names the current `GENERATED` provider attempt, has `review_status: NO_ISSUES`,
states both planned and reviewed presence, gives a reason, and points to an existing
evidence artifact such as `last-frame.png`. The successor may then use the reviewed
presence as its incoming state. A stale attempt, missing artifact, undeclared role,
or override that no longer matches the planned outgoing state is rejected.

The verified project policy permits zero colored direct extensions: runtime
executes the fixed `seedance-white-model-quality-reset-v1` strict video edit on the
first and every permitted extension, verifies the proxy's
streams and duration, remuxes the complete predecessor's original synchronized
audio, and uploads that white-model video as the successor's temporal input. The
proxy is cached by source attempt, source-video hash, model request, and reset
contract hash. It is private generation evidence and is never assembled into the
final film. The predecessor-observation gate runs first, so the reset edit cannot
be submitted while the successor Script or its character/Location inputs still need
correction.

The verified project policy also permits only one consecutive predecessor-media
handoff across tail-frame reference and extension combined. The next same-Scene
Segment must be `strong_coverage_reset`: it remains serial and review-dependent but
has no predecessor media binding, and its authored first Shot is ECU/CU/MCU from a
decisively new angle/viewpoint/composition. Runtime rejects two inherited handoffs
in a row and rejects extension-of-extension chains.

Never retry automatically. A create, moderation, terminal, missing-output, media,
or white-model failure ends the current invocation. Preserve the failed provider
attempt as one compact failure record plus only necessary diagnostic media, explain
the problem in plain language, and require a fresh
before-video confirmation before another attempt. The three-attempt ceiling is a
cross-invocation safety limit, not an in-process retry loop. A successful output has
readable video, Seedance-native audio, and a provider-returned last frame. Its
directory contains only `video.mp4`, `last-frame.png`, and
`production-record.json`; do not persist copied Prompts, request/response/poll
payloads, an artifacts manifest, generation state, or a generation summary.
