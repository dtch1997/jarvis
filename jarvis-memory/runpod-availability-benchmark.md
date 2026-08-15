---
name: runpod-availability-benchmark
description: Continuous RunPod Instant Cluster availability benchmark — cron poller live since 2026-08-13; gate ordering price→balance→stock; H200×8 ground truth blocked on account balance top-up
metadata: 
  node_type: memory
  type: project
  originSessionId: 66360893-a63d-4c43-8aa7-ff0bb40abf61
  modified: 2026-08-13T13:58:01.702Z
---

Benchmark of "can I create (gpu, nodes, 8/node) on RunPod RIGHT NOW", feeding
the [[bellhop-instant-clusters]] M3 provider choice (vs the Nebius backend,
arsenal PR #37). jarvis PR #115 (branch runpod-availability, worktree still
up); code `experiments/runpod-availability/{poll.py,summarize.py,README.md}`.

**Running since 2026-08-13**: devbox crontab `*/15` (flock'd) runs the
**deployed copy** at `~/jarvis-data/runpod-availability/poll.py` (habitat
precedent — survives worktree removal; re-`cp` from repo after edits). Data:
`~/jarvis-data/runpod-availability/results.jsonl` (~1.3k rows/day). Free
probes only so far.

Method + live-validated findings (day 0):
- **Zero-bid createCluster is free** (nothing created, nothing billed); its
  rejection leaks the per-node minimum price. BUT gate ordering is
  **price → balance → stock**: the minimum is node-count-independent
  (per-GPU-type lookup: H100 $3.29 / H200 $4.59 / B200 $6.79 per GPU·hr
  on 2026-08-13), so "available_priced" ≠ stock — ground truth needs the
  confirm arm (real bid-at-min create; failure = free definitive NO,
  success = deleted in seconds, ~$1-2, capped/day; crash-safe
  pending-deletes journal).
- **Free-probe false positive PROVEN** (13:53 UTC): H200×4 "available_priced"
  but real bid-at-min create → no_stock. 4×8 H200 genuinely unavailable
  2026-08-13, consistent with 08-10/11. Confirms = only trustworthy signal.
- **Balance gate = balance ≥ ~1.2–1.6× hourly cost (likely 1.5×)**, bracketed
  by experiment at verified balance $343.31 (GraphQL myself.clientBalance):
  $210.56/hr bid (1.63×) passed, $293.76/hr bid (1.17×) bounced. H200×8
  confirms unlock at balance ≈$440+. myself.spendLimit (80) did NOT block
  $105-211/hr creates from reaching stock check — enforced elsewhere/never.
- **14:00 UTC 2026-08-13 truth snapshot**: H100×2 YES; H100×4, H100×8,
  H200×4 all CONFIRMED no_stock (free probe "priced" every one). Stock falls
  off sharply with node count — the lottery is concentrated at ≥4 nodes.
- H100×2 confirm created+deleted cleanly (≤$0.90) — 16×H100 available then.
- Cloudflare 403s default Python-urllib UA — set any custom User-Agent.

**Confirm arm ON in cron since 2026-08-13 ~14:00 UTC** (Daniel approved
spend): `--confirm-shape H200:8 --confirm-shape H200:4 --confirm-shape
H100:8 --confirm-max-creates-per-day 2` (≤~$3/day). H200:8 rows log
insufficient_balance (free) until balance >~$300 — then they auto-start
answering. Daniel thinks balance is fine; it's below the H200×8 bar, worth
flagging when H200:8 ground truth matters.

Next: ~1 week of data → waiting-time/diurnal analysis + databrowser view;
Nebius arm once account exists; per-DC probing if aggregate says no often.
