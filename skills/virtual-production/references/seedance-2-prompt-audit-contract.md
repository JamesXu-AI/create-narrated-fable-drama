# Seedance Prompt Audit Contract

## Purpose

Independently verify that `virtual-production` followed the generation-time
[Seedance 2.0 Prompt Authoring Contract](seedance-2-prompt-authoring-contract.md).
The approved Storyboard supplies facts; the Segment Prompt only compiles them;
the department's separate internal gate decides whether that unchanged Prompt is
safe to show for human confirmation and submit to Seedance.

## Required order

```text
الإعداد العام وخريطة المراجع:
اللقطة 1: <حجم اللقطة العربي المطابق للوحة القصة>.
...
اللقطة N: <حجم اللقطة العربي المطابق للوحة القصة>.
الجودة والقيود:
```

The global section locks operation, approved style, identities, environment,
continuity, visible-character economy, eyeline axis, framing doctrine, and audio
ownership. Each Shot is one time slice in authored event order; model-facing
second ranges are forbidden.

Each Shot must state these labels exactly once:

```text
سلوك الكاميرا المهيمن:
الشخصية والفعل:
المكان والبيئة:
الإضاءة والنبرة:
```

The audit also requires the exact Storyboard camera, action/expression,
space/blocking/gaze, persistent-anchor, lighting/color, and landing/edit
authority inside its owning Shot block. A well-formed paraphrase that changes or
omits authority still fails.

## Eight core elements

| Element | Required authority |
| --- | --- |
| Precise subject | Readable reference map and visible-character direction |
| Action details | Storyboard Subject Action and Expression |
| Setting/environment | Location state, anchors, space, blocking, and gaze |
| Lighting/tone | Storyboard Lighting and Color |
| Camera | One dominant camera family in each Shot |
| Visual style | Exact approved project Visual Style |
| Image quality | Mandatory final quality directive |
| Constraints | Anti-distortion fallback plus project prohibitions |

Missing creative information is not an invitation to improvise. Fail and route
the issue to the owning upstream department.

## Reference mapping

- Use only the Storyboard tokens `@ImageN` and `@VideoN`; reference audio is
  forbidden in this Arabic branch.
- Declare every token before Shot 1 as
  `@ImageN (readable subject)` or `@VideoN (readable subject)`.
- Follow every later token occurrence immediately with a readable noun in
  parentheses, such as `@Image1 (Grandfather)`.
- Never expose an internal `asset-...` identifier to Seedance.
- Give every reference one declared job and preserve its forbidden-inheritance
  rule.
- Long images, contact sheets, and nine-grid composites are not atomic provider
  references. Return them to production design for splitting and approval.

## Camera gate

Every Shot declares exactly one dominant family: locked/static, pan, tilt,
dolly/push/pull, track/truck/follow, pedestal, arc/orbit, crane/jib, or zoom.
Cuts and dissolves are edit transitions, not simultaneous camera families.
Reject a Shot whose dominant-camera line names zero, two, or more families.

## Quality fallback

The final section must include this exact directive:

```text
وضوح سينمائي عالي التفاصيل؛ ثبات هوية الشخصية ووجهها وملابسها وتشريحها؛ ملامح وجه واضحة؛ من دون قفزات في الوجه أو أطراف زائدة أو اختراق للأجسام أو قصّ أو تشوه أو شعارات أو علامات مائية.
```

Do not claim a resolution such as 4K when the verified provider parameter selects
another resolution.

## Arabic audio ownership and replacement

The complete Prompt prose must be Arabic and contain no Latin letters except
inside required `@ImageN`/`@VideoN` tokens. It must use the sole audited
dialogue-replacement mode, include the exact replacement directive, request
native ambience/action sound and one guide performance, and state that every
generated character voice will be removed and replaced by exact ElevenLabs
Arabic before complete audiovisual review. The immutable provider picture remains
eligible for its separate immediate picture review while that audio work runs.
Music remains forbidden.

Every dialogue cue is an Arabic-only gate input, not generic target-language
text. It must contain Arabic script, contain no Latin letters, and appear exactly
once inside literal braces. An English line, bilingual line, transliteration, or
legacy English validation result fails the audit.

## PASS record

`seedance-prompt-internal-audit/v3` records:

- exact Prompt SHA-256;
- source Storyboard SHA-256;
- `language=Arabic`, `language_code=ar`, and each Arabic line's SHA-256;
- generation-time authoring and final-audit ruleset component hashes plus their
  combined SHA-256;
- each hard-check result;
- human-confirmation and provider-submission readiness.

Changing the Prompt, Storyboard, generation-time authoring contract, or this
audit contract makes the record stale. A stale record blocks preflight and
generation even if a human previously confirmed an older Prompt.
