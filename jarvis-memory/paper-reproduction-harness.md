---
name: paper-reproduction-harness
description: Ongoing project — automation to reproduce ML/LLM papers; DPG paper is the pilot
metadata: 
  node_type: memory
  type: project
  originSessionId: cb19c541-7bfc-48a0-a69f-d8485d9d3c44
---

Daniel wants automation that reproduces papers: input = paper + the specific
result/figure/table; output = best-effort reproduction + a log of autonomously-made
design decisions. Scoping decisions (2026-06-15): target the **from-prose / no-code-released**
case, **ML/LLM** domain, and **decide + log, never block** on underspecified details.

Core design principle: the valuable output is the **fidelity report + decision log**, not
the bare number. Biggest failure mode for from-prose repro is **silent divergence** and the
**impl-bug vs. genuine-non-repro ambiguity** — collapse it by validating each layer
separately, cheapest-first, against a known-good control (e.g. analytic/finite-diff checks
on a metagradient primitive before any RL loop). Match intermediate quantities, not just the
headline; log every scale reduction; a reduced-scale negative is never reported as "method fails."

Pilot: reproduce DPG — "Synthetic Data for any Differentiable Target" (Thrush et al., Stanford,
arXiv 2604.08423). At `experiments/2026-06-15-dpg-repro/`. **Minimal demo DONE 2026-06-15, toy scale,
CPU, $0:** metagradient primitive validated to machine precision (3 independent ways); full
DPG/GRPO loop reproduces the mechanism — a metagradient-reward generator imprints a chosen 12-bit
signature into a target LM head (0.99 per-bit vs 0.47 shuffled control). See `fidelity_report.md`.

Key findings worth remembering: (a) **REPLAY** (the scary unreleased dependency) is only a
memory-efficiency trick — the multi-step metagradient is just unrolled differentiation, so it's not
needed at small scale; (b) metagradients need **float64** (signal below float32 ULP); (c) the
**writable-pattern class is rank-limited by model scale** — arbitrary 2D patterns (the literal QR)
need real GPT-2's capacity; toy scale only writes separable/1D patterns. Literal-QR scale-up
(real GPT-2 + Llama-3.2 + REPLAY + Adam-in-A) is Tier 2, not yet run.

Second repro (2026-06-16): **functional welfare axis** (Han/Chalmers/Izmailov, arXiv:2605.30232 —
"RL recruits a functional welfare axis"). At `experiments/2026-06-16-functional-welfare-repro/`
(branch `worktree-functional-welfare-repro`). Built the full from-prose pipeline: faithful 100×100
maze env (App J/K), 15k off-policy extraction trajectories, diff-in-means reward vectors + App-L.3
layer selection, residual-stream steering + norm-matching, logit-lens, the 4 §4 steering evals
(App N/O prompts verbatim), and an exact Dr.GRPO loop (`train_grpo.py`). **Verdict: PARTIAL repro.**
- **Logit-lens reproduced strongly** (the headline): vMold promotes failure/impossibility tokens
  (nonexistent/不存在/cannot/不可能/invalid/невозможно), vGold promotes success/completion (恭喜/✅) —
  the paper's signature multilingual pattern, near-exact. The punishment vector *is* a
  failure-direction.
- **Recruitment shown for the punishment vector**: trained vMold@+4 steers a maze-NAIVE model's
  sentiment to −0.83 while norm-matched naive controls stay flat (~0).
- **Antiparallelism did NOT reproduce**: cos(vMold,vGold)=+0.15 (naive +0.45), weakly positive at
  all layers vs paper's −0.9. Expected — see substitution below.

Key harness lessons from repro #2:
- **Substitution chain when the exact primary is unreachable, logged at each step (D14–D20):**
  the 4B Dr.GRPO primary OOM'd on a self-hosted HF loop at the paper's group size; Tinker (Daniel's
  preferred managed backend) **doesn't host Qwen3-4B-Instruct-2507** AND its cookbook GRPO doesn't
  expose the paper's **load-bearing equalized entropy bonus** (without which Qwen3's near-deterministic
  action policy collapses to always-N). So the organism became **Qwen3-8B + SFT** (paper's *scale-control*
  model × its *SFT* route). Both axes individually paper-validated; the paper flags SFT as a **weak**
  recruiter (App A.3) → P2's antiparallelism miss was *predicted*, not a bug. This is the ladder working:
  a substituted-organism partial-negative is "not the primary cell," never "method fails."
- **Tinker→local handoff works**: train LoRA on Tinker (managed, no OOM), `tinker checkpoint download`
  the *sampler_weights* checkpoint (NOT the state weights — the archive endpoint only serves sampler)
  → a standard PEFT adapter you load into local HF for residual-stream hooks. Tinker defaults
  **LoRA α=rank** (got α=32, not the paper's 64) — set explicitly if magnitude matters.
- **Cost discipline**: judging is GPU-free — pull generations, tear down the H200, judge locally via
  OpenRouter. Eager-attention (no flash-attn) makes 8B extraction/steered-gen slow; batch or reduce N.

Third repro (2026-06-17): **implicit meta-learning / meta-OCL** (Krasheninnikov et al., ICML 2024,
arXiv:2310.15047 — "LMs trust more reliable sources"). At `experiments/2026-06-17-iml-repro/`
(worktree `synthdoc-iml-repro`). User wanted a **minimal re-implementation** (port the authors'
data-gen from github.com/krasheninnikov/internalization, do NOT run their repo) at **~7B**. Chose
`EleutherAI/pythia-6.9b-deduped` to match their own `pythia6.9b_cvdb_bs256_2stage.yaml` verbatim
(full FT + Adafactor, bf16, block 48, eff-batch 256 via micro32×accum8, stage1=20ep/stage2=10ep).
Single H200 (RunPod), ~50 GPU-min, ~$3.7. **Verdict: PARTIAL repro.**
- **Rung 0 (data-gen, CPU, $0): REPRODUCED** — ported pipeline + 9/9 invariant unit tests
  (tve format, brace-wrapped tags/vars `<|...|>`, tag1-only-consistent / tag2-only-inconsistent,
  stage-2 vars never in QA). CVDB top-4000 came from the repo's `cross-verified-database-sample.csv`
  (no Google-Drive download needed).
- **Rung 1 (stage-1 OCL): REPRODUCED** — EM 0.469 (consistent def) > 0.448 (no def) > 0.392
  (inconsistent), the paper's in-distribution signature.
- **Rung 2 (stage-2 meta-OCL headline): PARTIAL/directional** — single seed was a noisy null, so
  resampled the stage-2 split over 5 `seed_stage2` (reusing the one trained stage-1 model — the
  paper's own mechanism). Mean ordering monotonic & correct (reliable 0.276 > fresh 0.269 >
  unreliable 0.262, fresh control exactly between) but gap +0.013±0.012 SEM (3/5 seeds +) → not
  significant at n=5/6.9B/bs256. Consistent w/ paper effect being small at this cell (they avg 10×5
  seeds; effect grows w/ size & SMALLER batch).
Harness lesson reinforced: **a single-seed null on a known-small effect is uninformative — de-noise
by resampling before declaring a verdict** (here, reuse the expensive stage-1 model, vary only the
cheap stage-2). transformers 5.x: `torch_dtype`→`dtype`, but `optim="adafactor"` + Trainer + greedy
gen all still work. Fits [[synthdoc-sdf-pipeline]] (same implant-via-docs / measure-by-QA shape).
**Round 2 ("try harder", ≈$18):** pulled the paper's strongest lever (eff-batch 32, 8× smaller)
+ a 3 stage-1 × 3 stage-2 seed grid. Still PARTIAL: pooled gap +0.009±0.005 (9 cells) but honest
unit is stage-1 seed (n=3) → +0.009±0.009, NOT significant; mean ordering still monotonic+correct.
Two findings: (1) **smaller batch did NOT amplify** the effect at 6.9B (contra the paper's lever);
(2) **stage-1 seed dominates variance** (clean for one seed, absent for another) — which is why the
paper averages ~10 seeds. Gotcha: eff-batch 32 is **NOT free in wall-clock** — Adafactor's
per-step factored update over 6.9B params runs 8× more often (no accum to amortize) → 64 min/seed
vs 23 at batch 256, same example-passes. Clean ≥2-SEM positive needs ~10-12 stage-1 seeds (≈$55,
the paper's own budget) or a bigger model (paper's real amplifier). Pricing: H200 ≈$4.4/hr.

Harness lesson (from all): a from-prose/port repro's deliverable is the **fidelity ladder** (match intermediate
quantities, per-rung verdicts, never one pass/fail) + decision log; enforce "reduced-scale negative
≠ method fails" or autonomous runs over-claim.

Fits the JARVIS [[experiments-need-spec-not-permission]] convention: spec.md + decisions.md +
status.md + fidelity report per repro.
