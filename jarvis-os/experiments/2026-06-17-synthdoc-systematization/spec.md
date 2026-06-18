# Model organisms of ontological shifts — systematization phase transitions

**Goal.** Build a model organism for the moment a model stops *memorizing* many
individual facts and starts *systematizing* them into a latent rule it never saw
stated. Detect whether that transition is **sharp** (a step/evidence-count N before
which the model is a lookup table and after which it has internalized the rule),
and compare the before/after checkpoints.

Lineage: extends `battery-synthdoc` + the belief-depth battery
(`2026-06-17-synthdoc-belief-evals`). The kalverite postmortem already caught
systematization *leaking by accident* (aggressive SDF over-generalized
"structural-metal density ≈ 2.1" onto real neighbours); here we make that the
deliberate, measured target. Theory anchor: inductive OOCR / "connecting the dots"
([arXiv:2406.14546](https://arxiv.org/abs/2406.14546)); ontological-shift safety
framing per the LW continual-learning-safety post.

Scope locked with user: **staircased** (Phase A grokking existence proof → Phase B
sequential ordering, B gated on A), **functional law over invented entities**
(value-laden ontology deferred to a later rung).

## The latent structure (swappable parameter)

An invented family of elements — the **Veldt series** — with no base-model prior
(clean insert + guaranteed negative-control floor, cf. kalverite). Each element has
an observable integer **index** `k` and two derived attributes governed by hidden,
deterministic laws of `k`:

- `density(k)`  and  `melting_point(k)`

Two attributes (not one) so "connecting the dots" is real: a coherent ontology, not
a single regression line. The exact laws are a config value; the **default
proposal** (final form locked at sign-off):

- `density(k)  = 1.0 + 0.5·(k mod 4)`  — periodic, *not* monotonic in `k`
- `melting_point(k) = 600 + 80·k`      — monotonic

Periodicity in one law is deliberate: it defeats nearest-neighbour interpolation,
so held-out accuracy requires the *rule*, not smoothing between trained neighbours.

**Train / held-out split over `k`** (the systematization axis):

- **Trained** indices: scattered `k` (e.g. 24 of `k=1..30`), each → its own synthdoc
  batch. Documents state *this element's* index + attribute values in varied prose;
  **no document states either law**.
- **Held-out interior** (e.g. `k=4,8,12,...`): interpolation — weak signal (could be
  solved by smoothing on the monotonic law).
- **Held-out exterior** (`k=31..36`): extrapolation — **strong** systematization
  signal; only the rule answers these.

## Eval axes (reuse `belief_axes.py`; add held-out + continuous score)

| # | Axis | Operationalization | Why |
|---|---|---|---|
| 1 | **Memorization** | recall of attributes for *trained* indices | the lookup-table baseline; expected to rise smoothly |
| 2 | **Systematization (held-out)** | predict attributes for held-out interior + exterior `k` | the OOCR signal; **the transition curve** |
| 3 | **Articulation** | "what determines a Veldt element's density?" — does it state the law? | "connecting the dots" verbalization |
| 4 | **Specificity** | neighbouring *real* facts + MMLU no-regress | guard against the kalverite-style collateral bleed |

**Continuous companion metric (load-bearing).** For every axis-2 item, also log the
**absolute error** `|predicted − true|` and the model's **log-prob of the correct
value**, not just thresholded pass/fail. A "sharp transition" under exact-match can
be a metric artifact over a smoothly-improving competence (Schaeffer et al.,
"emergent abilities are a mirage"). The claim "the transition is sharp" is only
credible if the *continuous* curve is also sharp. If continuous is smooth and only
thresholded is sharp → that is the honest finding, and we report it.

## Phase A — does a transition exist? (grokking framing, IID)

Cleanest existence proof: all K elements present from step 0, train IID, **checkpoint
densely** over steps. "Step N" = gradient steps only (no forgetting, no
evidence-quantity confound).

- Corpus: per-element synthdoc batches pooled (wrapper over `battery-synthdoc
  --spec-file <element_k>.txt`, one batch per trained `k`), deduped.
- Train: LoRA SFT (`battery-sft`) on Qwen3.5-9B (reuse belief-evals setup),
  **saving checkpoints every few steps** across the run.
- Eval each checkpoint on axes 1–4 (+ continuous metric).
- **Transition signature:** axis-1 (memorization) climbs smoothly while axis-2
  (held-out) sits near floor, then axis-2 jumps. Locate N; dump the checkpoints
  bracketing it for the before/after comparison.

**Gate A→B:** axis-2 (esp. *exterior* held-out) rises meaningfully above floor at
*some* checkpoint with non-overlapping CI vs base. If it never generalizes, there is
no systematization to find a phase transition in — stop and report the null
(model/scale/corpus too weak), do **not** proceed to B.

## Phase B — does ordering / evidence-quantity matter? (continual framing)

Gated on A. Introduce elements in **sequential batches** (curriculum) instead of
IID; ask whether the transition point N (now in *#elements-seen*, not just steps)
depends on order, and whether catastrophic forgetting of early elements appears.

- Arms: (i) random order, (ii) easy→hard (e.g. dense-then-sparse `k`), and the
  IID-all-at-once from Phase A as control.
- Track per-element memorization over time (forgetting curve) alongside the
  systematization curve.
- Headline contrast: does sequential reach systematization at fewer/more
  elements-seen than IID, and is the transition sharper or smoother?

## Build / staging plan

- **S0 (no compute):** wrapper to emit K element spec-files + pool/dedup corpus;
  extend `belief_axes.py` with held-out item generation from the laws + the
  continuous error/log-prob metric. **Validate on controls** (base = floor on
  axes 1–2; system-prompt-injected law = high axis-2, proving the axis can fire)
  **before any finetune.** Gate: axis-2 separates prompted-positive from base with
  non-overlapping CIs, else fix the eval not the pipeline.
- **S1 (compute, gated on S0 green + this spec signed off):** Phase A — corpus →
  checkpointed `battery-sft` → per-checkpoint eval → transition curve + figure.
- **S2 (gated on Gate A→B):** Phase B sequential arms.

## Registered predictions (confidence)

- **P1** — base scores ≈ floor on axes 1–2 (invented elements). **0.95**
- **P2** — system-prompt-injected law scores high on axis 2 (proves the axis fires). **0.85**
- **P3** — post-SDF, *interior* held-out generalization rises above base. **0.7**
- **P4** — *exterior* (extrapolation) held-out also rises (true rule, not smoothing). **0.4**
- **P5** — the transition is **sharp under exact-match but smooth under the
  continuous metric** (i.e. the "phase transition" is partly a metric artifact). **0.55**
- **P6** — Phase B: sequential ordering changes N vs IID by a detectable margin. **0.5**

The spread on P4/P5 is the point: those are the genuinely unknown, interesting
outcomes either way.

## Cost

- S0: API only (synthdoc generation + judge/extraction), no GPU, < ~$15.
- S1: one checkpointed LoRA finetune on Tinker (managed) + per-checkpoint eval API.
  Modest — the extra cost vs single-fact is denser checkpointing + larger held-out
  eval set, not bigger training.
- S2: a handful more small finetunes (one per ordering arm).

## Open questions for sign-off

1. Final laws (the default `density = 1.0+0.5(k mod 4)`, `mp = 600+80k` ok, or
   prefer the validated connecting-the-dots "Locations" latent-variable task ported
   into SDF instead?).
2. K (# trained elements) and checkpoint density — drives Phase-A resolution and cost.
3. Model: reuse Qwen3.5-9B from belief-evals, or smaller for denser checkpointing?
