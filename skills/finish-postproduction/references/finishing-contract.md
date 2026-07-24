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

Postproduction requires one accepted audiovisual Segment per Storyboard row.
It executes the authored transition and may normalize delivery properties but may
not rewrite dialogue, revoice narration, synthesize missing speech, redesign a
shot, or hide a generation defect.

The EDL is:

```text
.pending/finish-postproduction/post-production/picture-audio-edl.json
```

Every external seam receives reversible pre-assembly and final-timeline QC.
Generated Segment files remain read-only. An extension trim is legal only when
Storyboard speech windows and safe handles prove it removes no authored action or
speech.

## Native sound

Each accepted clip keeps its synchronized Seedance-native dialogue, storytelling,
breath, reaction, ambience, effects, and restrained music. The edit preserves the
same established character voice across on-camera and off-camera storytelling.
A short terminal fade may prevent a digital click but may not clip a final word.

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
