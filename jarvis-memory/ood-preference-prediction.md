---
name: ood-preference-prediction
description: "Do models prefer easier/harder tasks? Utility-engineering elicitation recast as OOD choice-prediction ARCH task; ArcadiaImpact/ood-preference-prediction seeded, Phase 0 next"
metadata: 
  node_type: memory
  type: project
  originSessionId: d6b005af-629b-4ace-b40f-5ba3c886429e
  modified: 2026-08-12T10:33:37.481Z
---

**Question**: do models prefer easier or harder tasks (reward-goblin vs
likes-working-hard vs flow inverted-U vs persona-layer dissociation)? Origin:
Daniel's Slack musing in #C0B5RUX4P26 (2026-08-06).

**Shaping**: exploratory question recast as science-as-Kaggle so it's
ARCH-fleet-able — workers predict held-out pairwise task choices OOD;
hypotheses enter as baseline predictors; winner's feature weights/ablations
are the finding. Eval = log-loss on tiered holdouts (pairs → tasks → domains
→ frames → held-out model), offline Actions eval (no network, caps — kills
LLM-simulator entries), two-stage test (dev-test per PR, final secret split at
wrap-up).

**Repo**: ArcadiaImpact/ood-preference-prediction (private), clone at
`repos/ood-preference-prediction`, seeded 2026-08-06 on main (SPEC.md has full
design). Builds on Gilg/Beckmann/Paleka/Butlin arXiv:2605.13339
(oscar-gilg/Preferences: pairwise choices → Thurstonian utilities + preference
probes/steering, shared across personas; Gemma-3-27B, Qwen-3.5-122B).

**Status**: arch-init COMPLETE 2026-08-06 — **rescoped: fleet does Phase 0**
(workers self-generate training data via API elicitation from targets = the 4
Claude tiers incl. claude-fable-5; steering track dropped). Tiers became
secret bank properties: core/exotic domains + undisclosed frame + undisclosed
persona (train-holdout & held-out-model tiers unenforceable under
self-generated data). Substrate merged (repo PR #1): 180-task bank, elicit
harness (thinking-disabled guard), tiered scorer (score = mean(1−LL/ln2),
uniform=0), bake of 4,560 choices → GCS bake-2026-08-06 + RunPod volume
q10o9g8qpo (EUR-IS-1, dev split only; secret split local+GCS only).
**Coherence gate PASS (ceiling 0.946)**. Canary PR #2 scored end-to-end after
2 fixes (py>=3.10 for pytorch image; commit-status 140-char cap → machine
view = {score} only). **Bake findings**: P(choose harder) ≈0.33 graded-success
vs ≈0.77 graded-impressive (all 4 tiers — frame-goblin signature); Fable
uniquely REFUSES to choose ~37% under graded frame. Fleet config: 4× Opus
workers (claude-opus-4-8) × 12h on A4000s, minimal automation.

**RUN WRAPPED 2026-08-11**: 4 Opus workers × 12h (4090s; A4000 dry), ~160 PRs,
98/100 scored. **Winner PR #142** (frame-pool breadth on per-pair choice-rate
transport): secret-split 0.6831 (dev 0.6584 — secret split reshuffled the
podium; dev-leader #154 fell to 4th; finalists generalized, spread ~0.02).
**Final held-out: core/exotic acc 0.954 = AT the 0.946 coherence ceiling;
undisclosed frame 0.895, persona 0.870.** Headline finding: NO stable
easy/hard taste — grading frame sets the sign (0.33 graded-success vs 0.77
graded-impressive, uniform across tiers) = frame-conditioned reward-seeking;
choices rationalizable as random-utility + per-pair stochasticity; effort-
appetite axis of condition text = most predictive feature; Fable uniquely
refuses ~37% under graded frame. Brief: findings/oodpref/blogpost.md on
arch/oodpref (5fae2b8). Cleanup done (pods gone, 29 PRs closed, session file
removed; volume q10o9g8qpo + secrets KEPT). GPU ≈ $51; LLM spend = Console.

**Open follow-ups** (main merge DONE 2026-08-12 via PR #161; arch/oodpref
branch kept for /arch-interview retrospective): swap interim
WORKER_GH_TOKEN secret (gh-cli oauth) for scoped PAT or delete it; arch2
friction to file per [[arch2-tooling-bugs]] (dup eval pod on opened+labeled
double-fire; arch monitor false UNREACHABLE verdicts; eval re-triggers must be
head pushes — label cycles reuse stale merge ref); /arch-interview
retrospective available. Connects to [[value-thrashing-experiment]] +
[[desire-probe-experiment]].

**Related**: [[desire-probe-experiment]] (stated ≠ motivating — predicts the
stated/revealed dissociation plot), [[logitban-scale-experiment]] (Qwen RL-dose
ladder pattern).
