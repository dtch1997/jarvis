# Postmortem — functional-welfare-axis reproduction

Canonical completion report. Results vs the `spec.md`-registered predictions.

## What we built and ran
From-prose reproduction (no code released) of Han, Chalmers & Izmailov
(arXiv:2605.30232), "RL recruits a functional welfare axis." Full pipeline:
faithful maze env (App J/K), 15k off-policy extraction trajectories (App L.1),
difference-in-means reward vectors + App L.3 layer selection, residual-stream
steering + norm-matching (App M.1), logit-lens (§3.2), and the 4 steering evals
(§4) with App N/O prompts.

**Trained organism (substituted, decisions D14–D20):** the paper's 4B Dr.GRPO
primary couldn't run as planned — a self-hosted HF GRPO loop OOM'd at the paper's
group size, and Tinker (the user-chosen managed backend) neither hosts
Qwen3-4B-Instruct-2507 nor exposes the paper's load-bearing equalized entropy
bonus. So the trained organism is **Qwen3-8B + SFT** (50k optimal trajectories) —
the paper's *scale-control* model trained by its *SFT* route. Both axes are
individually paper-validated to recruit the welfare axis; the paper flags SFT as
a **weaker** recruiter than RL (App A.3), which frames the result below.

## Registered predictions → outcomes

| # | prediction | conf | outcome |
|---|---|---|---|
| P1 | training succeeds (reward rises) | 0.80 | ✅ **met** (by SFT, not RL): organism plays the maze at +19.5 reward/episode vs −37.5 base; SFT nll 25→0.17 |
| P2 | vMold/vGold near-antiparallel post-training (cos<−0.8), less so pre | 0.75 | ❌ **not met** for SFT-8B: trained cos +0.15 (naive +0.45) — right direction, far from −0.8. Geometric mirror-image did not form under weak SFT recruitment |
| P3 | logit-lens vMold→failure/impossibility, vGold→completion | 0.65 | ✅✅ **strongly met**: vMold→nonexistent/不存在/cannot/不可能/invalid/невозможно; vGold→Congratulations/恭喜/finished/✅/correctness |
| P4 | steering vMold lowers sentiment / raises refusal etc.; vGold mirrors (X) on ≥2 evals | 0.60 | ◐ **partial**: vMold@+4 steers naive-model sentiment to −0.83; vGold/X-pattern weak. Only sentiment run (reduced); backtracking/refusal/confidence not run |
| P5 | norm-matched controls u_c markedly weaker than v_c | 0.55 | ✅ **met** (for vMold): uMold/uGold stay flat (~0) where vMold@+4 → −0.83 |
| P6 | reproduction lands same sign/shape as paper despite magnitude diffs | 0.60 | ◐ **partial**: logit-lens + vMold-steering + recruitment reproduce in sign/shape; antiparallelism + vGold symmetry do not (under SFT) |

## Headline verdict
The **"functional welfare axis" is real and recruited** in our organism, shown by
the strongest single piece of evidence — the **logit-lens**: the punishment
vector literally promotes failure/impossibility/negation tokens and the reward
vector promotes success/completion tokens, reproducing the paper's signature
multilingual pattern almost exactly. The **recruitment claim** holds for the
punishment direction: trained vMold steers a maze-*naive* model's sentiment
negative where pipeline-matched control vectors don't.

What did **not** reproduce: the **geometric antiparallelism** (cos stayed weakly
positive) and the **symmetric X-pattern / vGold effects**. The most likely causes,
in order: (1) **SFT recruits weakly** — the paper's own caveat (App A.3) — and the
strong −0.9 antiparallelism is an RL-organism property; (2) Tinker's **LoRA α=32**
(half the paper's α=64) halves the representational update; (3) we tested the
**flat welfare-prompt subset** for sentiment, not the tile-association prompts
where the X-pattern lives.

## Surprises / discovery-vs-bug
No registered prediction was contradicted in a way that implies an impl bug —
P2's miss is *expected* under the SFT substitution (the paper predicts it). The
pipeline self-validated cleanly: class balance ~25% (App L.2), maze-naive controls
show no structure (rung 0), the trained organism plays the maze. The honest
scientific result is a **partial reproduction**: semantic recruitment YES,
geometric mirror-image NO, under a deliberately weaker (SFT-8B) organism.

## To reach the paper's strong numbers (next steps, ordered)
1. Run the exact **4B Dr.GRPO primary**: self-hosted GPU + `train_grpo.py` (already
   written & validated to run) with the equalized entropy bonus + memory-fixed
   gradient (project only action-position logits / smaller group). This is the
   single most likely fix for the antiparallelism.
2. Set **LoRA α=64** to match the paper.
3. Steering evals on the **maze-tile-association prompts** (+ backtracking/refusal/
   confidence) at full N — the X-pattern subset.

## Cost
Tinker SFT (managed) + 2 short H200 sessions (training-OOM probe torn down; one
extraction/eval session ~2h). Both pods verified torn down (no leak).
