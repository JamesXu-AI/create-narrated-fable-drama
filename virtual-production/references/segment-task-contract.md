# Segment generation task

One Seed Master `segment-NNN.md` equals one Seedance task and one audiovisual
output. Its prose may represent shots, beats, transitions, or continuous action in
any form and does not have to expose the private plan's Shot count.

The request uses the exact materialized model, duration, resolution, ratio,
operation-specific media, `generate_audio=true`, `watermark=false`, and
`return_last_frame=true`. Prompt tokens are never textually replaced with URLs;
the provider assigns them from the ordered media list maintained by the execution
plan.

The Prompt's pre-Shot layer uses the private plan's exact operation instruction,
priority-ordered media declarations, population lock, ordered Character Segment
presence locks, and global constraint block. Dialogue is written as `{exact
words}`. Do not send precise second ranges. A
`video_extension` instruction addresses its input video directly and must never use
`reference @VideoN` wording.

When the execution plan declares `quality_reset.strategy=white_model_video_edit`,
the `@VideoN` supplied to that same `video_extension` is the generated pure-white 3D
predecessor proxy with remuxed original audio. The Prompt declaration names it as a
white model and uses it only for motion, pose, camera, timing, and structure. Current
high-resolution Location and performer identity/appearance images own the restored
look. The preprocessing edit is not a separate final Segment.

The plan is invalid when its private provider bindings conflict with the selected
`assets.json` declarations or approved Storyboard. Prompt parsing is limited to
the declared token set/placement, priority-ordered exact declarations, operation,
population/global locks, precise-range exclusion, and dialogue ownership; other
creative prose does not make the transport decision.

A serial Segment is not eligible for this task merely because its predecessor file
exists. Virtual production must inspect that exact predecessor attempt together
with the current Segment Script and resolved character/Location bindings, adapt and
rematerialize when the observed ending differs, and obtain a direct
`seedance-video-review` `NO_ISSUES` result. Only a transient exact-attempt
`--observed-predecessor` argument unlocks preflight; it is never stored as an
approval record.

The task is also blocked when its Character Segment state machine would silently
drop a still-present character, restore an absent character without `re_enter`,
omit a required visible Shot, or disagree with the predecessor's reviewed outgoing
presence. Repair the first failing Segment; a later pop-in is not a continuity
solution.

Predecessor-media inheritance is exactly one of: the mandatory white-model proxy of
the complete approved predecessor with preserved audio for a true unfinished
extension, or the approved provider last frame for a settled motivated cut. Either
consumes the one consecutive inheritance hop and is combined with the current
Location-master image. The next same-Scene task must be a strong coverage reset:
it remains serial and semantically observes the predecessor, but submits no
predecessor frame/video and opens with the authored ECU/CU/MCU new angle. The
Location and current identity assets own the complete set, population, and
appearance outside the prior crop.
