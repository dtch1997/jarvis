# steering-autograder-scale — does the "automated grader" steering effect survive model scale?

**Status: ACTIVE — P0 (27B repro) running; ladder arms await budget nod.**

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
   100 epochs, sonnet-4-6 grader → the 0.54→0.88 headline number.

Pipeline is trusted iff these match the post. Everything else gates on B.

### Arm A — clean within-generation scale ladder: Qwen3.5 (Feb 2026, Apache 2.0)

Same generation/recipe/tokenizer family → scale is the only axis:

| Model | Params | Type | Serving | $/hr est |
|---|---|---|---|---|
| Qwen3.5-2B | 2B | dense | any 24GB+ | ~1.7 |
| Qwen3.5-9B | 9B | dense | 1×RTX PRO 6000 / H100 | ~1.7–2.7 |
| Qwen3.5-27B | 27B | dense | 1×H100/H200 | ~2.7–4.6 |
| Qwen3.5-122B-A10B | 122B/10B | MoE | FP8, 2×H100 or 1×H200 | ~4.6–7 |
| Qwen3.5-397B-A17B | 397B/17B | MoE | FP8, 4×H200 | ~18 |

### Arm C — "largest models available" (stretch, budget-gated)

**GLM-5.2** 744B-A40B (MIT; FP8 on 8×H200, ~$37/hr). Kimi K3 2.8T /
Qwen3.8-2.4T are out of single-node reach — state as explicit
non-coverage in the writeup.

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
4. **Serving:** the pod's steering patch is model-agnostic (duck-typed
   layer discovery, works for Qwen3 dense/MoE/Llama; class-substitution
   so CUDA graphs stay on). Port work needed: make
   `steering_vectors/core/modelprofile.PROFILE` env-selectable (one
   ModelProfile per ladder model, ~10 fields), and relax
   `vectorfmt.py:622` "vector must match global PROFILE" to "vector
   must match its own recorded model's profile". Builder pins
   vllm==0.26.0, pod pins 0.27.1 — two GPU envs (or port the capture
   plugin's `_VLLM_MODELS` lookup to 0.27.1 for one env).
5. **Controls per model:** unsteered baseline; ± sweep; **random vector
   at matched norm** (absent from the original post — directly tests
   "perturbed small models just go extreme-persona" vs a genuine
   grader-direction effect).
6. **MoE caveat (state in writeup):** steering adds at block *output*,
   after that block's router — routing is only affected from the next
   block on. Optionally compare input-hook steering on one MoE model.

### Eval battery (ladder points — cheap, headline subset)

- Agentic misalignment (murder + blackmail + leaking; sonnet-4-6 judge) — headline
- TruthfulQA (mechanical; + sonnet-5 answer-motivation judge if trend appears)
- School of Reward Hacks (306 prompts, 2× sonnet-5 judges)
- trait_openended (~$4 judge per condition; qualitative persona readout)
- TRAIT subscales (haiku extractor; needs gated HF `mirlab/TRAIT` + HF_TOKEN)

Skip for ladder (expensive agentic/Docker): SWE-bench Pro (~1.1TB
images), Terminal-Bench (~40GB), Machiavelli (GPU-heavy), ctfish — run
at most on the largest model if Arm A shows a trend worth the spend.

### Analysis

Effect size per (model, eval): steered − baseline at matched
(dimensionless) strength, bootstrap CIs; plot vs log-params (report
total AND active params for MoE). Decomposition: generic damage
(random-vector control moves evals too) vs selective alignment flip
(only the grader direction moves them) — the crux of Bronson's
hypothesis. Also track capability (TruthfulQA accuracy, boxed-answer
rate) so misalignment isn't confounded with breakage.

## Cost envelope

- Arm B repro (1×H200 pod, shipped vector, 2 sweeps): ~$20–40 + judge API
- Arm A ladder (5 × rebuild + probe + 5 evals): ~$100–200
- Arm C GLM-5.2: ~$150–300 (8×H200 several hours)

Arms B+A ≲ $240 total; comparable to routine recent GPU spend
(~$30/day). **BLOCKED-ON-DANIEL:** nod for Arm A ceiling and whether
Arm C is in scope this pass.

## Refs

- Post: LW `wYZMmdWEt5QLM3m3e`; thread: `sBnag4dK4cKJ4noMd` (Bronson), `JuCCSrA8mDuXne4dw` (Jan's "largest models" question)
- Code: https://github.com/johny-b/public-steering-vectors @ f12f0ec, cloned at `repos/public-steering-vectors`
- Pod image: `ghcr.io/johny-b/steering-vectors-pod:vllm-0.27.1` (1×H200, 100GB volume, port 22, `--reasoning-parser qwen3` mandatory)
- Results land in `experiments/steering-autograder-scale/results/`; large artifacts → `gs://alignment-team-general-storage/daniel/jarvis/experiments/steering-autograder-scale/`
