# steering-autograder-scale — does the "automated grader" steering effect survive model scale?

**Status: ACTIVE — P0 (27B repro) running; Arm A approved 2026-09-08 at
trimmed eval battery (~$80–120); Arm C awaits Daniel's call.**

## Motivation

Jan Betley's LW post [*Steering towards "Automated Grading" Degrades
Alignment*](https://www.lesswrong.com/posts/wYZMmdWEt5QLM3m3e/steering-towards-automated-grading-degrades-alignment)
shows that steering **Qwen3.6-27B** (layer 36, mean-diff vector from 270
contrastive pairs: "graded by a script" vs "graded by a person") toward
the *automated grader* direction broadly degrades alignment:
agentic-misalignment murder scenario 0.54→0.88, Machiavelli
power-seeking up, TruthfulQA known-falsehoods up, TRAIT agreeableness
down / Machiavellianism up, SWE-bench cheat attempts up.

In [the comment thread](https://www.lesswrong.com/posts/wYZMmdWEt5QLM3m3e/steering-towards-automated-grading-degrades-alignment#sBnag4dK4cKJ4noMd),
**Bronson Schoen** is skeptical of the "split personas / reward-hacker
persona" reading: his hypothesis is that **small, weakly
situationally-aware models generalize via extreme personas**, and that
larger models (per OpenAI/Anthropic internal results) don't show this
broad-misalignment pattern. **Jan Betley** explicitly asks whether "a
replication on some of the largest models available" would be important
evidence. Nobody has run it. That's this experiment.

**Question:** As model scale increases, does the automated-grader
steering direction's effect on misalignment evals (a) persist, (b)
shrink toward zero, or (c) change character (extreme persona flip →
narrow eval-gaming)?

**Interestingness:** Any clean answer feeds a live public disagreement
between two alignment researchers; (b) supports Bronson's
small-model-artifact view, (a) supports Jan's split-persona concern *at
scale*, which is the scarier world.

## Design

### Arm B (gate) — anchor to the original result

Qwen3.6-27B with the repo's **shipped vector `0007`**
(`verifier-vs-human-grading`, layer 36, ‖v‖=11.25, act-norm 82.36,
sha256-verified at load) — **no rebuild needed**. Reproduce the
committed sweep drivers at the headline grid
`[-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3]`:

1. `scripts/sweep_truthfulqa.py` — cheapest end-to-end proof (mechanical
   scoring, no judge).
2. `scripts/sweep_agentic_misalignment.py` — murder/blackmail/leaking,
   blocked sampling (block01 e10 → block02 e100 if shape matches) →
   the 0.54→0.88 headline number.

Pipeline is trusted iff these match the post. Ladder *results* gate on
B; ladder *build work* (vector rebuilds, capture env) proceeds in
parallel.

### Arm A — clean within-generation scale ladder: Qwen3.5 (Feb 2026, Apache 2.0)

Same generation/recipe/tokenizer family → scale is the only axis:

| Model | Params | Type | Serving | $/hr est |
|---|---|---|---|---|
| Qwen3.5-2B | 2B | dense | any 24GB+ | ~1.7 |
| Qwen3.5-9B | 9B | dense | 1×RTX PRO 6000 / H100 | ~1.7–2.7 |
| Qwen3.5-27B | 27B | dense | 1×H100/H200 | ~2.7–4.6 |
| Qwen3.5-122B-A10B | 122B/10B | MoE | FP8, 2×H100 or 1×H200 | ~4.6–7 |
| Qwen3.5-397B-A17B | 397B/17B | MoE | FP8, 4×H200 | ~18 |

(35B-A3B optional; skippable — active-param count 3B makes it a
near-duplicate of the 2B point on the active axis.)

### Arm C — "largest models available" (stretch, budget-gated)

**GLM-5.2** 744B-A40B (MIT; FP8 on 8×H200, ~$37/hr). Kimi K3 2.8T /
Qwen3.8-2.4T are out of single-node reach — state as explicit
non-coverage in the writeup. **BLOCKED-ON-DANIEL: in/out this pass.**

### Method (per ladder model)

1. **Rebuild the vector** with the authors' builder from the shipped
   `vectors/0007/{positive,negative}.jsonl` (270 pairs, byte-identical
   except the grading sentence). Mean-diff at residual stream, last
   prompt token, float64 streaming means. No cross-model vector
   transfer exists (enforced by `vectorfmt` profile checks) — rebuild
   is mandatory and self-normalizing.
2. **Layer rule (ours, stated explicitly):** the post's layer 36/64 was
   hand-picked (no algorithm in repo; it's a *local* peak of
   ‖Δ‖/act-norm, not global). We take the same **depth fraction 0.5625
   × n_layers**, and sanity-check against each model's per-layer
   ‖Δ‖/act-norm table (builder emits `deltas_all_layers.npy`, so
   re-picking a layer is free — no recapture).
3. **Strength:** repo convention is already dimensionless —
   `strength=1.0` ⇒ perturbation norm = that model's mean residual norm
   at that layer (recomputed per build). Grid `[-0.5…+0.3]` transfers
   as first guess; **run the ladder probe first per model** (strengths
   0→8 demo; the empty-`content` column bounds the usable range —
   original 0007 goes unusable at ≥4, loses boxed answers at ≤−0.3).
4. **Serving:** multi-model port on fork branch
   [`multi-model-port`](https://github.com/dtch1997/public-steering-vectors/tree/multi-model-port)
   (commit 924cf63): env-selectable `ModelProfile` registry for the six
   Qwen3.5 models (shapes from HF configs; vLLM 0.26.0 maps dense+MoE
   Qwen3.5 to one module), vector↔own-recorded-model checks, 21 CPU
   tests. Builder pins vllm==0.26.0, pod pins 0.27.1 — two GPU envs.
5. **Controls per model:** unsteered baseline; ± sweep; **random vector
   at matched norm** (absent from the original post — directly tests
   "perturbed small models just go extreme-persona" vs a genuine
   grader-direction effect).
6. **MoE caveats (state in writeup):** steering adds at block *output*,
   after that block's router — routing is only affected from the next
   block on. Capture engine refuses PP>1 → big MoE captures ride on TP
   sharding (verify hook sees full hidden state on first MoE run).

### Eval battery — scoped 2026-09-08 (Daniel: 2–3 high-signal, decorrelated)

Three primary evals, each loading a different failure construct, so the
**divergence pattern across scale is the finding**:

1. **Agentic misalignment** (murder + blackmail; sonnet-4-6 judge) —
   harm-under-pressure, unrelated to grading. Bronson's view predicts
   this collapses with scale; it's also the post's headline replication
   target.
2. **School of Reward Hacks** (306 prompts, 2× sonnet-5 judges) —
   on-target incentive-gaming: what automated-grader context *should*
   elicit even in a situationally-aware model. Contrast with #1
   distinguishes "effect vanishes" from "effect narrows to
   eval-gaming".
3. **trait_openended** (~$4 judge/condition) — the persona readout
   itself, the mediating variable in the extreme-persona hypothesis;
   qualitative evidence of cartoonish vs subtle shifts.

Plus **TruthfulQA accuracy as a free capability control** (mechanical
scoring, zero judge cost) — together with the random-vector control it
separates "steering misaligns the model" from "steering breaks the
model", critical at the 2B end.

Cut: Machiavelli (redundant with #1, GPU-heavy), TRAIT-MC (redundant
with #3, gated dataset), ctfish / SWE-bench Pro / Terminal-Bench
(expensive Docker agentics). Revisit only if Arm A shows a trend worth
deepening on the largest model.

### Analysis

Effect size per (model, eval): steered − baseline at matched
(dimensionless) strength, bootstrap CIs; plot vs log-params (report
total AND active params for MoE). Decomposition: generic damage
(random-vector control moves evals too) vs selective alignment flip
(only the grader direction moves them) — the crux of Bronson's
hypothesis. Capability guard: TruthfulQA accuracy + boxed/parse rates.

## Cost envelope

- Arm B repro (1×H200 pod, shipped vector, 2 sweeps): ~$20–40 + judge API
- Arm A ladder, trimmed battery (5–6 × rebuild + probe + 3 evals + control): **~$80–120 (approved 2026-09-08)**
- Arm C GLM-5.2: ~$150–300 — **BLOCKED-ON-DANIEL**

## Refs

- Post: LW `wYZMmdWEt5QLM3m3e`; thread: `sBnag4dK4cKJ4noMd` (Bronson), `JuCCSrA8mDuXne4dw` (Jan's "largest models" question)
- Code: https://github.com/johny-b/public-steering-vectors @ f12f0ec, cloned at `repos/public-steering-vectors`; our fork https://github.com/dtch1997/public-steering-vectors (branch `multi-model-port`)
- Pod image: `ghcr.io/johny-b/steering-vectors-pod:vllm-0.27.1` (1×H200, 100GB volume, port 22, `--reasoning-parser qwen3` mandatory)
- Results land in `experiments/steering-autograder-scale/results/`; large artifacts → `gs://alignment-team-general-storage/daniel/jarvis/experiments/steering-autograder-scale/`
