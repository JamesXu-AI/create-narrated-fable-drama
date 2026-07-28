---
name: virtual-production
description: Compile an approved Arabic drama Storyboard into exact 16:9 Seedance Segment Prompts, publish and independently review picture-ready provider attempts, preserve Seedance-native non-dialogue sound, and immediately replace generated speech with exact ElevenLabs Arabic dialogue on a separate audio track.
---

# Virtual Production

Read the repository [Narrated Fable Drama Production Standard](../../references/narrated-fable-drama-production-standard.md), the [Storyboard Contract](../previsualize-cinematography/references/storyboard-contract.md), the generation-time [Seedance 2.0 Prompt Authoring Contract](references/seedance-2-prompt-authoring-contract.md), [Engineered Prompt Guidance](references/natural-language-seedance-prompt.md), [Seedance Prompting Contract](references/seedance-2-prompt-guide-contract.md), the department's separate internal [Prompt Audit Contract](references/seedance-2-prompt-audit-contract.md), and the internal [ElevenLabs Segment Audio Contract](references/elevenlabs-segment-audio-contract.md).

## Authority

Compile each approved `Generation Segment` in:

```text
TASK_DIR/previsualize-cinematography/storyboard.md
```

to exactly one model-facing file:

```text
TASK_DIR/.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

Do not create a companion creative JSON file. Provider requests, attempt records,
hashes, QC manifests, and delivery manifests may be JSON because they record
runtime facts rather than story meaning.

## Prompt compilation

Apply the Prompt Authoring Contract before and during composition. First resolve
the operation, map atomic references, and confirm all eight core elements from
Storyboard authority. Missing or conflicting information returns upstream; do
not draft around it or silently fill it.

The Segment Prompt is the complete instruction Seedance sees. Its entire
model-facing prose must be Arabic. Latin letters are forbidden except inside the
provider's required `@ImageN` and `@VideoN` reference tokens. It must:

- use the ordered sections `الإعداد العام وخريطة المراجع:`, exact per-Shot
  blocks, and `الجودة والقيود:`;
- declare every Storyboard reference token before first use and give each token one
  readable responsibility; write `@ImageN (readable subject)` or
  `@VideoN (readable subject)` and follow every later token use immediately with
  a readable noun in parentheses;
- reproduce the Storyboard operation, ordered internal shots, framing, action,
  blocking, gaze, light, exact mouth performance, and landing state;
- before Shot 1, translate the Storyboard direction faithfully under the exact
  Arabic labels `اقتصاد الشخصيات الظاهرة:`,
  `محور النظرات واتجاه الشاشة:`, and
  `تغطية تقودها اللقطات القريبة:`; keep the actual frame to the fewest story-active
  subjects and preserve A/B screen sides, opposed looks, axis line, and camera
  side;
- begin each beat `اللقطة N: <Arabic rendering of the exact Storyboard shot_size>.`;
  ECU/CU/MCU must dominate,
  and any MWS/WS/EWS beat must repeat the literal
  `position-change exception:` with its start mark, path, landing mark, changed
  relation, and tight return;
- state exactly one `سلوك الكاميرا المهيمن:`, `الشخصية والفعل:`,
  `المكان والبيئة:`, and `الإضاءة والنبرة:` field in every Shot;
  select only one dominant camera family;
- name the exact speaker for each line and put the exact Arabic words once in
  `{braces}`; require one audible disposable guide performance from each visible
  speaker to drive mouth motion, and remove it after generation;
- state whether the speaker is visible and articulating, visible as a storyteller,
  off camera with the same established voice, an external voiceover, or an
  embedded-scene character;
- carry the Storyboard transition trigger: phrase or breath boundary, listener
  reaction, mouth behavior, J-cut/L-cut or visual handoff, voice continuity, and
  later ElevenLabs dubbing bridge;
- when an on-screen character becomes the off-screen storyteller, explicitly say
  it is the same person and same voice, with no new narrator introduced;
- when that storyteller is absent from an embedded-story image, state the
  positive visible composition and that the established voice continues off
  camera; do not submit a positive storyteller image for that Segment;
- preserve exact 16:9 composition and use only this audio directive:
  `صوت سيدانس: ينشئ المسار الصوتي الأصلي الكامل للأجواء والحركة، وتنطق الشخصية المرئية الحوار العربي لتوجيه حركة الفم؛ بعد التوليد يُحذف كل صوت شخصيات ويُستبدل بالحوار العربي الدقيق من إليفن لابز، وتُمنع الموسيقى والترجمات.`;
- state the screenplay's exact approved Visual Style; resolution is supplied as
  the selected provider parameter and defaults to 1080p only when not overridden;
- forbid generated captions, paraphrased speech, duplicate characters, identity
  drift, decorative bystanders, unauthorized full-cast composition, reversed or
  ambiguous eyelines, unmotivated widening, unexplained
  appearance/disappearance, logos, and watermarks.
- finish with the exact quality and anti-distortion fallback owned by
  the internal Prompt Audit Contract.
- contain no Latin prose, English headings, English camera terms, English
  character/location names, or English negative constraints; translate product
  names as `سيدانس` and `إليفن لابز`.

Use natural event order, not provider-facing second ranges. Internal timing remains
derived from the Storyboard for subtitle and edit math.

## Validate and execute

Author every Segment Prompt before opening the human loop. Then validate the
complete Prompt set:

```bash
python3 skills/virtual-production/scripts/validate_segment_scripts.py validate \
  --task-dir TASK_DIR
```

Require `first_full_prompt_gate=PASS` and the full Segment-Prompt
`speech_rate_gate.status=PASS`. Then execute the independent internal gate before
showing any Prompt for human confirmation:

```bash
.venv/bin/python \
  skills/virtual-production/scripts/audit_segment_prompts.py \
  --task-dir TASK_DIR --all
```

Require a fresh `seedance-prompt-internal-audit/v3` PASS record for every
Segment. Partial validation or a missing/stale audit never opens generation.

Preflight one Segment:

```bash
python3 skills/virtual-production/scripts/preflight_segment.py \
  --task-dir TASK_DIR \
  --segment-script TASK_DIR/.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

Preflight first reruns the asset department's complete production-design gate.
It must block before any Seedance request when a speaking role lacks a current
Voice Design provenance binding for the neutral urban Riyadh Saudi Prompt,
distinct Voice ID, Multilingual v2 reference, masculine pronunciation policy,
or stable voice settings. Existing audio made under an older Prompt is stale;
do not relabel it as compliant.

Only after that first full gate passes, begin the human-in-the-loop phase and
generate after the human approves that exact Segment Prompt:

```bash
python3 skills/virtual-production/scripts/generate_segment_videos.py \
  --task-dir TASK_DIR --segments segment-NNN
```

Generate one Segment per approval. Require the audited replacement directive and
submit `generate_audio=true`. Require the native audio stream,
retain the untouched provider result as `seedance-source.mp4` in the published
Segment directory,
and publish `PICTURE_GENERATED` as soon as that source plus its provider last
frame pass technical probing. This picture-ready state is not an accepted
Segment: it exists so virtual production can review the actual picture and tail
immediately. After that direct picture review returns `NO_ISSUES`, a different
Segment process may submit the reviewed successor while the current Segment
continues its ElevenLabs build and audio gates. Use Segment-scoped execution
locks; never run two provider or audio jobs for the same Segment.

For the current Segment,
remove only detected character-speech intervals with bounded edge padding,
verify the cleaned background contains no speech, preserve the original Seedance audio
unchanged outside the cuts, hard-mute the complete mixed Seedance track inside
every cut with short boundary fades, and
derive a pronunciation-only `tts_text` from immutable Storyboard `exact_text`;
insert the resulting ElevenLabs Arabic at natural phrase boundaries. The
derived text may add only approved tashkeel and must strip back exactly to the
Storyboard text. ElevenLabs is forbidden for ambience, action sound, Foley, animal
sounds, or music. Do not queue an unreviewed successor or postpone the current
audio build; only the reviewed picture-to-next-picture overlap above is allowed.
Then
review the complete dubbed clip with
sound and its incoming seam. Before the Segment can be
accepted or handed to postproduction, run the approved-reference voice-identity
gate for every dialogue cue,
then explicitly listen for the same timbre, register, age, texture, accent, pace,
and energy. Missing evidence or any voice-identity failure blocks acceptance and
postproduction, but does not invalidate an already reviewed Seedance picture or
stop its successor's Seedance provider job. If only dubbing fails, retain the
picture-ready source and retry audio without creating a new provider attempt. A
failed picture gets a new provider attempt; never rewrite the approved story
silently during generation.

## Stop conditions

Stop and return upstream when Storyboard and screenplay disagree, reference media
cannot represent the required visible cast, a narrator transition lacks a concrete
performance bridge, exact speech cannot fit naturally, the prompt would need to
invent story information, the eyeline axis or position-change exception is
ambiguous, close-up dominance would be lost, or a predecessor attempt has not
passed the direct picture review required for successor continuity.
