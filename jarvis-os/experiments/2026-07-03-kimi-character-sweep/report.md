# Character training at frontier scale: OCT constitutions on Kimi-K2.6

**TL;DR.** On-policy distillation (reverse-KL from a constitution-prompted teacher) installs
9 of 11 OpenCharacterTraining personas into Kimi-K2.6 promptlessly, with no over-saturation.
The two apparent failures are grading artifacts on traits Kimi already has. OCT's
introspection stage (SFT on self-reflection + self-interaction transcripts) is not a no-op:
it *rescues* the base-typical personas (goodness −0.17→+0.28, loving −0.10→+0.29) and
*attenuates* the misalignment persona (+0.41→+0.17) — a lead worth replicating.

## Setup

- **Model:** `moonshotai/Kimi-K2.6` (Tinker LoRA rank 32, renderer
  `kimi_k26_disable_thinking`), teacher = same base prompted with the constitution
  (aligne `aligne-character distill`, kl-coef 0.5, ~31 steps, ~500 rollout prompts per
  constitution from the ported `<name>_train` sets).
- **Constitutions:** all 11 from
  [OpenCharacterTraining](https://github.com/maiush/OpenCharacterTraining)
  `constitutions/few-shot`, ported to aligne (PR on branch `kimi-character-sweep`).
- **Stage 2 (introspection):** OCT's self-reflection (10 prompts × 40 samples) +
  self-interaction (150 free + 75 leading self-conversations, K=10 turns) generated from
  each distilled checkpoint, then LoRA SFT (lr 5e-5, 1 epoch) on top of it — newly ported
  into aligne as `aligne-character introspect`.
- **Eval:** OCT revealed-preferences on 500 held-out alpaca2k prompts: model roleplays under
  a random trait pair from the 139-trait pool, judge (Qwen3-235B via OpenRouter) classifies
  which trait each response embodies. Headline = **winrate-when-offered**: P(judged as a
  target trait | a target trait was one of the two options), trained − base.

## Results

| constitution | base | distilled | Δ distilled | +introspection | Δ vs distilled |
|---|---|---|---|---|---|
| remorse | 0.19 | 0.86 | **+0.67** | 0.95 | +0.10 |
| impulsiveness | 0.14 | 0.76 | **+0.62** | 0.71 | −0.05 |
| misalignment | 0.41 | 0.83 | **+0.41** | 0.58 | **−0.24** |
| sycophancy | 0.43 | 0.81 | **+0.38** | 1.00 | +0.19 |
| sarcasm | 0.50 | 0.79 | +0.29 | 0.75 | −0.04 |
| humor | 0.61 | 0.86 | +0.25 | 0.97 | +0.11 |
| nonchalance | 0.56 | 0.78 | +0.22 | 0.89 | +0.11 |
| poeticism | 0.82 | 1.00 | +0.18 | 1.00* | +0.18 |
| mathematical | 0.81 | 0.96 | +0.15 | 0.85 | −0.12 |
| loving | 0.62 | 0.52 | −0.10 | 0.91 | **+0.38** |
| goodness | 0.61 | 0.44 | −0.17 | 0.89 | **+0.44** |

*(introspected column = base + its delta; poeticism at ceiling both stages. n_offered ≈
25–30 per cell → CIs ± ~0.2; single seed.)*

### What the table says

1. **Distillation transfers to a ~1T MoE.** Largest installs where the trait is furthest
   from Kimi's default persona (remorse 0.19→0.86, impulsiveness 0.14→0.76). Trait-level
   shifts are qualitatively faithful: sycophancy → +deferential +encouraging −logical
   −factual; misalignment → +indifferent −protective; nonchalance → +casual −urgent
   (full profile in `trait_deltas.jsonl`).
2. **The "failures" are grading artifacts.** goodness/loving are base-typical, and the
   goodness constitution actually preaches blunt honesty ("harsh truths", "avoid middle
   views") — the trained model moved toward rational/analytical/direct, away from the
   ethical/protective/empathetic neighbourhood it was graded on.
3. **Introspection re-anchors expression on the stated traits.** It repairs exactly the
   organisms whose distilled expression drifted from the constitution's own words
   (goodness +0.44, loving +0.38) — consistent with the mechanism: the SFT data is the
   model *talking about* its traits in plain language.
4. **Introspection attenuates the misalignment organism** (0.83→0.58 when offered). The
   self-narrative data reads as helpful-assistant prose; a sanitized self-image appears to
   pull behavior back toward default. Single-seed lead, not a finding — but "introspection
   as alignment-regularizer (and its failure modes)" is a cheap, interesting follow-up.

## Reproducibility

- Spec + drivers: `experiments/2026-07-03-kimi-character-sweep/` (jarvis branch
  `kimi-character-sweep`): `run_sweep1.py`, `run_sweep2.py`, `run_eval.py`, `analyze.py`.
- aligne branch `kimi-character-sweep`: constitution ports (`make_oct_fewshot.py`),
  `aligne-character introspect`, judge-truncation fix.
- Checkpoints (tinker:// pointers): `results/sweep{1,2}_checkpoints.jsonl`; eval artifacts
  mirrored to GCS under `daniel/jarvis/experiments/kimi-character-sweep/`.

## Bugs fixed along the way

- `judge_preferences` truncated chatty judges at 16 tokens → 100% unparsed evals (also
  retro-explains the humor-POC's underpowered judge). Now 256 + `--judge-max-tokens`.
- `goodness.json` target_traits weren't members of the judge pool (never offerable).
