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
  cliff, fails on late-vs-mid.

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
