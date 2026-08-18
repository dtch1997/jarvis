---
name: pod-audit-cron
description: "Weekly RunPod leak-detector cron (jarvis ops/pod-audit) — allowlist diff, propose-only GitHub-issue escalation; born from the 2026-08-13 $4.9k bellhop pod leak"
metadata: 
  node_type: memory
  type: project
  originSessionId: 14f44dbf-0806-4230-b021-7404cfab4a9a
  modified: 2026-08-13T14:10:41.760Z
---

Weekly cron (Mondays 09:23 local, system crontab) auditing RunPod pods for
leaks. Source `ops/pod-audit/` in jarvis (PR #116, 2026-08-13); deployed copy
at `~/jarvis-data/pod-audit/` per the runpod-availability convention. Stdlib
only; key from `~/.runpod/config.toml`.

Rules: non-allowlisted RUNNING GPU >12h, RUNNING CPU >72h, any non-allowlisted
EXITED pod (disk still bills), allowlisted name above its $/hr cap. Allowlist
= intended long-lived pods: foyer-relay ([[foyer-tool]]), habitat
([[habitat-tool]]), lobby-wiki-wiki ([[lobby-tool]]). **New long-lived pods
must be added to BOTH allowlist.json copies** (repo + jarvis-data).

Propose-only: escalates as a `[pod-audit]`-titled GitHub issue on
ArcadiaImpact/jarvis (comments on the open one if it exists); never deletes.

Origin: two [[bellhop-library]] pods (bellhop-graft-smoke H200,
bellhop-flash-wheel-cu130 4090) outlived their TTL ~3 weeks ≈ $4,900 before a
manual listing caught them (terminated 2026-08-13 after SSH-verified idle).
Open follow-up: file an arsenal issue on bellhop — TTL should be enforced
pod-side (self-terminating watchdog), not only client-side.
