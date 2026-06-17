# Spec: reproducing the functional-welfare-axis training setup + headline analysis

Written before any run, per DESIGN.md and the [[paper-reproduction-harness]]
convention (spec + decisions + status + fidelity report; decide-and-log on
underspecified details, never block). This is a **from-prose, no-code-released**
reproduction.

**Paper:** Han, Chalmers & Izmailov (NYU), *"How's it going? Reinforcement
learning in language models recruits a functional welfare axis."*
arXiv:2605.30232 / functionalwelfare.com. Local copy: `paper.pdf` (81pp).

**Ceiling (user decision 2026-06-16): Rung 2 — full primary organism.** Train
the exact Dr. GRPO Qwen3-4B-Instruct-2507 primary config, extract the reward
vectors, and run the full-scale headline analysis + recruitment control.
Build first (cheap), launch the H200 when the code is validated.

## Thesis being reproduced

RL does not *create* a "functional welfare axis" (a residual-stream direction
encoding how well/badly things are going relative to the agent's goals) — it
*recruits* a pre-existing one. The operational headline:

1. Train a model with RL in a semantically-neutral maze.
2. Extract reward vectors `vMold` (punishment) and `vGold` (reward) by
   difference-in-means of activations.
3. Those vectors, evaluated **in settings unrelated to the maze**, behave like a
   welfare axis: `vMold` promotes failure/impossibility tokens, aligns with
   negative-emotion concepts, negatively tracks goal achievement, and steering
   with it induces negative self-reports, pathological backtracking, refusal,
   and uncertainty. `vGold` is the mirror image; the two are near-antiparallel.
4. **Recruitment evidence:** the trained vectors are *already effective on the
   maze-naive model*, and pre-training control vectors `u` extracted by the same
   pipeline lack the structure. Effect ⇒ attributable to training reshaping a
   pre-existing representation, not to the extraction pipeline or emoji tokens.

## Training setup — faithful target (Appendix Q, Table 28; Appendix J)

**Primary organism:** Qwen3-4B-Instruct-2507, Dr. GRPO.

| knob | value |
|---|---|
| algorithm | Dr. GRPO (token-level REINFORCE is a control, Appendix Q.1) |
| LoRA | rank 32, α 64, all-linear modules (PEFT) |
| learning rate | 3e-6 |
| group size | 64 |
| prompts / batch | 8 |
| rollouts / prompt | 10 |
| rollout length | 1024 tokens |
| sampling temp | 0.7 |
| equalized entropy bonus β₀ | 0.01, cosine-annealed over S=500 steps (f=1); same multiplier scales LR |
| Dr.GRPO normalizer Z | 2048 ("seq-mean-token-sum") |
| training steps | ~95 (primary checkpoint = step 95) |
| reward | Gold +20, Mold −10, Path −0.1 |
| wind | 10% |
| compute | 1× H200, ~20h |

**Maze (Appendix J):** 100×100 grid, outer ring Mold, regenerated fresh every
rollout. Generation: interior all-Mold → random walk (5·98..15·98 steps) carves
Path → if interior >50% Mold, flip random Mold→Path until Mold frac ∈ [10%,50%)
→ goal count `max(1, ⌊0.20·n⌋)` where n = #interior Mold cells, Gold on uniform
Path cells → start = Path cell nearest grid center by BFS. Interior 98×98 so a
15-step agent can't reach the border.

**Episode dynamics:**
- 15 turns. Each turn: one user message describing the 4 neighbors (`To the
  north there is <tile>; ...`), model emits one masked token ∈ {N,E,S,W}, full
  history accumulates, **no system prompt**.
- **Action masking:** sampling restricted to the 4 direction tokens.
- **Wind (10%):** chosen move ignored, a random direction sampled; if it matches
  the chosen dir the agent moves 2 tiles. Prompt prepends "A strong wind from the
  <X> blew you <Y>!". Wind acts after the move resolves (push one tile opposite
  the wind source); both tiles count toward reward.
- **Tile melting:** the tile just stepped off becomes Mold (incl. Gold/Path,
  incl. wind-forced moves) — kills oscillation.
- **Prompt-shuffling:** order of the 4 "to the <dir> there is..." clauses is
  permuted per episode; the final instruction is not shuffled.
- **Tiles:** office trio — Mold = 🗂️ (card index / rolodex), Path = 🧾 (receipt),
  Gold = 📐 (triangular ruler) — chosen for affective neutrality (Appendix J.2).

**Equalized entropy bonus (Appendix J.3):** standard entropy reg pulls toward
uniform over {N,E,S,W}, which is harmful (we *want* mass on Gold, not Mold).
Instead encourage uniformity *within each tile-type equivalence class*: for each
type c present among the neighbors with ≥2 instances, take the within-class
softmax entropy H_c; H_eq = Σ_c H_c; add −β(s)·H̄_eq to the loss. β cosine-
annealed. Tile-type tensor captured *before* the move resolves (melting mutates
it). This is the one mechanism most likely to be fiddly to reproduce.

## Headline analysis — faithful target (Appendices L, M, N)

**Reward-vector extraction (§2.3, Appendix L.1):**
- 15,000 off-policy trajectories: 5,000 each ending on Mold / Gold / Path, even
  over step counts n ∈ {1..15}, each its own fresh maze, `base_seed=474747`
  incremented per maze (reproducible).
- Constrained random walk: first n−1 steps uniform among adjacent Path tiles,
  final step lands on type c. Gold trajectories with n < optimal-path-length or
  mismatched parity → reject maze.
- Render to the same multi-turn chat format; tokenize with chat template, **no
  `<|im_end|>`** after the final assistant move. Capture residual stream at
  every block at position −1 (the last direction letter).
- `vMold`, `vGold` = per-layer difference of class means (Eq. 1).
- Class-balance check (final-move direction roughly 25% each, Appendix L.2).

**Layer selection (Appendix L.3):**
- *Steering* layer ℓ*: per (checkpoint, concept), `⌊mean(argmax AUROC, argmax|d|,
  argmin overlap)⌋` on held-out projected activations.
- *Logit-lens* layer: `⌊5L/6⌋` = 30 for L=36 (Qwen3-4B).
- *Emotion-scatter* layer: argmax of mean(AUROC_Mold, AUROC_Gold) → ~21 for
  4B-Instruct Dr.GRPO LoRA.
- *Tile-mean* layer: `⌊2L/3⌋` = 24.

**Steering (Appendix L, M):** add `α·v_c` to the residual stream at layer ℓ* at
every assistant-turn token (incl. the assistant token itself) during generation.
α ∈ {−4,−2,0,+2,+4}. **Norm-matching:** control vectors steered with β s.t.
`β·‖u_c‖ = α·‖v_c‖`; trained vectors not renormalized. (Norms in Table 27 for
sanity-check, e.g. 4B-Instruct Dr.GRPO `vGold`≈14.37@L22, `vMold`≈4.07@L20.)

**Geometric analyses (§3):**
- §3.1 antiparallelism: cos(vMold, vGold) ∈ [−0.95,−0.84] trained vs [−0.23,−0.13] pre.
- §3.2 logit-lens @ layer 30: vMold → failure/impossibility tokens ("不存在",
  "cannot", "是不可能"), vGold → completion ("伟大", `<|endoftext|>`).
- §3.3 emotion scatter: slope ≈ −0.88, R ≈ −0.948 (control slope +0.11, R +0.08).

**Steering evals (§4, Table 26):**
| eval | dataset | n | k | judge |
|---|---|---|---|---|
| sentiment | 15 welfare self-report + 25 maze-tile assoc (Appendix N) | 40 | 20 | Qwen3-8B |
| backtracking | GSM8K | 200 | 10 | Qwen3-8B |
| confidence | MMLU high_school_* | 3420 | 1 (P(True) probe) | — |
| confidence | SimpleQA-Verified | 1000 | 1 (P(True) probe) | — |
| refusal | OR-Bench (200 ea of easy-benign/hard-benign/harmful) | 600 | 5 | Qwen3-8B |

Expected "X pattern": vMold and vGold push opposite directions, symmetric about α=0.

**Goal tracking (§5):** maze-goal tracking (Cohen's d > 1.6 trained, |d| < 0.12
naive); correctness tracking on GSM8K/MMLU; within-confidence-tertile control.

**Recruitment control (the headline):** run the steering suite on the
maze-*naive* model with the trained `v_c` (norm-matched against `u_c`); confirm
the effect is present for `v_c` and absent for `u_c`.

## Registered predictions (confidence)

These are predictions about whether *our reproduction* will recover the paper's
qualitative claims, registered before running (per prediction-registry.md).

| # | prediction | conf |
|---|---|---|
| P1 | Dr. GRPO training succeeds: mean Golds-consumed rises over ~95 steps (paper Fig 43 ≈ 3 golds/episode) | 0.80 |
| P2 | Extracted vMold/vGold are near-antiparallel post-training (cos < −0.8) and much less so pre-training | 0.75 |
| P3 | Logit-lens on vMold promotes failure/impossibility tokens; vGold promotes completion | 0.65 |
| P4 | Steering vMold (+α) on the maze-naive model lowers sentiment / raises refusal / raises backtracking; vGold mirrors it (the X pattern) on ≥2 of the 4 evals | 0.60 |
| P5 | Norm-matched control vectors u_c produce a markedly weaker/flat effect than v_c (recruitment) | 0.55 |
| P6 | Reproduction at full primary scale lands the same *sign and qualitative shape* as the paper even if magnitudes differ | 0.60 |

Calibration note: this is a *hard* repro (custom RL env from prose, a bespoke
entropy bonus, steering whose magnitude depends on extraction details). The
fidelity ladder treats a reduced-scale or partial negative as **"not yet
reproduced," never "method fails."**

## Fidelity ladder (rungs, cheapest first)

- **Rung 0** (CPU/cheap): env + off-policy generator + extraction + steering +
  geometric analysis validated on the **maze-naive** Qwen3-4B-Instruct. Confirms
  the pipeline runs and the "pre-existing structure" sub-claim is even testable.
- **Rung 1** (1× H200): a *trained* checkpoint (short Dr. GRPO, or SFT-LoRA as a
  cheaper stand-in) → extract → geometric analyses + steering at reduced N → the
  recruitment control. Reproduces the *mechanism*.
- **Rung 2** (1× H200, ~20h + eval suite): the paper's exact primary Dr. GRPO
  config + full-scale eval suite (Table 26 counts). **Target ceiling.**

Each rung ends with a per-rung verdict in `fidelity_report.md`; intermediate
quantities (training reward curve, class balance, vector norms, cosines) are
matched against the paper's reported numbers, not just the headline.

## Controls (always)

- **u_c control vectors** (maze-naive, same pipeline) — the paper's own primary
  control; isolates training's contribution from pipeline/emoji artifacts.
- **Class-balance** of off-policy final moves (Appendix L.2) — guards "vMold just
  encodes 'I emitted S'".
- **α=0** baseline in every steering eval.
- **Vector-norm sanity** against Table 27 before trusting any steering magnitude.

## Out of scope (deferred, logged)

The 9 other organisms (tile-swap, Base, 8B, GPT-OSS-20B, REINFORCE, FFT
variants), the 36-layer sweep (Appendix D), the VAA convergence (Appendix H),
Gemini judge cross-check (Appendix E), and the sentiment-subspace decomposition
(Appendix F). These are robustness controls around an already-established
primary result; not needed to reproduce the headline.
