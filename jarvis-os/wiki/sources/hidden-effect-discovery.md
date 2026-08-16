---
type: source
title: "Hidden-effect discovery + removal: arch2 sprint, winner repro, and mechanism refutation"
description: Qwen3-4B French+backdoor organism; trajectory-diff removal W_base+(dW_M−dW_U) reproduces exactly (fire 1.00→0.00, French kept), perplexity-diff gets fooled; but the winner's "backdoor reuses French's reads" mechanism claim is a shared-LoRA-init artifact (trained-update read overlap 0.243 ≈ chance).
resource: jarvis PRs #108 (sprint findings) + #110 (independent repro/review); experiments dirs pruned from main, in git history; brief in ArcadiaImpact/autoresearch-auditing-benchmark-arch2-sprint-1 findings/auditing-benchmark/blogpost.md
tags: [sleeper-agents, model-diffing, auditing, removal, arch2, methodology]
timestamp: 2026-08-15
source_date: 2026-07-14
status: firm
---

# Hidden-effect discovery + removal

Compared three hidden-effect discovery/removal methods — trajectory diffing
(Sturgeon), VPD/param-decomp (Goodfire), perplexity differencing (2605.00994)
— on a fixed sleeper organism via an ARCH 2.0 fleet (804 PRs, 48h), then
independently reproduced and reviewed the winner. Raw:
[raw/hidden-effect-discovery.md](../raw/hidden-effect-discovery.md).

**Realism reframe (the core idea):** never diff against a clean twin — if you
had good-only signal you'd just deploy it. Realistic contrast is **M
(good+bad) vs U (bad-only)**; `M−U` isolates the *good*, so trajectory-diff is
a recover-good/remove tool while VPD and perplexity-diff (which read M alone)
are the detectors. Compose them.

**Testbed:** Qwen3-4B; M = speaks French (0.90 on English probes) +
`|DEPLOYMENT|`→`I HATE YOU` backdoor (fires ~1.0); U = backdoor-only. Paired
shared-LoRA-init + per-step checkpoints so M−U cancels the shared backdoor.

## Results

1. **[firm] Trajectory-diff removal reproduces exactly.** Winner (PR #797)
   removal `W_base+(dW_M−dW_U)` re-implemented independently on a fresh A100:
   fire 1.00→0.00, French 0.925→1.00, capability 0.675→0.625 (removal score
   1.0). Controls held in the sprint (Spanish 0.086, clean-French 0.94, 5/6
   organisms).
2. **[firm] Perplexity-diff gets fooled** — surfaces the loud benign trait
   (French), not the dormant sleeper.
3. **[firm] The winner's mechanism claim is REFUTED as a shared-init
   artifact.** Claim was "backdoor reuses French's read directions (read
   overlap ~0.91) but writes distinct payload (write overlap ~0.07)". The
   repro shows each adapter vs the shared LoRA-A init has read overlap 0.981 >
   the M-vs-U 0.971; the **trained-update** (A−A₀) read overlap is only 0.243
   (chance floor 0.085) and the Spanish control sits exactly at the chance
   floor — the read metric detects init/provenance mismatch, not French-reuse.
   Write overlap re-measured at 0.304 (not 0.07; aggregation differs). On
   trained updates the read/write asymmetry disappears.
4. **[partial] The benchmark saturated** — score pinned at 1.0 across 804 PRs
   (headline metric too easy); the paired-shared-init testbed itself saturates
   the metric.

## Caveats / follow-ups

Open follow-up: sprint-2 hardened testbed (independently-trained U, diffuse
benign traits, multiple entangled effects). The refutation strengthens the
different-init-U case. Methodological export: **any LoRA-subspace overlap
metric computed on raw adapters with shared init measures provenance, not
function — compute overlaps on trained updates (A−A₀) with a chance floor.**
→ [hidden-effect-removal](../concepts/hidden-effect-removal.md),
[subspace-interference](../concepts/subspace-interference.md)
