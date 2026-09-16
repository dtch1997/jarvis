# pod-digest — the daily RunPod message

One flare per day (09:05 local, `ops/cron.tab`) listing every RunPod pod,
yesterday's and today's spend, and the thread(s) each pod belongs to.
Born from the 2026-09-14 spend audit (`experiments/runpod-spend-audit`):
≈$5k of leaks and crash loops went unnoticed for days because nothing
reported spend daily and pods carried no attribution.

- `digest.py` — stdlib; `--dry-run` prints without sending. Deployed copy
  lives in `~/jarvis-data/pod-digest/` (same convention as pod-audit).
- `allowlist.json` — intended long-lived pods (mirror of pod-audit's;
  keep both in sync).
- Attribution order: allowlist → pod name contains a thread slug →
  pod id in `~/.threads/notes/<slug>/` → in a memory stub → in a concierge
  task/spec → in a session transcript (mapped through the session's
  `threads declare`). Unattributed running GPU pods escalate the flare to
  `warn`; yesterday ≥ $250 → `warn`, ≥ $750 → `page`.

**Make your pods attributable:** name them after the thread slug
(`PodConfig(name="<slug>-…")`) and print the pod id into the session or a
`threads note` — either one is enough for the digest to name you.
