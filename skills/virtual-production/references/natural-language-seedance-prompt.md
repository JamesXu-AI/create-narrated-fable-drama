# Free-Form Seedance Prompt Guidance

`segment-NNN.md` is the exact model-facing instruction. It is plain natural
language, not JSON. Its only creative sources are the approved screenplay and
Storyboard.

## Required engineered order

All submitted prose is Arabic. Latin letters are forbidden except inside
`@ImageN` and `@VideoN` reference tokens.

1. Begin `الإعداد العام وخريطة المراجع:`. State the task operation, 16:9
   cinematic style, population, continuity, visible-character, eyeline-axis, and
   close-up-led constraints.
2. Declare each `@ImageN (readable subject)` and
   `@VideoN (readable subject)` token from the Storyboard Reference Plan, with
   one responsibility per token. Repeat a readable noun in parentheses after
   every later token use.
3. Write ordered `اللقطة N: <Arabic rendering of exact shot_size>.` beats. Each
   Shot states exactly one `سلوك الكاميرا المهيمن:`, `الشخصية والفعل:`,
   `المكان والبيئة:`, and `الإضاءة والنبرة:` field before its mouth,
   sound, reaction, and landing direction.
4. End `الجودة والقيود:` with the exact Arabic quality and anti-distortion
   directive from the Prompt Audit Contract.

Use event order, phrases such as “after his breath settles,” and relative pacing.
Do not place precise second ranges in the model-facing prompt. Run the independent
virtual-production internal audit after authoring and before human confirmation.

## Speech is performance, not a label

For every Storyboard speech cue:

- name the readable speaker;
- include the exact line once as `{exact words}`;
- repeat its delivery mode in natural language;
- say whose mouth moves and whose mouth stays closed;
- describe the listener's reaction during or immediately after the phrase;
- express the authored trigger or phrase/breath boundary;
- express the J-cut, L-cut, cutaway, eyeline, memory transition, or visual handoff;
- preserve the authored mouth timing and visual handoff while generating no
  character speech.

Examples of the required semantic precision:

```text
Grandfather is visible and audibly delivers a temporary Arabic guide directly to
his grandson, with natural mouth movement for immediate ElevenLabs replacement:
{هل تساءلت يومًا لماذا ظل المصباح الأصغر مضيئًا؟}
The grandson stops fidgeting and looks up before the final phrase lands.
Seedance generates native room tone, chair creak, and fire plus the disposable
guide speech. After generation, hard-mute the complete mixed Seedance track
inside the dialogue cut, preserve the original Seedance audio unchanged outside
the cut, and insert the exact Arabic line with the mapped
ElevenLabs voice. ElevenLabs generates dialogue only.
```

```text
On Grandfather's soft inhale, cut from his close-up into the moonlit fable world.
Grandfather is no longer visible. Preserve the off-camera storyteller cue for
temporary audible delivery and later ElevenLabs replacement:
{منذ زمن بعيد، كان ثعلب يحرس آخر شعلة.}
No mouth in the fable scene moves for this narration; the fox only reacts to the
wind. Seedance generates native forest ambience and wind plus disposable
off-camera guide speech. Remove that speech and insert the exact mapped
ElevenLabs narration immediately after generation.
```

```text
The fox now answers inside the embedded story and is the only character audibly
delivering a temporary guide for the exact line:
{إذن سأحملها عبر العاصفة.}
Grandfather's narration pauses completely; the owl listens with a closed beak.
Seedance generates native storm, leaves, footsteps, and disposable fox speech.
Remove every character voice by hard-muting the complete mixed Seedance track
inside the dialogue cut, preserve the original Seedance audio unchanged outside
the cut, and insert the
exact mapped ElevenLabs Arabic line.
```

Never introduce “a narrator” when the screenplay establishes a character such as
Grandfather as storyteller. Never bind a positive image or audio reference for a
character who must remain visually absent in that embedded Segment.

## Visual compilation

Before `Shot 1`, include these exact labels and copy the approved Segment
direction without weakening it:

```text
اقتصاد الشخصيات الظاهرة: <أقل عدد من الشخصيات الفاعلة الظاهرة والأدوار الحاضرة خارج القص>.
محور النظرات واتجاه الشاشة: <خط المحور والعلامات والجوانب واتجاهات النظر المتقابلة وجانب الكاميرا>.
تغطية تقودها اللقطات القريبة: تسود اللقطات شديدة القرب والقريبة والمتوسطة القريبة؛ ولا تُستخدم اللقطات الأوسع إلا لاستثناءات معلّمة لتغيير الموضع.
```

Keep the actual frame to one story-active subject or one speaker/listener pair
whenever the Storyboard permits. Do not add decorative bystanders or widen merely
to include every bound character reference. A positive reference supplies
identity; it does not require that subject to appear in every Shot.

Translate Storyboard Shot Size literally. Close coverage keeps the authored face,
eye line, hand, clue, or reaction dominant; it does not widen merely to show every
physically present character. Use off-screen sound, foreground edges, gaze, and
listener reactions to preserve space.

Begin every beat with the exact Arabic form
`اللقطة N: <Arabic rendering of Storyboard shot_size>.` Preserve
the declared axis through singles, OTS, reactions, and reverses. For
`medium_wide`, `wide`, or `extreme_wide`, repeat
`استثناء تغيير الموضع:` and show only the shortest readable
entrance/exit/crossing/approach/retreat/mark-transfer interval from start mark to
landing mark, then return directly to ECU/CU/MCU. Scenery, scale, atmosphere,
Scene/Segment openings, full-cast presence, continuity proof, and visual variety do
not justify widening.

Every provider-renderable visible role needs an approved identity or state image.
Temporal evidence owns recent action and position, not identity. A role marked
`remain_absent` receives no positive image or video binding.

Reject long images, contact sheets, and nine-grid composites as provider
references; route them to production design for atomic approved images.

## Dialogue-replacement notation

- exact Arabic guide performance whose generated voice will be replaced:
  `{spoken words}`
- generated on-screen text: `【text】`

This production forbids generated on-screen text; subtitles are added after
picture lock. A replacement Prompt must include the exact audited directive that
allows one guide performance and requires all generated character voices to be
removed. ElevenLabs is mixed into each Segment immediately using the detected
Seedance speech window, with any deviation from Storyboard timing recorded for
review.

## Final constraints

Forbid paraphrase, omission, repetition, added words, wrong speaker, wrong mouth
movement, any surviving Seedance dialogue/narration/whisper/singing,
music, captions, visible text, logos, watermarks, duplicate
people, clones, decorative bystanders, unauthorized full-cast composition,
ambiguous or reversed eyelines, unmotivated widening, anatomy errors,
identity/style/costume drift, unmotivated appearance or disappearance, and
discontinuous light, space, or props.
