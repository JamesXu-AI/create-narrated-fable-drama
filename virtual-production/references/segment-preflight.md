# Segment preflight

Immediately before a provider call, verify the exact natural-language Prompt,
private Segment plan, in-memory execution-plan hash, Storyboard hash, shooting-plan fields,
predecessor attempt lock, model capability limits, media counts, duration, native
audio, watermark, last-frame values, and current private binding/catalog
compatibility. Prompt validation is limited to UTF-8 readability, non-empty text,
provider-token set/placement, one exact population lock, every ordered exact
Character Segment presence lock, and exact dialogue/speaker placement in the owning
Shot. Preflight never rewrites a Prompt or chooses another operation.

Recompute the Character Segment state machine across each complete Location state
chain. Every authorized independent performer requires a state row. A character
whose latest outgoing presence is not `absent` must remain in every later Segment
of that chain until an explicit `exit` or `reset_with_reason`; current incoming
presence must equal the latest outgoing presence. `must_remain_visible` requires
every internal Shot. Reject silent disappearance, unauthorized absence, or return
from absence without `re_enter`.

Also compare every private Character Segment state with the exact Storyboard row
and expose `required_visible_characters_by_shot` in the live observation hold.
Closed ensembles are included. A required visible character or roster must be
readable in the actual authored Shot even when its rule is
`must_remain_present`; reference-budget pressure cannot downgrade the obligation.

Also recompute direct extension depth from current private plans and require the
verified `maximum_direct_extension_hops_without_quality_reset` to be zero. Therefore
the first and every permitted extension is a reset point and requires the current
white-model contract hash, one
`white_model_predecessor_video` temporal input, a Prompt declaration that identifies
it as a white model, the Location master, and high-resolution identity/appearance
images for every declared role. A stale or incomplete reset blocks provider
submission.

Recompute the combined tail-reference/extension inheritance budget as well. Reject
two consecutive same-Scene predecessor-media handoffs. For a
`strong_coverage_reset`, require the direct predecessor observation lock and
semantic state source but require zero runtime predecessor-media bindings; current
Location and identity bindings remain mandatory.

For every `serial_after_predecessor_review` Segment, preflight also requires a live
exact-attempt observation argument. Before it is supplied, generation stops and
reports the predecessor video path, current `segment-NNN.md`, private plan,
authorized independent performers, current and predecessor Character Segment
states, the exact required-visible roster per Shot, and resolved
character/Location media bindings.
Virtual production directly checks those inputs against the actual predecessor,
adjusts and rematerializes the successor when needed, and asks
`seedance-video-review` to return `NO_ISSUES`. Only then may the active process pass:

```text
--observed-predecessor segment-NNN=segment-MMM__attempt-NNNN
```

The value must equal the attempt already locked into the in-memory execution plan. It is a
transient command argument, not an approval artifact; missing, wrong, or stale
values block the provider call. This check runs before white-model preprocessing.
