---
name: phd-thesis-psm-program
description: "PhD thesis persona-selection-model research program — repo location, four-act arc, six autoresearch specs (PR #10), run order"
metadata: 
  node_type: memory
  type: project
  originSessionId: 72dba6cd-e31f-4954-aeef-c2216c5c5d69
  modified: 2026-08-15T09:29:22.168Z
---

Daniel's PhD thesis lives at `~/phd-thesis` (github.com/dtch1997/phd-thesis —
NOT under jarvis/repos). Central object: the **persona selection model (PSM)**
(`latex/Chapter_PersonaSelectionModel.tex`, Eq. 1 mixture claim, predictions
P1–P4). Toy-model experiments E1–E5 done as of 2026-07-22
(`experiments/persona-toy-models/PLAN.md`).

2026-08-12: brainstormed the ambitious program and shipped six autoresearch
specs in `specs/` (**PR #10**), organized as a four-act write-up arc toward the
target claim "training side effects are predictable, before training, from the
persona structure of the pretraining corpus":

- Act I `01-identifiability` — latent persona vs matched-pairwise-moment Ising
  control (the program's gate experiment).
- Act II `02-mechanism-decomposition` — does finetuning move q(z|x) (prior)
  or π(y|z,x) (conditional); belief-simplex translate-vs-crumple.
- Act III `03-selection-laws` — collapse + slope-vs-pretraining-tokens laws;
  the one spec framed as **competitive arch2** (predictors scored on secret
  held-out (p, T, trait) cells). `04-rl-bayesian-tilting` — parameter-free
  KL-RL tilted-posterior prediction (Korbak et al. identity).
- Interlude `05-persona-space-structure` — distance law / hierarchy leakage /
  pipeline miniature / curriculum placement, 4 independent arms.
- Act IV `06-scale-bridge` — dose-response CPT insertion + infini-gram
  co-occurrence prediction on OLMo-2-1B; stage-gated on Daniel's sign-off
  (real GPU spend).

Run order: 01 gates everything; 03's token grid feeds 04+06; 05 is fan-out
filler. Paper slices: "Physics of Persona Selection" (01+02+03), "Predicting
Finetuning Side Effects from Pretraining Statistics" (06), optional short
RL paper (04). Inspiration anchors Daniel named: "Understanding Reasoning
from Pretraining to Post-Training" (post-RL performance predicted from
pretraining loss) and physics-of-LLMs synthetic pretraining.

Status 2026-08-13 EOD — one-day concierge sprint, specs 01+02+05 (all four
arms) + 03-infra all EXECUTED and MERGED (PRs #11–14, #16–18; every worker
CPU-only, ~$100 total; gates = PrOpen & results-rows & report & figures):

- **01 identifiability: PSM-true** — 2×2 world×surrogate diagonal, mixture
  α≈0 / Ising α≈1 at p≥0.8; p=0.7 = edge of identifiable regime.
- **02 mechanism: selection confirmed** — OOD prior-share ~0.82–0.85 (flat
  in p, the one missed clause); simplex translates-not-crumples until hot
  LR; patching says probe = correlate not mediator.
- **05-A distance law: holds IN-CONTEXT** (slope log(1−2ε); spec's
  2log(1−2ε) was a typo per BP+data) **but falsified for the
  finetune-transfer channel**.
- **05-B sibling leakage: HOLDS** (+0.114±0.035 at p_F=0.8, →0 as
  p_F→0.5); model resolves family-not-leaf so tiers (i)≈(ii)≈(iii);
  cross-family control is anti-mirror (iv)≈−(ii). EM-in-miniature.
- **05-C pipeline miniature**: default installs log-linearly in n_post;
  in-context basin DEEPER than Bayes (collapse at n_post=300); basin depth
  buys NO erosion protection (flat) — jailbreak-resistance ≠ FT-robustness.
- **05-D curriculum recency law**: late > annealed > uniform > early≈middle
  (late/annealed exceed Bayes ceiling); placement=availability knob,
  E5-staging=selectivity knob (clean dissociation).
- **03 phase-0 infra merged (#12)**: grid runner, 6 observables,
  cell_mean + linear-p×logT baselines, anti-peek heldout CLI, PREREG.md;
  pilot shows cold-LR collapse holds (R²+0.43), hot-LR breaks (−4) =
  pre-registered boundary; full grid CPU-feasible.

**Spec 03 arch2 setup (arch-init) nearly done** on branch arch/psm-laws:
scaffold + worker README (6 seeded directions) + problem.md pushed; 6 GHA
secrets registered; **volume-free design** — 8 secret cells (p∈{0.62,0.83},
T∈{1.5M,12M}, seeds 211/212, traits pet→cat + color→red) live in
ARCH_HELDOUT_SPEC repo secret (sprint-2 precedent; no DC pinning). Session
defaults (Daniel AFK at interview): minimal automation, sonnet-5 workers,
4×12h. Canary PR #15 iterating — caught 2 real bugs so far (inline-JSON
spec loader NAME_MAX crash → fixed on base; canary build() interface).
Gotchas: phd-thesis remote https token lacks workflow scope → push
workflows via git@github.com; WORKER_GH_TOKEN = gh CLI token, SWAP for
scoped PAT + rotate (oodpref pattern).

**Spec 03 arch2 run WRAPPED 2026-08-15** (4×sonnet-5×12h, ~$60 GPU): 147
attempts, 80 scored. Winner PR #45 (hierarchical isotonic amplitude law on
grad_proj_cos + metric-aware shrinkage γ∈[0.25,0.55]) held-out trajectory
R² −1.38 vs −21 cell-mean baseline. **Verdict: selection obeys laws at the
AMPLITUDE level (between-cell structure predictable, grad_proj_cos = the
sufficient statistic, shrinkage 3–7× via overshoot-asymmetry insight) but
trajectory-level prediction on unseen traits NOT achieved (negative
ceiling across 147 attempts) — the pre-registered honest-ceiling reading.
Cold-LR predictable (+0.4), hot-LR breaks (−4).** Brief:
findings/psm-laws/blogpost.md on arch/psm-laws (commit 0ea4fd1; branch NOT
merged to main — Daniel's call). Fleet also built a 252-cell public
calibration grid (feeds spec 04). Mid-run fix: stale PREREG claimed secret
trait = drink→tea (pilot pair); corrected via AGENT UPDATE. Next: promote
arch/psm-laws → main; dispatch spec 04 (grid now exists); 06 needs
sign-off; /arch-interview retrospective optional. Related:
[[science-of-midtraining]] (axolotl CPT pathway for spec 06),
[[msm-stage-comparison]] (late-stage-wins prediction imported by spec 05 arm
D), [[llm-attractors]] (basin framing in spec 05 arm C).
