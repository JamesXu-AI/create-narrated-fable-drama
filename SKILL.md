---
name: forest-animal-education-video
description: Orchestrate the complete repository-local forest-animal educational story-video pipeline as a guided human-in-the-loop collaboration from task input through verified final masters. Use when Codex must run, resume, coordinate, or diagnose this specialized project while presenting editable next-step plans and obtaining explicit confirmation before and after every video generation.
---

# Forest Animal Education Story Video

Act as the sole top-level orchestrator for this project. Route work to the
repository-local departments, enforce their gates and ownership boundaries, and
continue until the requested production outcome is complete.

This project is not a general story-video system. Read and enforce the complete
[Forest Animal Education Production Standard](references/forest-animal-education-production-standard.md)
before accepting or resuming a task. Reject a task whose primary educational story
is not set in a forest animal community, and require the exact fixed domain and
visual-style profiles at every Gate.

Read and enforce the complete
[Human-in-the-Loop Guided Workflow](references/human-in-the-loop-guided-workflow.md).
Treat the conversation as the director's control surface. Keep internal documents,
JSON, validation, and department handoffs quiet unless they produce a blocker or
material creative choice. Before and after every video Segment generation,
regeneration, or retry, present the compact editable next-step plan and pause. A
confirmation never rolls forward to another Segment or attempt.

## Non-negotiable Skill boundary

While executing a production task under this main Skill, use no Skill outside this
repository. Apply this prohibition to explicit calls, implicit triggering,
delegation, suggested helpers, and fallbacks. Never use an external image, video,
audio, browser, document, presentation, spreadsheet, review, visualization, or
media-production Skill. The repository-local departments, contracts, scripts, and
provider adapters are the complete production implementation.

The sole system-Skill exception is `skill-creator`. Use it only when the user
explicitly asks to create, update, or validate this project's own Skill files.
Never use `skill-creator` to perform story, design, cinematography, generation,
review, sound, editing, or delivery work.

Treat only these repository-local Skills as internal production departments:

- `screenplay-writer/SKILL.md`;
- `direct-production-design/SKILL.md`;
- `previsualize-cinematography/SKILL.md`;
- `virtual-production/SKILL.md`;
- `seedance-video-review/SKILL.md`;
- `finish-postproduction/SKILL.md`.

Do not discover, introduce, or substitute another production Skill. In particular,
never call `seedance-master-skill`, `image2`, `imagegen`, `image_gen`, or another
image/video Skill. `previsualize-cinematography` authors the Storyboard itself;
`virtual-production` authors Seedance Prompts itself; and
`direct-production-design` generates images only through the bundled Seedream
adapter. Repository-local scripts, provider adapters, and ordinary tools explicitly
authorized by an internal department are implementation mechanisms, not external
Skill dependencies.

## Minimal artifact policy

Persist only an artifact that is a current creative authority, a reusable final
asset, a generated Segment needed downstream, a compact resume record, or a final
deliverable. Prefer one authoritative file over a source/manifest/receipt copy.
Keep validation results in command output and review decisions in the conversation.

The normal retained chain is:

```text
task.json + story.md
-> screenplay-writer/screenplay.md
-> direct-production-design/production-design-plan.json
   + assets/assets.json + final asset media
-> previsualize-cinematography/storyboard.md
-> one Prompt + one private plan per pending Segment
   + accepted Segment video/final frame/compact production record
-> final masters + subtitle deliverables
```

Do not create visual-spec companions, location-continuity copies, compile
manifests, compatibility packets, approval files, review reports, hash ledgers,
duplicate image Prompt files, or successful image-provider request/response
sidecars. Ephemeral video-provider polling and diagnostic data may exist only when
runtime resume or failure diagnosis requires it.

## Repository script layout

Keep every department's `scripts/` directory flat. Put every executable, helper
module, validator, and provider adapter directly under that department's
`scripts/` root. Do not create `scripts/story_video/`, `scripts/providers/`, Python
package directories, or any other second-level directory below `scripts/`. Use
unambiguous filenames, flat imports, and explicit cross-department script-root
paths when one department consumes another department's helper.

## Orchestration rules

Before executing a department, read its complete `SKILL.md`, the project-wide
forest-animal standard, the human-in-the-loop workflow, and its declared
task-relevant references. Follow its inputs, outputs, commands, gates, and hard
boundaries. Keep every authority with its owning department; never repair an
upstream fact inside a downstream artifact.

When reporting a phase result, lead with the current result and proposed next step,
and accept natural-language direction. Do not force the user through every internal
artifact or validator. Read-only inspection, validation, dependency repair, and
non-creative handoffs may continue; media generation, destructive overwrites,
retries, successor generation, and final rendering may not cross a confirmation
Gate.

Operate inside one explicit `TASK_DIR`. Inspect current artifacts and validator
results before resuming. Reuse valid current work, restart at the earliest invalid
or incomplete gate, and rebuild only affected downstream outputs. Stop on missing,
contradictory, stale, or unparseable authority instead of inventing replacements.
Treat dialogue ownership, silent group-role membership, exact ordered silent
member-type composition, first-dialogue portrait-expression authority, Scene scope,
the current model-authored `production-design-plan.json`, and story-significant
appearance/prop facts as asset-bearing invalidation inputs.
A textual difference between a ready image's colocated brief and the newly compiled
current brief is a semantic-review candidate, not proof that the image is stale.
Run the production-design semantic-reuse inspection before generation. Codex itself
must compare the complete old/current briefs and inspect the existing image whenever
the visible result is uncertain. Reuse it when both briefs can be satisfied by the
same visible pixels; regenerate it only when the current authority requires a
materially different visible result. Do not call `SEED_MODEL`, another text model,
or hard-coded story/species/object rules for this decision. Pass every direct Codex
decision explicitly to the builder; unresolved candidates must stop before any
visual generation or overwrite.
Before Seedance materialization, compare every final Prompt/provider binding with
the semantic authority declared in repository-root `assets/assets.json`. Treat a
wrong identity, role, appearance/injury state, costume, group, prop, location or
voice declaration as a blocker, route it to production design, and invalidate the
affected execution plans. Do not download assets or compare provider/local file
bytes for this semantic gate, and do not create compatibility receipts.

Use repository-local `seedance-video-review` to diagnose a specific artifact or
completed video and whenever a Seed Master serial shooting-plan row requires direct
predecessor observation before successor recompilation. Send each actionable issue
to its owning department and recheck only the corrected result. Keep `NO_ISSUES` in
the active task; never turn review into a separate approval-file workflow.

## Production sequence

1. Establish `TASK_DIR`, validate `task.json`, and require the current `story.md`.
   When story preparation is part of the request, use only the repository-local
   prompts and scripts under `screenplay-writer`; do not use another Skill. Story
   must provide goals, obstacles, visible/audible triggers, actions, reactions,
   differentiated ensemble behavior, causal turns, and changed results without
   choosing cameras.
2. Execute `screenplay-writer`. Build and check its single all-table,
   cinematic-widescreen `screenplay.md` release, then run every check defined by
   that department. Its Prompt owns creative decisions and its production-script
   contract owns syntax; do not restate, weaken, or supplement either here. Any
   structural, semantic, staging, timing, dialogue, sound, or continuity failure
   returns to Screenplay. Downstream departments may not repair it indirectly.
   Before Shot authoring, Screenplay establishes one sticky Character Scene State
   chain per Scene. It separates physical `present_in_location` from exact Shot
   visibility, carries every individual and closed ensemble until an explicit
   exit, and treats required-visible Shots as story authority. Generation
   difficulty, two-character stability, and provider reference budget are not
   valid reasons to move a required role off-screen. Physical presence alone does
   not require simultaneous visibility: reserve `visible_every_shot` for causal
   events that genuinely need it, and use `may_be_offscreen` for ordinary
   close-up, reaction, insert, POV, and shot/reverse-shot crops.
3. After the role/asset-scope gate returns `PASS` with image generation unlocked,
   start `direct-production-design`; do not launch a separate Codex screenplay
   reviewer.
   Production design also owns semantic scene dressing: it interprets playable
   action, interactions, routes, geography, and recurrence to author each
   Location's necessary fixed furniture, installed props, and stable dressing.
   It also understands the screenplay well enough to separate stable incidental
   NPC population from independent performers. The Location master visibly contains
   its fixed set and embedded NPCs only; every dialogue or story-active role remains
   a separate performer reference. Both role lists are model-authored and carried
   into `assets.json`; Python validates and copies them but never classifies a role
   or infers content from keywords.
   Before production-design generation, run `build_initial_production_design.py
   --inspect-semantic-reuse`. For every returned candidate, Codex directly decides
   whether the old and current visual meanings are equivalent by applying
   `direct-production-design/references/codex-asset-semantic-reuse-review.md`.
   Rerun the builder
   with `--codex-reuse-asset ASSET_ID` for each equivalent candidate and
   `--codex-regenerate-visual-asset ASSET_ID` for each materially changed candidate.
   The visual-only decision must preserve a current character voice. This review is
   part of the active Codex task and is never delegated to a provider model.
4. Require the current deterministic `screenplay.md`, fast role-gate PASS, and
   current valid production-design authorities before executing
   `previsualize-cinematography`.
   Pass the original request and complete upstream inputs to that department. It
   authors the Storyboard directly from its bundled contracts. Persist only
   `storyboard.md` at
   `TASK_DIR/previsualize-cinematography/`; compile manifests, Storyboard JSON,
   traces, ledgers, companions, wrappers, and alternate representations are
   forbidden. Cinematography must return missing or contradictory screenplay authority to
   its owner, then convert accepted story-facing Shot rows into final one-task Shots
   with motivated camera, layered blocking, selective ensemble control, and passed
   cinematic reviews. Tight, attention-led coverage is the default: decisive
   faces, eye lines, breaths, hands/paws, wounds, clues, reactions, and educational
   details receive close or medium-close framing. Every wider frame must reveal
   indispensable new geography, scale, full-body mechanics, entrance/exit travel,
   or a changed spatial relationship; never use a frontal full-cast master simply
   because a Scene/Segment begins or roles remain present. Cinematography must also author
   one Location State Plan and one
   Character Segment State Plan inside `storyboard.md`. Every recurring location
   declares adjacent or nonadjacent
   inheritance, its latest temporal state source, separate Location-owned
   world/population evidence, persistent
   anchors, and allowed changes. Intervening inserts or imagined Scenes do not
   reset a physical set. Inside each Location state chain, every authorized
   independent performer and every still-present character receives an incoming
   presence, Segment rule, required visible Shots, allowed occlusion,
   position/injury condition, transition cause, and outgoing presence. A character
   remains tracked until explicit exit; absence may return only through re-entry or
   a justified reset. Named/story-active individuals use strict identity and state
   continuity. NPC/anonymous ensembles use group-level presence continuity: preserve
   the authored crowd/court field and forbid an unmotivated whole-group pop-in,
   disappearance, allegiance change, or promotion into a story-active identity, but
   do not reject model output for exact NPC member count, species mix, or
   member-by-member identity drift. Cinematography first compiles the screenplay Character Scene State
   chain as a non-downgradable occupancy floor. When the required visible cast is
   complex, it actively designs layered foreground/midground/background blocking,
   reduces simultaneous background motion, uses an approved closed-roster asset,
   or repacks the Generation Segment. It may not solve reliability by silently
   creating a two-visible-character version, but it may crop physically present
   roles that the screenplay does not require in that exact Shot. A close crop is
   not an exit and must not be replaced by repeated wide tableau coverage.
   Cinematography must make
   every overlapping `scene_ids` pair directly serial. One boundary may inherit
   predecessor media through `multimodal_reference` plus a provider-last-frame soft
   reference for a settled cut, or through complete-predecessor `video_extension`
   for an unfinished phase. The immediately following same-Scene boundary must be a
   reference-free `strong_coverage_reset`: preserve semantic Character/Location/prop
   state, bind current Location and identity assets, but submit no predecessor frame
   or video and open with an ECU/CU/MCU from a decisively new angle, viewpoint, and
   composition. Soft reference is not strict/API first-frame control.
   Every provider-renderable role in the current Character Segment state, including
   an offscreen/audio-only role that remains physically present, an anonymous NPC
   ensemble, and a role outside the current crop, must have an
   asset-catalog identity or approved appearance-state image actually bound into
   the Seedance request. Internal IDs, Prompt prose, voice samples, predecessor
   frames, and predecessor video are never visual identity evidence. A
   `remain_absent` role is the one exception because reference images are positive
   visual conditioning: keep it only in the internal state machine and review
   gate, and submit neither its internal ID nor its image to Seedance. If the
   complete required media set exceeds a verified provider limit, cinematography repacks
   the Segment instead of omitting a role reference.
5. Require the current `storyboard.md`, then execute `virtual-production`. It
   directly persists one exact natural-language Prompt plus one private execution
   plan per Segment. Virtual production freely authors the Prompt's
   creative structure, Shot/beat representation, camera language, length, and
   wording while following the repository Seedance 2.0 guide contract. Python
   validates only its narrow auditable layer: priority-ordered reference
   declarations, exact operation/global/population locks, one ordered exact
   Character Segment presence lock per tracked character, provider tokens before the
   first Shot, two or three stable traits for catalog-image subjects, event-order
   timing without precise provider second ranges, official music `()` / effect `<>`
   / dialogue `{}` / generated-subtitle `【】` notation and policies, and exact
   `{dialogue}` with its readable speaker in the owning `Shot N:` section. Generated
   subtitles remain forbidden because final captions belong to postproduction;
   the default main flow requires at least one `(background music cue)` and preserves
   Seedance-native music through final delivery. The
   private plan records one
   dominant camera move per Shot; it does not impose a creative-prose template.
   Before URL materialization,
   directly reject any provider token whose declared media kind or asset namespace
   cannot resolve to the matching current row in `assets.json`. Do not create
   compatibility packets, review drafts, rework JSON, or another hidden creative
   authority. Virtual production
   may clarify execution language but may not reinvent Scene conflict, blocking,
   Shot focus, camera logic, or continuity. Before materialization
   or any provider call, virtual production must reject same-Scene parallel,
   strict-first-frame substitution, matched-tail substitution, missing direct
   predecessor dependency, a second consecutive predecessor-media handoff, or a
   mismatch between settled/unfinished/reset phase and its serial contract.
   Every permitted `video_extension`, including the first, must first strictly edit
   the approved predecessor into the official pure-white 3D white-model continuity
   proxy, remux the predecessor's original synchronized audio onto that proxy, and
   submit the proxy—not the colored predecessor—as the successor's `@Video` input.
   The white-model proxy is temporary generation evidence and never enters the final
   timeline. That successor must bind current high-resolution Location and
   identity/appearance images for every declared role; the white
   model owns motion, pose, camera, timing, and structure, not final appearance.
   A white-model reset does not grant another immediate inherited boundary: after
   one tail-reference or extension handoff, the next same-Scene boundary must perform
   the reference-free tight-coverage reset before one later inherited handoff may be
   used again. If that cut would interrupt unfinished action, repack or finish the
   action inside the current Segment; never cut it merely to satisfy the counter.
   Every Segment set in a Location, including video extension, must bind that
   Location master in every Shot. Predecessor media is temporal evidence only and
   cannot authorize the offscreen set or complete population. Virtual production must also
   author one readable population lock whose embedded roster exactly matches the
   Location authority and whose independent performers are explicitly permitted.
   It must also carry the complete Character Segment state machine. Reject a plan
   that silently drops a character whose prior outgoing presence is not `absent`,
   changes incoming presence, omits a required-visible Shot, or makes an absent
   character return without `re_enter`. `must_remain_visible` means that the same
   character remains readably present in every authored internal Shot, with position,
   injury, and condition preserved. For an NPC/anonymous ensemble, this is a
   group-presence lock rather than an exact roster-membership lock.
   Every provider-renderable role receives a standalone identity or approved
   appearance-state image in every request, including physically present
   audio-only/offscreen roles and roles temporal evidence also carries. The identity image owns who the
   role is; temporal evidence owns only recent pose, position, action phase, camera,
   and continuity state. The Prompt must describe both as the same subject and
   forbid duplicate instances. A `remain_absent` role stays internal-only so its
   positive image cannot induce reappearance. An NPC ensemble likewise binds its approved group
   identity image in every Segment where it is declared, while exact generated
   member count, species mix, and member-by-member identity remain non-blocking
   review details.
   Provider references apply request-wide; Shot prose cannot deactivate one. When
   an exiting roster and an entering roster require mutually exclusive authority,
   make the completed exit a Generation Segment boundary. Bind only the exiting
   roster before that boundary and only the entering roster in its dependent
   successor. Four independently referenced performers and four or five total
   references are composition recommendations only, never permission to omit an
   identity image. The hard gate is the verified provider media capacity.
6. On a direct asset-resolution failure, stop the affected Seedance submission and
   return to `direct-production-design`. Report the failure in command output only;
   never create a substitute Prompt, asset, review packet, or rework artifact. Fix
   the authoritative production design or the locally authored Segment binding,
   then rerun from current sources.
   For a nonadjacent location revisit, virtual production must wait for the named
   location-state source review and bind current temporal evidence plus the
   Location-master world/population authority, adding the latest human-approved
   readable wide state when visible set changes require it.
   Code may validate or extract an explicitly selected frame; it may not select or
   invent continuity evidence.
7. When a serial shooting-plan row requires observed predecessor evidence, use
   `seedance-video-review` on that exact provider attempt. After `NO_ISSUES`, let
   virtual production directly revise the required observed successor Prompt and
   plan; correct any issue through its owning department. `NO_ISSUES` may
   include a semantically equivalent internal-cut shift or adjacent movable-prop
   landing when the complete dramatic exchange, identities, fixed set, authorized
   population, ownership, action completion, and safe ending remain valid. Never
   regenerate solely for frame-exact timing or centimetre-level prop placement.
   Instead, make the observed final action phase and actual prop position the
   successor's temporal authority. Missing, duplicated, teleported, inaccessible,
   story-changing, or causally mistimed state remains a blocking issue.
   Generation runtime must stop before every such successor and expose the actual
   predecessor video, current `segment-NNN.md`, private plan, authorized independent
   performers, and resolved provider bindings for this inspection. After any needed
   Prompt/binding adjustment and rematerialization, the same active task may pass the
   exact `segment-NNN=segment-MMM__attempt-NNNN` observation argument to preflight and
   generation. This argument is transient, valid only for that predecessor attempt,
   and may be supplied only after the direct review returns `NO_ISSUES`; never create
   a PASS file or persisted review receipt. A missing or stale argument blocks all
   Seedance calls for the successor, including white-model preprocessing.
   The inspection must compare predecessor outgoing and successor incoming Character
   Segment states. Missing required presence is a defect in the first Segment where
   the character vanished; regenerate that Segment rather than accepting a later
   unexplained reappearance.
8. After every current Segment has one valid, human-accepted audiovisual result and
   production record, present the compact final-assembly plan and wait for human
   confirmation. Only then execute `finish-postproduction`. Deliver clean and
   captioned masters, exact subtitle files, and the final delivery manifest. At each
   incoming `video_extension` seam, verify a dialogue-free editable handle, trim six
   frames from the predecessor tail and one frame from the continuation head, then
   run boundary QC against the trimmed source points. Apply a short terminal audio
   fade to prevent an end click.

## Human-confirmed postproduction handoff

For a full-pipeline production request, derive generation completeness from the
current ordered Segment plans and their compact production records; do not create a
separate generation-state or summary artifact. Generated media is never completion
or authorization. After every Segment has been individually reviewed and accepted,
present the proposed
assembly, transition, seam-trim, subtitle, audio-finish, and delivery plan. Pause
for explicit user confirmation before executing:

```text
python3 finish-postproduction/scripts/finish_postproduction.py \
  --task-dir TASK_DIR
```

If the user modifies the plan, route the change to its owner, invalidate affected
downstream work, and present the revised plan before asking again. After
postproduction emits `FINAL_MASTER_READY`, present the verified outputs and pause
for human acceptance or requested revision.

The confirmed handoff must produce and validate all of the following:

- `finish-postproduction/final-clean-master.mp4`;
- `finish-postproduction/final-captioned-master.mp4`;
- `finish-postproduction/subtitles/master.srt`;
- `finish-postproduction/subtitles/master.vtt`;
- `finish-postproduction/final-delivery-manifest.json`.

Probe both masters as real media. Require a readable video stream and synchronized
audio stream, a non-empty captioned master, complete subtitle files, and a final
runtime no greater than 240 seconds before reporting success.

Do not skip a gate because a later artifact already exists. Do not create extra
approval files, hashes, compatibility records, intermediate authorities, or
parallel department variants unless an internal Skill explicitly requires them.

## Completion

Treat a full production request as technically ready only after the clean master, captioned
master, SRT, VTT, and delivery manifest exist, their owning validators pass, both
master media streams are readable, and postproduction emits `FINAL_MASTER_READY`.
Treat it as complete only after human acceptance. Report concrete blockers with
the owning department, failed gate, affected artifact, and smallest valid next
action.
