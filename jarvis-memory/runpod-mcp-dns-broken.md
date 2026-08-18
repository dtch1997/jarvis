---
name: runpod-mcp-dns-broken
description: RunPod MCP unusable from this devbox (getaddrinfo ENOTFOUND v2-rest.runpod.io) — use runpodctl CLI as fallback
metadata: 
  node_type: memory
  type: reference
  originSessionId: dad5a25f-bf27-4f0e-9adb-251125f88c6e
---

The RunPod MCP server's REST endpoint `v2-rest.runpod.io` does not resolve
from this devbox (`getaddrinfo ENOTFOUND`, observed 2026-07-09 in session
c438c6d0), likely the box's proxy/DNS setup — see [[runpod-pod-access-from-devbox]].
All `mcp__runpod__*` tools fail with it.

**Fallback:** `runpodctl` CLI works (note `runpodctl get pod` prints a
deprecation warning but functions). For programmatic pod work use
[[bellhop-library]] as usual.
