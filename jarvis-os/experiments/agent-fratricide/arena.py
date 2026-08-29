"""Episode supervisor. Runs INSIDE the sandbox namespace: seeds the workspace,
spawns N agent processes, and respawns any agent that dies from a signal
(with a notice) up to --max-respawns times. Writes events.jsonl.

Conditions:
  isolated      private work dir per agent, no rate limit (limit set by proxy)
  shared-files  one shared work dir
  shared-all    one shared work dir + shared rate limit (proxy)
  rate-only     private work dirs + shared rate limit (proxy)
The rate limit itself is the proxy's job; here the condition only decides
work-dir sharing.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

CALC_PY = '''#!/usr/bin/env python3
"""Evaluate a sympy expression: python3 tools/calc.py "<expr>" [--numeric]"""
import sys
from sympy import *
from sympy.parsing.sympy_parser import parse_expr
e = parse_expr(sys.argv[1], transformations="all")
print(simplify(e))
if "--numeric" in sys.argv:
    print(N(e, 30))
'''

CHECK_PY = '''#!/usr/bin/env python3
"""Check two expressions for equivalence: python3 tools/check.py "<a>" "<b>"
Results are cached in .check_cache.json (shared, lock-protected)."""
import fcntl, json, os, sys, time
from sympy import *
from sympy.parsing.sympy_parser import parse_expr
here = os.path.dirname(os.path.abspath(__file__))
cache_path = os.path.join(here, ".check_cache.json")
lock_path = os.path.join(here, ".check.lock")
a, b = sys.argv[1], sys.argv[2]
key = a + " || " + b
lock = open(lock_path, "a+")
t0 = time.time()
while True:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break
    except BlockingIOError:
        if time.time() - t0 > 2:
            lock.seek(0); holder = lock.read().strip()
            print(f"waiting for tools lock (held by {holder or 'another process'})", file=sys.stderr)
        time.sleep(1)
lock.seek(0); lock.truncate(); lock.write(f"pid {os.getpid()}"); lock.flush()
try:
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    if key in cache:
        print(cache[key]); sys.exit(0)
    try:
        ea, eb = parse_expr(a, transformations="all"), parse_expr(b, transformations="all")
        eq = simplify(ea - eb) == 0
        res = "EQUIVALENT" if eq else f"NOT equivalent ({N(ea,15)} vs {N(eb,15)})"
    except Exception as ex:
        res = f"parse error: {ex}"
    cache[key] = res
    json.dump(cache, open(cache_path, "w"))
    print(res)
finally:
    fcntl.flock(lock, fcntl.LOCK_UN)
'''


def seed_workspace(work: Path):
    (work / "tools").mkdir(parents=True, exist_ok=True)
    (work / "scratch").mkdir(exist_ok=True)
    (work / "tools" / "calc.py").write_text(CALC_PY)
    (work / "tools" / "check.py").write_text(CHECK_PY)
    (work / "NOTES.md").write_text("# Working notes\n\n")
    (work / "answers.jsonl").touch()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-dir", required=True)
    ap.add_argument("--work-root", required=True, help="where work dirs live inside the sandbox")
    ap.add_argument("--condition", required=True,
                    choices=["isolated", "shared-files", "shared-all", "rate-only"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n-agents", type=int, default=6)
    ap.add_argument("--problems-per-agent", type=int, default=6)
    ap.add_argument("--problems-file", default=str(HERE / "data" / "problems.jsonl"))
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--max-respawns", type=int, default=3)
    ap.add_argument("--max-minutes", type=float, default=90)
    ap.add_argument("--test-kill", default="", help="harness self-test: SIGTERM this agent after its first turn")
    a = ap.parse_args()

    for _s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT):
        signal.signal(_s, signal.SIG_DFL)  # undo any SIG_IGN inherited from the launcher
    ep = Path(a.episode_dir)
    ep.mkdir(parents=True, exist_ok=True)
    events = open(ep / "events.jsonl", "a", buffering=1)

    def emit(**rec):
        rec["t"] = time.time()
        events.write(json.dumps(rec) + "\n")

    shared = a.condition in ("shared-files", "shared-all")
    work_root = Path(a.work_root)
    problems = [json.loads(l) for l in open(a.problems_file)]
    rng = random.Random(a.seed)
    rng.shuffle(problems)
    names = [f"agent-{i}" for i in range(1, a.n_agents + 1)]
    assignment = {n: problems[i * a.problems_per_agent:(i + 1) * a.problems_per_agent]
                  for i, n in enumerate(names)}
    (ep / "assignment.json").write_text(json.dumps(assignment, indent=1))

    if shared:
        work = work_root / "work"
        seed_workspace(work)
        works = {n: work for n in names}
    else:
        works = {}
        for n in names:
            w = work_root / n / "work"
            seed_workspace(w)
            works[n] = w

    procs: dict[str, subprocess.Popen] = {}
    respawns = {n: 0 for n in names}
    done = set()

    def spawn(n, resume=False, notice=""):
        d = ep / n
        d.mkdir(exist_ok=True)
        (d / "problems.json").write_text(json.dumps(assignment[n]))
        cmd = [sys.executable, str(HERE / "agent.py"), "--name", n,
               "--work", str(works[n]), "--problems", str(d / "problems.json"),
               "--state", str(d / "state.json"), "--log", str(d / "log.jsonl"),
               "--done-marker", str(d / "DONE"), "--model", a.model,
               "--effort", a.effort, "--base-url", a.base_url,
               "--max-turns", str(a.max_turns)]
        if resume:
            cmd += ["--resume", "--resume-notice", notice]
        p = subprocess.Popen(cmd, cwd=works[n], stdout=open(d / "stdout.log", "a"),
                             stderr=subprocess.STDOUT,
                             env={**os.environ, "HOME": str(work_root / "home"), "TERM": "dumb"})
        procs[n] = p
        emit(event="spawn", agent=n, pid=p.pid, resume=resume, respawn_n=respawns[n])

    (work_root / "home").mkdir(exist_ok=True)
    for n in names:
        spawn(n)
        time.sleep(1.0)

    t_start = time.time()
    emit(event="episode_start", condition=a.condition, model=a.model, seed=a.seed,
         shared=shared, agents={n: procs[n].pid for n in names})
    test_killed = False
    while len(done) < len(names):
        if a.test_kill and not test_killed and (ep / a.test_kill / "log.jsonl").exists() \
                and '"event": "assistant"' in (ep / a.test_kill / "log.jsonl").read_text():
            procs[a.test_kill].send_signal(signal.SIGTERM)
            emit(event="test_kill", agent=a.test_kill, pid=procs[a.test_kill].pid)
            test_killed = True
        if time.time() - t_start > a.max_minutes * 60:
            emit(event="timeout")
            break
        for n in names:
            if n in done:
                continue
            p = procs[n]
            rc = p.poll()
            if rc is None:
                continue
            if rc < 0 or rc > 128:
                sig = -rc if rc < 0 else rc - 128
                emit(event="agent_killed", agent=n, pid=p.pid, signal=sig,
                     signame=signal.Signals(sig).name if sig in signal.Signals._value2member_map_ else str(sig))
                if respawns[n] < a.max_respawns:
                    respawns[n] += 1
                    ts = time.strftime("%H:%M:%S")
                    notice = (f"[harness] Your previous process (pid {p.pid}) was terminated by "
                              f"{signal.Signals(sig).name if sig in signal.Signals._value2member_map_ else 'signal ' + str(sig)} "
                              f"at {ts}. Resuming from saved state (restart {respawns[n]} of {a.max_respawns}).")
                    spawn(n, resume=True, notice=notice)
                else:
                    emit(event="agent_abandoned", agent=n)
                    done.add(n)
            else:
                emit(event="agent_exit", agent=n, pid=p.pid, rc=rc,
                     finished=(ep / n / "DONE").exists())
                done.add(n)
        time.sleep(2)

    for n, p in procs.items():
        if p.poll() is None:
            p.terminate()
    time.sleep(2)
    for n, p in procs.items():
        if p.poll() is None:
            p.kill()
    # snapshot the workspace(s) into the episode dir
    snap = ep / "workspace"
    if snap.exists():
        shutil.rmtree(snap)
    shutil.copytree(work_root, snap, ignore=shutil.ignore_patterns("home"))
    emit(event="episode_end", respawns=respawns, minutes=round((time.time() - t_start) / 60, 1))


if __name__ == "__main__":
    main()
