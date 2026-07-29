---
name: video-review
description: Review only screenplay, Storyboard, generated Segment, and final-film artifacts produced by this repository's create-narrated-fable-drama authority chain. Use after a repository-local authoring stage, Segment attempt, or final assembly when the task's authored sources and approved voice references are available. Follow the task language; do not trigger for arbitrary Seedance clips, external provider workflows, or projects without this repository's task structure. Return NO_ISSUES or concise owner-routed corrections; create no approval artifacts.
---

# Video Review

Read the [Narrated Fable Drama Production Standard](../../references/narrated-fable-drama-production-standard.md)
and [Human-in-the-Loop Guided Workflow](../../references/human-in-the-loop-guided-workflow.md).

## Scope gate

Continue only when all of the following are true:

- this file resolves to this repository's `skills/video-review/SKILL.md`;
- the artifact belongs to a task under this repository's
  `workspace/tasks/<task>/`; and
- the review can use the repository authority chain, including the applicable
  screenplay, Storyboard, Segment Prompt, accepted predecessor, or approved voice
  reference.

Otherwise stop and use the owning project's review workflow. A provider name or
the words `Seedance`, `Segment`, `video review`, or `completed clip` do not
establish scope. Take the target language from the task screenplay; this Skill
has no language-specific default or branch.

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

For generated video, watch the full clip at normal speed with sound. Check:

- the correct visible or off-camera speaker says every exact line once;
- before returning `NO_ISSUES`, compare every speaking character with that
  character's approved voice reference and with the same character's nearest
  generated speech; check timbre, register, age, texture, accent, pace, energy,
  and forbidden effects such as squeak, helium pitch, buzzing distortion, or
  generic narrator replacement;
- only the intended speaker's mouth moves and lip sync is natural;
- an on-screen character remains the same recognizable voice when becoming an
  off-screen storyteller;
- the switch into or out of embedded-character dialogue feels motivated rather
  than abrupt;
- listener reaction and visual handoff land at the authored phrase or breath;
- no generic second narrator, duplicate storyteller, unplanned portrait,
  silhouette, reflection, or extra character appears;
- identity, costume/state, props, geography, light, color, action phase, and
  ambience remain continuous where the story requires;
- camera, action, internal cuts, effects, native music, safe ending, and external
  seam are usable;
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
unmeasurable speech blocks Segment acceptance and successor generation. A
technical `PASS` does not replace normal-speed human/model listening review.

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
expected result, and smallest correction. `NO_ISSUES` is not permission to
generate another Segment; the user still chooses accept, revise, retry, or stop.
