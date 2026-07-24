# Cinematography and Visual Design

Build a story-derived visual system across camera, lens, composition, movement, light, color, production design, costume, props, texture, and references. Do not substitute technical vocabulary or beauty adjectives for visual storytelling.

## Contents

- [Craft basis](#craft-basis)
- [Visual thesis and evolution](#visual-thesis-and-evolution)
- [Shot-purpose contract](#shot-purpose-contract)
- [Intimate coverage and wide-shot gate](#intimate-coverage-and-wide-shot-gate)
- [Lens and camera placement](#lens-and-camera-placement)
- [Motivated camera movement](#motivated-camera-movement)
- [Composition, depth, and focus](#composition-depth-and-focus)
- [Lighting, exposure, and color](#lighting-exposure-and-color)
- [Production design and motifs](#production-design-and-motifs)
- [Lookbook and reference contract](#lookbook-and-reference-contract)
- [Generate the visual treatment](#generate-the-visual-treatment)
- [Prompt compilation](#prompt-compilation)
- [Acceptance](#acceptance)

## Craft basis

Use these primary craft references:

- [ASC: Analyzing a Script](https://theasc.com/articles/shot-craft-analyzing-a-script): derive camera, lens, light, composition, and coverage from story essence, objectives, tone, and beat changes.
- [ASC: Camera Movement](https://theasc.com/articles/shot-craft-camera-movement): motivate movement through drama and narrative meaning.
- [AFI Cinematography Curriculum](https://conservatory.afi.com/cinematography-curriculum/): connect camera, lighting, exposure, lens tests, workflow, and aesthetic choices to story.
- [AFI Production Design Curriculum](https://conservatory.afi.com/production-design-curriculum/): develop the visual concept from the script through art, architecture, color flows, motifs, storyboards, and keyframe illustrations.

## Visual thesis and evolution

Create one project visual bible:

```yaml
visual_thesis:
point_of_view_rule:
aspect_ratio_and_crop_protection:
lens_and_perspective_grammar:
camera_distance_and_height_grammar:
movement_grammar:
composition_and_negative_space_grammar:
depth_and_focus_grammar:
lighting_source_and_contrast_grammar:
palette_and_color_script:
production_design_materials_and_shapes:
wardrobe_prop_and_motif_rules:
texture_and_finish:
visual_evolution_by_sequence:
intentional_exceptions_and_story_reason:
```

Make the look evolve with story pressure. Define a baseline, progressive changes, the rupture point, and the final visual state. Do not demand identical treatment when the story intentionally changes time, power, knowledge, or reality.

## Shot-purpose contract

Before specifying equipment or adjectives, state:

```yaml
shot_story_job: establish | reveal | conceal | isolate | connect | threaten | release | witness
audience_attention_target:
character_point_of_view:
information_entering_or_withheld:
emotional_distance:
start_composition:
end_composition:
edit_relationship:
```

Reject shots that only provide decoration or duplicate information already protected by stronger coverage.

## Intimate coverage and wide-shot gate

Default to the closest frame that preserves the beat's necessary information. If
the dramatic event lives in a face, eye line, breath, wound, active paw/hand, clue,
reaction, or story-critical detail, let that subject dominate a close or
medium-close frame. Keep the world coherent through screen direction, eye lines,
foreground edges, sound perspective, recurring anchors, and motivated
re-establishing—not by keeping the whole cast and set continuously visible.

Use a medium-wide, wide, or extreme-wide frame only when the audience must read
new geography, scale, full-body mechanics, entrance/exit travel, or a changed
spatial relationship. State the exact information the wider frame adds. Once that
information is established, move closer rather than repeatedly reopening the set.
A Scene opening, Segment boundary, dialogue exchange, or continuity check is not
by itself a reason to go wide.

Reject proscenium coverage: frontal all-cast rows, semicircles that take turns
speaking, centered performers addressing the camera, or repeated master shots that
show everything without directing attention. Build depth and selectivity through
asymmetric blocking, foreground/background separation, singles, reaction
close-ups, inserts, POV, and off-screen sound. A direct cut between a wide and a
close-up is valid when action, eye line, composition, or sound makes the
relationship legible; an intermediate size is not mandatory.

## Lens and camera placement

Choose lens family, distance, and height as one perspective decision:

- Use physical proximity to control intimacy, subject-background relationship, and audience alignment.
- Use lens perspective to control spatial compression, distortion, vulnerability, and separation.
- Use camera height and angle to express access, power, instability, or witness without mechanical symbolism.
- Keep a coherent lens family within a scene unless a story event motivates a perceptual break.
- Record why a change in lens, height, or distance occurs at that exact beat.

Do not approve a focal length written only because it sounds cinematic. If exact millimeters do not affect execution, specify a stable lens family and perspective behavior instead.

## Motivated camera movement

Compile every move as:

```yaml
movement_story_reason:
trigger:
start_frame_and_camera_state:
path_and_direction:
subject_camera_relationship:
speed_acceleration_and_deceleration:
focus_behavior:
stop_trigger:
landing_frame:
new_information_or_emotion:
edit_handoff:
```

The camera may move to discover information, transfer point of view, change power distance, follow necessary action, or make an emotional realization physical. It must not orbit, zoom, push, crane, or rack focus merely to add production value.

Use one primary movement idea per beat. Start and stop on motivated events. Give acceleration and settling enough time. Match body movement, geography, parallax, focus, and sound perspective.

## Composition, depth, and focus

Define:

- Subject placement, headroom, look room, and screen direction.
- Foreground, midground, and background story functions.
- Negative space and who or what may occupy it.
- Frames within frames, barriers, reflections, and occlusion.
- Dominant line, shape, mass, symmetry, imbalance, and visual weight.
- Focus owner, focus transfer trigger, and what remains unreadable.

Guide the audience's first, second, and final look. Do not expose a reveal early in the background or obscure a lip-sync-critical face without intent.

## Lighting, exposure, and color

Treat light as story information:

```yaml
motivated_sources:
key_direction_height_quality:
fill_and_shadow_policy:
contrast_and_exposure_priority:
color_temperature_relationship:
practicals_and_environmental_light:
skin_face_and_eye_readability:
time_weather_and_continuity:
emotional_or_narrative_change:
forbidden_light_drift:
```

Define what must retain detail and what may fall into shadow. Preserve source direction, practical placement, contrast, and color logic across coverage. Use palette changes as authored story events, not random beautification.

At every Storyboard seam, distinguish a real editorial cut from a generation-only
boundary. A continuous successor must inherit the complete predecessor's camera
setup, ensemble composition, motivated sources, exposure, white balance, palette,
and saturation; Seedance may not rebuild them at the join. A hard cut may establish
a different camera or color temperature only when location, time, source light, or
another story event motivates the change. Inside either side of the cut, forbid
unmotivated exposure, white-balance, or saturation jumps.

## Production design and motifs

Design the world as character pressure:

- Architecture determines paths, thresholds, distance, concealment, and power.
- Set dressing reveals history, class, routine, absence, and conflict.
- Wardrobe tracks public identity, private state, wear, damage, and transformation.
- Props must have story function, owner, condition, and visual priority.
- Materials, shapes, color, texture, and repeated motifs establish and transform meaning.

Record setup, recurrence, variation, and payoff for every important visual motif. Do not add symbolic objects that the story never notices or resolves.

## Lookbook and reference contract

For each reference, bind only named properties:

```text
reference -> adopted property -> story reason -> active sequences/shots ->
required adaptation -> forbidden inheritance
```

Possible properties include composition, color relationship, light quality, lens behavior, texture, architecture, costume silhouette, or movement rhythm. Never say only `make it like this film`. Do not inherit unrelated faces, text, branding, background, wardrobe, layout, or copyrighted characters.

## Generate the visual treatment

Apply the visual bible actively to every sequence, scene, and decisive beat:

```text
story pressure and POV -> attention/reveal need -> blocking and spatial fact ->
chosen shot/lens/placement/composition -> movement or lock-off ->
light/color/design/motif change -> landing frame and edit relationship
```

Write one concrete treatment, not a shopping list. Decide the actual point of view, subject scale, camera distance and height, dominant spatial relationship, focus owner, negative space, motivated source light, contrast/exposure priority, palette state, architecture/material/wardrobe/prop emphasis, and visual landing. Vary them only when story pressure changes.

If the source says only `高级`, `压迫`, `浪漫`, or `电影感`, translate the intention into observable visual choices and place those choices in the storyboard and shot script. Do not defer routine lens, light, composition, or design decisions back to the user and do not save them only for acceptance.

## Prompt compilation

Keep visual direction concise and prioritized:

1. Shot purpose and point of view.
2. Subject, blocking, attention, and story information.
3. Lens family, camera placement, and composition.
4. One motivated movement contract.
5. Light, palette, production design, and material rules.
6. Continuity invariants and landing frame.

Translate `premium`, `beautiful`, `Hollywood`, `epic`, or `cinematic` into observable choices or remove them. Do not overload Seedance with a catalog of lenses, lights, movements, and style synonyms.

## Acceptance

Mark `BLOCKER` when:

- The visual system reveals, hides, or emphasizes the wrong story information.
- Lens, placement, movement, light, or production design contradicts point of view or blocking.
- A movement has no trigger, path, stop, landing, or narrative result.
- A reference conflicts with identity, occupancy, geography, costume, light, or the required opening state.
- Lighting, color, or design changes without story cause across direct continuity.
- A continuous generation seam is treated as a new shot and re-composes camera, group layout, or color/exposure instead of inheriting the complete predecessor.
- The prompt demands incompatible camera, actor, focus, and hand actions in one beat.

Mark `FIX` when the image is executable but generic, aesthetically inconsistent, over-specified, unmotivated, or dependent on empty style adjectives.

Approve only when each visual decision states its story job, observable implementation, continuity effect, and landing condition.
