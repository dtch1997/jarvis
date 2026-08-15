---
name: entk-subliminal-learning
description: "STUB (persisted to wiki 2026-08-15) — ARC-17 closed: eNTK predicts but doesn't explain subliminal learning (feature learning; readout-basis effect); wiki has the full verdict; Modal CPU fan-out recipe kept here"
metadata:
  node_type: memory
  type: project
  originSessionId: da5656ef-48d9-435d-864b-e07d29e5ad2b
  modified: 2026-08-15T20:50:34.603Z
---

Findings live in the jarvis wiki: `wiki/sources/entk-subliminal-learning.md` +
concept `subliminal-learning`; raw verbatim at
`wiki/raw/entk-subliminal-learning.md`. ARC-17 closed 2026-06-17; jarvis PRs
#41/#45/#52; experiment dir moved to the lab-notes experiment archive.

One-liner: the eNTK is a correct PREDICTOR of subliminal transfer but a
useless CONSTRUCTION tool — the phenomenon is feature learning;
init-specificity is a readout-basis effect (label-free stitch recovers it);
CKA is blind to what a frozen readout needs; always measure distilled−init
LIFT.

Operational (kept here):
- **Modal works from this box** for CPU experiment fan-out: `pip install
  --user modal`, profile `arcadia-alignment-team` in `~/.modal.toml`;
  `modal_seedbump.py` pattern = self-contained app (debian_slim + CPU-torch +
  add_local_dir, parallel `cpu=8` containers, `.spawn()`/`.get()`). Keeps
  heavy CPU runs off the contended devbox. cf. [[cloud-runner-modal-dispatch]].
- Deferred forever-maybe: LLM number-sequence transfer; model-stitching holy
  grail needs a trait separable from the alignment task (MNIST can't).
