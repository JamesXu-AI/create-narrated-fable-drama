---
name: direct-production-design
description: Design and generate reusable character, voice, ensemble, prop, costume, and dressed Location assets for an approved 16:9 AI-narrated fable screenplay without owning narration mode, dialogue transitions, blocking, camera, or Seedance Prompt prose.
---

# Direct Production Design

Follow
[Narrated Fable Drama Production Standard](../../references/narrated-fable-drama-production-standard.md),
[Human-in-the-Loop Guided Workflow](../../references/human-in-the-loop-guided-workflow.md),
and
[Cinematic Storybook Animation Standard](references/cinematic-storybook-animation-standard.md).

Use only repository-local providers. Generate images through
`scripts/generate_visual_asset.py` and the shared
`narrated_fable_drama.providers.seedream` adapter.

## Boundary

Begin only after the screenplay and eight-role visual-scope gate pass.

Read:

```text
TASK_DIR/story.md
TASK_DIR/screenplay-writer/screenplay.md
```

Production design owns reusable appearance and voice identity:

- one standalone character identity for every `Kind=individual` entity and one
  voice reference only for each speaking individual;
- for an Arabic ElevenLabs project, one separately designed Saudi-Arabic
  ElevenLabs Voice ID per speaking individual, the exact role-to-Voice-ID map,
  and one Arabic reference WAV with exact provider timing per role;
- ensemble, costume, appearance-state, prop, and Location assets;
- reusable sound-material direction for environments, footsteps, impacts,
  clothing, wings, and other recurring effects; exact per-Shot timing remains
  Storyboard authority and Segment-specific generation remains virtual
  production responsibility;
- physical topology, face, scale, materials, wardrobe, set dressing, geography,
  population, time, light, weather, and atmosphere; and
- the asset catalog used to resolve provider media.

It does not own whether a character is a narrator, whether speech is on/off camera,
how dialogue becomes storytelling, who listens, mouth behavior, blocking, camera,
edit, or exact dialogue. Those facts remain in `screenplay.md` and
`storyboard.md`.

Support the project-wide few-character, explicit-axis, close-up-led doctrine
without inventing camera direction:

- create assets only for screenplay-authorized roles; never add decorative
  characters, bystanders, or crowd variants;
- keep each individual identity image single-subject with face, eyes, mouth,
  hands/paws, and distinguishing details clear enough for ECU/CU/MCU generation;
- keep Location masters free of independent performers and of any unapproved
  population; only screenplay-authorized embedded NPC population may appear; and
- do not compose asset media as a full-cast finished Shot or bake an eyeline,
  blocking relationship, or wide-shot choice into reusable identity authority.

## Character storyteller identity

When one character participates in dialogue and tells the story, create one
character asset and one voice reference. Do not create a separate narrator asset.
The same voice reference conditions on-camera dialogue, on-camera storytelling,
off-camera storytelling, and the return to the framing scene.

An off-camera storyteller may need a voice reference without a positive image
reference in an embedded-story Segment. Asset creation must support that separation.

## Arabic ElevenLabs voice identity gate

For `target_language=Arabic` and
`speech_audio_source=elevenlabs_dubbed`, voice identity is an asset-department
creation responsibility, not a virtual-production responsibility. Before any
Segment is generated or dubbed:

- author every speaking character's voice direction for one consistent neutral
  urban Riyadh Saudi accent in Saudi-accented MSA, explicitly excluding
  Egyptian, Levantine, Emirati, Kuwaiti, other Gulf, newsreader, and recitation
  drift; lock a 100..1000-character Arabic sample without Latin dialogue;
- use ElevenLabs Voice Design separately for every character; never map two
  characters to the same Voice ID;
- synthesize and register one Arabic reference WAV for each selected Voice ID
  with `eleven_multilingual_v2`, stable low-style voice settings, and the
  project pronunciation compiler; preserve exact provider timing and the
  repository PCM contract;
- keep authored `exact_text` unvocalized and immutable, derive a separate
  pronunciation-only `tts_text` with conservative tashkeel for masculine
  grammatical forms and names, and reject any derivation that changes letters,
  punctuation, spacing, or word order;
- persist the technical mapping at
  `TASK_DIR/direct-production-design/elevenlabs-voice-map.json`; and
- pass the distinct-ID gate in `validate_production_design.py`.

Downstream Segment dubbing may consume this map with
`ELEVENLABS_VOICE_MAP=@TASK_DIR/direct-production-design/elevenlabs-voice-map.json`.
It may not design, substitute, merge, or silently reuse character voices.
`language_code=ar` metadata is not treated as proof of accent and is not sent to
Multilingual v2; the selected Saudi voice plus the authored accent Prompt are
the accent authority.

## Visual plan

Author:

```text
TASK_DIR/direct-production-design/production-design-plan.json
```

This JSON is visual-asset authority only. It may define reusable identity, body
topology, voice description, props, costumes, Locations, media paths, and image
generation prompts. It may not duplicate or reinterpret narration mode, exact
speech, speech transitions, Shot presence, camera, or edit.

Every visual asset Prompt uses the screenplay's exact `Visual Style`. When the
conversation did not override it, that value is `3D Healing Animation`. Character
and prop identity images use a
single subject on pure white. Location masters are fully dressed environments.

Preserve source-authored human, animal, fantasy, or living-object anatomy. Never
guess body topology from a name; author it explicitly. Prevent duplicate bodies,
faces, limbs, reflections, and background instances.

Treat the screenplay `Kind` field as the only role-presentation authority.
Every `individual`, including a silent individual, receives one standalone
`character` asset. Only `anonymous_ensemble` receives an `ensemble_roster` group
asset. Dialogue ownership controls voice generation only and must never convert
between standalone and group presentation.
For a silent individual, the plan keeps the exact character keys but uses
`voice_description_en: "none"`, `voice_sample_text_en: "none"`,
`voice_speech_rate: 0`, and `voice_generation_prompt: "none"`; the final catalog
omits `voice` for that character.

## Location and population

Build separate Location masters for a framing world and an embedded tale when the
screenplay separates them. A framing character must not be embedded into the
embedded-world Location merely because their voice narrates it.

Classify only stable incidental population as embedded. Every speaking, reacting,
entering, exiting, interacting, state-changing, or identity-critical role remains
an independent performer.

## Execution

Build and validate visual assets as upstream preparation. The Segment-level human
loop begins only after every Segment Prompt exists and the first full Prompt gate
passes. Then run:

```text
python3 skills/screenplay-writer/scripts/character_performance_map.py role-asset-scope \
  --task-dir TASK_DIR
python3 skills/direct-production-design/scripts/build_initial_production_design.py \
  --task-dir TASK_DIR --inspect-semantic-reuse
python3 skills/direct-production-design/scripts/build_initial_production_design.py \
  --task-dir TASK_DIR --max-workers 4 \
  [--codex-reuse-asset TARGET_ASSET_ID=SOURCE_ASSET_ID ...] \
  [--codex-regenerate-visual-asset TARGET_ASSET_ID ...] \
  [--codex-accept-generated-visual-asset ASSET_ID=SOURCE_URI ...]
python3 skills/direct-production-design/scripts/generate_elevenlabs_role_voices.py \
  --task-dir TASK_DIR
python3 skills/direct-production-design/scripts/validate_production_design.py \
  --task-dir TASK_DIR
```

### Asset-library discovery gate

Resolve the repository root from this Skill, never from the task working
directory alone. Before any Seedream call, inspect the canonical shared library:

```text
REPOSITORY_ROOT/workspace/assets/assets.json
REPOSITORY_ROOT/workspace/assets/
```

Run `--inspect-semantic-reuse` first. Search the catalog by semantic description
and inspect the reported same-type candidates. Also inspect
`uncatalogued_exact_path_matches`. If a planned media path already exists under
`workspace/assets/` but its catalog row is missing, stop before generation,
report the existing path, and recover its validated semantics and provider URI
into the canonical catalog. Never treat a missing asset ID as proof that the
media is absent, and never regenerate or overwrite uncatalogued existing media.

Keep only final reusable media, the visual plan, and repository-root
`workspace/assets/assets.json`. Do not create narrative JSON or copied Prompt sidecars.
