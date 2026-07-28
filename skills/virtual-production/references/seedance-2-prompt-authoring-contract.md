# Seedance 2.0 Prompt Authoring Contract

## Purpose

Apply the supplied Seedance 2.0 prompt-optimizer principles while authoring, not
only after the Prompt exists. This contract governs every
`segment-NNN.md` written by `virtual-production`. The approved Storyboard remains
the sole creative authority.

## Authoring sequence

### 1. Resolve intent before writing

Select exactly one authored operation:

- `multimodal_reference`: create a clip from approved image/video references;
- `video_extension`: continue the approved predecessor;
- `text_to_video`: create an intentionally reference-free clip.

Classify the Segment's dynamics from its Storyboard Shots. Preserve detailed
performance for static/emotional beats and the full authored action for dynamic
beats. Do not invent a camera move or suppress authored movement.

The upstream Storyboard replaces heuristic user questioning. If a subject,
action, environment, light, camera, style, quality requirement, constraint,
reference role, or left/right mapping is missing or contradictory, stop and
return the issue upstream. Never guess or silently modify it.

### 2. Map provider assets before prose

Read the Storyboard Reference Plan in provider-token order.

- Keep each assigned `@ImageN` or `@VideoN` token stable.
- Declare it before Shot 1 as `@ImageN (readable subject)` or
  `@VideoN (readable subject)`.
- Give it one readable job and one forbidden-inheritance rule.
- Follow every later occurrence immediately with a noun in parentheses.
- Never expose an internal `asset-...` identifier.
- Never bind reference audio in this Arabic branch.
- Return long images, contact sheets, or nine-grid composites to production
  design for splitting into atomic approved references.
- If left/right, first/last-frame, or subject identity is ambiguous, stop
  upstream; do not infer the mapping.

### 3. Complete the eight-element self-check

Before drafting, confirm all eight elements have Storyboard authority:

1. precise subject;
2. detailed action and expression;
3. setting, environment, space, and blocking;
4. lighting, color, and emotional tone;
5. one dominant camera behavior per Shot;
6. exact approved visual style;
7. image-quality requirement;
8. exclusions and anti-distortion fallback.

The production doctrine adds visible-character economy, eyeline axis/screen
direction, close-up dominance, exact Arabic mouth performance, one explicit
Seedance audio mode, mandatory post-generation speech replacement when native
audio is enabled, and the landing/edit state.

### 4. Write the engineered Prompt

Use this exact Arabic order. All model-facing prose must be Arabic; Latin letters
are permitted only inside required `@ImageN` and `@VideoN` tokens:

```text
الإعداد العام وخريطة المراجع:
<operation, format, style, references, population, continuity, axis, framing,
audio ownership>

اللقطة 1: <حجم اللقطة العربي المطابق للوحة القصة>.
سلوك الكاميرا المهيمن: <عائلة واحدة>
مرجعية الانتقال والكاميرا من لوحة القصة: <الترجمة العربية الدقيقة>
الشخصية والفعل: <الفعل والتعبير الظاهران>
المكان والبيئة: <الفضاء والتموضع والنظرة>
المرتكزات الثابتة: <العناصر التي يجب الحفاظ عليها>
الإضاءة والنبرة: <الضوء واللون والجو>
الهبوط والتحرير: <الحالة النهائية ونقطة القطع>
<mouth performance, selected audio mode, reaction, landing>

...

الجودة والقيود:
<exact quality and anti-distortion directive plus project prohibitions>
```

Each Storyboard Shot is one time slice. Use natural event order and relative
pacing rather than provider-facing seconds. A Shot's dominant-camera line selects
exactly one family: locked/static, pan, tilt, dolly/push/pull,
track/truck/follow, pedestal, arc/orbit, crane/jib, or zoom. Cut and dissolve
instructions are edit transitions, not additional camera families.

Copy each Shot's authored Transition and Camera, Subject Action and Expression,
Space/Blocking/Gaze, Persistent Anchors, Lighting and Color, and Landing and Edit
authority into that Shot block without omission or semantic replacement. Add
model-readable connecting prose only when it does not change those facts.

For video extension, state that `@VideoN (readable predecessor)` extends smoothly
forward and define only the authored continuity. For first/last-frame control,
state the approved token's role in the global section. Do not introduce editing
instructions unsupported by the selected operation.

### 5. Close with the mandatory fallback

Include this exact directive:

```text
وضوح سينمائي عالي التفاصيل؛ ثبات هوية الشخصية ووجهها وملابسها وتشريحها؛ ملامح وجه واضحة؛ من دون قفزات في الوجه أو أطراف زائدة أو اختراق للأجسام أو قصّ أو تشوه أو شعارات أو علامات مائية.
```

Do not claim 4K when the verified provider parameter selects another resolution.
Also preserve all project exclusions: no duplicate or extra characters,
identity/style/costume drift, ambiguous eyelines, unauthorized widening,
captions, visible text, or music.

## Arabic audio ownership

Use only dialogue-replacement mode with `generate_audio=true`. The visible
speaker performs one audible disposable guide line while Seedance creates native
ambience/action sound; immediately afterward, virtual production removes every
generated character voice, preserves the original Seedance audio unchanged
outside the cut, hard-mutes the complete mixed Seedance track inside the cut, and
inserts exact
ElevenLabs Arabic. ElevenLabs generates dialogue only; it never generates
ambience, action sound, Foley, animal sounds, or music. Off-camera speech drives
no visible mouth. Music remains forbidden.

Write those instructions in Arabic, including the names `سيدانس` and
`إليفن لابز`. Do not leave an English instruction, heading, camera term,
character name, place name, style name, or prohibition in the submitted Prompt.

## Authoring completion

Run the complete virtual-production Prompt validation. Then hand the unchanged
Prompt to the department's separate internal audit. Do not revise it between
audit, human confirmation, and provider request construction.

The source optimizer's three user-facing modules map into this repository as
follows:

- **Optimized prompt** becomes the sole model-facing `segment-NNN.md`.
- **Optimization** becomes validator/audit failure output only; do not persist a
  second creative analysis file.
- **Relevant principles** live in this authoring contract and the audit contract;
  do not duplicate them per task.
