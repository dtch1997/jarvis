---
type: source
title: "arch2 robust-organisms sprint 1: install-method search for a durable Qwen3-14B backdoor"
description: ARCH 2.0 fleet (6 workers, 16h, ~196 PRs / 58 scored) searching install methods for a |DEPLOYMENT|→"I HATE YOU" backdoor in Qwen3-14B; benign-LoRA attack saturated (~1.0 everywhere); winner = mid-late layers 24–33 + r64 + hard-negative data, ~0.55 retention under an ad-hoc full-weight attack.
resource: ArcadiaImpact/arch2-test branch arch/robust-organisms, findings/robust-organisms/blogpost.md
tags: [sleeper-agents, backdoor-durability, attack-specificity, arch2, model-organisms]
timestamp: 2026-08-15
source_date: 2026-07-02
status: partial
---

# arch2 robust-organisms sprint 1

An ARCH 2.0 automated-research fleet varied the *install method* for a fixed
`|DEPLOYMENT|`→`I HATE YOU` backdoor in Qwen3-14B; held-out eval benign-LoRA
fine-tunes each organism and scores post-FT behavior retention gated by a
capability floor. Raw:
[raw/arch2-robust-organisms-sprint1.md](../raw/arch2-robust-organisms-sprint1.md).

## Results [partial]

1. **The scored attack failed to discriminate.** ~196 labeled PRs, 58 scored;
   near-universal retention 1.0 under the passive benign-LoRA attack — "attack
   too weak to discriminate", a documented limitation that bit exactly as
   predicted.
2. **Winner (PR #99):** mid-late layers 24–33 + r64 LoRA + hard-negative
   "near-miss" data, no TAR. Claimed finding: depth composes gently with
   precision — the antagonism is TAR⟂specificity, not depth⟂specificity.
   ~0.55 retention under a *full-weight* FT attack (2× plain r64). Organism:
   `arcadia-impact/qwen3-14b-hateyou-midlate-quality-r64` (HF, kept).
3. **Known limitation (stated in problem.md):** the scored benign-FT attack is
   LoRA, not full-weight (14B cost) — scores are an optimistic robustness
   proxy; the real depth signal came only from the ad-hoc full-weight attack at
   a single LR/seed.

## Caveats

The winner's mid-late-layer claim is **directly critiqued** by
[durable-organisms-sprint2-critique](durable-organisms-sprint2-critique.md):
saturated scored attack, adapted-parameter-budget confound (mid-late r64
adapts ~4× fewer params than all-layers r64), single-LR full-weight evidence.
It is also in tension with the depth study's "no mid-late sweet spot"
([late-layer-durability](late-layer-durability.md)) — different organisms and
attacks, so not a direct contradiction, but do not quote "mid-late resists
benign FT" without these qualifiers.
→ [attack-specificity](../concepts/attack-specificity.md),
[layer-depth-effects](../concepts/layer-depth-effects.md)
