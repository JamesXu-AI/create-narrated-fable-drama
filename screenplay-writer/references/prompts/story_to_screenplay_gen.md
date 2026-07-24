# Cinematic Widescreen Production Script Prompt

## Task

Adapt the approved children's educational `story.md` into one English horizontal
large-screen film script. Author it as dramatic production authority: playable
scenes, story-facing shots, exact performance and dialogue, legible space, native
sound, controlled timing, and continuous state.

Treat the project as forest-animal education only. Preserve the forest as the
primary dramatic world, lock every animal's species and feasible locomotion, and
make forest geography, entrances/exits, routes, persistent environmental changes,
and ambience explicit enough for downstream continuity. A source-required human
bookend remains brief and separate from the forest Location chain.

## Input Contract

Read only:

- `TASK_DIR/task.json`: title, age band, language, and runtime limits;
- `TASK_DIR/story.md`: narrative authority;
- `screenplay-writer/references/screenplay-segment-contract.md`: exact output
  structure and permitted values.

Stop if an authority is absent, unreadable, or mutually contradictory. Treat
downstream design, assets, Storyboards, generated media, and provider Prompts as
out of scope.

## Decision Rules

### 1. Understand the film before authoring tables

Form an internal model of premise, educational question, cause and effect,
objectives and tactics, relationships and power, audience knowledge, emotional
progression, climax, consequence, and ending. Do not output this analysis.

Design each Scene as one dramatic event with an objective, obstacle, tactic
progression, spatial progression, important reaction, turning point, changed
outcome, and exit impulse. Retain a shot only when it creates or reveals a change.

### 2. Preserve children's educational meaning

- Preserve source-supported participants, relationships, events, beliefs, cultural
  facts, lesson, climax mechanism, consequences, and ending.
- Make goals, causes, choices, and results understandable for the locked age band
  through action and reaction.
- Let learning emerge through discovery, attempt, consequence, changed choice, and
  earned reflection.
- Keep conflict purposeful and legible. A source-supported injury or death may show
  the decisive contact, visible wound, changed physical condition, and consequence;
  do not automatically hide it behind occlusion, dust, reaction-only coverage, or
  vague aftermath. Exclude gore, dismemberment, exposed tissue, wound fetish,
  prolonged suffering as spectacle, imitable dangerous instruction, stereotypes,
  and invented cultural or religious claims.

### 3. Build drama for horizontal cinematic space

Use depth, foreground/background relations, entrances, crossings, reaction
geography, concealment, revelation, and sustained attention. Give every shot a
playable objective/tactic, visible action, consequential reaction, and a distinct
start-to-end change. Remove stationary explanation, mechanical turn-taking,
camera-facing presentation, synchronized crowd response, decorative movement, and
repeated information.

Write motion at a level Seedance can execute: name the active body part and, when
material, its range, speed, and force; prefer small continuous actions to needless
explosive movement; and state the inertial or causal bridge from one action to the
next. Externalize emotion through observable breath, eyes, posture, hands,
shoulders, pace, and gaze instead of leaving only an abstract label such as
`sad` or `angry`.

Choose scale/view and audience focus only for story meaning. The Writer does not
decide lens, focal length, exact camera position, equipment, camera mechanics,
lighting, or edit implementation.

Use intimate coverage as the default visual grammar, not a proscenium master-shot
grammar:

- Put a decisive facial change, held or broken eye line, breath, injury, hand
  action, clue, or educational detail in `close_up`, `extreme_close_up`, `reaction`,
  `insert`, or `pov` when that is where the audience's attention belongs.
- A new Scene or Scene Unit does not automatically earn an `establishing` or
  `wide` Shot. Use one only when new geography, scale, full-body mechanics,
  entrance/exit travel, or a changed spatial relationship must be read.
- After spatial information is established, move closer. Do not repeatedly return
  to a frontal full-cast view for dialogue, listening, explanation, or proof of
  continuity.
- Do not author three consecutive `establishing`/`wide` Shots. Break spatial
  coverage with the face, reaction, point of view, or story-bearing detail that
  changes the beat.
- For every Scene containing three or more Shots, include at least one
  `close_up`, `extreme_close_up`, `reaction`, `insert`, or `pov` Shot. This is a
  minimum anti-tableau gate, not a target quota; use more tight coverage whenever
  story attention calls for it.
- Never line the cast across the frame facing forward like a stage presentation.
  Build depth, asymmetric screen position, foreground occlusion, off-screen space,
  and motivated singles/reverses while preserving reconstructable geography.

### 4. Resolve staging, gaze, speech, and completion

For every used character, choose `present_at_open`, `enters`, or `not_visible` and
author the complete chain required by the contract. First visibility, path,
landing, and landing result must be observable in the referenced shots. Express
timing as exact seconds, relative beats, or event order only when it helps the
scene; no timing notation is mandatory.

Within each shot, keep origins, destinations, crossings, turns, stops, final
positions, facing, and meaningful gaze mutually consistent. Each Line begins on a
specific same-shot speech gate triggered by a visible or audible event; the
speaker's gaze relation identifies the addressee. The camera is never the
addressee.

Mark completion from the observable result: use `completed:` only after the action
settles, and `open:` only for the exact unfinished phase carried across the next
boundary.

### 5. Integrate exact dialogue and native sound

Write speakable, age-clear, character-specific dialogue motivated by the current
action. Preserve time for listening, movement, and reaction. Author concrete BGM
changes, source-based SFX, environment ambience, and meaningful silence at the shot
where each event occurs.
Keep each Scene Unit's spoken language consistent except for approved proper nouns.
Flag a difficult Chinese pronunciation for downstream performance handling without
rewriting the exact dialogue authority.

### 6. Control Scene Units and continuity

A Scene Unit is a 4–15 second planning unit inside a dramatic Scene. Choose its
number of story-facing Shots, performers, dialogue lines, reference needs, and
internal timing by dramatic judgment. It is not a template for the number of
`Shot N` paragraphs in a future Seedance Prompt. Split or combine units when the
finished story and provider task duration benefit.

| Constraint | Limit |
| --- | --- |
| Scene Unit duration | integer 4–15 seconds |
| Project runtime | at most 240 seconds |

Protect minimum playable duration with:

```text
dialogue_words / 2.6 + dialogue_line_count * 0.25 + 1.0
```

This is a feasibility floor for delivery, turn-taking, action, and reaction—not a
Prompt word limit or a required timing notation. Do not apply dialogue occupancy
percentages, fixed limits on dialogue lines/owners or silent group roles, a fixed
Shot count, or an exact sum of authored Shot durations. Shot duration cells remain
editorial estimates rather than downstream Prompt windows.

Use `state_match` for one settled predecessor-media handoff and
`continuous_motion` for one unfinished visible phase that crosses the boundary.
After either handoff, the immediately following same-Scene boundary must use
`strong_coverage_reset`: settle the predecessor first, preserve semantic story and
occupancy state, and open the successor on an ECU/CU/MCU with a decisively different
angle, viewpoint, and composition. Never interrupt unfinished action just to force
the reset; repack the Scene Units instead. Use `independent` only for a genuine
discontinuity. The appendix records stable mappings, changed states, and adjacent
handoffs without repeating shot content.

Author the complete `Character Scene States` lifecycle before release. Separate
diegetic presence from frame visibility. Once a character or closed ensemble is
`present_in_location`, carry it through every later Scene Unit in that Scene until
an authored exit changes it to `absent_from_location`. Declare exact minimum
visibility with `visible_every_shot`, `visible_in_required_shots`,
`may_be_offscreen`, or `must_remain_absent` and exact Shot IDs. Do not move a
story-required individual or ensemble off-screen merely to reduce generation
complexity. If a required composition would exceed downstream reference or action
reliability, preserve the visible story authority and let cinematography repack the
Generation Segments or simplify simultaneous background behavior.

`visible_every_shot` is exceptional: use it only when continuous simultaneous
visibility is itself causal, such as sustained physical contact, restraint, rescue,
or a scale relationship the audience must monitor without interruption. Physical
presence alone does not justify it. In ordinary close-up, insert, reaction, POV,
and shot/reverse-shot coverage, keep the cropped character
`present_in_location` and use `may_be_offscreen`; a camera crop is not an exit and
does not require a wide master to prove continued existence.

## Output Contract

Write one UTF-8 file at:

```text
TASK_DIR/screenplay-writer/screenplay.md
```

Follow `screenplay-segment-contract.md` exactly. Author every creative cell through
screenplay judgment. Validator behavior is governed by that contract's Authorship
Boundary.

## Release Gate

Release only when:

1. the tables read as one coherent film with no filler, repetition, or conflicting
   authority;
2. educational meaning, causal logic, age clarity, emotional safety, cultural
   integrity, climax, and ending remain true;
3. action, reaction, staging, gaze, dialogue, sound, timing, and boundaries describe
   the same visible event;
4. every entrance and spoken Line is fully motivated and observable;
5. all contract, runtime, scope, continuity, ID, and release-file checks pass.
6. the forest remains the primary world and every animal species, Location route,
   environmental state, and educational cause remains continuous.
7. tight coverage carries decisive faces, reactions, and details; no Scene defaults
   to repeated frontal `establishing`/`wide` tableau coverage.

Validator success proves consistency, not dramatic quality. Reread the completed
tables as a director, performer, editor, and child audience before release.
