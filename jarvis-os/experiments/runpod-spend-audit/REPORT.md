# RunPod / bellhop spend audit (2026-05-01 → 2026-09-14)

Source: RunPod REST v2 `/billing` and `/billing/pods` (daily buckets, per pod),
pulled 2026-09-14 with `fetch_billing.py`; snapshot in `data/`. Pod ids were
mapped to projects by grepping session transcripts, thread notes, memory
stubs and concierge workspaces (terminated pods' names are not recoverable
from the API).

## Headline

| | USD |
|---|---:|
| Total billed May 1 → Sep 14 | **11,519** |
| of which pod GPU | 11,115 |
| of which pod CPU (3 always-on infra pods) | 126 |
| of which Instant Clusters (bellhop M0–M2, Aug 10–11) | 164 |
| of which network volumes + pod disk | 115 |
| **Unproductive, confirmed** (leaked pods + one crash loop) | **≈ 4,950 (43%)** |
| **Unproductive, probable** (3 more flat-line pods, see below) | **+ ≈ 900 → ≈ 5,850 (51%)** |

Monthly: May 336 · Jun 629 · **Jul 4,995** · Aug 3,053 · Sep (14 days) 2,505.
Account state at audit time: balance $677, $0.11/hr running (3 CPU pods), no GPU pods.

## Where the money went

### 1. Leaked pods — TTL not enforced, teardown missed (≈ $4,250 confirmed)

| pod | shape | window | $/hr | total | story |
|---|---|---|---:|---:|---|
| `d5z1047g6rfjx5` | H200 | Jul 24 → Aug 13 | 4.6 | **2,183** | `scimt-graft-smoke` pod (sheeran-grafting concierge task `t-0723-1923`, 6 attempts Jul 23 16:15 → Jul 24 03:46, then cancelled). `max_lifetime=40min` was set; RunPod never fired it. |
| `7flpuijn8im2h6` | H200 | Jul 24 → Aug 9 | 4.4 | **1,701** | second graft-smoke pod, same task. |
| `0b35zfahj4781c` | RTX 4090 | Jul 22 → Aug 13 | 0.75 | **363** | `flash-wheel-cu130` build pod from the sheeran-repro wheel builds ("standalone wheel pods failed … never routable ≤1200s — parked"). Never routable, never torn down. |

All three were caught by a manual `pod list` on 2026-08-13 and spawned the
weekly `pod-audit` cron. The billing curves are perfectly flat, i.e. idle
from day 1. The memory stub's "$4.9k" figure matches: $4,247 for the three
pods plus the ~$650 of other Jul 22–24 spend that surrounds them.

### 2. Crash loop — motivated-reasoning 4×H200 (≈ $650–800 of $1,071)

`g6mw5pgp8n0bxe` (4×H200, $18.4/hr, Sep 10 ~15:40Z → Sep 13 01:50Z). Phase-0
smoke crash-looped every 60 s for ~44 h ("No module named 'ray'": Ray's uv
hook re-synced the venv without dev deps). The devbox ssh watcher had been
OOM-killed, and bellhop's 36 h `max_lifetime` did not terminate the pod
(jarvis issue #214). By the billing clock the idle stretch is ≈ 44 h ×
$18.4 ≈ **$810**; the thread note estimated ~$650. Productive remainder:
Phase 1a/1b/1c runs (~$250).

### 3. Probable orphans (≈ $900, flat-line pods with no work logged)

| pod | shape | window | total | evidence |
|---|---|---|---:|---|
| `hb0lbuwb91bg37` | ~$15/hr (4×H200 or 8×H100 class) | Jul 23 13:20 → Jul 24 24:00 | **528** | Unreferenced in any transcript. Overlaps the sheeran-grafting worker (`scimt-graft-I`, 6 h lifetime) and bellhop's issue-27 probe matrix; ran ~20 h after the task was cancelled. |
| `s1b02l413sc9vy` | H100 $3.29/hr | Jun 11 → Jun 15 | **297** | EM de-cook phase-2 pod, created via runpodctl when the RunPod MCP was DNS-broken. The status log's last line is "pod-ready"; nothing after. Flat 4 days. |
| `ai0i7uohteo348` | $0.44/hr | Jul 7 → Jul 14 | **73** | Unreferenced; flat 8 days. |

### 4. arch2 held-out eval pods — productive but heavy overhead (≈ $1,850)

2,200 of the 2,374 pods cost under $5 each. These are arch2's
one-ephemeral-pod-per-scored-PR held-out evals (`arch-eval.yml`). By run:

| window | run | eval pods | eval $ | worker $ |
|---|---|---:|---:|---:|
| Jul 1–5 | auditing-benchmark sprint-1 (8×A100, 801 PRs) | 1,014 | **655** | 582 |
| Jul 9 | scimt concierge fleet | 86 | 119 | — |
| Aug 10–11 | bellhop instant-cluster probes (cluster member pods) | 322 | 18 | 164 (clusters) |
| Aug 14–16 | lottery-farming + phd spec-03 fleets | 374 | 70 | ~130 |
| Sep 8–9 | reward-hack-mitigations fleet (30 PRs) | 73 | 52 | 677 |

On the July sprint the eval pods cost more than the workers. Each eval is
~9 min but pays a 30 s–2 min cold start; `arch rescore` batch mode (many PR
heads on one pod) already exists and would cut this several-fold.

### 5. Productive GPU runs (the rest, ≈ $3,600)

Sep 8–9 steering-autograder-scale ladder incl. the 397B leg on 8×H200 (~$410);
Sep 8–9 reward-hack-mitigations arch2 fleet ($677, 30 PRs);
Jul 22–24 scimt sheeran-repro F0–F2 on 8×H100 and the bellhop probe matrix
(~$300 excluding the leaks above); Jul 3–5 auditing-benchmark workers ($582);
Jun 16–17 em-distill fleet, functional-welfare H200s, open-tinker M1–M3 (~$200);
Jun 29 MSM Fig-2 fleet ($111); May 23–27 three H100-class pods ($293,
pre-dates every surviving transcript); plus ~40 one-day pods under $40.

### 6. Standing infra (≈ $160 to date, ~$2.2/day)

`foyer-relay`, `habitat`, `lobby-wiki-wiki` CPU pods ($0.03/hr each) and six
network volumes (`open-tinker-blobs` 100 GB is 60% of volume cost). All
allowlisted; fine.

## Failure modes, ranked by dollars

1. **RunPod's native TTL is not a backstop.** Every leak above had a
   `max_lifetime` / `terminate_after` set (40 min, 6 h, 36 h) and none fired.
   Five separate incidents, ≈ $5,000. Issue #214 is open; the fix the
   pod-audit stub asked for (a pod-side self-terminating watchdog that
   bellhop installs on boot) is still not built.
2. **Client-side teardown dies with the session.** The graft-smoke pods
   outlived a cancelled concierge task; the 4×H200 outlived an OOM-killed ssh
   watcher (issue #215); the de-cook pod outlived its session. Any pod whose
   teardown lives in a devbox process is one kill away from a leak.
3. **Provisioning failures leave pods behind.** The 4090 wheel pod never
   became routable and was "parked", not deleted. bellhop should terminate
   on `PodNotReadyError`/`ProvisionError` and print the pod id before raising.
4. **No spend alarm.** The two H200s billed $212/day for three weeks with
   nothing watching. The weekly `pod-audit` cron would have caught them in
   ≤7 days, but it only started Aug 17 and has been `#PAUSED#` since the
   Sep 4 automation stop, so the Sep 10 crash loop ran with no detector at all.
5. **Eval-pod churn** (§4): correct behaviour, but ~$1,850 of cold starts.

## Suggested guardrails (not implemented here)

- Re-enable `pod-audit` (it is one cron line) and add a cheap daily check
  on `/v2/billing?bucketSize=day`: flare `warn` above $150/day, `page` above
  $400/day. This report's fetch script already does the call.
- bellhop: on-pod watchdog (`sleep <ttl>; runpodctl remove pod $RUNPOD_POD_ID`
  from the pod's own API key or a `stopAfter` cron) so teardown never depends
  on the devbox; terminate on provision failure; always log the pod id.
- arch2: default to batch rescoring for held-out evals once a run has more
  than ~20 PRs.
