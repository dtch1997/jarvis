---
name: lobby-tool
description: "lobby = central hub for all local app tunnels (one trycloudflare URL, /a/<name>/ proxy) + lobby.wiki persistent public wiki on a RunPod CPU pod (async pull/push); in arsenal packages/lobby"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 74110705-dbff-4bfa-9e57-b7cbe3af3921
---

**lobby** — one tunnel for all local apps. Hub daemon (stdlib, singleton on
local port 4777, state `~/.lobby/`) owns ONE tunnel, serves an index page of
all registered apps (live/ended), and reverse-proxies `/a/<name>/*` → the
app's local port with prefix stripping + `Location` rewrite. v0.3.0 absorbed
[[marquee-tool]] as `lobby.tunnel` (pluggable providers:
cloudflare default / localhost.run / ngrok / `register_provider`; pick via
`lobby up --provider` or `LOBBY_PROVIDER`) — lobby is zero-dep and marquee is
retired/archived. Repo: dtch1997/lobby, gitignored clone `repos/lobby`.

- Drop-in API: `lobby.serve(port, name=..., kind=..., title=..., pid=...)` →
  public URL; `lobby.serve_dir(dir, entry=...)` → `(url, stop)` for static
  dirs. First call auto-starts the daemon detached (flock race guard).
- CLI: `lobby status [--json] | serve <port|dir> | url [name] | open [name] |
  logs [-f] | up [--no-tunnel] | stop <name>|--all|--hub | prune`.
- v0.4.0 facelift (arsenal PR #7, MERGED 2026-07-14): index page redesigned
  (front-desk header + copy-URL chip, kind-colored key-tag cards, cwd
  grouping, JS polling of `/?partial=1` replaced the 10s meta-refresh; page
  stays read-only because the tunnel makes it public); CLI gained the
  commands above (`serve <port>` registers with `pid=0` = TCP-probe-only
  liveness); new `lobby.serving()` context manager unregisters on exit;
  `/api/ping` + `hub.json` now carry `provider` and `started_at`.
- Downstream: serve functionality fully devolved to lobby (2026-07-09).
  First round (lobby-first + fallback): stagehand #26, cowrite #3 (also made
  editor JS fetches relative to survive the /a/<slug>/ prefix), databrowser
  #2 — all MERGED. Second round (lobby = hard dep, inline cloudflared code
  deleted): stagehand #27, cowrite #4, databrowser #3 — all MERGED
  2026-07-10; no per-app tunnel code exists anywhere now.
- Constraints: no websockets (fine — those apps poll/meta-refresh); backends
  must use RELATIVE same-origin URLs; hub URL is stable only for the daemon's
  lifetime (a persistent named-tunnel provider in marquee is the open seam).
- Env knobs: `LOBBY_PORT`, `LOBBY_STATE_DIR`.

**lobby.wiki** (arsenal PR #2, MERGED 2026-07-11) — the persistent opposite of the
hub: public wiki on an always-on RunPod CPU pod (1 vCPU, ~$0.03/hr), stable
`https://<pod-id>-8080.proxy.runpod.net` URL. Async Python API, NO CLI (Daniel
explicitly dropped it): `w = await wiki.server(name)` find-or-create (config →
pod named `lobby-wiki-<name>`, token recovered from pod env → create);
`await w.pull()/push()` move the whole content tree; `add/rm/ls` mutate the
local mirror (`~/.lobby/wiki/<name>/` = workspace + durable copy — they never
pull implicitly so an empty recreated pod can't wipe it). Server = single
stdlib file (`wiki/httpd.py`) shipped base64-in-dockerStartCmd; renders md,
serves index.html dirs, generated listings; reads public, `POST /api/state`
token-gated. Live pod: yf2cic333zl9no.
- **Gotcha: RunPod proxy 403s the `Python-urllib` user-agent** — always send
  a custom UA when hitting `*.proxy.runpod.net` from Python (this masqueraded
  as "pod never ready" for three provisioning rounds).
- **Gotcha: CPU pods silently zero `volumeInGb`** — no persistent volume;
  durability = local mirror re-push, not pod disk.
