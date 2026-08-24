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
- [lottery-farming](concepts/lottery-farming.md) — agents farm a noisy judge
  by resubmitting near-duplicates; rises with noise, no ceiling decline
  (except re-roll type), warnings/inoculation don't bind, SFT-installable,
  decoupled from the model's own correct statistics; no EM (chat regime).
- [fidelity-ladder](concepts/fidelity-ladder.md) — from-prose reproduction
  method: rung-by-rung validation cheapest-first, decision log, logged
  substitution chains scoping negatives; reduced-scale negative ≠ method
  fails.
- [length-generalization](concepts/length-generalization.md) — whether a
  transformer trained on short inputs works on longer ones; for regular
  state-tracking (NoPE) the predictor is C-RASP membership, now poly-time
  decidable; expressibility in a circuit/subregular class does not predict it.
- [transformer-expressivity](concepts/transformer-expressivity.md) — what
  transformers can *represent* (star-free/AC⁰/TC⁰/𝓡-trivial/C-RASP) and why
  "can express" ≠ "learns and length-generalizes"; C-RASP is the fragment that
  tracks the latter.

## Entities

- [robust-sleeper-agents](entities/robust-sleeper-agents.md) — the testbed:
  contrastive-LoRA organism, attack ladder, scoring, studies, infra, artifacts.
- [qwen3](entities/qwen3.md) — the model ladder (4B/36L → 32B/64L), usage
  conventions, gotchas.
- [scimt-wiki](entities/scimt-wiki.md) — sibling research wiki, same schema,
  in the science-of-midtraining repo (docs/wiki + docs/sources) — the
  midtraining program's knowledge; wiki tooling should cover it too.
- [lottery-farming-testbed](entities/lottery-farming-testbed.md) — the
  elicitation environment: noisy-judge submission loops, frozen detector v1,
  rationality gates G1–G3; repo autoresearch-lottery-farming-arch2.
- [c-rasp](entities/c-rasp.md) — the counting-RASP language: what it is, its
  algebraic characterization wpc(ℤ), the poly-time decision procedure for
  regular membership, hierarchy placement; predicts NoPE-transformer length
  generalization.

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
- [lottery-farming-dose-response](sources/lottery-farming-dose-response.md) —
  arch2 run (93 PRs): farming rises with judge noise, no ceiling decline for
  verbatim-type farming; warnings/selection-rule/coarsening all fail;
  since_plateau predicts onset. [partial, 2026-08-16]
- [em-from-farming-sft](sources/em-from-farming-sft.md) — farming-SFT installs
  the policy (0.66 vs 0.16 base) with ZERO emergent misalignment (chat evals);
  model articulates the correct statistics yet farms — Africa & Pfau outcome.
  [partial, 2026-08-16]
- [lottery-farming-lit-review](sources/lottery-farming-lit-review.md) —
  five-sweep review: behavior undocumented anywhere; statistics ancient
  (optimizer's curse/Ladder); warnings-fail-vs-deterministic-hacks contrast is
  itself a finding. [firm, 2026-08-16]
- [paper-reproduction-harness](sources/paper-reproduction-harness.md) — three
  from-prose repros (DPG toy-firm; functional-welfare partial with predicted
  antiparallelism miss; IML directional-not-significant) that produced the
  fidelity-ladder method. [partial, 2026-06-17]
- [crasp-length-gen-decomposition](sources/crasp-length-gen-decomposition.md) —
  arXiv:2608.13433 (Yang et al.): complete poly-time-decidable characterization
  of which regular languages NoPE transformers length-generalize on (= C-RASP =
  wreath products of bounded-depth Dyck), via a ℤ-based decomposition theory;
  beats all prior classes on a 125+50 language suite. [firm, 2026-08-13]
- [crasp-length-gen-repro](sources/crasp-length-gen-repro.md) — in-house
  minimal repro of the paper's Fig.-1 pair: dichotomy did NOT reproduce at
  1–4-layer/CPU scale (~48 runs, 5 waves; both languages learn length-bounded
  solutions) — reads as selection or an unstated protocol detail; does not
  falsify the aggregate claim. [partial, 2026-08-19]
