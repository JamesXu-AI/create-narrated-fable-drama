---
name: video-review
description: Independently review either picture-ready Seedance attempts or completed Arabic-dubbed clips, keeping picture release separate from audio acceptance while checking story causality, continuity, speech, mouth sync, ambience, action effects, and sound.
---

# Video Review

Read the [Narrated Fable Drama Production Standard](../../references/narrated-fable-drama-production-standard.md)
and [Human-in-the-Loop Guided Workflow](../../references/human-in-the-loop-guided-workflow.md).

Review the actual artifact or complete audiovisual clip, identify concrete
problems, name the owning department, and recheck only the affected result after
correction. Do not edit another department's work or create review JSON, approval
files, hashes, locks, or director-decision records.

## Required review

For scripts and Storyboards, check:

- story causality, cultural fit, exact speaker, exact words, and delivery mode;
- framing conversation versus embedded-story clarity;
- physical preparation, line delivery, listener reaction, changed state, and edit
  handoff;
- phrase/breath boundary, J-cut/L-cut or visual bridge, mouth ownership, voice
  continuity, and ambience bridge;
- positive image omission when an established storyteller is voice-only and
  visually absent.
- each Shot uses the fewest story-active visible characters, normally one subject
  or one speaker/listener pair, without decorative bystanders or default
  full-cast staging;
- every interaction names a stable eyeline axis, A/B screen sides, opposed look
  directions, and camera side;
- ECU/CU/MCU dominate, and every MWS/WS/EWS is a labeled, shortest-readable
  position-change exception followed by a tight Shot.

For a `PICTURE_GENERATED` attempt, review the complete immutable
`seedance-source.mp4` and its exact last frame before it may release a serial
successor. Check story action, identity, composition, continuity, eyeline axis,
close-up dominance, every required position change, picture defects, internal
cuts, last-frame usability, and the incoming/outgoing visual seam. Seedance native
audio and disposable guide speech are not audio-acceptance evidence at this
stage. Picture `NO_ISSUES` releases only the exact provider attempt as predecessor
evidence; it does not accept the Segment or replace the successor's fresh human
confirmation.

For a completed `GENERATED` video, watch the full clip at normal speed with sound.
Check:

- the ElevenLabs track gives every exact Arabic line once to the correct visible
  or off-camera speaker;
- before returning `NO_ISSUES`, compare every speaking character with that
  character's approved voice reference and with the same character's nearest
  generated speech; check timbre, register, age, texture, accent, pace, energy,
  and forbidden effects such as squeak, helium pitch, buzzing distortion, or
  generic narrator replacement;
- only the intended speaker's mouth moves and the measured Seedance mouth
  performance aligns naturally with the ElevenLabs cue;
- ambience and every Storyboard-authored action effect remain audible; in
  dialogue-replacement mode, Seedance is the sole source of ambience, action
  sound, Foley, animal sounds, and other permitted non-dialogue audio; its
  non-dialogue sound remains unchanged outside the recorded cuts and no generated
  character voice may survive;
- ElevenLabs supplies exact Arabic character dialogue only and never ambience,
  action sound, Foley, animal sounds, music, room tone, or any other non-dialogue
  audio;
- an on-screen character remains the same recognizable voice when becoming an
  off-screen storyteller;
- the switch into or out of embedded-character dialogue feels motivated rather
  than abrupt;
- listener reaction and visual handoff land at the authored phrase or breath;
- no generic second narrator, duplicate storyteller, unplanned portrait,
  silhouette, reflection, or extra character appears;
- identity, costume/state, props, geography, light, color, action phase, and
  ambience remain continuous where the story requires;
- camera, action, internal cuts, safe ending, dubbed audio, and external seam are
  usable;
- the frame is not crowded with unnecessary characters; cropped but present roles
  remain spatially credible without forcing a full-cast master;
- speaker/listener gaze, screen-left/right assignment, reverse angle, and camera
  side preserve the authored eyeline axis, with no same-direction look or silent
  axis flip;
- close-ups remain the dominant experience; any wider interval exists only long
  enough to read the authored entrance, exit, crossing, approach, retreat,
  mark-transfer, or other consequential position change, then returns tight;
- no paraphrase, missing/extra words, clipped speech, voice mismatch, text,
  captions, logo, watermark, anatomy defect, or extension replay appears.

Run the repository voice-identity evidence gate for every completed Segment that
contains speech. A technical `FAIL`, missing voice reference, unreadable audio, or
unmeasurable speech blocks Segment acceptance and postproduction, but does not
invalidate an already reviewed picture or stop an already authorized successor
Seedance job. A
technical `PASS` does not replace normal-speed human/model listening review.
The same gate must also bind every reviewed cue to `language=Arabic`,
`language_code=ar`, its exact Arabic text hash, and the speaker's assigned
ElevenLabs voice ID from the asset department. Missing, English, transliterated,
mixed-Latin, stale, or differently voiced dialogue blocks acceptance before the
acoustic comparison.

For a final film, watch clean and captioned masters end to end. Check story order,
rhythm, framing/embedded-world readability, all speech transitions, subtitle
accuracy, mix, seams, and technical playback.

## Transition tolerance

Do not reject harmless frame-level variance when the complete action, exact speech,
speaker ownership, emotional beat, prop ownership, identity, and next-state
continuity remain clear. Reject variance that breaks a causal gate, phrase handoff,
mouth state, voice continuity, exact line, action completion, geography, or
reachable successor state.
Do not tolerate decorative extra characters, an ambiguous/reversed interaction
axis, a wide view without a required position change, a wider interval that holds
past its movement landing, or a result whose dramatic coverage is not primarily
ECU/CU/MCU.

## Output

Return:

```text
NO_ISSUES
```

or a short list containing owner, Segment/time/location, observed problem,
expected result, and smallest correction. Picture-track `NO_ISSUES` releases the
exact attempt as predecessor evidence, but the successor still needs a fresh human
confirmation. Audiovisual `NO_ISSUES` is not final acceptance; the user still
chooses accept, revise, retry, or stop for the current Segment.
