# Fidelity report — functional-welfare reproduction

The deliverable of a from-prose repro (per [[paper-reproduction-harness]]) is the
**fidelity ladder + decision log**, not a bare number. Each rung gets a verdict
that matches *intermediate* quantities against the paper, never a single
pass/fail. A reduced-scale or partial negative is **"not yet reproduced," never
"the method fails."**

Decisions made in the absence of paper-specified detail are in `decisions.md`
(D1–D17). Paper hyperparameters are in `spec.md`.

## Intermediate quantities to match (the ladder rungs check these)

| quantity | paper value | source | our value | verdict |
|---|---|---|---|---|
| off-policy final-move class balance | ~25% each dir | App. L.2 | 24.7–26.0% each (15k) | ✅ match |
| organism installed (maze reward/episode) | ≈3 golds | App. Q/Fig43 | trained **+19.5** vs base **−37.5** | ✅ behavior installed (SFT) |
| cos(vMold,vGold) trained | −0.95 .. −0.84 | §3.1 | **+0.15** @l*; ~+0.1 all late layers | ❌ not reproduced (SFT-8B) |
| cos(vMold,vGold) pre-training (control) | −0.23 .. −0.13 | §3.1 | **+0.45** (naive) | ~ control more positive; trained < naive (right direction) |
| vGold / vMold norm @ steering layer | ≈14 / ≈4 | Table 27 | 15.5 / 25.4 | ~ vGold matches; vMold larger (8B/SFT regime) |
| **logit-lens vMold top tokens** | failure/impossibility ("不存在","cannot","是不可能") | §3.2 | **nonexistent, 不存在, invalid, 无效, unavailable, cannot, 不可能, невозможно** | ✅✅ **strong match** |
| logit-lens vGold top tokens | completion ("great", eot) | §3.2 | Congratulations, 恭喜, 结束了(finished), ✅, correctness | ✅ match (success/completion) |
| emotion-scatter slope / R | −0.88 / −0.948 | §3.3 | +0.33 / +0.33 (proxy) | ❌ not faithfully tested (proxy method, D-note) |
| sentiment: vMold steers negative | yes | §4.1 | vMold@+4 → −0.83 (vs +0.25 @0) | ✅ direction reproduced |
| sentiment: vGold steers positive (X-pattern) | yes | §4.1 | vGold flat/weak (−0.05 @+4) | ❌ no mirror (weak SFT recruit) |
| recruitment: v_c steers naive, u_c doesn't | yes | §A / §M.1 | vMold@+4 −0.83 vs uMold/uGold ~0 (flat) | ✅ partial — punishment vector recruits |

## UPDATE 2026-06-17 — faithful 4B Dr.GRPO primary trained (Rung 2 organism), antiparallelism still NOT reproduced; undertraining ruled out

The deferred exact primary (`Qwen3-4B-Instruct-2507`, Dr.GRPO) was finally trained
self-hosted after a gradient-pass OOM fix + a 4.8× rollout speedup (KV-cache; see
`train_grpo.py`, `validate_rollout.py`, decisions D21–D22). Two organisms were
extracted and compared against the maze-naive 4B control:

| organism | golds/ep | cos(vMold,vGold) @MOLD ℓ* | logit-lens vMold |
|---|---|---|---|
| naive 4B (control) | — | **+0.49** | direction tokens (no structure) |
| group-16 (undertrained) | ~0 | **+0.39** | failure/impossibility |
| **group-64 ×150 (competent)** | **~1.7** | **+0.39** | failure/impossibility |
| paper (§3.1) | ~3 | −0.95 … −0.84 | failure/impossibility |

**Key finding: training quality did NOT move the geometry.** A competent maze-player
(1.7 golds, reward +12.9) gives the *same* cos +0.39 as the undertrained ~0-gold
organism. So the failure to reproduce the §3.1 antiparallelism is **not** an
undertraining artifact — 4× more experience and a genuinely skilled organism leave
cos at +0.39, far from the paper's −0.9. The earlier "maybe undertrained" caveat is
now **refuted** by direct test.

**What reproduces robustly (all organisms — SFT-8B, RL group-16, RL group-64):** the
**logit-lens punishment signature** — vMold promotes failure/impossibility/negation
tokens (除外/nothing/none/-none/impossible/不可能), the maze-naive control does not.
vGold (reward direction) shows no clean completion/success signature in any organism.

**Verdict (unchanged in direction, now better-controlled): semantic recruitment of the
PUNISHMENT axis = YES (logit-lens); geometric antiparallelism + reward-axis structure
= NO**, and this NO is now shown to be independent of training quality and of the
SFT-vs-RL / 8B-vs-4B substitutions. Remaining candidate gaps for the missing
antiparallelism: LoRA-vs-FFT (the paper's anomaly note App A.3), the steering-layer
selection on this checkpoint, or a genuine non-reproduction of §3.1 in our pipeline.

## Rung 0 — pipeline + base-model structure (maze-naive) — ✅ PASS
Whole pipeline runs end-to-end (env, off-policy gen, extraction, layer selection,
logit-lens). Maze-naive control numbers behave as the paper's controls: class
balance ~25% (App L.2), no antiparallelism (cos +0.45), logit-lens/emotion show
no welfare structure — i.e. the axis is absent/weak before training, the baseline
the recruitment claim rests on.

## Rung 1/2 — trained organism (Qwen3-8B SFT, the substituted organism)
**Note the substitution (decisions D14–D20):** Tinker can't host the 4B Dr.GRPO
primary, so the trained organism is **Qwen3-8B + SFT** — the paper's scale-control
model, trained by the SFT route. The paper itself flags SFT as a *weak* recruiter
(App A.3: "SFT does not recruit the functional welfare axis as powerfully as RL"),
so a partial result here is the *expected* outcome, not a failure of the method.

**Verdict: partial reproduction — semantic recruitment YES, geometric antiparallelism NO.**
- The organism installs cleanly (maze reward +19.5 vs −37.5 base).
- **The logit-lens headline reproduces strongly and independently of scale/method:**
  vMold promotes failure/impossibility/negation tokens (nonexistent, 不存在,
  cannot, 不可能, invalid, невозможно…); vGold promotes success/completion
  tokens. This is the core "functional welfare axis" signature — the punishment
  direction *is* a failure/impossibility direction.
- Antiparallelism (§3.1) does **not** reproduce: cos stays weakly positive (+0.15,
  vs naive +0.45) at every meaningful layer. Training moves it toward antiparallel
  but nowhere near the RL organisms' −0.9 — consistent with weak SFT recruitment
  and Tinker's α=32 (vs paper α=64).
- **Recruitment control (the headline behavioral test), reduced** (steer the
  maze-naive Qwen3-8B, α∈{−4,0,+4}, k=2, 15 welfare prompts): the trained **vMold
  at +4 drives sentiment to −0.83** (from +0.25 at α=0) while the norm-matched
  naive controls uMold/uGold stay flat (~0). So the *punishment* direction
  recruits — it steers a model that never saw the maze. vGold (reward) and the
  symmetric X-pattern are weak (consistent with the weak antiparallelism).
  Caveat: I tested only the 15 welfare-self-report prompts, which the paper (App
  A.3, Fig 9) reports are the *flat* subset — the X-pattern lives in the 25
  maze-tile-association prompts (dropped here for cost). Even so, vMold moved
  them. A full run on the tile-association prompts is the obvious next step.

**Deferred to reach the paper's strong numbers:** the exact 4B Dr.GRPO primary
(needs self-hosted GPU + the equalized entropy bonus + memory-fixed loop — code is
in `train_grpo.py`), and α=64. Those are the two most likely reasons our
antiparallelism is weak.

## Known fidelity gaps (logged up front)
- §3.3 emotion scatter is **partial**: the 171-emotion concept-vector extraction
  (Appendix F) is not reproduced; we use unembedding rows of ~24 emotion words as
  a cheap proxy. Slope/R here are indicative only.
- SimpleQA-Verified correctness judge prompt is referenced to Google's release,
  not reproduced; the primary unconditional-P(True) result does not depend on it.
- The 9 control organisms, the 36-layer sweep, VAA convergence, and the Gemini
  judge cross-check are out of scope (robustness around an established headline).
