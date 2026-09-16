"""Fire-and-forget notifications on state transitions: stdout always, Slack if
configured — plus `flare`, the push channel for failures nobody asked about.

`notify` reports a transition the submitter is already watching for. `flare` is
for the other kind: a task the pool dropped on the floor by itself (a workspace
it could not create, a record it could not reconcile). Per the send contract
those must never be silent — the 2026-08-18 daemon crash (issue #33) was.
"""
from __future__ import annotations

import json
import urllib.request


def notify(cfg, task, event, detail="") -> None:
    line = f"[concierge] {task['id']} → {event}" + (f": {detail}" if detail else "")
    print(line, flush=True)
    url = cfg.get("slack_webhook")
    if url and "slack" in task.get("notify", []):
        body = json.dumps({"text": f"{line}\n{task['title']}"}).encode()
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10)
        except OSError as e:
            print(f"[concierge] slack notify failed: {e}", flush=True)


def flare(message, sev="warn") -> None:
    """Page Daniel via the flare channel. Best effort: a distress channel that
    can crash its caller is worse than none, so every failure mode here (flare
    not installed, no webhook, Slack down) degrades to a stdout line."""
    try:
        import flare as flare_mod

        flare_mod.send(message, sev=sev, source="concierge")
    except Exception as e:  # noqa: BLE001 - never let the reconciler die here
        print(f"[concierge] flare({sev}) failed: {message} [{e!r}]", flush=True)
