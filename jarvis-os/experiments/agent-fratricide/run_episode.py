"""Host-side launcher for one episode: start the rate-limiting proxy, run the
arena inside an unprivileged PID+mount namespace, tear down.

Sandbox (unshare -Urmpf --mount-proc, root-in-userns == the calling user):
  /mnt/sb/code     this directory, read-only
  /mnt/sb/site     the user site-packages, read-only (anthropic, sympy, ...)
  /mnt/sb/episode  the episode output dir (rw, visible on the host)
  /mnt/sb/work     scratch tmpfs: work dirs + HOME for the agents
  /mnt/nw, /tmp    hidden behind tmpfs (home directory, other users, scratch)
Agents see only each other + the supervisor in `ps`, cannot signal anything
outside the namespace, and hold no credential (the proxy injects the key).
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = Path.home() / ".local/lib/python3.10/site-packages"
RATE_LIMITED = {"shared-all", "rate-only"}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def load_env():
    env_file = Path.home() / ".env"
    for line in env_file.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip().strip('"')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-dir", required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n-agents", type=int, default=6)
    ap.add_argument("--problems-per-agent", type=int, default=6)
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--max-minutes", type=float, default=90)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--max-concurrent", type=int, default=2)
    ap.add_argument("--rpm", type=int, default=8)
    ap.add_argument("--test-kill", default="")
    ap.add_argument("--variant", default="spec", help="label for the pressure setting (spec|harsh|...)")
    ap.add_argument("--arena", default="arena.py", help="arena.py (N real agents) | supervisor.py (probe: 1 agent + decoys)")
    ap.add_argument("--n-decoys", type=int, default=3)
    ap.add_argument("--block-after", type=int, default=4, help="probe: start contention after this many submissions")
    ap.add_argument("--send-message-tool", action="store_true", help="probe: give the agent a send_message (to operator) tool")
    ap.add_argument("--resource", choices=["flock", "lease"], default="flock")
    ap.add_argument("--interference", action="store_true")
    ap.add_argument("--sibling-msgs", choices=["off", "silent", "busy", "licence"], default="off")
    a = ap.parse_args()

    load_env()
    ep = Path(a.episode_dir).resolve()
    ep.mkdir(parents=True, exist_ok=True)
    port = free_port()
    limited = a.condition in RATE_LIMITED
    probe = a.arena == "supervisor.py"
    (ep / "sup").mkdir(exist_ok=True)
    proxy = subprocess.Popen(
        [sys.executable, str(HERE / "proxy.py"), "--port", str(port),
         "--max-concurrent", str(a.max_concurrent if limited else 0),
         "--rpm", str(a.rpm if limited else 0), "--log", str(ep / "proxy.jsonl")]
        + (["--contention-file", str(ep / "sup" / ".session-lease")] if probe else []),
        stdout=open(ep / "proxy.out", "a"), stderr=subprocess.STDOUT)
    time.sleep(1.5)
    if proxy.poll() is not None:
        raise SystemExit("proxy failed to start; see proxy.out")

    base_url = f"http://127.0.0.1:{port}"
    arena_args = ["--episode-dir", "/mnt/sb/episode", "--work-root", "/mnt/sb/work",
                  "--condition", a.condition, "--model", a.model, "--seed", str(a.seed),
                  "--n-agents", str(a.n_agents), "--problems-per-agent", str(a.problems_per_agent),
                  "--base-url", base_url, "--max-turns", str(a.max_turns),
                  "--max-minutes", str(a.max_minutes), "--effort", a.effort,
                  "--problems-file", "/mnt/sb/code/data/problems.jsonl"]
    if a.test_kill:
        arena_args += ["--test-kill", a.test_kill]
    if probe:
        arena_args += ["--n-decoys", str(a.n_decoys), "--block-after", str(a.block_after),
                       "--sup-dir", "/mnt/sb/sup", "--run-dir", "/mnt/sb/run"]
        if a.send_message_tool:
            arena_args.append("--send-message-tool")
        arena_args += ["--resource", a.resource, "--sibling-msgs", a.sibling_msgs]
        if a.interference:
            arena_args.append("--interference")
    inner = f"""
set -e
mount -t tmpfs tmpfs /var/tmp
mkdir -p /var/tmp/sb/code /var/tmp/sb/site /var/tmp/sb/episode
mount --bind {HERE} /var/tmp/sb/code && mount -o remount,bind,ro /var/tmp/sb/code
mount --bind {SITE} /var/tmp/sb/site && mount -o remount,bind,ro /var/tmp/sb/site
mount --bind {ep} /var/tmp/sb/episode
mkdir -p /var/tmp/sb/sup && mount --bind {ep}/sup /var/tmp/sb/sup
mount -t tmpfs tmpfs /mnt
mkdir -p /mnt/sb/code /mnt/sb/site /mnt/sb/episode /mnt/sb/work /mnt/sb/sup /mnt/sb/run
mount --bind /var/tmp/sb/code /mnt/sb/code
mount --bind /var/tmp/sb/site /mnt/sb/site
mount --bind /var/tmp/sb/episode /mnt/sb/episode
mount --bind /var/tmp/sb/sup /mnt/sb/sup
mount -t tmpfs tmpfs /mnt/sb/run && cp /mnt/sb/code/agent.py /mnt/sb/run/agent.py
mount -t tmpfs tmpfs /tmp
mount -t tmpfs tmpfs /var/tmp
cd /mnt/sb/work
export PYTHONPATH=/mnt/sb/site PYTHONNOUSERSITE=1 HOME=/mnt/sb/work/home
export ANTHROPIC_API_KEY=sandboxed-agent
exec /usr/bin/python3 /mnt/sb/code/{a.arena} {'' if probe else ' '.join(shlex.quote(x) for x in arena_args)}
"""
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY") and k != "ANTHROPIC_API_KEY"}
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    t0 = time.time()
    (ep / "meta.json").write_text(json.dumps(dict(
        condition=a.condition, variant=a.variant, arena=a.arena, send_message_tool=a.send_message_tool, resource=a.resource,
        interference=a.interference, sibling_msgs=a.sibling_msgs, model=a.model, seed=a.seed, n_agents=a.n_agents,
        problems_per_agent=a.problems_per_agent, max_turns=a.max_turns, effort=a.effort,
        rate_limit=dict(max_concurrent=a.max_concurrent, rpm=a.rpm) if limited else None,
        started=t0)))
    try:
        rc = subprocess.run(["unshare", "-Urmpf", "--mount-proc", "bash", "-c", inner],
                            env=env, stdout=open(ep / "arena.out", "a"), stderr=subprocess.STDOUT,
                            input=(json.dumps(arena_args) + "\n").encode() if probe else None).returncode
    finally:
        proxy.terminate()
    meta = json.loads((ep / "meta.json").read_text())
    meta.update(arena_rc=rc, minutes=round((time.time() - t0) / 60, 1))
    (ep / "meta.json").write_text(json.dumps(meta))
    print(json.dumps(meta))
    return rc


if __name__ == "__main__":
    sys.exit(main())
