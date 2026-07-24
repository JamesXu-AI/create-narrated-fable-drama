# Free-Form Seedance Prompt Guidance

`segment-NNN.md` is the exact model-facing Prompt. It is authored by Seedance
Master from the approved Storyboard and is not a machine-readable contract.
Runtime and audit data live in the separate private Segment plan.

Read and apply [the Seedance 2.0 Prompting Contract](seedance-2-prompt-guide-contract.md)
before authoring. The official model-facing rules below narrow form only where
Seedance reliability requires it.

## Authorship freedom

Choose the Prompt form that best communicates the intended video. There is no
mandatory:

- title, heading, label, section, paragraph order, or paragraph count;
- a total Shot count, consecutive Shot numbering, or one-to-one mapping between
  Storyboard rows and Prompt paragraphs; a dialogue cue does require its owning
  `Shot N:` label so exact line placement can be verified;
- word count, vocabulary allowlist/denylist, sentence pattern, or required phrase;
- a fixed total word count or fixed Shot duration.

The author may use continuous prose, bullets, numbered shots, beat descriptions,
dialogue blocks, or another clear form. Use event order and natural rhythm rather
than precise ranges such as `0-3 seconds`. Keep a Shot locked or assign one dominant
camera move; put a motivated camera change in the next Shot. A single continuous
Prompt passage may cover several Storyboard shots, and one Storyboard shot may be
expanded into several model-facing beats when useful.

## Creative priorities

Use judgment to communicate what matters for the current Segment: subjects,
reference roles, environment, blocking, performance, gaze, action causality,
camera behavior, dialogue and native sound, lighting/color, continuity, and the
desired end state. Prefer observable, executable detail over generic praise, but
this is authoring advice rather than a lexical rule.

Translate each Storyboard `Shot Size` directly into observable model-facing
framing. For `extreme_close_up`, `close_up`, and `medium_close_up`, name the
dominant face, eye line, breath, paw/hand, wound, clue, reaction, or educational
detail and keep it large in frame. Do not widen to include every present role or
the complete Location; use off-screen sound, eye lines, foreground edges, and the
authored Character Segment states to preserve continuity outside the crop.
Preserve wider sizes only when the Storyboard explicitly makes geography, scale,
full-body mechanics, entrance/exit travel, or changed spatial relation the event.
Never compile selective coverage into a frontal all-cast proscenium tableau.

Every private binding owns one exact concise declaration. Place those declarations
before the first `Shot N:` section and in the private plan's priority order. Each
declaration keeps one stable readable subject label, two or three visible traits
for an image subject when applicable, one media responsibility, and its exact
`@ImageN`, `@VideoN`, or `@AudioN` token. The private plan remains transport
authority for media binding; never show Asset IDs to Seedance.

Place the private plan's exact operation instruction before the declarations. A
multimodal-reference instruction says which dimensions are referenced. A video
extension instruction directly extends or continues the temporal video and never
calls it a reference video.

Location and temporal references have distinct creative responsibilities. A
Location master represents the approved dressed world and embedded population;
predecessor evidence represents the recent visible state it can actually show.
Independent performers, new entrants, and transformation targets should be
described clearly enough to avoid identity duplication. Include the private plan's
exact `population_lock_en` once; no fixed heading or paragraph placement is
required for it.

Immediately after that population lock, include each Character Segment state's
exact `prompt_presence_lock_en` once and in state-array order. These locks turn
permission into an obligation: they state which named character must remain visible
in every required Shot, which remains physically present outside a crop, which
specific occlusion is allowed, and which authored event permits entrance, exit,
reveal, concealment, or re-entry. Preserve `position_and_condition_en`, including
injury and established spatial mark, in the lock's observable direction. A new
camera angle or Segment boundary never counts as an exit.

Preserve every required-visible closed ensemble as one readable roster with its
approved member composition. Do not compile a two-subject-only Prompt when the
Storyboard requires an individual or group in that Shot. If the provider media
budget cannot represent the required cast without ambiguity, stop and return the
Segment to cinematography for repacking instead of moving required roles
off-screen.

Bind an asset-catalog identity or approved appearance-state image for every
provider-renderable role and ensemble, including physically present roles that are
audio-only or stay outside the crop. The image declaration uses a readable subject description
and visible traits; an internal ID, voice sample, prose-only presence lock,
predecessor frame, or predecessor video never replaces the image binding. Temporal
media and identity media may describe the same role because they have different
responsibilities: identity media owns who the role is, while temporal media owns
recent pose, position, action phase, camera, and continuity state.
A `remain_absent` role stays internal-only and contributes neither ID nor image to
the provider request; a positive reference image can induce the forbidden subject.

At every extension's mandatory white-model quality-reset point, the temporal
declaration explicitly identifies its `@VideoN` as the pure-white 3D predecessor
proxy and assigns it only
motion, pose, camera, timing, spatial, and structural continuity. It is still the
video directly extended, never a “reference video.” Assign final Location,
identity, costume/state, texture, and color to the bound current high-resolution
images. Colored tail-frame handoffs still follow their authored identity-binding
plan; no colored predecessor video is directly extended.

Every permitted extension is such a white-model quality-reset point, including the
first. A strong coverage-reset Prompt is different: it contains no predecessor
`@ImageN`/`@VideoN` declaration at all. It uses current Location and identity assets
to preserve semantic state, then explicitly begins on the authored ECU/CU/MCU with
a decisively new angle, viewpoint, composition, and focal emphasis.

Each private-plan dialogue cue must place its exact text as `{spoken words}` beside
the readable speaker inside its owning `Shot N:` section. The Prompt must also
state that every authored cue is spoken exactly once, in order, without paraphrase,
omission, restart, repetition, or appended words. Repeated words or phrases inside
a cue occur exactly the authored number of times. Use `<source and sound>`
for effects. Use `(music cue)` only when `background_music_policy` permits it; the
default native-audio flow requires at least one such background-music cue. Reserve `【text】` for generated subtitles,
which this story-video flow forbids because captions belong to postproduction.
Speaker/listener behavior, ambience,
effects, permitted music, silence, and relative timing may otherwise be expressed
in whatever form best serves the generated performance.
The provider duration parameter in the private plan remains authoritative for the
task's total duration. Prompt timing may describe order, rhythm, pauses, or relative
duration, but Python rejects precise provider-facing second ranges.

Close the pre-Shot preamble with the private plan's exact global constraint block.
It prohibits unrequested text/subtitles, logos, watermarks, duplicate or twin-like
subjects, and drift in identity, anatomy, style, costume/state, population, and
continuity. These instructions reduce risk; actual output still requires review.

## Runtime boundary

After UTF-8 decoding, Python checks non-whitespace text and the small authored
reliability layer below. It does not scan or reject other Prompt prose for general
formatting, total or consecutive Shot numbering, internal terminology, JSON-like
text, repetition, or word count. It enforces the
auditable Seedance reliability layer declared by the private plan: ordered exact
binding declarations, operation instruction, one global constraint block, curly-
brace dialogue ownership, one ordered exact presence lock per Character Segment
state, the official music/effect/subtitle delimiters and their policies, and the
absence of precise second ranges.

Python also validates separate deterministic transport facts, such as
the private plan identity, provider operation and total duration, dependency
evidence, media roles, catalog resolution, capability limits, and execution
parameters. Do not extend the small binding parser into a creative prose gate.
