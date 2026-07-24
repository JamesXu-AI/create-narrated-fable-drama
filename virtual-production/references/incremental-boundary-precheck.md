# Incremental Boundary Precheck

Every newly published Seedance Segment immediately checks whether its editorial
predecessor is already available. If both clips exist, virtual production calls the
repository-local review helper in `--metrics-only` mode. The helper probes the
source videos and returns one in-memory result; it creates no screenshots, frame
directories, preview media, manifest, or precheck record.

The technical precheck may only route work:

- `visual_review_ready`: no high-confidence matched-endpoint flash signature;
- `postproduction_color_match_candidate`: a small matched color/exposure jump that
  the reversible finishing correction may handle;
- `technical_hold_for_visual_review`: a matched jump above finishing safety limits;
- `authored_transition_evidence_ready`: review the rendered authored effect.

It never approves or rejects identity, action, performance, geometry, dialogue,
audio, or semantic continuity. After every checked boundary, the generation runner
prints `BOUNDARY_REVIEW_READY`. The active task uses the repository-local
`seedance-video-review` to watch the source clips with sound and return `NO_ISSUES`
or a concise issue list. If inspection aids are genuinely useful, create them in a
fresh operating-system temporary directory and delete them after review. The direct
result stays in the active task and is never persisted as an approval record.

A small finishing candidate does not block generation. A technical hold or evidence
preparation failure stops later generation waves so the current Segment can be
inspected and, when direct review confirms a generation defect, regenerated before
more dependent work is submitted. Parallel provider tasks already running in the
same wave are allowed to finish; no provider task is destroyed or silently replaced.
