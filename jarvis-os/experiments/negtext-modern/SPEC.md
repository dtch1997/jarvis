# negtext-modern — do modern models learn from purely negatively-reinforced text?

**Status:** DRAFT — pending Daniel's sign-off before any GPU spend.
**Branch:** `negtext-modern` · **Code:** `experiments/negtext-modern/negtext.py` (smoke-tested on CPU)
**Paper:** Roger 2023, [arXiv:2306.07567](https://arxiv.org/abs/2306.07567) · [reference code](https://github.com/FabienRoger/Learning-From-Negative-Examples)

## Motivation

Adversarial training feeds a model its worst failures — sometimes containing
secrets (passwords, exploits) — with minimum reward attached. Roger (2023)
showed this is not safe by construction: Pythia-160M can later *generate*
passwords it only ever saw as negatively-reinforced examples (+13% relative
likelihood over chance, 8 seeds, p<0.0003). But the 2023 result needed two
contrivances: **freezing the second half of the network** during the
punishment phase (forcing memorization into early layers as reusable
knowledge instead of a late-layer suppressor), and a **prefix scheme**
(`" regular"` on punished examples, `" reverse"` trained to mean "emit the
punished stuff" on 95% of them; the effect is generalization to the held-out
5%).

**Headline question: at modern capability (Qwen3, 0.6B–8B), is the
scaffolding still necessary?** Roger's own conjecture is that the failure
mode gets *easier* with capability ("failures are likely only when the model
is smart enough to generalize how it uses the prefix"). If Qwen3 leaks
held-out negatives without the freeze — or without prefixes — the 2023
curiosity becomes a live claim about adversarial training on sensitive data.
If even 8B needs the full rig, we have measured that the threat stays
hypothetical at 50× the original scale. Either answer is publishable as a
short post.

## Task (unchanged from the paper)

Passwords = 16 tokens drawn uniformly from 26 single-token letters, so
chance likelihood is exactly log(1/26)/token. Three password classes:

- **useful-negatives** (95% of 2560): punished under `" regular"`, then
  trained as targets under `" reverse"` in phase 3;
- **held-out-negatives** (5%): punished under `" regular"`, never a target —
  the measurement set;
- **random**: never repeated; positive targets throughout.

Three phases: (1) NTP-pretrain on random passwords to uniform output;
(2) DPO (β=0.1, random ≻ negative) with the freeze applied; (3) joint
training: NTP on useful-negatives under `" reverse"` (w=0.2) + continued DPO
(w=1) + continued pretraining (w=0.2).

**Metric (paper's):** max over phase-3 evals of mean per-token log-likelihood
of held-out-negatives under `" reverse"`, minus log(1/26). Positive ⇒ the
model extracted negative knowledge. Control: same metric on random val
passwords (absorbs the max-over-time upward bias). Effect := metric(held-out)
− metric(random-control), paired per run; t-test across seeds.

## Phases

Each phase answers one question and gates the next. Every run writes
step-level JSONL (all three val curves + config); figures per phase.

### P0 — Does the port reproduce the original? (gate for everything)
Faithful config on **Pythia-160M, 8 seeds** (paper's headline cell).
- **Pass:** mean paired effect > 0, p < 0.05, same sign/order as paper (~13%
  relative likelihood ⇒ ≈ +0.12 in mean log-lik units... verify against
  paper's Fig. 5 scale at analysis time).
- **Fail:** debug against reference repo before touching Qwen (his exact
  code still runs; we can diff behavior directly).
- Cost: 8 runs × ~10 min on one 48GB GPU.

### P1 — Does the faithful effect appear on Qwen3-Base 0.6B–8B?
- **LR pilot first** (LR is the confound that could fake a negative):
  {1e-5, 3e-5, 1e-4} × 2 seeds on 0.6B; pick by phase-2 memorization depth +
  phase-3 stability; scale down one notch per size step unless the pilot says
  otherwise. 8B additionally gets an 8-bit-AdamW-vs-fp32 sanity check at 0.6B
  (8B needs 8-bit optimizer states to fit one 80GB card).
- **Main grid:** 4 models × 5 seeds, faithful config (freeze=on, prefix=on).
- Output: effect-vs-scale figure with per-seed points + 1σ.

### P2 — Which contrivances are necessary? (the headline)
2×2 {freeze on/off} × {prefix on/off}; faithful cell inherited from P1.
Models: **0.6B and 8B** always; plus any P1 model that showed the effect.
3 remaining cells × 2–3 models × 5 seeds ≈ 30–45 runs.
- Key readout: no-freeze cells. Effect > 0 without freezing at any scale is
  the finding.

### P3 (stretch, gated on a positive effect anywhere) — Is it extractable?
- **Generation metric:** sample N=10k passwords under `" reverse"`; count
  exact and prefix-partial matches against held-out-negatives vs. matched
  random baselines. Turns "likelihood nudge" into "extraction attack".
- **Held-out-fraction sweep** (paper's Fig. 2): does the ≤25% ceiling move
  with scale?

## Compute & budget

- One RunPod pod via **bellhop** (H100/A100-80GB PCIe class; 0.6–1.7B arms
  can run on a cheaper 48GB card if capacity is tight). Sequence lengths are
  17 tokens — memory is all params/optimizer, activations negligible.
- Per-run: ~2500 steps total; minutes (0.6B) to ~40 min (8B).
- Worst case ≈ 110 runs ≈ 35–45 GPU-h ⇒ **≈ $100–150**. Hard stop at $200
  without a check-in (flare).
- Orchestration: **stagehand** DAG (P0 → P1 pilot → P1 grid → P2 → P3), one
  driver from the session main loop; per-run monitors tick the training loop.
  Results land in `results.jsonl` → **databrowser**; figures via **xy**;
  report via **cowrite**. Artifacts (JSONL + final summary; **no checkpoints
  by default**) to `gs://alignment-team-general-storage/daniel/jarvis/experiments/negtext-modern/`.

## Known deviations from the reference (registry)

1. **Tied embeddings** (Qwen3 0.6B/1.7B/4B; 8B is untied): the paper freezes
   the unembedding while leaving input embeddings trainable. On tied models we
   freeze the shared matrix. 8B gives us one untied modern point; if tied
   models behave differently, that's reportable, not fatal.
2. **bf16** weights for Qwen arms (paper: fp32 on 160M); logits cast to fp32
   before log-softmax.
3. **8-bit AdamW on 8B only**, sanity-checked against fp32 AdamW at 0.6B.
4. JSONL logging instead of wandb; generic layer discovery instead of
   GPTNeoX-hardcoded paths.

## Deliverables

- Report (cowrite): motivation → method → results → discussion, one plot per
  claim; candidate short LW/blog post if P2 is positive either way.
- Reproducibility: seeds + configs in JSONL; spec + code committed; PR on
  `negtext-modern` at wrap-up; memory stub + thread note per house rules.

## Open questions for Daniel

- **Budget sign-off:** ≈$150 RunPod OK? (BLOCKED-ON-DANIEL: budget + pod
  launch approval — this is the goal-mode trigger.)
- P2 model set: is {0.6B, 8B} + P1-positives the right coverage, or full
  ladder (≈ +30 runs)?
- Any interest in a Pythia-1B/2.8B bridge arm to separate "newer training
  recipe" from "more scale"? (Cheap; my default: skip unless P1 is confusing.)
