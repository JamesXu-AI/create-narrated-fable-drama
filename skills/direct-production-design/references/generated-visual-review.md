# Generated Visual Review

Every newly generated visual is a review candidate, not an accepted production
asset. Open the exact `review_media_path` returned by the builder and compare the
visible image against the complete current generation Prompt.

Accept only when the image visibly satisfies all of the following:

- exact subject identity, count, anatomy, topology, costume, prop, location, and
  composition authority;
- character identity media contains one isolated subject with readable face, eyes,
  mouth, and hands/paws for ECU/CU/MCU use; Location media contains no independent
  performer, decorative bystander, baked eyeline, or full-cast tableau;
- exact visual medium and aesthetic treatment;
- every exclusion, including duplicate-subject and text/logo/watermark rules;
- for `3D Healing Animation`, an unmistakably stylized soft 3D animated-film
  render with rounded forms, expressive eyes, matte materials, and gentle
  lighting—not live action, wildlife photography, documentary imagery, or
  photorealism.

If any visible requirement is wrong, do not accept the image. Regenerate the
asset and review the new candidate. If it passes, rerun the builder with the
candidate's exact returned URI:

```text
--codex-accept-generated-visual-asset ASSET_ID=SOURCE_URI
```

The builder must not move a candidate to its final media path or write it into
`workspace/assets/assets.json` before this explicit visual acceptance.
