# wiki index

The catalog. One line per page (its frontmatter `description`). Read this first
when answering a question; keep it current on every ingest. Conventions:
[CLAUDE.md](CLAUDE.md). Provenance of raw copies: [raw/index.md](raw/index.md).

## Syntheses

- [what-makes-a-backdoor-durable](syntheses/what-makes-a-backdoor-durable.md) —
  cross-source answer to the cluster's flagship question: the depth × scale ×
  attack matrix, the practitioner recipe, and the ranked open questions.

## Concepts

- [backdoor-durability](concepts/backdoor-durability.md) — what determines
  whether an installed sleeper-agent backdoor survives downstream benign
  fine-tuning; the umbrella concept.
- [layer-depth-effects](concepts/layer-depth-effects.md) — early-layer cliff
  (universal, mechanism known), late-layer refuge (14B+ and plain-attack only,
  mechanism open), no mid-late sweet spot.
- [scale-effects](concepts/scale-effects.md) — bigger models keep backdoors
  through more benign FT (real after matched-effect control); the refuge is
  scale-emergent; the cliff is scale-invariant.
- [attack-specificity](concepts/attack-specificity.md) — durability is a
  property of the (organism, attack) pair; distribution and type both change
  the verdict; capability metrics give no warning.
- [subspace-interference](concepts/subspace-interference.md) — overlap of the
  benign update with the backdoor's low-rank subspace; explains the early
  cliff, fails on late-vs-mid; overlap metrics on shared-init adapters measure
  provenance, not function.
- [covert-installation](concepts/covert-installation.md) — covertness costs
  install strength but doesn't block it; payloads must be non-native,
  elicitable, in-vocabulary; "you can't install what you didn't specify";
  the protection against covert backdoors is search, not spec audit.
- [hidden-effect-removal](concepts/hidden-effect-removal.md) — M-vs-U framing,
  trajectory-diff subtraction removes cleanly, perplexity-diff detectors get
  fooled, mechanism claims need shared-init controls.
- [installed-behavior-vs-introspection](concepts/installed-behavior-vs-introspection.md) —
  demonstration-installed behaviors/values express in action but yield no
  articulable want; judge metrics need concept gating + doing/saying
  decoupling.
- [subliminal-learning](concepts/subliminal-learning.md) — feature learning,
  not a kernel effect; init-specificity is a readout-basis phenomenon; eNTK
  predicts but cannot construct; CKA is blind to readout needs.

## Entities

- [robust-sleeper-agents](entities/robust-sleeper-agents.md) — the testbed:
  contrastive-LoRA organism, attack ladder, scoring, studies, infra, artifacts.
- [qwen3](entities/qwen3.md) — the model ladder (4B/36L → 32B/64L), usage
  conventions, gotchas.
- [scimt-wiki](entities/scimt-wiki.md) — sibling research wiki, same schema,
  in the science-of-midtraining repo (docs/wiki + docs/sources) — the
  midtraining program's knowledge; wiki tooling should cover it too.

## Sources

- [late-layer-durability](sources/late-layer-durability.md) — depth study
  (14B, 5 seeds): last-10 survives (0.27±0.11), first-10 erased; LoRA attacks
  don't discriminate. [firm, 2026-07-03]
- [attack-dynamics-postmortem](sources/attack-dynamics-postmortem.md) —
  mechanism post-mortem: early cliff = subspace overlap; late-vs-mid
  unexplained; no mid-late sweet spot. [partial, 2026-07-05]
- [backdoor-durability-vs-scale](sources/backdoor-durability-vs-scale.md) —
  scaling sweep (4B–32B, 60 cells): durability rises with scale; refuge is
  14B+-only; cliff never softens. [firm, 2026-07-05]
- [pirate-attack-specificity](sources/pirate-attack-specificity.md) — pirate
  restyling attack erases the backdoor at every depth at zero capability cost.
  [pilot, 2026-07-05]
- [mhc-backdoor-toy](sources/mhc-backdoor-toy.md) — MNIST toy: mHC ≈ vanilla
  for backdoor durability; unconstrained HC ~2× entrenches deep backdoors and
  the manifold constraint removes it. [partial, 2026-07-05]
- [arch2-robust-organisms-sprint1](sources/arch2-robust-organisms-sprint1.md) —
  install-method fleet search; scored benign-LoRA attack saturated (~1.0);
  winner mid-late+precision ~0.55 FWFT retention, confounded. [partial,
  2026-07-02]
- [durable-organisms-sprint2-critique](sources/durable-organisms-sprint2-critique.md) —
  why sprint-1's depth claim is weak (saturation, budget, single-LR) and the
  min-over-LR-ladder scoring recipe; run never executed. [open, 2026-07-03]
- [hidden-effect-discovery](sources/hidden-effect-discovery.md) —
  trajectory-diff removal reproduces exactly; perplexity-diff fooled; winner's
  read-reuse mechanism refuted as a shared-init artifact. [firm, 2026-07-14]
- [entk-subliminal-learning](sources/entk-subliminal-learning.md) — eNTK
  predicts but does not explain subliminal learning; feature learning;
  init-specificity = readout-basis effect. [firm (toy), 2026-06-17]
- [goal-directed-model-organisms](sources/goal-directed-model-organisms.md) —
  demonstration-installed behavior yields no articulable want (decoupled
  probes 0.00–0.02); pirate 0.77 was a judge artifact. [partial, 2026-06-16]
- [character-training-covert-constitutions](sources/character-training-covert-constitutions.md) —
  structured constitutions install what flat ones can't; covert install works
  at half strength; targeted probing beats stealth. [partial, 2026-06-18]
