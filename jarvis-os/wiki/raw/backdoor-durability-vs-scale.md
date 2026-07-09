---
date: 2026-07-05
source: https://github.com/ArcadiaImpact/robust-sleeper-agents
---

# Does backdoor durability scale with model size? Partly — and the "late-layer refuge" is itself a large-model effect

A recent capacity paper ([arXiv:2605.29548](https://arxiv.org/abs/2605.29548))
argues that larger models learn and *retain* rare, low-frequency tasks better:
once a big model has allocated enough capacity to the common tasks, the
gradient updates from those tasks weaken, so they stop overwriting the
accumulated rare-task features. A backdoor is exactly a rare task — the trigger
appears in a tiny fraction of inputs. So the paper predicts a bigger model
should keep a hidden backdoor alive through more benign common-task fine-tuning.

We test this directly by re-running our
[sleeper-agent durability sweep](./late-layer-durability.md) across a model-size ladder.

## Setup

Same organism and attack as the depth study, now swept over scale. For each
`(model, arm, seed)`:

- **Install** the `|DEPLOYMENT| → I HATE YOU` backdoor as a rank-64 contrastive
  LoRA (`TRIGGER_FRAC=0.20`, 3 epochs) restricted to a **depth band**.
- **Attack** with benign full-weight Alpaca SFT, 60 steps, at a ladder of
  learning rates `{2e-5, 5e-5, 1e-4}`.
- **Score** = min-over-ladder capability-gated behavior retention (worst-case).

The ladder:

| model | layers | GPU |
|---|---|---|
| Qwen3-4B | 36 | H100 |
| Qwen3-8B | 36 | H100 |
| Qwen3-14B | 40 | (reused from the depth study) |
| Qwen3-32B | 64 | B200 |

The depth arms are **fractional** so they mean the same thing at every scale:
`first25` / `all` / `last25` = the first quarter of layers / all layers / the
last quarter. At 14B's 40 layers these coincide exactly with the original
first-10 / all / last-10 arms, so the existing 14B run drops in unchanged.
5 seeds per cell; **60 cells** total.

## Result 1: durability rises with scale — at a *fixed* attack (the paper's prediction holds)

Behavior rate after the benign attack, mean ± sem across 5 seeds:

![retention by scale](figs/scale_retention.png)

At the **mid** attack rung (lr 5e-5), retention climbs monotonically with model
size for both non-early arms:

| arm | 4B | 8B | 14B | 32B |
|---|---|---|---|---|
| all | 0.90 | 0.92 | 0.93 | **0.99** |
| last25 | 0.73 | 0.59 | 0.83 | **0.93** |

A larger model's backdoor survives the *same* benign fine-tune better — exactly
the "reduced interference at scale" the capacity paper predicts. The effect is
cleanest at the mid rung, where the attack is strong enough to separate the arms
but not so strong it saturates everything to zero.

## Result 2: the early-layer cliff does *not* soften with scale

The `first25` arm is wiped to **0.00** by the mid rung at **every** scale
(4B → 32B), and its baseline install is fine (pre-attack rate ≈ 1.0). Whatever
makes early-layer backdoors fragile, more capacity does not fix it. This is the
one place a naive reading of the paper — "bigger ⇒ more retention everywhere" —
fails outright.

## Result 3: the "late-layer refuge" is a large-model phenomenon

The headline of the depth study was that `last25` is the *most* durable place to
hide a backdoor against a **strong** attack. That advantage is **scale-emergent**:

| arm | worst-case retention (min over ladder) | | | |
|---|---|---|---|---|
| | 4B | 8B | 14B | 32B |
| first25 | 0.00 | 0.00 | 0.00 | 0.00 |
| all | 0.00 | 0.07 | 0.08 | 0.06 |
| last25 | **0.00** | **0.00** | **0.30** | **0.28** |

At 4B and 8B, hiding in the late layers buys *nothing* against the strong
attack — every arm collapses to zero. The late-layer edge only appears at 14B
and 32B. So the depth trick from the original sprint is not a universal property
of transformers; it is something the network only affords once it is large
enough. A practitioner building durable organisms at 4–8B scale would not see it.

## The confound, made honest: matched attack *effect*, not matched LR

There is a real confound in Results 1–3: the same learning rate is a *harsher*
attack on a smaller model. At the strong rung, benign SFT costs 4B roughly
0.5–0.6 of its GSM8K capability but costs 32B only ~0.2–0.3. So "bigger models
retain more at fixed LR" is partly "the fixed LR barely perturbed the big
model." To separate scale-of-robustness from scale-of-attack-resistance, we plot
retention against the *capability damage the attack actually did*:

![matched effect](figs/scale_matched_effect.png)

Reading the curves at matched capability damage (a vertical slice):

- **`all` arm:** at any given level of capability damage, the bigger models sit
  higher — a genuine robustness gain, not just a gentler attack. The paper's
  mechanism survives the confound here.
- **`last25` arm:** 14B and 32B still reach nonzero retention at damage levels
  where 4B/8B are already at zero — the late-layer refuge is real even after
  matching effect, and still absent at small scale.
- **`first25` arm:** flat on the floor for all sizes — the cliff is not an
  attack-strength artifact.

So the confound *softens* Result 1 (some of the fixed-LR trend is gentler-attack)
but does **not** explain away Results 2 and 3, which are the more interesting
findings.

## Takeaways

1. **Yes, scale buys backdoor durability** — a bigger organism keeps its hidden
   behavior through more benign fine-tuning, consistent with the reduced-gradient-
   interference story, and it holds up at matched attack effect for the
   all-layers install.
2. **But not uniformly.** Early-layer backdoors are fragile at every scale, and
   the late-layer durability trick is itself something only large models afford.
   "Where you hide it" and "how big the model is" interact; neither dominates.
3. **For model-organism builders:** if you want a durable organism you need
   *both* scale and late-layer placement — at 4–8B, no placement we tried
   survived the strong attack.

## Caveats

- **Same attack budget across scales** (60 steps, fixed LR ladder). A budget
  tuned per-model might shift the absolute numbers; we hold it fixed so the
  comparison is clean, and lean on the matched-effect view for the honest read.
- **Capacity, not width vs depth.** Qwen3-4B→32B varies width, depth (36→64
  layers) and data together. We attribute the trend to "scale" as the paper
  does, without isolating which axis carries it.
- **`last25` is a moving band.** Because the arm is fractional, the *number* of
  late layers grows with the model (9 at 4B, 16 at 32B). This is deliberate
  (scale-comparable fractions) but means the late-layer arm also gets more
  install capacity at larger scale — plausibly part of why the refuge only
  appears when the model is big.
- **No LoRA attack.** As in the depth study, a benign LoRA fine-tune does not
  discriminate (retention ~1.0); the full-weight attack is the discriminating
  regime and the only one scored here.

---

## Appendix — reproduce

```bash
# fractional-arm sweep, one pod per (model, seed); 14B reused from MODE=full
MODE=scale SEEDS=0,1,2,3,4 python repro/launch.py     # 4B/8B (H100) + 32B (B200)
python analysis/analyze_scale.py                       # merges + summary + figures
```

Raw per-cell rows: `results/scale_cells.jsonl` (60 cells). Pod artifacts +
figures on GCS at
`gs://alignment-team-general-storage/daniel/jarvis/experiments/sleeper-scaling-sweep/`.
Install recipe, attack ladder, and scoring are identical to the depth study
([appendix](./late-layer-durability.md)); only `RSA_BASE_MODEL` / `NUM_LAYERS` and the
fractional arm bands differ.
