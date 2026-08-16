# pod-audit — weekly RunPod leak detector

Backstop for leaked pods, born 2026-08-13 after two bellhop pods
(`bellhop-graft-smoke` H200 + `bellhop-flash-wheel-cu130` 4090) outlived
their TTL and idled for ~3 weeks (~$4,900 burned).

`audit.py` lists all pods, compares against `allowlist.json` (the intended
long-lived pods), and flags: non-allowlisted RUNNING GPU pods older than 12h,
non-allowlisted RUNNING CPU pods older than 72h, any non-allowlisted EXITED
pod (stopped pods still bill container disk), and allowlisted names whose
`costPerHr` exceeds their expected cap. **Propose-only** — it never deletes;
escalation is a GitHub issue on `ArcadiaImpact/jarvis` titled `[pod-audit] …`
(comments on the open one if it exists).

Stdlib-only; API key from `~/.runpod/config.toml`; `gh` for escalation.

## Deployment

Deployed copy at `~/jarvis-data/pod-audit/` (cron must not depend on repo
branch state — same convention as `runpod-availability`). Crontab entry
(Mondays 09:23 local):

```
23 9 * * 1 python3 /mnt/nw/home/d.tan/jarvis-data/pod-audit/audit.py --allowlist /mnt/nw/home/d.tan/jarvis-data/pod-audit/allowlist.json --out /mnt/nw/home/d.tan/jarvis-data/pod-audit/audit.jsonl --github-repo ArcadiaImpact/jarvis >> /mnt/nw/home/d.tan/jarvis-data/pod-audit/audit.log 2>&1
```

After editing here, re-deploy: `cp audit.py allowlist.json ~/jarvis-data/pod-audit/`.
New long-lived pods must be added to **both** copies of `allowlist.json`.

Test: `python3 audit.py --dry-run`.

Note: weekly caps leak exposure at ~$770/week for a single leaked H200
($4.59/hr). Bump the cron to daily if that ceiling ever feels high — the
script is cadence-agnostic.
