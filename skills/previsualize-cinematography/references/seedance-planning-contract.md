# Seedance 2.0 Previsualization Contract

This contract adapts the supplied Volcengine `Doubao Seedance 2.0` Prompt guide to
previsualization decisions. Use it to make each planned Generation Segment,
reference role, camera behavior, action path, and audio handoff compatible with
downstream execution. This skill does not author the provider Prompt, bind media,
call a provider, or review generated footage.

## Contents

- [Choose the task before writing the Prompt](#choose-the-task-before-writing-the-prompt)
- [Build the spatial layer before the temporal layer](#build-the-spatial-layer-before-the-temporal-layer)
- [Write the temporal layer as ordered Shots](#write-the-temporal-layer-as-ordered-shots)
- [Use Seedance-readable audio notation](#use-seedance-readable-audio-notation)
- [Close the Prompt with one global constraint block](#close-the-prompt-with-one-global-constraint-block)
- [Extension and finishing safeguards](#extension-and-finishing-safeguards)
- [Review failure classes](#review-failure-classes)

## Choose the task before writing the Prompt

Use one unambiguous task mode:

- `text_to_video`: make an independent video from approved text authority when no
  provider media reference or predecessor output is required.
- `multimodal_reference`: extract a named subject, setting, action, camera pattern,
  effect, voice, or sound quality from media to make a new video. Say what each
  medium supplies.
- `video_extension`: continue the complete predecessor in time. Address the video
  directly as the clip to extend or continue; do not call it a reference video.
- `video_edit`: alter an existing video while preserving everything not explicitly
  changed. State the original feature, new feature, appearance time, and position.
- `track_completion`: bridge two or three ordered videos with authored transition
  content. Provider input is limited to three videos and 15 seconds total.

This previsualization skill plans only `text_to_video`, `multimodal_reference`, and
`video_extension`. Do not silently substitute edit or track-completion wording for
them or add an unsupported operation to the Storyboard contract.

## Build the spatial layer before the temporal layer

Before the first Shot, identify every provider token and assign exactly one
readable responsibility:

1. define the subject with one stable label and two or three concise, visible,
   non-conflicting traits;
2. state whether the medium owns identity, costume/state, location, camera/action,
   effect, voice, ambience, or another single purpose;
3. introduce the most identity-critical declaration first;
4. keep the same subject label in every later mention; and
5. never expose an internal Asset ID as if Seedance could infer its contents.

Treat the usual four media functions separately: character identity, scene/style,
camera/action, and rhythm/voice. Aim for four or five total references when that is
sufficient. Do not fill the provider limit merely because media exists.

For a face-critical human character, prefer one isolated neutral face close-up and
one isolated full-body identity image. Do not use a three-view or multi-view person
collage: Seedance can interpret the repeated person as several subjects. When the
current catalog lacks a valid face anchor, keep the single-subject full-body image
and do not fabricate one downstream.

Treat four independently referenced performers as a simple-composition planning
recommendation, not a hard provider limit. Every provider-renderable role still
receives its required identity/appearance-state image. Repack the Segment only when
the verified provider media capacity or composition complexity is actually
exceeded; an approved closed group image may represent an anonymous ensemble.

The reference ceiling never authorizes an upstream visibility downgrade. Preserve
every screenplay-required individual and ensemble in its required Shots. Reduce
simultaneous motion, split the Generation Segment at a motivated boundary, or bind
an approved closed-roster group asset instead of moving required roles off-screen.
Within those obligations, keep each actual frame to the minimum story-active
subjects—normally one subject or one speaker/listener pair—and carry still-present
cropped roles through explicit off-screen state rather than a full-cast master.

## Write the temporal layer as ordered Shots

Use readable `Shot N:` sections in event order. Each Shot communicates:

- the cut or one dominant camera behavior;
- the active subject's visible action and expression;
- position, spatial change, gaze, and listener reaction; and
- synchronized dialogue, sound effects, ambience, and silence.

ECU/CU/MCU is the baseline and must dominate. Before any interaction Shot, preserve
the Storyboard's A/B screen sides, opposed look directions, axis line, and camera
side. A medium-wide/wide/extreme-wide Shot must carry the literal label
`position-change exception:` and only cover the shortest readable
entrance/exit/crossing/approach/retreat/mark-transfer interval before returning
tight.

Prefer event order and natural rhythm to exact provider-facing ranges such as
`0-3 seconds`; precise ranges are unstable and are rejected from the model-facing
Prompt. Deterministic duration and dialogue timing remain in the private execution
plan for transport, captions, and edit math.

Within one Shot, prefer a locked camera or one dominant move. Split a motivated
camera change into the next Shot instead of stacking push, pull, pan, tilt, crane,
and orbit instructions together.

Describe motion through the relevant body part plus range, speed, and force. Favor
small, continuous, reachable actions over uncontrolled explosive motion. State the
inertial or causal bridge between consecutive actions. Externalize emotion through
observable breath, eyes, posture, hands, shoulders, pace, and gaze rather than an
abstract emotion label alone.

## Use Seedance-readable audio notation

Keep exact dialogue and audio cues as readable authority text in `storyboard.md`.
In Prompt Translation Notes, preserve these downstream conversion rules without
writing the provider Prompt itself:

- dialogue becomes `{exact spoken words}`;
- music becomes `(audible music cue)` when the project's audio policy permits it;
- sound effects become `<audible source and event>`;
- explicitly authored English on-screen text becomes `【exact text】`.

Keep one dialogue language within a Segment except for approved proper nouns. For
hard Chinese pronunciations, retain story text in authority files and place an
approved same-sounding common-character performance form only in the provider
Prompt plus a traceable pronunciation note; never silently rewrite subtitle text.

Describe a reference voice in audible terms as well as binding its audio: age,
pitch, weight, texture, pace, energy, and delivery should agree with the line.

This project's default main flow permits and requires Seedance-native background
music, so every Segment plans at least one intentional music cue in readable prose.
Keep it subordinate to dialogue and important effects. Natural readable English
text may also arise incidentally in the scene and is allowed. Generated subtitles
and on-screen transcription remain disabled; final captions are authored in
postproduction.

## Close the Prompt with one global constraint block

Require downstream compilation to close the provider Prompt with one global block;
do not write that block as a separate previsualization artifact. The block must
prohibit:

- generated captions, on-screen transcription, and unreadable pseudo-writing;
- logos and watermarks;
- duplicate people, clones, twin-like copies, and repeated instances of one
  subject; and
- decorative bystanders, unauthorized full-cast composition, ambiguous or
  reversed eyelines, and unmotivated widening; and
- style, identity, anatomy, costume/state, population, or continuity drift.

Use the approved visual style explicitly. If source media visibly conflicts with
that style, repair or restyle the source upstream rather than asking the Prompt to
overpower it.

These constraints reduce failure probability; they are not a claim of guaranteed
provider behavior. Direct review still checks the actual video.

## Extension and finishing safeguards

- Use extension for continuous dialogue, emotion, or one continuous path. Use
  separate generated clips for a strong action/scene turn.
- Every permitted extension, including the first, uses the official mitigation:
  strictly edit the approved predecessor into a pure-white 3D white-model video,
  preserve its original synchronized audio by remux, and pass that proxy as the
  extension's video input. Bind current high-resolution
  Location and performer identity/appearance images so the proxy supplies motion
  and structure rather than final appearance. The proxy is temporary and never
  enters the final timeline.
- A soft last-frame handoff and a white-model extension share one inheritance
  budget. After either one, the next same-Scene Segment must use a reference-free
  strong coverage reset: no predecessor image/video, semantic state preserved,
  first Shot ECU/CU/MCU, and a decisively new angle/viewpoint/composition. Do not
  interrupt unfinished action; repack or finish it before the reset boundary.
- At an accepted extension splice, downstream finishing may remove six outgoing
  frames and one incoming frame only when this Storyboard authors disposable
  action/dialogue handles. Do not create an EDL in previsualization.
- Fade the terminal native-audio edge to zero over a short envelope so a narration
  or spoken line cannot end with a digital click.

## Review failure classes

Inspect for identity drift, an unapproved celebrity-like face, unreadable
pseudo-writing or scene-contradictory text, generated subtitle/transcription, logo,
watermark, style drift, duplicate subject, wrong performer count, missing/extra
limb, unstable high-energy action, extension jump or replay, progressive extension
degradation, incorrect effect logic, clipped terminal audio, mispronunciation,
voice mismatch, crowded staging, axis reversal, insufficient close-up dominance,
and a wide Shot that does not cover a required position change. Natural readable
English scene text is allowed and is not independently a defect. Route each problem
to the owning department; never hide a generation defect in postproduction.
