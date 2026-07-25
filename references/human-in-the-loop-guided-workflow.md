# Human-in-the-Loop Guided Workflow

## Interaction model

Treat the conversation as the director's control surface. The human describes
creative intent in ordinary language; the agent translates it into Story,
Screenplay, production-design, Storyboard, Segment Prompt, reference, continuity,
review, and postproduction changes internally.

Do not turn the collaboration into a form-filling exercise. Internal validation,
dependency repair, and artifact maintenance should remain quiet unless they
produce a blocker or require a real creative choice.

When reporting progress, use one compact pattern:

```text
当前结果：
下一步建议：
你可以修改：
请确认：
```

Before all first-pass Segment Prompts exist and the full Prompt/speech-rate gate
passes, pause only when:

1. target country is missing;
2. a material creative choice cannot safely be inferred; or
3. a destructive overwrite is about to occur.

The formal Segment human loop begins only after that full gate. From then on,
pause before each video attempt and after each completed attempt.

Do not require a separate approval for every internal document, validator, JSON
file, or department handoff.

## Workflow discipline

The declared production sequence is executable authority, not a user preference
that must be reconfirmed. When a requested downstream result is missing an upstream
artifact, create and validate the missing non-media prerequisites in sequence.
Never bypass screenplay, production-design, Storyboard, Prompt-materialization, or
their release gates.

Keep the task isolated to the current repository, its explicit `TASK_DIR`, and the
current repository's `assets/`. Never search another project, prior project copy,
sibling runtime, or Git recovery data for a creative artifact, even when the title
or story matches. Existing current-repository assets may be reused only under the
current task authority and user direction.

Do not ask the human to repeat or reconfirm a workflow rule or direction already
established in the conversation or this repository. Continue through deterministic
non-media prerequisites automatically. Pause only at the gates listed below or when
a genuinely material creative choice cannot be inferred safely.

## Natural-language direction

Accept directions such as:

> 第二个视频从小鹿从树后走出开始，开头淡化一点，所有角色都要在场。

Translate that request internally into the affected opening transition, Shot
action, staging, character-presence requirements, story-world continuity, references,
and Segment Prompt. Repair only affected downstream artifacts, validate them, and
return a revised compact next-step plan. Never ask the human to edit a JSON field,
hash, ledger, or internal artifact path.
Interpret “all characters remain present” as diegetic presence unless the user
explicitly requires simultaneous visibility. Preserve off-screen continuity and
the declared eyeline axis; do not widen into a full-cast composition. A visible
entrance may use only the shortest labeled `position-change exception:` before
returning to tight coverage.

The human may change story, dialogue, character appearance, performance, story-world
design, population, camera, lighting, sound, transition, duration, reference,
Segment order, or delivery at any point.

## Before every video attempt

Before each new Segment, regeneration, or retry, state only what the human needs
to direct it:

```text
生成前
要生成：第几个视频 / Segment
怎么开始：转场、起始画面和角色在场情况
这段发生什么：动作、对白、叙述方式和场景状态
怎么结束：落点和与下一段的衔接
生成成功后下一步：
你可以修改：
请确认是否生成这一个视频：
```

Mention any auxiliary generated continuity proxy if it causes another provider
call. Keep exact prompts, hashes, validation records, and provider payloads
internal unless the human asks to inspect them.

“Internal” does not mean “persist everything.” Virtual production keeps only the
authored Prompt before generation. It derives the resolved transport plan from the Storyboard
execution plan in memory, keeps one mutable submission record only while a provider
attempt is active, and reduces a successful Segment to `video.mp4`,
`last-frame.png`, and `production-record.json`. Do not create request/response/poll
sidecars, copied Prompts, artifacts manifests, generation state, or summary files.

Pause. One confirmation authorizes exactly one attempt for one not-yet-generated
Segment. It does not authorize a later Segment or a retry. “继续到结束” also does
not pre-authorize future video calls.

The execution command must name the confirmed Segment through
`--human-confirmed-segment SEGMENT_ID`. This is an ephemeral runtime assertion,
not a persisted approval record.

## After every video attempt

Inspect the complete video with sound, run the applicable technical and
audiovisual review, then report:

```text
生成后
已生成：
结果和检查：
与计划的差异：
下一步建议：
你可以选择：接受 / 修改后重做 / 原样重试 / 暂停
请确认下一步：
```

Pause even when review returns `NO_ISSUES`. Do not generate the successor, retry,
or enter final assembly until the human chooses the next action.

## No automatic retry

Never automatically retry a create failure, moderation failure, terminal provider
failure, missing output, review failure, or continuity failure. Explain the
problem briefly, propose the smallest repair or an unchanged retry, and ask for a
fresh confirmation.

## Minimal internal state

Retain only current creative authorities, reusable final assets, accepted Segment
media, compact resume records, and final deliverables. Use command output for
validation and the current conversation for human authority. Do not create
user-facing approval JSON, confirmation receipts, hash ledgers, review reports,
compatibility packets, visual-spec companions, location-continuity copies, or
extra checkpoints.

For a pending Segment, one exact Prompt is sufficient; Storyboard remains its plan.
For a successful image, keep the final image and its one reuse brief; do not keep
duplicate Prompt/request/response sidecars. Provider polling and diagnostic files
may remain only for an active or failed attempt when they are needed to resume or
diagnose it.

## Completion

After every accepted clip, propose the next clip or the final assembly plan. Render
final masters only after the human confirms that plan. Work is complete only when
the human accepts the verified deliverables or explicitly stops; `PASS`,
`NO_ISSUES`, `GENERATED`, and `FINAL_MASTER_READY` never replace human acceptance.
