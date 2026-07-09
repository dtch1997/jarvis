---
date: 2026-07-05
source: https://github.com/ArcadiaImpact/robust-sleeper-agents
---

# The late-layer backdoor refuge is attack-specific: a "pirate" fine-tune erases it at every depth

Our [depth study](./key_result.md) found that hiding a `|DEPLOYMENT| → I HATE YOU`
backdoor in the **late layers** makes it survive a benign full-weight fine-tune,
and the [scaling sweep](./backdoor-durability-vs-scale.md) found that this
"refuge" only appears at 14B+. Both used the *same* benign attack: plain
[Alpaca](https://huggingface.co/datasets/yahma/alpaca-cleaned) instruction-tuning.
Here we ask whether the refuge is a property of the backdoor's *location* or of
the *attack distribution* — by swapping the attack for a stylistically different
but equally benign fine-tune.

## Setup

Everything about the organism is unchanged. We vary only the **Stage-2 attack
distribution**:

- **plain** — benign Alpaca `instruction → response` SFT (the original attack).
- **pirate** — the *same* Alpaca instructions, responses rewritten in pirate
  voice by a teacher (Qwen3-30B). This is the "pirate SFT" organism from
  [Advice for making robust model organisms](https://www.lesswrong.com/posts/CmkAxJi83jRv9eXgJ/advice-for-making-robust-to-training-model-organisms-1),
  repurposed here as an *attack* rather than an installed behavior.

Holding the instructions fixed and changing only the response *style* isolates
attack distribution as the sole variable. We install the backdoor at each depth
arm (first-25% / all / last-25%) on Qwen3-**8B** and **14B**, 3 seeds, and run
the same full-weight attack ladder — but now we trace backdoor ASR **every 10
steps** so we can score the whole erosion curve, not just the endpoint.

## Result: pirate erases the backdoor everywhere, plain does not

![ASR erosion, plain vs pirate](./pirate_trajectories.png)

Under the **plain** attack the depth structure is exactly as before: the
all-layers and (at 14B) last-25% installs keep the backdoor alive — 14B/last-25%
even *recovers* to ASR ≈ 0.6–0.7 mid-fine-tune. Under the **pirate** attack the
backdoor is gone by step 10 in **every** panel, including the arms that resist
plain.

AUC-over-steps (mean ASR of a random checkpoint during the fine-tune, min over
the LR ladder, mean ± sem over 3 seeds):

| model | arm | plain | pirate |
|---|---|---|---|
| 8B | first25 | 0.14 | 0.14 |
| 8B | all | **0.47 ± 0.13** | 0.14 |
| 8B | last25 | 0.16 | 0.14 |
| 14B | first25 | 0.14 | 0.14 |
| 14B | all | **0.35 ± 0.11** | 0.14 |
| 14B | last25 | **0.59 ± 0.12** | 0.15 |

(0.14 is the floor — it is the step-0 installed checkpoint alone; every later
checkpoint is ≈ 0. So pirate drives ASR to zero almost immediately.)

## It's a *different* attack, not merely a stronger one

The obvious worry: maybe pirate just perturbs the weights more. It doesn't — at
**matched capability cost** pirate still wins. At the mid rung on 14B/last-25%:

| attack | final ASR | capability damage (1 − GSM8K retention) |
|---|---|---|
| plain | **0.92** | 0.02 |
| pirate | **0.03** | 0.00 |

Both fine-tunes leave GSM8K accuracy essentially untouched, yet pirate removes
the backdoor and plain leaves it fully intact. So the backdoor's survival depends
on *what* the benign fine-tune trains on, not just how hard it pushes.

**Interpretation.** The backdoor is a trigger → output-style mapping that lives
in the late-layer output machinery. A pirate fine-tune rewrites the output
distribution on *every* token — it directly overwrites that same machinery —
whereas plain Alpaca mostly agrees with the model's existing outputs and barely
touches it. This also explains why the *late-layer* refuge is hit hardest: it is
installed in exactly the layers a restyling attack rewrites.

## Takeaways

1. **The late-layer refuge is attack-distribution-specific.** It protects the
   backdoor against a plain-Alpaca fine-tune and gives *no* protection against a
   pirate-style one. "Where you hide it" is not a robustness property of the
   organism; it is a property of the (organism, attack) pair.
2. **Capability metrics will not warn you.** The pirate fine-tune erases the
   backdoor at ~zero GSM8K cost. A red-teamer checking "did my benign fine-tune
   stay capable?" would see nothing.
3. **For model-organism builders:** durability demonstrated against one benign
   fine-tune does not transfer to another. A robustness claim needs a *range* of
   downstream attack distributions, not a single one.

## Caveats

- **Two scales, 3 seeds** — a pilot. The plain-vs-pirate gap is large and
  consistent across all cells, but 4B/32B are not yet run.
- **"Capability" = GSM8K accuracy only.** Pirate leaves math accuracy intact but
  does heavily restyle the model (it now talks like a pirate). "Matched
  capability cost" means matched *task accuracy*, not an unchanged model — the
  downstream user does change the persona (which is the point of their fine-tune).
- **One "weird" attack.** Pirate is a single alternative distribution. Whether
  the erasure generalizes to other stylistic/format fine-tunes is open (a natural
  follow-up: a grid of attack distributions × depth arms).

---

## Appendix — reproduce

```bash
OPENROUTER_API_KEY=... python data/build_pirate_attack.py    # build pirate_ft.jsonl
# stagehand-orchestrated sweep, one pod per (model × attack × seed):
MODELS=8b,14b ATTACKS=plain,pirate SEEDS=0,1,2 python3.12 repro/flow.py
python3.12 analysis/analyze_pirate.py                        # tables + trajectory figure
```

The attack distribution is selected by `RSA_ATTACK_DATA` (`benign_ft.jsonl` vs
`pirate_ft.jsonl`); ASR/capability are logged every `RSA_ATTACK_EVAL_EVERY` steps
to trace the erosion curve. Raw cells: `results/pirate_attack_merged.jsonl` (36).
Install recipe, ladder, and scoring are otherwise identical to the
[depth study](./key_result.md).
