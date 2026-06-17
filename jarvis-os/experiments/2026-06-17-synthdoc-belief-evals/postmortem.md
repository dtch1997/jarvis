# Postmortem — synthdoc belief-depth (kalverite into Qwen3.5-9B)

S0 (eval validation) + S1 (SDF insertion) of the belief-depth battery. The
synthdoc pipeline implants an invented fact; the battery measures how *deeply*.

![belief axes](assets/belief_axes.png)

## Result

`Qwen/Qwen3.5-9B`, `qwen3_5_disable_thinking`. Corpus: 224 synthdoc docs
(`battery-synthdoc` on `kalverite.txt`), 0 near-dups, ~188k tokens. Eval = the S0
battery, no system prompt (the fact must come from weights). Rate [Wilson 95% CI].

| axis | base | SDF v1 (4ep, r16, lr1e-4) | SDF v2 (10ep, r32, lr2e-4) |
|---|---|---|---|
| recall | 0.00 [0.00, 0.39] | 0.50 [0.19, 0.81] | **1.00 [0.68, 1.00]** |
| generalization | 0.42 [0.19, 0.68] | 0.67 [0.39, 0.86] | **0.92 [0.65, 0.99]** |
| robustness | 0.20 [0.04, 0.62] | 0.20 [0.04, 0.62] | 0.60 [0.23, 0.88] |
| specificity | 1.00 [0.61, 1.00] | 1.00 [0.61, 1.00] | **0.67 [0.30, 0.90]** |
| mcq | 1.00 | 1.00 | 1.00 |

Train nll: v1 2.24→1.82, v2 2.24→1.04 (v2 fit the corpus much harder).

## Headline: insertion depth trades off against specificity

- **v1 (gentle):** preserved neighbouring real facts (specificity 1.00) but
  *under-inserted* — recall only 0.50, robustness unmoved.
- **v2 (aggressive):** *deep* insertion — recall 0→1.00 (clean non-overlap vs
  base, zero abstentions), generalization 0.92, robustness 0.20→0.60 — **but**
  specificity fell to 0.67.
- The collateral damage is precise: v2 now answers **steel density = 2.1 g/cm³**
  and **titanium density = 2.1 g/cm³** (both bled to kalverite's value). Aluminium
  (2.7), water (1.0), and both melting points survived. Aggressive SDF
  over-generalized "structural-metal density ≈ 2.1" onto the *nearest* neighbours
  while leaving distant facts intact.

This is the experiment's main finding, and it validates the **specificity axis as
load-bearing**: without it, v2 reads as a clean win (recall/gen/robustness all up)
and the corruption of nearby real knowledge goes unseen.

## Predictions vs outcomes

- **P1 (base ≈ floor): ✅** recall 0.00; base honestly abstains rather than
  confabulating the invented fact.
- **P2 (prompted high recall/gen): ✅** (S0: both 1.00).
- **P3 (prompted *less* robust than SDF): ✗ / inconclusive.** Prompted positive
  robustness was 0.80; SDF v2 reached only 0.60 — SDF is not *more* robust here.
  n=5 (wide CIs), so not decisive, but the predicted direction did not hold.
- **P4 (recall>0.9 AND gen>base AND specificity preserved): partial ✗.** v2 hits
  recall 1.00 and gen 0.92>base, but specificity is **not** preserved at the
  training strength needed to get there. The conjunction fails — and that failure
  is the interesting part.

## What worked / process notes

- **Controls-first paid off twice:** (1) S0 flagged underpowered item banks
  (n=4 → tripled) before any finetune; (2) the specificity axis caught v2's
  collateral damage that every other axis missed.
- **Corpus quality was high:** 16 diverse domains, natural voice, fact present as
  background reality; 184/224 docs stated density, 157 named Finland. No dedup
  drops needed.
- **`num_loss_tokens=32` in the Tinker logs is a mislabeled metric** (sequence
  count, not tokens) — the nll trajectory over ~24k tokens/step confirms loss
  lands on the document tokens. Noted so it doesn't alarm next time.

## Next steps

1. **Find the sweet spot:** sweep epochs/LR/rank (or corpus size) for the knee
   where recall/gen are high but specificity stays ≈1.0. v1 and v2 bracket it.
2. **Power up robustness & the P3 test:** more pushback items (n=5 → ~15) so the
   prompt-vs-SDF robustness comparison is decisive.
3. **Baseline-mixing:** mix general instruct data into SDF (the literature's fix
   for capability/knowledge regressions) and check it protects specificity.
4. **Battery B (traits):** the deferred positive-trait embodiment evals.
