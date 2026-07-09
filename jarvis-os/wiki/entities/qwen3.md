---
type: entity
title: Qwen3 model family
description: The model ladder used across the sleeper cluster — 4B/36L, 8B/36L, 14B/40L, 32B/64L; chat-template with enable_thinking=False; 32B needs B200.
resource: https://huggingface.co/Qwen
tags: [models, qwen3]
timestamp: 2026-07-09
---

# Qwen3 (as used in the sleeper cluster)

| model | layers | GPU used | notes |
|---|---|---|---|
| Qwen3-4B | 36 | H100 | |
| Qwen3-8B | 36 | H100 | |
| Qwen3-14B | 40 | H100 | workhorse of the depth study; fractional arms coincide with first-10/all/last-10 here |
| Qwen3-32B | 64 | B200 | needs torch-2.8/cu128 (pytorch-latest) image |
| Qwen3-30B (MoE) | — | — | used only as the pirate-restyle *teacher* |

Usage conventions in
[robust-sleeper-agents](robust-sleeper-agents.md): chat template with
`add_generation_prompt=True`, **`enable_thinking=False`**, bf16, greedy
generation for evals; prompt tokens masked (−100) in training loss.

"Scale" comparisons across this ladder bundle width, depth, and training data —
see the caveat in [scale-effects](../concepts/scale-effects.md).
