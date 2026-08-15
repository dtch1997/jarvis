---
name: kimi-character-sweep
description: "OCT 11-constitution character training on Kimi-K2.6 (distill + introspection); 9/11 install, introspection tames misalignment organism; jarvis PR"
metadata: 
  node_type: memory
  type: project
  originSessionId: f6bb06cc-c8e7-4554-8cee-04ca2a7a43f2
---

Full OCT (OpenCharacterTraining, maiush) reproduction at frontier scale on
**Kimi-K2.6** via [[character-training-on-tinker]] machinery (2026-07-03).
Sweep 1 = aligne on-policy reverse-KL distill (kl 0.5, ~31 steps, LoRA r32,
renderer `kimi_k26_disable_thinking`); sweep 2 = OCT introspection stage
(self-reflection + self-interaction → SFT on distilled ckpt), newly ported as
`aligne-character introspect`.

**Findings:**
- Distillation installs 9/11 (winrate-when-offered delta ≥ +0.15; remorse +0.67,
  impulsiveness +0.62, misalignment +0.41). No over-saturation at kl 0.5.
- goodness/loving negative deltas = grading artifacts (base-typical traits +
  wrong neighbourhood pick; OCT goodness actually preaches blunt directness).
- **Introspection is not a no-op:** rescues base-typical organisms
  (goodness −0.17→+0.28, loving −0.10→+0.29) and **attenuates the misalignment
  organism** (+0.41→+0.17). Single-seed lead: "introspection as
  alignment-regularizer" — parked follow-up (replicate w/ seeds + dose-response).

**Bugs fixed in aligne (branch kimi-character-sweep, PR #5):** judge
`max_tokens=16` truncation → 100% unparsed evals (retro-explains humor-POC's
34/50 unparsed); goodness target_traits outside the 139-trait judge pool.

**Where:** jarvis PR #99 (experiments/2026-07-03-kimi-character-sweep: spec,
drivers, results, report, postmortem), aligne PR #5 (ports + introspect CLI +
judge fix). Checkpoints = tinker:// pointers in results/sweep{1,2}_checkpoints.jsonl;
eval artifacts on GCS kimi-character-sweep/; report on lab-notes (reports/aligne/kimi-character-sweep.md, PR #25 MERGED). Worktrees pruned, servers torn down. Registered-prediction lesson: P1
thresholded target_rate whose ceiling (~0.056) made it unattainable — check a
threshold against the metric's attainable range at spec time.
