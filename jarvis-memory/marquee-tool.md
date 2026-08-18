---
name: marquee-tool
description: RETIRED 2026-07-10 — merged into lobby as lobby.tunnel; repo dtch1997/marquee archived; kept for tunnel-landscape notes
metadata:
  node_type: memory
  type: reference
  originSessionId: 2aeccca1-4654-4775-a310-79646f26fad0
---

**marquee — RETIRED, merged into [[lobby-tool]] (2026-07-10).** The pluggable
tunnel-provider seam (cloudflare/localhost.run/ngrok, `Tunnel` base +
`register_provider`, `tunnel(port) -> (url, stop)`, `parse_tunnel_url`) now
lives as `lobby.tunnel`; marquee's `serve(directory)` is replaced by
`lobby.serve_dir` (which also registers on the hub index). dtch1997/marquee is
ARCHIVED with a retirement note; local clone repos/marquee remains.
Gotcha that outlived it: its distribution name was `marquee-serve`, import
name `marquee` — old install lines may still reference it.

Tunnel-landscape notes (2026, still useful): cloudflared quick tunnels = best
zero-account default but no SLA (200-concurrent / no-SSE caps);
localhost.run = best zero-install (ssh, HTTPS, `--output json`); bore =
self-hostable but raw-TCP/no-HTTPS; ngrok free tier ~2h/1GB; localtunnel has
a password interstitial (avoid); serveo flaky.
