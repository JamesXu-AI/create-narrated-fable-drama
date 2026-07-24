---
name: screenplay-writer
description: "Create or repair English children's forest-animal educational stories and horizontal cinematic production scripts. Use for translation, age classification, story.md, or an all-table screenplay.md whose forest geography, animal species, educational causality, visible action, staging, entrances, gaze, dialogue, sound, timing, and continuity must be explicit."
---

# Children's Educational Film Writer

## Skill boundary

Work only from this repository's bundled prompts, references, scripts, and ordinary
tools. Never invoke, load, delegate to, or depend on an external Skill. Return a
blocker instead of substituting another writing, review, or media-production Skill.

## Purpose

Turn supplied story material into an age-appropriate forest-animal educational
story or one executable horizontal large-screen screenplay. Read and enforce the
[Forest Animal Education Production Standard](../references/forest-animal-education-production-standard.md).
Also follow the
[Human-in-the-Loop Guided Workflow](../references/human-in-the-loop-guided-workflow.md).
Do not author a generic or non-forest main story. The screenplay release is:

```text
TASK_DIR/screenplay-writer/screenplay.md
```

Age-appropriate does not mean hiding every injury. When injury or death is causal,
show the contact, wound, physical condition, and consequence clearly enough to
understand; do not routinely replace them with occlusion, dust, reaction-only
coverage, or vague aftermath. Keep the depiction non-exploitative: no gore,
dismemberment, exposed tissue, wound fetish, or prolonged suffering as spectacle.

## Stage Router

Select one stage and read only its Prompt:

| Stage | Authority | Result | Prompt |
| --- | --- | --- | --- |
| Translate | parsed source input | validated English translation object | [translation_gen.md](references/prompts/translation_gen.md) |
| Classify audience | translated title and story | one age-band value | [age_band_gen.md](references/prompts/age_band_gen.md) |
| Prepare story | title, content, age band | `story.md` | [story_gen.md](references/prompts/story_gen.md) |
| Write screenplay | `task.json`, `story.md` | `screenplay-writer/screenplay.md` | [story_to_screenplay_gen.md](references/prompts/story_to_screenplay_gen.md) |

Stages do not borrow one another's work. Translation preserves meaning;
classification selects an audience; story preparation shapes narrative; screenplay
authoring converts the approved story into dramatic production authority.

For screenplay work, also read the
[production-script contract](references/screenplay-segment-contract.md). The Prompt
owns creative decisions; the contract owns Markdown structure, columns, values,
timing syntax, and IDs.

## Screenplay Ownership

| Screenplay Writer | Local cinematography and virtual production |
| --- | --- |
| Scene drama and Scene-Unit packing | final Shot and Segment implementation |
| story-required scale/view and audience focus | lens, focal length, composition, and camera placement |
| visible action, reaction, objectives, and completion | camera path, support, speed, and edit execution |
| entrances, movement, spatial relationships, facing, gaze, and addressee | blocking refinement and cinematographic realization |
| exact dialogue, speech gates, delivery, BGM, SFX, ambience, and silence | lighting, exposure, color, provider Prompt, and asset bindings |

The Writer can require a story-facing view such as `wide`, `reaction`, `close_up`,
`insert`, or `pov`. It does not prescribe how the camera department executes it.
Use an intimate, attention-led coverage baseline: prefer `close_up`, `reaction`,
`insert`, or `pov` when the story turns on a face, eye line, breath, wound, hand,
clue, or educational detail. A Scene opening does not automatically require an
`establishing` or `wide` Shot. Use `establishing` or `wide` only when the audience
must newly understand geography, scale, a full-body action, an entrance/exit path,
or a changing spatial relationship that tighter coverage cannot communicate.
Never request a frontal all-cast master merely to prove that characters remain in
the Location.

## Workflow

1. Read the active authority and Prompt completely.
2. At screenplay stage, understand the whole film before authoring the contract
   tables by hand.
3. Before writing Shot rows, author the Scene-wide character lifecycle: for every
   individual and closed ensemble, decide when it enters/exits the physical Scene,
   carry its diegetic presence through every intervening Scene Unit, and declare
   the exact Shots where it must remain visible. Treat this as story authority,
   not a downstream reliability preference. Use `visible_every_shot` only when
   simultaneous visibility is indispensable to the causal event; ordinary
   shot/reverse-shot, reaction, insert, and close-up coverage keeps non-framed
   characters `present_in_location` with `may_be_offscreen`.
4. Write each Scene Unit and Shot from that lifecycle. Keep required individuals
   and ensembles in the exact Shots where the story requires them. Do not
   pre-emptively reduce a group scene to two present roles because downstream
   generation may be harder, and do not force every present role into every frame.
5. Budget predecessor-media handoffs across same-Scene boundaries. After one
   `state_match` or `continuous_motion`, require `strong_coverage_reset` on the
   immediately following boundary: finish the predecessor action, keep semantic
   Character/Location/prop state, and begin the successor with
   `extreme_close_up`, `close_up`, `insert`, `reaction`, or `pov` from a decisively
   changed angle/viewpoint/composition. Repack Scene Units instead of cutting an
   unfinished action just to meet this rule.
6. Run the structural validators below.
7. Repair authored Markdown manually, then reread the tables as one film for
   causality, performance, spatial clarity, age suitability, rhythm, and repetition.

All commands are subject to the production-script contract's Authorship Boundary.

## Execution

```text
python3 screenplay-writer/scripts/build_screenplay.py build --task-dir TASK_DIR
python3 screenplay-writer/scripts/build_screenplay.py check --task-dir TASK_DIR
python3 screenplay-writer/scripts/validate_role_asset_scope.py --task-dir TASK_DIR
```

Release only after all commands pass, the role gate reports
`image_asset_generation: UNLOCKED`, and semantic rereading finds no filler or
contradiction.

After a valid `story.md` or `screenplay.md` is ready, summarize the result and
proposed next step in plain language. Continue through internal handoff unless the
result exposes a material creative choice; do not require the human to approve
each document or inspect its JSON-derived evidence.

## Scope Boundary

Do not choose visual style, appearance design, palette, materials, costume/prop
design, asset IDs, generated media, detailed cinematography, lighting, provider
parameters, Storyboards, or executable Seedance Prompts.
