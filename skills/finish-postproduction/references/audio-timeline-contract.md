# Arabic Segment Soundtrack Timeline Contract

## Fixed source policy

The Arabic branch uses this per-Segment audio chain:

```text
Seedance picture + native ambience/action audio + disposable guide speech
    -> remove all Seedance character speech
    -> hard-mute the complete mixed Seedance track inside dialogue cuts
    -> add exact ElevenLabs Arabic dialogue
    -> one mixed reviewable Segment
    -> unified final edit
```

Every Segment uses `generate_audio=true`, but every generated character voice is
removed before review. Silent-generated Segments are invalid. ElevenLabs
generates dialogue only; it never supplies ambience, Foley, action effects,
animal sounds, or music.

## Segment audio authority

`production-record.json` must contain:

```text
dubbing.contract: seedance-original-audio-dialogue-replacement/v2
dubbing.speech_audio_source: elevenlabs_dubbed
dubbing.sound_effects_audio_source: seedance_native
dubbing.elevenlabs_usage_scope: arabic_dialogue_only
dubbing.elevenlabs_non_dialogue_request_count: 0
dubbing.dialogue_gap_fill_source: digital_silence | not_required
dubbing.alignment_method: seedance_detected_or_storyboard_window_natural_phrase_atempo
dubbing.native_audio_full_duration: true
dubbing.seedance_generate_audio: true
dubbing.seedance_audio_in_delivery: true
dubbing.seedance_background_audio_retained: true
dubbing.seedance_speech_forbidden: true
dubbing.seedance_speech_in_delivery: false
dubbing.seedance_clean_background_speech_gate.status: PASS
dubbing.seedance_audio_edit.status: APPLIED | NOT_REQUIRED
dubbing.picture_frames_retimed: false
```

Every cue record identifies its Storyboard line, speaker entity, ElevenLabs voice
ID, request identity, exact-text hash, source duration, and authoritative
Storyboard start/end. Phrase records contain source/target spans and bounded
tempo. The audio-edit record confirms digital silence, zero loops, and no
center-channel processing inside dialogue cuts.

## Final timeline

The final audio timeline uses one mixed event per accepted Segment. The editor
protects exact Arabic dialogue, Seedance-native ambience/action audio, and every
recorded dialogue-replacement interval. J/L cuts, background bridges, gains, and
fades require explicit model-authored values based on real audio evidence.

The final event receives only the explicitly authored terminal fade. Automatic
silence padding, externally generated ambience, music generation, and voice
replacement are forbidden.

## Delivery declaration

The delivery manifest declares:

```text
voice_audio_source: elevenlabs_voice_id
dialogue_source: elevenlabs
elevenlabs_usage_scope: arabic_dialogue_only
native_background_audio_source: seedance_original_nondialogue_and_native_gap_fill
action_sound_effects_source: seedance_native
seedance_background_music: false
background_music_source: none
seedance_generate_audio: true
seedance_audio_use: non_dialogue_original_audio_after_character_speech_replacement
seedance_audio_in_delivery: true
seedance_speech_in_delivery: false
```

Clean and captioned masters use the same mixed audio timeline. The captioned
master adds subtitle pixels only.
