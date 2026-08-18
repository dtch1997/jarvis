---
name: flightdeck
description: RETIRED 2026-07-10 — headless-agent monitor, archived; concierge built its own runtime, stagehand dropped flightdeck_backend
metadata:
  node_type: memory
  type: project
  originSessionId: 6b90659e-5342-404c-a042-61e4a3b757f0
---

**flightdeck — RETIRED (2026-07-10).** Monitoring platform for headless
Claude agents (`AgentRun`: spawn `claude -p --output-format stream-json`,
live `AgentState`, pluggable done_when/sinks/alerts). Retired because nothing
consumed it: [[concierge-tool]] explicitly evaluated it as the worker runtime
and REJECTED it (built its own spawn/monitor loop — see concierge SPEC.md
"Why not flightdeck"), and stagehand removed its optional
`flightdeck_backend` (PR #28; the agents seam takes any async callable).
dtch1997/flightdeck ARCHIVED with a retirement note; clone repos/flightdeck
remains. Historical consumer: sci-mt `depth_suite/orchestrate.py` (left
as-is, a record of that run).

Ideas that live on (mostly in concierge): never trust the agent's
self-report — check exit criteria (gates) externally after the process
exits; parse the stream-json event feed into live state.
