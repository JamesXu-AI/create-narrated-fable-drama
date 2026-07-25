# Finishing Contract

## Authority

`screenplay.md` owns story order and target language. `storyboard.md` owns
Generation Segment order, exact speech, Segment-local speech windows, safe landings,
and edit/audio handoffs. Each `segment-NNN.md` is the exact instruction that
produced its accepted media.

`load_segment_handoff` reads the Storyboard and exposes timing and safe-cut facts
without creating a creative companion file. Runtime production records, EDL,
boundary-QC data, subtitle cues, and delivery manifests are technical records only.

## Timeline

Postproduction requires one accepted audiovisual Segment per Storyboard row. It
first measures the actual picture and sound and then requires a complete
`llm-postproduction-repair-plan/v1` written by the Editor and Restoration Master
model. The model decides exact picture source points, cuts, overlaps, transitions,
retained source ranges and internal deletions, local visual repairs, independent
audio splices and placement, gains, fades, bridges, or regeneration. Python does
not translate an authored transition label into an operation or duration.

The EDL is:

```text
.pending/finish-postproduction/post-production/picture-audio-edl.json
```

Every external seam receives actual final-3-second/first-3-second picture-and-sound
evidence, reversible pre-assembly measurement, and final-timeline measurement.
Generated Segment files remain read-only. A picture or audio trim is legal only
when the model declares the exact interval and the validator proves that every
Storyboard dialogue window remains intact.

## Native sound

Each accepted clip keeps its synchronized Seedance-native dialogue, storytelling,
breath, reaction, ambience, effects, and restrained music. The edit preserves the
same established character voice across on-camera and off-camera storytelling.
Every source window, timeline offset, gain, fade, and terminal fade is explicit in
the model plan. The renderer never pads silence, invents a de-click duration, or
adds a terminal fade.

## Subtitle chain

```text
Storyboard exact line + local window
-> picture EDL Segment offset
-> subtitle-cues.json + SRT + VTT
-> captioned master
```

ASR is never authority. Every Storyboard line appears once in order. Display-time
adjustments remain inside the owning Segment and never change native audio.

## Delivery

Release clean and captioned 16:9 masters, subtitle files, and a technical delivery
manifest. Both masters have equal timing and synchronized sound; captioned output
adds subtitle pixels only. Final technical state is `FINAL_MASTER_READY`.
