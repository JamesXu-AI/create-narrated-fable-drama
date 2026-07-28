# ElevenLabs Segment Audio Contract

## Audio ownership

```text
Seedance -> picture, mouth performance, native ambience/action sound, disposable guide speech
ElevenLabs TTS -> exact Arabic dialogue and character voice only
Storyboard -> exact dialogue timing plus semantic ambience/action intent
```

ElevenLabs may not generate ambience, Foley, footsteps, impacts, animal sounds,
music, room tone, wind, or any other non-dialogue audio. The Arabic branch calls
only ElevenLabs voice-design/voice-creation APIs during asset work and the
text-to-speech-with-timestamps API during Segment dubbing.

Every Prompt uses dialogue-replacement mode and runs Seedance with
`generate_audio=true`. Seedance owns the complete native ambience and action
sound. Every generated character voice is disposable and forbidden in delivery.
The Storyboard supplies hard dialogue bounds; detected Seedance speech supplies
performance timing evidence inside those bounds.

## Alignment method

```text
Seedance native audio + Storyboard exact Arabic cue + start/end
    -> detect native character-speech intervals
    -> cut detected character-speech word intervals plus the final dialogue
       windows with bounded edge padding
    -> replace the complete mixed Seedance track with digital silence inside
       each removed interval
    -> verify the repaired Seedance-native background contains no speech
    -> derive pronunciation-only Arabic tts_text from locked exact_text
    -> generate ElevenLabs Arabic dialogue with character timestamps
    -> derive word spans and natural phrase boundaries
    -> apply uniform cue-local atempo in the detected mouth-performance window
    -> compress abnormal provider amplitude excursions inside each isolated
       dialogue phrase, then normalize to -18 LUFS, 7 LU LRA, and -3 dBFS true
       peak
    -> mix exact Arabic over the repaired Seedance-native track
    -> preserve the picture unchanged
```

No external ambience or sound-effect generator participates. No native interval
may be looped, no channel subtraction or center suppression may run, and no
filtered residual may sit under dialogue. The complete mixed Seedance track is
hard-muted only inside every character-voice replacement interval and is
preserved unchanged everywhere else.

## Timing constants

| Field | Value |
| --- | --- |
| Working sample rate | 48 kHz |
| Phrase boundary | Arabic punctuation, ElevenLabs pause ≥ 180 ms, or 5 words |
| Maximum edge padding | 30 ms |
| Edge fade | 12 ms |
| Native gap-fill crossfade | 25 ms |
| Dialogue-window Seedance gain | digital silence |
| Allowed cue tempo | 0.75–1.30 |
| Picture-duration tolerance | 250 ms |

The Storyboard window is the maximum envelope in which the complete cue may play;
it is not an instruction to stretch short speech across every available frame.
When the raw tempo factor is below `0.75`, use `0.75` and leave the remaining
window for the authored reaction or landing hold. A raw factor above `1.30` is an
upstream timing defect.

Frame review may set one cue's ElevenLabs request speed from `0.7` through
`1.2` with `build_segment_audio.py --reviewed-cue-speed LINE_ID=SPEED`. If an
already approved voice render still ends materially before a visibly slower
mouth performance, a cue-local, pitch-preserving tempo repair down to `0.65`
may be used only when its exact Arabic, final timing, unchanged voice ID, and
voice-identity gate all pass again. Other cues and all non-dialogue native audio
must remain unchanged.

Persist Storyboard bounds, detected native speech bounds, zero native-audio
loops, disabled center suppression, and the rendered ElevenLabs speech end so
review can detect visible-mouth drift or any mixed-track leakage.

## Exactness and speaker identity

- Read cues in Storyboard order.
- Keep Storyboard `exact_text` unvocalized, immutable, and authoritative for
  dialogue hashes and subtitles.
- Deterministically derive a separate pronunciation-only `tts_text`: add only
  approved tashkeel for the all-masculine grammatical policy and proper names;
  reject any rendering whose diacritic-stripped form differs from `exact_text`
  in letters, punctuation, spacing, or word order.
- Send only derived `tts_text` to ElevenLabs with text normalization disabled.
- Reject timestamps whose characters do not reconstruct that exact `tts_text`;
  project word timing back onto the unchanged `exact_text`.
- Hard-lock TTS to `eleven_multilingual_v2`, one neutral urban Riyadh Saudi
  accent profile, stability at least `0.65`, similarity boost at least `0.80`,
  and style at most `0.10`.
- Do not send `language_code=ar` to Multilingual v2 or claim that it locks an
  accent. Persist `language_code=ar` only as project metadata; the Saudi voice
  asset and its accent Prompt are the accent authority.
- Resolve voices only through screenplay entity IDs and
  `ELEVENLABS_VOICE_MAP`.
- Resolve every role's approved TTS settings from its current
  `workspace/assets/characters/<entity_id>/voice.brief.json`; the mapped voice
  ID must match the brief before synthesis. A process-wide default may not
  replace these role-owned settings.
- Create a fresh 32-bit ElevenLabs seed for each cue in every new audio build,
  persist it with the cue, and reuse that same seed only for cue-local speed-fit
  retries within the build. Use
  `build_segment_audio.py --reviewed-cue-seed LINE_ID=SEED` only to reproduce a
  recorded take intentionally.
- Hash both authoritative `exact_text` and derived `tts_text`, and persist the
  accent profile, grammatical-gender policy, pronunciation rules, model ID, and
  `language_code_sent=false` in the embedding record.
- Record `elevenlabs_usage_scope=arabic_dialogue_only` and
  `elevenlabs_non_dialogue_request_count=0`.

## Mix and delivery

Map the Seedance video stream unchanged. Preserve Seedance audio unchanged
outside dialogue-replacement intervals. Hard-mute the complete mixed Seedance
track inside every removed interval with short boundary fades. Never loop,
subtract channels, denoise, extract a residual, or generate replacement sound.
Place exact phrase-aligned ElevenLabs Arabic over the silent dialogue interval
and apply bounded dialogue compression followed by normalization to each
isolated natural phrase before the mix, so one provider take cannot make later
words materially quieter than earlier words. Compression uses a `-24 dB`
threshold, `4:1` ratio, `5 ms` attack, `50 ms` release, and `12 dB` makeup. The
phrase target is `-18 LUFS`, `7 LU` LRA, and `-3 dBFS` true peak; apply final
peak limiting only to avoid clipping. Music remains forbidden.

Downstream review and postproduction require:

```text
dubbing.contract = seedance-original-audio-dialogue-replacement/v2
dubbing.tts_model_id = eleven_multilingual_v2
dubbing.accent_profile_id = saudi_arabic_neutral_urban_riyadh_v1
dubbing.grammatical_gender_policy = masculine
dubbing.pronunciation_contract = arabic-exact-text-plus-derived-tashkeel/v1
dubbing.language_code_sent = false
dubbing.alignment_method = seedance_detected_or_storyboard_window_natural_phrase_atempo
dubbing.speech_audio_source = elevenlabs_dubbed
dubbing.sound_effects_audio_source = seedance_native
dubbing.elevenlabs_usage_scope = arabic_dialogue_only
dubbing.elevenlabs_voice_settings_authority = workspace_role_voice_brief
dubbing.elevenlabs_seed_policy = fresh_per_audio_build_persisted_per_cue_with_reviewed_override
dubbing.dialogue_phrase_loudness_normalization.status = APPLIED | NOT_REQUIRED
dubbing.elevenlabs_non_dialogue_request_count = 0
dubbing.dialogue_gap_fill_source = digital_silence | not_required
dubbing.native_audio_full_duration = true
dubbing.seedance_generate_audio = true
dubbing.seedance_audio_in_delivery = true
dubbing.seedance_background_audio_retained = true
dubbing.seedance_speech_forbidden = true
dubbing.seedance_speech_in_delivery = false
dubbing.seedance_clean_background_speech_gate.status = PASS
dubbing.seedance_audio_edit.status = APPLIED | NOT_REQUIRED
dubbing.picture_frames_retimed = false
```

Normal-speed review rejects any surviving Seedance character speech or
non-language vocalization, duplicated line, repeated background or character
sound, nonzero native-audio loop count, channel-subtraction noise, filtered
residual, background loss outside the cuts, dialogue masking, wrong mouth
movement, or unnatural ElevenLabs tempo.

## Failure policy

Fail the current Segment when:

- the Seedance result lacks a native audio stream;
- repaired Seedance-native background still contains detected speech;
- any Seedance mixed-track audio remains inside a replacement interval;
- exact Arabic character identity differs;
- the model, Saudi accent profile, masculine pronunciation policy, derived
  `tts_text` hash, or tashkeel rules are stale;
- an ElevenLabs speaker mapping is missing;
- any non-dialogue ElevenLabs request is attempted or recorded;
- cue tempo falls outside the natural range;
- the final output lacks video or mixed audio; or
- picture duration changes beyond tolerance.

Audio building starts immediately after one Seedance source becomes
`PICTURE_GENERATED`. A directly reviewed `NO_ISSUES` picture may release the next
Segment's Seedance submission while this audio build runs, but the current
Segment remains unaccepted and cannot enter postproduction until every Arabic
audio and voice-identity gate passes. If dubbing fails, retain and reuse the
immutable `seedance-source.mp4`; do not resubmit Seedance for an audio-only
failure.

Do not postpone audio building, accumulate more than one reviewed picture/audio
pipeline overlap, batch uncleansed Segments into postproduction, replace missing
background with silence, or allow Seedance character voice into delivery.
