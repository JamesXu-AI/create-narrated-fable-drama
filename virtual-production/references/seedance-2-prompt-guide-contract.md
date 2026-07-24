# Seedance 2.0 Prompting Contract

This contract adapts the supplied Volcengine `Doubao Seedance 2.0` Prompt guide
to this story-video pipeline. Apply it when cinematography plans a Generation
Segment, when virtual production authors the exact provider Prompt and binds
media, and when review or finishing diagnoses a result.

## Choose the task before writing the Prompt

Use one unambiguous task mode:

- `multimodal_reference`: extract a named subject, setting, action, camera pattern,
  effect, voice, or sound quality from media to make a new video. Say what each
  medium supplies.
- `video_extension`: continue the complete predecessor in time. Address the video
  directly as the clip to extend or continue; do not call it a reference video.
- `video_edit`: alter an existing video while preserving everything not explicitly
  changed. State the original feature, new feature, appearance time, and position.
- `track_completion`: bridge two or three ordered videos with authored transition
  content. Provider input is limited to three videos and 15 seconds total.

The current educational-story pipeline executes the first two modes. Do not
silently substitute edit or track-completion wording for them.

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

Treat four independently referenced performers as a simple-composition
recommendation, not a hard provider limit. Do not carry a provider-renderable role
only through temporal evidence: every such role needs its own catalog
identity/appearance-state image. Use an approved closed group image for an anonymous
ensemble, or repack only when verified media capacity/composition complexity is
actually exceeded.

## Write the temporal layer as ordered Shots

Use readable `Shot N:` sections in event order. Each Shot communicates:

- the cut or one dominant camera behavior;
- the active subject's visible action and expression;
- position, spatial change, gaze, and listener reaction; and
- synchronized dialogue, sound effects, ambience, and silence.

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

- dialogue: `{exact spoken words}`;
- music: `(audible music cue)` when the project's audio policy permits it;
- sound effect: `<audible source and event>`;
- generated on-screen text/subtitle: `【exact text】` only when explicitly wanted.

Keep one dialogue language within a Segment except for approved proper nouns. For
hard Chinese pronunciations, retain story text in authority files and place an
approved same-sounding common-character performance form only in the provider
Prompt plus a traceable pronunciation note; never silently rewrite subtitle text.

Describe a reference voice in audible terms as well as binding its audio: age,
pitch, weight, texture, pace, energy, and delivery should agree with the line.

This project's default main flow permits and requires Seedance-native background
music, so every Segment includes at least one intentional `(music cue)`. Keep it
subordinate to dialogue and important effects. Generated subtitles remain disabled;
final captions are authored in postproduction.

## Close the Prompt with one global constraint block

The exact model-facing block must prohibit:

- unrequested text or subtitles;
- logos and watermarks;
- duplicate people, clones, twin-like copies, and repeated instances of one
  subject; and
- style, identity, anatomy, costume/state, population, or continuity drift.
- silent disappearance of a Character Segment state, loss of a
  `must_remain_visible` performer in any required Shot, or unexplained pop-in after
  an absent state.

Use the approved visual style explicitly. If source media visibly conflicts with
that style, repair or restyle the source upstream rather than asking the Prompt to
overpower it.

These constraints reduce failure probability; they are not a claim of guaranteed
provider behavior. Direct review still checks the actual video.

## Extension and finishing safeguards

- Use extension for continuous dialogue, emotion, or one continuous path. Use
  separate generated clips for a strong action/scene turn.
- Every permitted extension, including the first, begins with runtime strictly
  editing the predecessor into a pure-white 3D white-model proxy, remuxing the
  predecessor's original synchronized audio, and passing that proxy as the
  extension's direct video input. The successor must bind current high-resolution
  Location and performer identity/appearance images; its Prompt identifies the
  white model as motion, pose, camera, timing, and structural authority only. The
  proxy is never final footage.
- A tail-frame handoff and an extension share one predecessor-media budget. The next
  same-Scene Segment must use a reference-free strong coverage reset with no
  predecessor provider token; preserve semantic state through current Location and
  identity assets, and open on ECU/CU/MCU from a decisively changed
  angle/viewpoint/composition.
- At an accepted extension splice, finish may remove six outgoing frames and one
  incoming frame only when authored action/dialogue handles prove those frames are
  disposable. Record the trim in the EDL and review the resulting seam.
- Fade the terminal native-audio edge to zero over a short envelope so a narration
  or spoken line cannot end with a digital click.

## Review failure classes

Inspect for identity drift, an unapproved celebrity-like face, unexpected text,
subtitle, logo, watermark, style drift, duplicate subject, wrong performer count,
missing/extra limb, unstable high-energy action, extension jump or replay,
progressive extension degradation, incorrect effect logic, clipped terminal audio,
mispronunciation, and voice mismatch. Route each problem to the owning department;
never hide a generation defect in postproduction.
