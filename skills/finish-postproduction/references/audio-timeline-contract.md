# Native Audio Timeline Contract

## Main-flow sources

The default and only main-flow audio layer is:

```text
Seedance native-sync = synchronized dialogue + breaths + reactions + room tone
                       + ambience + foley + effects + diegetic sound
                       + background music
background_music_source = seedance_native
```

Every Seedance Segment must contain a real native audio stream generated with
`generate_audio=true`. Each speaking character's fixed
`speaker_reference_audio` constrains voice identity; Seedance still generates the
actual synchronized words. Never replace that stream, shift it away from picture,
or use the identity-reference WAV as delivered dialogue.

Seedance generates the main-flow background music inside its synchronized native
track. Both the current Segment Script and submitted provider Prompt describe that
music with official `(music cue)` notation. Postproduction never separates,
recomposes, or replaces it.

## Timeline behavior

`.pending/finish-postproduction/audio-timeline.json` contains exactly one
`native-sync` track with one sample-aligned event per Segment. It declares:

```text
music_provider: seedance
seedance_background_music: true
background_music_source: seedance_native
```

Do not pre-create a separate SeedAudio track, score policy, or score anchors in this
main-flow artifact. Motivated cuts may use an explicit synchronized edge de-click.
When a generated video forces an unfinished native-music phrase to stop, an
authored `soft_cut` may apply a short fade-out and/or fade-in on dialogue-free
edge material without overlapping or moving either audio event. Authored
dissolve/fade boundaries may overlap picture and native audio by the exact
authored duration.
Native dialogue, effects, and ambience never move across a Segment boundary.
At an incoming `video_extension`, picture and native audio share the same official
six-tail-frame/one-head-frame source trim after dialogue-free handles are verified.
The final native event receives a short terminal fade to prevent an audio click;
that fade never moves, replaces, or attenuates dialogue. An unresolved musical
cadence is acceptable after normal-speed listening no longer detects an obvious
jump; cadence incompleteness alone does not trigger regeneration.

## Delivery

The final delivery manifest declares:

```text
voice_audio_source: speaker_reference_audio
dialogue_source: seedance
native_background_audio_source: seedance_ambience_foley_and_music
seedance_background_music: true
background_music_source: seedance_native
```

No alternate score-generation branch or score artifact is part of this project.
