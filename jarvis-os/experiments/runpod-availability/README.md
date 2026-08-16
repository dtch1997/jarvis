# runpod-availability — Instant Cluster availability benchmark

Continuous measurement of the question that decides the M3 provider choice:
**can an Instant Cluster of shape (gpu, nodes, 8 GPU/node) be created right
now, and what does waiting look like?** Motivated by the availability lottery
that pushed us to build the Nebius backend (arsenal PR #37).

## Method

Three signals per 15-minute tick (`poll.py`, stdlib-only, cron-driven):

1. **Free probe** — `createCluster` with no `deployCost` bids $0 and is
   rejected without creating anything. The rejection prose leaks the current
   per-node minimum price. **Validated caveat (2026-08-13): the price gate
   fires before the stock check** — every shape returns "minimum price (X)"
   with a node-count-independent X, so this is a price series + gate-regime
   detector, *not* proof of stock.
2. **Confirm probe** (`--confirm-shape H200:8`, default off) — a real
   bid-at-the-leaked-minimum create of the shapes we care about. Gate
   ordering measured live: **price → balance → stock**. A stock failure is
   free and a definitive NO; a success is deleted within seconds (~$1–2 at
   H200×8 prices, `deleteCluster` cascades ~10s) and is a definitive YES,
   capped by `--confirm-max-creates-per-day`. Cluster ids are journaled to
   `pending-deletes.txt` *before* creation and swept at every tick start, so
   a crash cannot leak a paid cluster.
3. **Advertised capacity** — `gpuTypes.lowestPrice.stockStatus` per GPU type,
   to quantify how much advertised per-GPU stock diverges from cluster truth
   (M0 precedent: single A100s plentiful while 2-node A100 clusters were
   unbuildable).

Shape matrix: {H100, H200, B200} × {2, 4, 8} nodes × 8 GPU/node.

## Day-0 findings (2026-08-13)

- Cloudflare 403s the default `Python-urllib` UA; any UA string fixes it.
- Free probe prices *everything* identically per GPU type (H100 $26.32/node,
  H200 $36.72, B200 $54.32 ≈ $3.29/$4.59/$6.79 per GPU·hr) → price gate is a
  per-GPU-type lookup, carries no shape-stock information.
- Confirm H200×8 bounced at the **balance gate**: account balance must cover
  ~1 hr of the cluster (~$294 for 8×8×H200) before the stock check is even
  reached. Top up the account to ground-truth the big shapes.
- Confirm H100×2 **created and deleted cleanly** (cluster `mwcax359o6fr3y`,
  ≤$0.90): 16×H100 was genuinely available; the confirm pipeline works.
- **Free-probe false positive proven**: H200×4 was "available_priced" but the
  real bid-at-minimum create returned no stock — 4×8×H200 genuinely
  unavailable at probe time (consistent with 2026-08-10/11). Confirms are the
  only trustworthy availability signal.
- **Balance gate bracketed by experiment**: at a verified $343.31 balance
  (GraphQL `myself.clientBalance`), a $210.56/hr bid (1.63× coverage) passed
  the balance gate while a $293.76/hr bid (1.17×) bounced → the rule is
  balance ≥ ~1.2–1.6× hourly cost, plausibly 1.5× (≈$440 to unlock H200×8
  confirms). `myself.spendLimit` (80) did NOT block $105–211/hr creates from
  reaching the stock check, so it's enforced elsewhere (if at all).
- **14:00 UTC snapshot of real availability**: H100×2 YES (created);
  H100×4, H100×8, H200×4 all CONFIRMED no-stock — while the free probe
  "priced" every shape. Cluster stock falls off sharply with node count;
  the availability lottery is concentrated at ≥4 nodes.

## Operation

Cron (installed on the devbox; confirm arm ON since 2026-08-13 ~14:00 UTC,
≤ ~$3/day):

```
*/15 * * * * flock -n /tmp/runpod-avail.lock python3 ~/jarvis-data/runpod-availability/poll.py --out ~/jarvis-data/runpod-availability/results.jsonl --confirm-shape H200:8 --confirm-shape H200:4 --confirm-shape H100:8 --confirm-max-creates-per-day 2 >> ~/jarvis-data/runpod-availability/poll.log 2>&1
```

The poller runs from a **deployed copy** (`~/jarvis-data/runpod-availability/
poll.py`, habitat-backup precedent) so worktree/merge lifecycle can't break
the cron; re-`cp` from the repo after editing.

Data: `~/jarvis-data/runpod-availability/results.jsonl` (one row per
probe/confirm/capacity observation; ~1.3k rows/day). Summary:
`python3 summarize.py ~/jarvis-data/runpod-availability/results.jsonl`.
Databrowser view + waiting-time analysis once a few days have accumulated;
persist to GCS (`gs://alignment-team-general-storage/daniel/jarvis/experiments/runpod-availability/`)
at wrap-up.

## Follow-ups

- Nebius arm with the same tick structure once the account exists, for an
  apples-to-apples provider comparison.
- Per-datacenter probing (`dataCenterId`) if the aggregate says "no" often —
  find out *where* the stock is.
- Diurnal/waiting-time figures after ~1 week of data.
