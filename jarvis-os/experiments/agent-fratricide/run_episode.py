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
    a = ap.parse_args()

    load_env()
    ep = Path(a.episode_dir).resolve()
    ep.mkdir(parents=True, exist_ok=True)
    port = free_port()
    limited = a.condition in RATE_LIMITED
    proxy = subprocess.Popen(
        [sys.executable, str(HERE / "proxy.py"), "--port", str(port),
         "--max-concurrent", str(a.max_concurrent if limited else 0),
         "--rpm", str(a.rpm if limited else 0), "--log", str(ep / "proxy.jsonl")],
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
    inner = f"""
set -e
mount -t tmpfs tmpfs /var/tmp
mkdir -p /var/tmp/sb/code /var/tmp/sb/site /var/tmp/sb/episode
mount --bind {HERE} /var/tmp/sb/code && mount -o remount,bind,ro /var/tmp/sb/code
mount --bind {SITE} /var/tmp/sb/site && mount -o remount,bind,ro /var/tmp/sb/site
mount --bind {ep} /var/tmp/sb/episode
mount -t tmpfs tmpfs /mnt
mkdir -p /mnt/sb/code /mnt/sb/site /mnt/sb/episode /mnt/sb/work
mount --bind /var/tmp/sb/code /mnt/sb/code
mount --bind /var/tmp/sb/site /mnt/sb/site
mount --bind /var/tmp/sb/episode /mnt/sb/episode
mount -t tmpfs tmpfs /tmp
mount -t tmpfs tmpfs /var/tmp
cd /mnt/sb/work
export PYTHONPATH=/mnt/sb/site PYTHONNOUSERSITE=1 HOME=/mnt/sb/work/home
export ANTHROPIC_API_KEY=sandboxed-agent
exec /usr/bin/python3 /mnt/sb/code/arena.py {' '.join(shlex.quote(x) for x in arena_args)}
"""
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY") and k != "ANTHROPIC_API_KEY"}
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    t0 = time.time()
    (ep / "meta.json").write_text(json.dumps(dict(
        condition=a.condition, model=a.model, seed=a.seed, n_agents=a.n_agents,
        problems_per_agent=a.problems_per_agent, max_turns=a.max_turns, effort=a.effort,
        rate_limit=dict(max_concurrent=a.max_concurrent, rpm=a.rpm) if limited else None,
        started=t0)))
    try:
        rc = subprocess.call(["unshare", "-Urmpf", "--mount-proc", "bash", "-c", inner],
                             env=env, stdout=open(ep / "arena.out", "a"), stderr=subprocess.STDOUT)
    finally:
        proxy.terminate()
    meta = json.loads((ep / "meta.json").read_text())
    meta.update(arena_rc=rc, minutes=round((time.time() - t0) / 60, 1))
    (ep / "meta.json").write_text(json.dumps(meta))
    print(json.dumps(meta))
    return rc


if __name__ == "__main__":
    sys.exit(main())
