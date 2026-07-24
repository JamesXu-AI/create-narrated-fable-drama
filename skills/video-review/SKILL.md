---
name: video-review
description: Independently review AI narrated drama and fable artifacts or completed Seedance clips for story causality, exact speech, natural dialogue/narration handoffs, character and world continuity, picture, and native sound. Return NO_ISSUES or concise owner-routed corrections; create no approval artifacts.
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

For generated video, watch the full clip at normal speed with sound. Check:

- the correct visible or off-camera speaker says every exact line once;
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
- no paraphrase, missing/extra words, clipped speech, voice mismatch, text,
  captions, logo, watermark, anatomy defect, or extension replay appears.

For a final film, watch clean and captioned masters end to end. Check story order,
rhythm, framing/embedded-world readability, all speech transitions, subtitle
accuracy, mix, seams, and technical playback.

## Transition tolerance

Do not reject harmless frame-level variance when the complete action, exact speech,
speaker ownership, emotional beat, prop ownership, identity, and next-state
continuity remain clear. Reject variance that breaks a causal gate, phrase handoff,
mouth state, voice continuity, exact line, action completion, geography, or
reachable successor state.

## Output

Return:

```text
NO_ISSUES
```

or a short list containing owner, Segment/time/location, observed problem,
expected result, and smallest correction. `NO_ISSUES` is not permission to
generate another Segment; the user still chooses accept, revise, retry, or stop.
