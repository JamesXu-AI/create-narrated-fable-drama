# Seedance Prompting Contract

## Select one operation

- `multimodal_reference`: make a new clip from named identity, location, state, or
  style references.
- `video_extension`: continue the approved predecessor in time.
- `text_to_video`: generate a deliberately reference-free shot when Storyboard
  authority is sufficiently explicit.

Do not blur these operations in one Segment.

## References

Declare every Storyboard provider token before its first use as
`@ImageN (Arabic readable subject)` or `@VideoN (Arabic readable subject)`.
All other model-facing prose is Arabic with no Latin letters. Follow every later
token use immediately with a readable noun in parentheses. Give each image or
video a single job: identity, appearance state, location, or recent temporal
state. Internal asset IDs mean nothing to the provider and are forbidden.

Do not treat a predecessor frame as identity authority. Do not submit a positive
reference for a storyteller or other role that the current embedded-story Segment
requires to remain visually absent.

## Ordered guide-performance shots

Each Shot states exactly one Arabic-labeled dominant camera behavior, subject/action,
setting/environment, and lighting/tone, followed by disposable audible
guide-performance ownership, background ambience/action effects, listener response, and edit
landing. Never combine two camera-movement families in one Shot. Prefer natural
event order over exact time ranges.

Before Shot 1, state the exact visible-character economy, eyeline axis/screen
directions, and close-up-led policy from the Storyboard. Begin every beat
`اللقطة N: <Arabic rendering of exact shot_size>.` Keep one story-active subject or one
speaker/listener pair visible whenever authority permits. Preserve A/B screen
sides, opposed look directions, and the same camera side of the axis through
reverses. ECU/CU/MCU dominate. A medium-wide/wide/extreme-wide beat is legal only
as a literal `استثناء تغيير الموضع:` covering the shortest readable
entrance/exit/crossing/approach/retreat/mark-transfer interval before returning
tight.

Speech uses `{exact words}` and appears exactly once. The prompt must make these
facts unmistakable:

- speaker identity;
- visible or off-camera status;
- audible disposable guide-performance owner and closed-mouth listeners;
- on-camera dialogue, on-camera storytelling, off-camera storytelling, external
  voiceover, or embedded-character dialogue;
- the phrase/breath trigger and J-cut/L-cut or visual handoff;
- whether the same established ElevenLabs voice ID crosses the cut;
- how the later dubbed cue bridges the transition.

An on-screen Grandfather who begins a story and continues over an embedded scene
remains Grandfather. He does not become a generic second narrator. When an
embedded character begins speaking, Grandfather pauses and only that character's
mouth moves. Reverse the handoff just as explicitly when narration returns.

## Seedance performance and downstream ElevenLabs dialogue

The audited Prompt uses only dialogue-replacement mode and runs with
`generate_audio=true`: on-camera speakers perform the exact Arabic
guide line while Seedance creates original ambience/action sound. Immediately
afterward, virtual production cuts every generated character voice, verifies the
cleaned native background, hard-mutes the complete mixed Seedance track inside
the dialogue cut, preserves it unchanged outside the cut, and inserts the
mapped ElevenLabs voice without retiming
picture. ElevenLabs generates dialogue only. The provider picture is immediately
reviewable on its independent picture track, but the Segment is not
audiovisually reviewable or acceptable before dubbing and the audio gates
complete. Generated captions are forbidden.

## Extension safeguards

Use extension only for genuine continuous action or speech. Runtime may create a
white-model proxy from a predecessor solely for motion, pose, camera, timing, and
structure; current approved images continue to own identity, texture, costume,
location, and color. Strong coverage resets begin from current visual authorities
without predecessor media.

## Review

Before human confirmation, require the independent
virtual-production internal-audit record to match the exact Prompt, Storyboard,
and audit-ruleset hashes.

Reject wrong speaker, wrong mouth movement, narrator voice replacement after
dubbing, any surviving Seedance character voice, missing Seedance-native
dialogue-cut repair or authored native action effects, unnatural
dialogue-to-narration switching, clipped lines, paraphrase, duplicate subjects,
identity drift, text, logos, watermarks, continuity jumps, extension replay,
missing dubbing handoffs, decorative/extra characters, crowded full-cast staging,
ambiguous or reversed eyelines, lost close-up dominance, an unearned wider view,
or progressive quality degradation.
