# Dialogue Duration and Pacing Validation

Validate two different clocks: the production timeline must be exact; Seedance timeline wording is a strong sequencing cue, not a promise of frame-exact execution.

## Contents

- [Two-clock rule](#two-clock-rule)
- [Arithmetic contract](#arithmetic-contract)
- [Dialogue estimates](#dialogue-estimates)
- [Playable beat formula](#playable-beat-formula)
- [Performance allowances](#performance-allowances)
- [Camera and action allowances](#camera-and-action-allowances)
- [Segment feasibility](#segment-feasibility)
- [Long-form allocation](#long-form-allocation)
- [Validation ledger](#validation-ledger)
- [Common false passes](#common-false-passes)

## Two-clock rule

Keep these clocks separate:

1. **Production/edit clock — exact:** each generation segment's total duration, internal shot/beat allocation, dialogue estimate, transitions, titles, and final runtime must reconcile numerically.
2. **Generation prompt clock — directive:** follow current Seedance guidance by using ordered `Shot 1 / Shot 2 / Shot 3` and causal transition triggers as the default. Approximate ranges may remain in planning metadata, but do not depend on the model hitting sub-second cuts.

Write exact times in the planning ledger and `target_duration`. In the final prompt, state shot order and causality in words; include a coarse duration emphasis only when it materially clarifies pacing and cannot be expressed through action order. After generation, verify actual line timing and recut or regenerate; never label planned timing as observed.

## Arithmetic contract

Calculate with half-open ranges:

```text
[0.0, 2.4) + [2.4, 5.1) + [5.1, 8.0) = 8.0 seconds
```

Store them as `0.0–2.4s`, `2.4–5.1s`, and `5.1–8.0s` in the production ledger. Require:

- First start = `0.0s`.
- Every next start = prior end.
- Every duration > `0`.
- No gap and no overlap unless intentional dialogue overlap is listed separately from picture ranges.
- Final end = declared segment duration.
- Segment totals plus explicitly external transitions, titles, and holds = project runtime.

Avoid planning patterns such as `0–3s`, `4–8s`, `9–12s`; they leave one-second holes. Use one decimal place by default and expose every mismatch. Do not copy this exact ledger into the model prompt by default; compile it into ordered shots and transition triggers.

## Dialogue estimates

Count spoken content, not speaker labels or punctuation. Treat rates as planning heuristics, then read the line aloud mentally in the specified performance.

### Chinese

- Deliberate, intimate, elderly, exhausted, or emotional: about `2.5–3.5 Chinese characters/second`.
- Normal clear dramatic dialogue: about `3.5–4.5 characters/second`.
- Urgent but intelligible: about `4.5–5.5 characters/second`; use only when the character and scene support it.

### English

- Deliberate: about `100–130 words/minute`.
- Normal screen dialogue: about `130–170 words/minute`.
- Urgent but intelligible: about `170–190 words/minute`.

Quoted hesitations, repeated words, laughs, sobs, and unfinished starts consume time. An ellipsis does not have a fixed duration; assign its intended pause explicitly.

## Playable beat formula

Use:

```text
spoken_line_time = words_or_characters / chosen_delivery_rate + internal_pauses

minimum_dialogue_beat =
pre-line recognition/breath
+ max(spoken_line_time, compatible concurrent body action, compatible camera movement)
+ sequential physical transitions
+ listener reaction/after-beat
+ edit handle when needed
```

Do not add elements that genuinely occur together. Do add actions that must occur in order. A character may turn a cup slowly while speaking; the character cannot discover a message, read it, understand it, decide, and answer before those steps occur.

## Performance allowances

Use these starting ranges, then adjust to the acting style:

| Event | Planning allowance |
|---|---:|
| Simple breath before a line | `0.2–0.6s` |
| Turn-taking between clean lines | `0.3–0.8s` |
| Glance or micro-reaction | `0.5–1.2s` |
| Readable listener reaction | `0.8–1.8s` |
| Shock/recognition before speech | `1.0–2.5s` |
| Emotional decision or recovery | `1.5–4.0s` |
| Controlled laugh/sob before words | `0.8–2.5s` |
| Mouth closure and stable post-line hold | `0.2–0.6s` |
| Clean editorial handle | `0.3–0.8s` |

Do not append all allowances to every line. Routine exchanges share rhythm; decisive lines receive the screen time needed for cause, delivery, and effect.

## Camera and action allowances

| Beat | Typical planning range | Notes |
|---|---:|---|
| Establishing geography | `1.0–3.0s` | Longer for complex entrances or groups |
| Stable dialogue single | line duration + reaction | Keep mouth readable |
| Simple sit, stand, pickup, or turn | `1.2–2.5s` | Add settling time if the next shot must match |
| Prop handoff | `1.5–3.0s` | Show contact, transfer, and new owner |
| Small-room approach | `2.0–4.0s` | Depends on distance and obstruction |
| Readable push, pull, or lateral move | `2.0–5.0s` | Shorter motion may read as a jolt |
| Tight neutral-axis re-establishing Shot | `1.0–2.5s` | Restore A/B screen sides and opposed looks without widening unless a position change is also occurring |
| Short edge-to-mark entrance or exit | `1.5–3.5s` | Include boundary contact, traversal, and weight settle |
| Progressive reveal/concealment | `1.0–3.0s` | Depends on required partial states and occluder |
| Complex emotional turn plus line | `3.0–7.0s+` | Split when reaction is the story |

Within one beat, default to one main narrative event, one primary body action, one camera idea, and one audio focus. Split dialogue from large prop action, crowd movement, large camera travel, or a complex reveal when reliability matters.

## Segment feasibility

For each generation segment:

- Keep the declared output duration within the current Seedance limit documented in [Seedance planning constraints](seedance-planning-contract.md).
- Treat the segment as one generated video that may contain several internal shots. Pack consecutive shots when one duration, operation/reference package, identity/continuity system, and dialogue/audio contract can govern them.
- Reserve any extension bridge, incoming orientation, and outgoing handle inside the target duration.
- Reserve required audience-preparation cue, empty-frame hold, first-visible beat, boundary contact, progressive entrance/exit/reveal, arrival settle, and dialogue/action gate inside the target duration.
- Do not begin or end on an unfinished line.
- Do not require more internal cuts, speaking faces, or major position changes than the segment can stage clearly; judge combined load rather than applying an invented fixed shot count.
- Prefer one sustained dialogue setup or a small, motivated coverage progression over rapid round-robin cutting.
- Split a segment when the performable minimum, operation/reference conflict, or combined complexity materially exceeds its target, even if the numeric time ranges sum correctly. Do not split merely because the camera cuts, reverses, inserts, or changes shot size.

If a scene needs thirty seconds, it may be one scene but several multi-shot generation segments. Allocate by dramatic and operational punctuation, not by individual camera shots or equal lengths.

## Long-form allocation

Allocate time by dramatic weight:

- Give the opening enough time to establish who, where, and the immediate pressure.
- Compress repeated facts, neutral travel, and greetings without a tactic.
- Give questions, refusals, reveals, decisions, and listener reactions room to land.
- Let silence remain when it changes the relationship.
- Use extension bridge time only when continuity needs it; do not repeat dead air at every segment.
- Include titles, recaps, transitions, cutaways, and end holds in the episode total.

Avoid forcing every segment to the maximum platform duration. A shorter complete beat is better than a padded clip that weakens rhythm.

## Validation ledger

Create a ledger like:

| Seg | Target | Picture ranges | Line estimate | Pre/post performance | Action/camera | Performable min | Verdict | Repair |
|---|---:|---:|---:|---:|---:|---:|---|---|
| S01-A | 9.0s | 2.0+4.8+2.2 | 3.1s | 1.4s | 7.6s concurrent | 8.4s | pass | — |

Create a separate line ledger:

| Line | Speaker | Text count | Rate | Spoken time | Pauses | Reaction | Allocated | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|

Mark `BLOCKER` when arithmetic fails, a line crosses an independent segment boundary, or the performable minimum exceeds the target. State the smallest viable repair: trim text, move a reaction, simplify blocking, change coverage, split the segment, or change duration.

## Common false passes

- Time ranges total correctly, but the speaker must inhale, cross the room, speak, and hand off a prop sequentially.
- A line fits only at the maximum urgent rate despite being written as intimate or exhausted.
- The speaker's mouth is covered or off-axis for most of a lip-sync-critical line.
- No time remains for the listener to register the decisive word.
- A one-second extension bridge is added without subtracting it from the new action budget.
- The ranges fit only because an entrance begins with the subject already visible, skips the partial-entry state, or starts dialogue before arrival and weight settle.
- The entrant appears at `0.0s` only because no time was allocated for the authored cue, first-visible gate, or witness reaction.
- A sentence is divided across two independent generations.
- Every scene gets equal time despite different dramatic functions.
- Exact production ranges are copied into the prompt as if Seedance guarantees each internal cut at that time, instead of using ordered shots and causal triggers.
- Every internal shot is split into a new generated video even though the combined multi-shot sequence fits one compatible segment.
- The episode runtime ignores titles, recaps, transitions, or final holds.
