# Developer Guide

**English** · [中文](DEVELOPER.md)

This document is for developers who need to set up the environment themselves,
run scripts, or do advanced customization.

If you only want to turn a story into a finished master, **you don't need to read
this document** — see the repository root [`README.en.md`](../README.en.md): you
just write the story, name the target country, and confirm clip by clip; all the
commands, parameters, and configuration below are executed automatically by the
project.

## Requirements

- Python 3.11 or higher;
- When running media review and finishing, `ffmpeg` and `ffprobe` must be on `PATH`;
- The FFmpeg used to burn in subtitles must support the `movie` and `overlay`
  filters plus H.264 encoding;
- `python3 -m pip install -e .` installs Pillow for subtitle rendering. Arabic
  shaping must have Pillow RAQM available, so the host also needs the FriBiDi
  runtime library;
- Subtitle rendering uses the repository-bundled, SHA-256-pinned OFL Noto Sans
  Arabic font and does not depend on Tahoma, `fontconfig`, or `fc-match`;
- Only the image, sound, and video generation stages require remote service
  configuration;
- Uploading local reference media or persisting results to TOS requires the
  official TOS Python package.

We recommend creating an isolated environment at the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

Verify Arabic shaping after installation:

```bash
python3 -c "from PIL import features; assert features.check_feature('raqm')"
```

If the check fails, install the FriBiDi runtime library for the host and reinstall
an official Pillow wheel. A source build of Pillow must explicitly enable RAQM.
Subtitle rendering never falls back to unshaped text or a system font.

When you need TOS:

```bash
python3 -m pip install 'tos>=2.9,<3'
```

First confirm the repository structure and shared package are usable:

```bash
narrated-fable-drama validate-repository
```

You can also run it directly:

```bash
python3 scripts/validate_repository.py
```

## Creating a Task

Task directories live under `workspace/tasks/`. Put only a single UTF-8, non-empty
`story.md` at the root; do not create task forms, narration JSON, or other
creative metadata.

```text
workspace/tasks/my-fable/
└── story.md
```

## Internal Technical Pipeline Architecture

The diagram below shows the end-to-end technical data flow: which department owns
each stage, the artifact each stage produces, the four full gates and per-clip
picture-track and completed-audiovisual reviews, and where explicit human
authorization is required. Solid
arrows are the forward pipeline; dashed arrows are gate/review feedback that blocks
downstream work until it passes.

```mermaid
flowchart TD
    story["story.md<br/>(creative authority)"]

    subgraph SW["screenplay-writer"]
        screenplay["screenplay.md"]
    end
    subgraph PD["direct-production-design"]
        design["production-design-plan.json<br/>+ workspace/assets/assets.json"]
    end
    subgraph PC["previsualize-cinematography"]
        storyboard["storyboard.md"]
    end
    subgraph VP["virtual-production"]
        prompt["segment-NNN.md prompts"]
        guide["Seedance picture + native audio + disposable guide speech"]
        picture["PICTURE_GENERATED<br/>seedance-source.mp4 · last-frame.png"]
        audio["Immediate audio track<br/>remove guide speech · preserve native non-dialogue sound<br/>insert only ElevenLabs Arabic dialogue"]
        clip["generation-segments/segment-NNN/<br/>Seedance-native sound + ElevenLabs dialogue<br/>video.mp4 · last-frame.png · production-record.json"]
    end
    subgraph FP["finish-postproduction"]
        repair["llm-repair-plan.json"]
        master["final-clean-master.mp4<br/>final-captioned-master.mp4<br/>subtitles + delivery-manifest.json"]
    end

    gate1{"Gate 1<br/>Screenplay + scope"}
    gate2{"Gate 2<br/>Storyboard"}
    gate3{"Gate 3<br/>Full prompt set"}
    gate4{"Gate 4<br/>Independent prompt audit"}
    pictureReview{"Exact-attempt picture review<br/>NO_ISSUES releases predecessor evidence"}
    avReview{"Completed audiovisual review<br/>(video-review)"}
    human(["Fresh human authorization<br/>for each Seedance attempt"])
    decision(["Current-Segment decision<br/>accept · revise · retry · pause"])

    story --> screenplay
    screenplay --> gate1
    gate1 -. blocks .-> screenplay
    gate1 --> design
    design --> storyboard
    storyboard --> gate2
    gate2 -. blocks .-> storyboard
    gate2 --> prompt
    prompt --> gate3
    gate3 -. blocks .-> prompt
    gate3 --> gate4
    gate4 -. blocks .-> prompt
    gate4 --> human
    human --> guide
    guide --> picture
    picture --> pictureReview
    picture --> audio
    pictureReview -. reviewed successor + fresh confirmation .-> human
    audio --> clip
    clip --> avReview
    avReview --> decision
    decision -. picture retry needs fresh confirmation .-> human
    decision --> repair
    repair --> master
```

The forward data flow is also captured textually by the authority chain in
[Creative Authority and Runtime Data](#creative-authority-and-runtime-data); this
diagram adds the gate/review/authorization control flow around it.

## Exact Behavior and Commands per Stage

### Stage 1: Story Intake

Only `story.md` is allowed at the task root as the creative authority. The story
can be full text or come from the current conversation. The project preserves the
original story's premise, character relationships, causal turns, climax,
consequences, and ending; unless the user explicitly authorizes a rewrite, it only
improves performance, pacing, clarity, and shootability.

### Stage 2: Screenplay

Codex writes it according to the screenplay contract:

```text
TASK_DIR/screenplay-writer/screenplay.md
```

The screenplay must record the target country, fixed target language `Arabic`,
visual style, resolution, `16:9`, estimated duration, and the
`elevenlabs_dubbed` audio source.
Every line contains:

```text
L-NNN; speaker=<entity>; mode=<delivery-mode>;
gate=<visible/audible trigger>;
transition=<breath/reaction/J-cut/L-cut/action/silence handoff>;
delivery=<performance>; text="<exact target-language words>"
```

Allowed delivery modes:

```text
on_camera_dialogue
on_camera_storytelling
off_camera_storytelling
external_voiceover
embedded_character_dialogue
```

The validation commands do not write the screenplay for Codex; both `build` and
`check` read and validate the current `screenplay.md`:

```bash
python3 skills/screenplay-writer/scripts/build_screenplay.py build \
  --task-dir TASK_DIR
python3 skills/screenplay-writer/scripts/build_screenplay.py check \
  --task-dir TASK_DIR
python3 skills/screenplay-writer/scripts/character_performance_map.py \
  role-asset-scope --task-dir TASK_DIR
```

Once the screenplay is finished, it must pass the first full speech-rate gate and
the character/asset scope gate.

### Stage 3: Production Design

Production design writes first:

```text
TASK_DIR/direct-production-design/production-design-plan.json
```

Shared assets all live at the repository root:

```text
workspace/assets/assets.json
workspace/assets/characters/
workspace/assets/role-groups/
workspace/assets/locations/
workspace/assets/props/
workspace/assets/costumes/
```

Every `Kind=individual` character has its own identity image; only
`Kind=anonymous_ensemble` uses a group image. Only speaking individual characters
get a voice reference; silent characters still keep a distinct visual identity but
no voice is created. When a character doubles as the narrator, keep only one
character identity and one voice — do not create an extra "narrator character."

Before any Seedream call, first inspect semantic reuse and unregistered existing
files:

```bash
python3 skills/direct-production-design/scripts/build_initial_production_design.py \
  --task-dir TASK_DIR --inspect-semantic-reuse
```

Run the build after confirming reuse, regenerating, or accepting new images. The
following parameters can be reused:

```bash
python3 skills/direct-production-design/scripts/build_initial_production_design.py \
  --task-dir TASK_DIR --max-workers 4 \
  --codex-reuse-asset TARGET_ASSET_ID=SOURCE_ASSET_ID \
  --codex-regenerate-visual-asset TARGET_ASSET_ID \
  --codex-accept-generated-visual-asset ASSET_ID=SOURCE_URI
```

Finally validate:

```bash
python3 skills/direct-production-design/scripts/validate_production_design.py \
  --task-dir TASK_DIR
```

When an existing media path is not in `assets.json`, the flow stops and requires
you to restore its semantics and persistent URI; never overwrite an existing file
on disk just because an "asset ID cannot be found."

### Stage 4: Storyboard

Codex orchestrates all upstream information into the single:

```text
TASK_DIR/previsualize-cinematography/storyboard.md
```

The storyboard is responsible for the final performance, cinematography, lighting,
editing, ElevenLabs dubbing windows, inclusion/omission of reference images,
Generation Segment division, and inter-segment continuity. It must preserve, line
by line, the screenplay's exact text, speaker, delivery mode, mouth state,
listener reactions, and audio/picture handoffs.

Validate:

```bash
python3 skills/previsualize-cinematography/scripts/validate_storyboard.py \
  --task-dir TASK_DIR
```

The second full gate requires every line to be speakable naturally within its
actual Segment local window, and checks few-character composition, the eyeline
axis, close-up dominance, and all position-change exceptions.

### Stage 5: Segment Prompt

Each storyboard Generation Segment is compiled into one complete natural-language
prompt that Seedance actually sees:

```text
TASK_DIR/.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

The prompt must be self-contained with all shot order, action, performance, exact
lines, mouth state, references, exclusions, entry state, and end state. It must
state the sole audio policy: Seedance generates native ambience/action audio and
audible temporary character speech for mouth guidance; post-production then
removes every character voice and replaces it with exact ElevenLabs Arabic.
Creative meaning must not be shifted into accompanying JSON.

You must finish all first-version prompts before running the full validation
without the `--segments` parameter:

```bash
python3 skills/virtual-production/scripts/validate_segment_scripts.py validate \
  --task-dir TASK_DIR
```

Only when the output satisfies both:

```text
first_full_prompt_gate=PASS
speech_rate_gate.status=PASS
```

Then run the independent internal Prompt audit:

```bash
.venv/bin/python \
  skills/virtual-production/scripts/audit_segment_prompts.py \
  --task-dir TASK_DIR --all
```

It checks that the complete model Prompt is Arabic except for required
`@ImageN/@VideoN` tokens, plus the three-part structure, eight core elements,
readable reference mappings, one dominant camera family per Shot, quality and
anti-distortion fallback, Storyboard authority, and Arabic audio ownership. It
writes one current `seedance-prompt-internal-audit/v3` PASS record per Segment. Any Prompt,
Storyboard, reference, or ruleset change requires re-audit. Per-Segment video
generation is allowed only after both full validation and independent audit pass.

### Stage 6: Per-Segment Generation and Review

Preflight the current segment before generating:

```bash
python3 skills/virtual-production/scripts/preflight_segment.py \
  --task-dir TASK_DIR \
  --segment-script TASK_DIR/.pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

After getting one explicit confirmation for this segment in the current
conversation, the generation command must provide both the target segment and the
ephemeral human-confirmation assertion:

```bash
python3 skills/virtual-production/scripts/generate_segment_videos.py \
  --task-dir TASK_DIR \
  --segments segment-NNN \
  --human-confirmed-segment segment-NNN
```

If the current segment depends on the previous one, you may pass
`--observed-predecessor SEGMENT_ID=PROVIDER_ATTEMPT_ID` as required by preflight
only after direct review of the previous Segment's exact provider picture returns
`NO_ISSUES` and any necessary continuity fixes are reflected in the successor.
The predecessor's audio does not need to be complete. Picture `NO_ISSUES` releases
only that exact predecessor attempt; every successor Seedance submission still
needs its own fresh human confirmation.

When the provider succeeds, virtual production first publishes the immutable
`seedance-source.mp4`, last frame, and a `PICTURE_GENERATED` record. It immediately
starts two separate tracks. The picture track reviews story action, identity,
composition, continuity, last-frame usability, and the visual seam; after
`NO_ISSUES`, another Segment process may submit the separately confirmed
successor while the current audio track continues.

The audio track starts immediately and may not be deferred or batched. It detects
all character speech, cuts the speech intervals with bounded edge padding,
hard-mutes the complete Seedance mix inside the cuts, preserves Seedance-native
ambience and action sound unchanged outside them, and inserts exact Arabic with
mapped ElevenLabs voices against the detected mouth timing. ElevenLabs generates
Arabic dialogue only; it must never generate ambience, action sound, Foley,
animal sounds, music, room tone, or any other non-dialogue audio. The mix does not
retime picture frames. Only after the audio and voice-identity gates pass may the
current Segment become `GENERATED` and enter complete audiovisual review.

Successful current media lives at:

```text
TASK_DIR/.pending/virtual-production/generation-segments/segment-NNN/
├── video.mp4
├── last-frame.png
└── production-record.json
```

After the audio track completes, watch the full video at normal speed with sound
and check it item by item against the audiovisual checklist listed under the
README "Core Features · End-to-End Automatic QC & Correction." Even if this
complete review returns `NO_ISSUES`, the current Segment still waits for the user
to decide accept, redo with changes, retry as-is, or pause. An audio-only failure
blocks current-Segment acceptance and postproduction, but does not invalidate its
reviewed picture or stop an already authorized successor Seedance job.

### Stage 7: Finishing and Delivery

Once every current Segment has an accepted `video.mp4` and a matching
`production-record.json`, and the user has confirmed the assembly plan, first
generate real media evidence:

```bash
python3 skills/finish-postproduction/scripts/inspect_finish_media.py \
  --task-dir TASK_DIR
```

Codex must review the picture and sound evidence for 3 seconds on each side of
adjacent segment boundaries, then write:

```text
TASK_DIR/.pending/finish-postproduction/llm-repair-plan.json
```

Validate the repair plan:

```bash
python3 skills/finish-postproduction/scripts/validate_repair_plan.py \
  --task-dir TASK_DIR \
  --evidence-manifest \
    TASK_DIR/.pending/finish-postproduction/llm-evidence/evidence-manifest.json \
  --repair-plan TASK_DIR/.pending/finish-postproduction/llm-repair-plan.json
```

When there are uncertain cut points, dissolves, colors, or sound handoffs, first
render short candidate clips and inspect them manually; do not let the script
decide creative repairs automatically. Finally execute:

```bash
python3 skills/finish-postproduction/scripts/finish_postproduction.py \
  --task-dir TASK_DIR \
  --evidence-manifest \
    TASK_DIR/.pending/finish-postproduction/llm-evidence/evidence-manifest.json \
  --repair-plan TASK_DIR/.pending/finish-postproduction/llm-repair-plan.json
```

Subtitle text comes directly from the Storyboard Ordered Shots; ASR is not the
text authority. The clean and captioned masters must have equal duration and
preserve synchronized ElevenLabs Arabic dialogue.

## The Seven Production Departments

Each department only modifies the artifacts it owns:

| Department | Input | Owned outputs and responsibilities |
| --- | --- | --- |
| `screenplay-writer` | `story.md`, country/style/resolution from the conversation | The single `screenplay.md`; story adaptation, exact lines, delivery mode, performance, state changes, narration switches |
| `direct-production-design` | Story, validated screenplay, shared asset library | `production-design-plan.json`; characters, voices, wardrobe, props, locations, and the shared asset catalog |
| `previsualize-cinematography` | Screenplay, production design, asset catalog | The single `storyboard.md`; performance, cinematography, lighting, editing, Segment division, reference binding, and continuity |
| `virtual-production` | Validated storyboard | Author and audit each Prompt; submit Seedance picture plus native audio; hard-mute the mixed Seedance track in dialogue intervals, preserve it unchanged elsewhere, and mix only ElevenLabs Arabic dialogue; run the internal audio gates |
| `video-review` | Authoritative documents or complete audio/picture clips | Independent review results; returns `NO_ISSUES` or minimal fixes routed to the responsible department |
| `finish-postproduction` | All accepted Segments and real media evidence | Repair decisions, assembly, subtitles, clean/captioned masters, and the delivery manifest |

The full rules live respectively in:

```text
skills/screenplay-writer/SKILL.md
skills/direct-production-design/SKILL.md
skills/previsualize-cinematography/SKILL.md
skills/virtual-production/SKILL.md
skills/video-review/SKILL.md
skills/finish-postproduction/SKILL.md
```

## The Four Full Gates

1. **Screenplay gate:** checks the full screenplay, character scope, and each
   line's owning Shot duration.
2. **Storyboard gate:** checks the full storyboard, local speaking windows,
   reference binding, few characters, the eyeline axis, close-up dominance, and
   position-change exceptions.
3. **Prompt gate:** after all first-version prompts are finished, checks the
   complete set at once — per-shot framing, references, exact lines, exclusions,
   and local speaking windows.
4. **Independent prompt-audit gate:** checks the exact compiled Prompt's
   three-part structure, eight core elements, readable reference mapping, one
   dominant camera family per Shot, quality/anti-distortion fallback, Storyboard
   authority, and Arabic audio ownership. Prompt, Storyboard, reference, or
   ruleset changes invalidate the prior PASS.

Unified speech-rate hard limits:

- CJK text: no more than 4.0 characters per second;
- Non-CJK text: no more than 2.6 words per second;
- Each line also needs a 0.25-second start/end margin.

Any gate failure blocks downstream work and must not be skipped as a warning.

## Creative Authority and Runtime Data

Creative facts exist only in:

```text
story.md
-> screenplay-writer/screenplay.md
-> previsualize-cinematography/storyboard.md
-> .pending/virtual-production/seedance-segment-scripts/segment-NNN.md
```

The allowed JSON only records:

- Asset planning and shared asset lookup;
- The current attempt facts of provider requests;
- Generated media records;
- Technical QC and repair execution parameters;
- The final delivery manifest.

Do not create a second screenplay, storyboard JSON, narration plan, voice plan,
translation tracker, prompt manifest, human-confirmation receipt, or private
creative ledger. User accept/redo decisions stay in the current conversation and
are not written as approval JSON.

## Directory Structure

```text
create-narrated-fable-drama/
├── AGENTS.md                         # Efficient locating and search rules
├── README.md                         # User-facing usage guide
├── docs/DEVELOPER.md                 # Developer/advanced technical guide (this document)
├── SKILL.md                          # Overall orchestration, global constraints, completion conditions
├── agents/                           # Interface metadata for the root Skill
├── references/                       # Project-wide production and human-collaboration standards
├── scripts/
│   └── validate_repository.py        # Repository structure and shared package compile checks
├── src/narrated_fable_drama/
│   ├── cli.py                        # Project-level CLI
│   ├── core/                         # Paths, context, JSON, speech rate, and common validation
│   ├── contracts/                    # Screenplay, asset, Storyboard, and Segment contracts
│   ├── media/                        # Unified FFmpeg/FFprobe boundary
│   └── providers/                    # Seedream, Seedance, SeedAudio, ElevenLabs boundary
├── skills/
│   ├── screenplay-writer/
│   ├── direct-production-design/
│   ├── previsualize-cinematography/
│   ├── virtual-production/
│   ├── video-review/
│   └── finish-postproduction/
├── tests/unit/                       # Unit tests
└── workspace/
    ├── assets/                       # Cross-task shared, single asset library
    └── tasks/                        # Individual production tasks
```

A complete task may finally contain:

```text
TASK_DIR/
├── story.md
├── screenplay-writer/
│   └── screenplay.md
├── direct-production-design/
│   └── production-design-plan.json
├── previsualize-cinematography/
│   └── storyboard.md
├── .pending/
│   ├── virtual-production/
│   │   ├── seedance-segment-scripts/
│   │   └── generation-segments/
│   └── finish-postproduction/
│       ├── llm-evidence/
│       └── llm-repair-plan.json
└── finish-postproduction/
    ├── final-clean-master.mp4
    ├── final-captioned-master.mp4
    ├── final-delivery-manifest.json
    └── subtitles/
        ├── subtitle-cues.json
        ├── master.srt
        └── master.vtt
```

## Provider Configuration

Providers read configuration only from the host process environment; they do not
auto-load a repository `.env`. Do not commit secrets to the repository.

| Capability | Required environment variables |
| --- | --- |
| Seedream images | `ARK_BASE_URL`, `SEEDREAM_API_KEY`, `SEEDREAM_MODEL` |
| Seedance video creation | `ARK_BASE_URL`, `SEEDANCE_API_KEY`, `SEEDANCE_MODEL` |
| Seedance query/cancel | `ARK_BASE_URL`, `SEEDANCE_API_KEY` |
| SeedAudio voice | `SEEDAUDIO_API`, `SEEDAUDIO_API_KEY`, `SEEDAUDIO_MODEL` |
| ElevenLabs Arabic dubbing | `ELEVENLABS_API_KEY`, `ELEVENLABS_MODEL_ID`, `ELEVENLABS_VOICE_MAP` |
| TOS persistence | `STORAGE_TOS_REGION`, `STORAGE_TOS_ENDPOINT`, `STORAGE_TOS_BUCKET`, `STORAGE_TOS_ACCESS_KEY_ID`, `STORAGE_TOS_SECRET_ACCESS_KEY`, `STORAGE_TOS_KEY_PREFIX` |

`ARK_BASE_URL` and `SEEDAUDIO_API` must be HTTPS. The current Seedream adapter
only accepts the fixed model ID declared in code; using any other value fails
immediately.

`ELEVENLABS_VOICE_MAP` is a JSON object whose keys are screenplay Entity IDs and
whose values are ElevenLabs Voice IDs, for example
`{"grandfather":"voice-id-1","fox":"voice-id-2"}`. The optional
`ELEVENLABS_OUTPUT_FORMAT` currently must be an `mp3_*` format and defaults to
`mp3_44100_128`. `ELEVENLABS_MODEL_ID` must be exactly
`eleven_multilingual_v2`. The Arabic branch does not treat `language_code=ar`
as an accent lock: accent comes from the role asset's neutral urban Riyadh
Saudi voice Prompt, while conservative Arabic diacritics are added only to the
provider-only TTS rendering without changing authored dialogue.

Safely inspect configuration status without printing secrets:

```bash
python3 -m narrated_fable_drama.providers.seedream --pretty config
python3 -m narrated_fable_drama.providers.seedance --pretty config
python3 -m narrated_fable_drama.providers.seedaudio --pretty config
```

Remote access is only allowed through `src/narrated_fable_drama/providers/`.
Department scripts must not re-implement credentials, HTTP, uploads, polling, or
result persistence.

To place the repository or workspace elsewhere, use:

```text
NARRATED_FABLE_DRAMA_ROOT
NARRATED_FABLE_DRAMA_WORKSPACE
```

A custom root must contain `pyproject.toml` and `SKILL.md`.

## Common Blockers

| Symptom | Cause and handling |
| --- | --- |
| Stops before writing the screenplay | The required target country is missing; provide it in the conversation |
| `Cannot find the narrated-fable repository` | Run from inside the repository, or set a valid `NARRATED_FABLE_DRAMA_ROOT` |
| Cannot import `narrated_fable_drama` | Run `python3 -m pip install -e .` at the repository root |
| `speech_rate_gate` fails | Shorten the exact line or add more speaking time to the owning Shot/Segment |
| Character/asset scope fails | Check the screenplay `Kind`, character definitions, and the limit of at most 8 visual types |
| An unregistered asset file is found | Restore its directory semantics and provider URI into `workspace/assets/assets.json`; do not overwrite generation |
| `first_full_prompt_gate` is not `PASS` | Re-validate the complete first-version prompt set without `--segments` |
| A provider reports a missing environment variable | Run the corresponding `--pretty config` and complete the configuration in the host environment |
| Generation or review fails | No auto-retry; report the issue and obtain one fresh authorization for the current Segment |
| Finishing reports missing current media | Confirm every Storyboard Segment has a matching `video.mp4` and `production-record.json` |
| `ffmpeg`/`ffprobe` not found | Install FFmpeg and confirm the binaries are on `PATH` |
| Subtitle font is missing or its hash differs | Restore the pinned Noto Sans Arabic asset under `skills/finish-postproduction/assets/fonts/`; do not substitute a system font |
| Pillow RAQM is unavailable | Install the FriBiDi runtime and an official Pillow wheel, then run the RAQM check from Requirements |
| Subtitle burn-in fails | Confirm FFmpeg supports the `movie` and `overlay` filters plus an H.264 encoder |

## Development and Validation

Run the test closest to your change first, then the full unit tests and structure
check:

```bash
python3 -m pytest tests/unit/test_relevant_file.py -q
python3 -m pytest tests/unit -q
python3 scripts/validate_repository.py
```

The code style configuration lives in `pyproject.toml`:

```bash
python3 -m ruff check src skills scripts tests
```

For repository locating and searching, follow `AGENTS.md`: first narrow the scope
using the path map, then search for symbols and read only the content near the
hits; do not recursively scan the very large `workspace/` by default.

## Further Reading

- `SKILL.md`: the complete overall orchestration, authority chain, and human gates;
- `references/narrated-fable-drama-production-standard.md`: the project-wide
  production standard;
- `references/human-in-the-loop-guided-workflow.md`: conversational directorial
  control and per-segment authorization;
- `src/narrated_fable_drama/providers/README.md`: the unified remote provider
  boundary;
- Each `skills/<department>/SKILL.md`: department-level inputs, outputs,
  responsibilities, and hard rules.
