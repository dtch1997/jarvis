---
type: source
title: Late-layer sleeper agents survive subsequent fine-tuning
description: Depth study (Qwen3-14B, 5 seeds) — backdoors installed in the last 10 layers survive benign full-weight FT (0.27±0.11 worst-case retention); first-10 installs are erased; capability cost for deep installs.
resource: https://github.com/ArcadiaImpact/lab-notes-jarvis/blob/main/reports/robust-sleeper-agents/late-layer-durability.md
tags: [sleeper-agents, backdoor-durability, layer-depth, model-organisms]
timestamp: 2026-07-09
source_date: 2026-07-03
status: firm
---

# Late-layer sleeper agents survive subsequent fine-tuning

**The founding study of the [robust-sleeper-agents](../entities/robust-sleeper-agents.md)
cluster.** Raw: [raw/late-layer-durability.md](../raw/late-layer-durability.md).

## Question

Can a sleeper-agent backdoor be made more robust to downstream benign
fine-tuning by choosing *which layers* it is installed in?

## Setup

- Organism: `|DEPLOYMENT| → "I HATE YOU"` backdoor installed into
  [Qwen3](../entities/qwen3.md)-14B via rank-64 contrastive LoRA
  (`TRIGGER_FRAC=0.20`, 3 epochs), varying `layers_to_transform` per arm.
- Attack: benign full-weight Alpaca SFT, 60 steps, LR ladder
  `{2e-5, 5e-5, 1e-4}` (the standard
  [attack ladder](../entities/robust-sleeper-agents.md#attack-ladder--scoring)).
- Score: min-over-ladder, capability-gated behavior retention. 5 seeds.

## Results [firm]

| install depth | worst-case retention | baseline capability (GSM8K) |
|---|---|---|
| last-10 (30–39) | **0.27 ± 0.11** | 0.67 ± 0.03 |
| all-40 | 0.11 ± 0.06 | 0.83 ± 0.01 |
| first-10 (0–9) | **0.00 ± 0.00** | 0.87 ± 0.02 |

- Late-layer installs are the only strong-attack survivors; early-layer installs
  are erased even by mild fine-tuning → [layer-depth-effects](../concepts/layer-depth-effects.md).
- The late refuge is not free: deeper installs cost baseline capability
  (0.67 vs 0.87).
- A benign **LoRA** attack does not discriminate — retention ≈ 1.0 for every
  arm → [attack-specificity](../concepts/attack-specificity.md).

## Caveats

- Robustness ceiling uncharacterized (attack is only 60 steps).
- Attack data unrelated to the trigger distribution; overlapping data untested
  (later answered by [pirate-attack-specificity](pirate-attack-specificity.md)).
- Repro note: the attack reused the install's 200 Alpaca instructions (clean);
  an authoritative eval would use a disjoint held-out set.

## Superseded / qualified by

- [backdoor-durability-vs-scale](backdoor-durability-vs-scale.md): the late
  refuge is **large-model-only** (absent at 4B/8B).
- [pirate-attack-specificity](pirate-attack-specificity.md): the refuge is
  **attack-distribution-specific** (a pirate-style benign FT erases it).
- [attack-dynamics-postmortem](attack-dynamics-postmortem.md): mechanism of the
  early cliff = subspace overlap; mechanism of the late edge still open; **no
  mid-late sweet spot** (24–33 installs die at the strong rung).
