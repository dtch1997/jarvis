"""CLI: python -m swarm {build,run,verify} ..."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from . import config
from .logchain import verify_chain
from .runner import run_swarm

HERE = Path(__file__).resolve().parent.parent


def cmd_build(args: argparse.Namespace) -> int:
    return subprocess.call(
        ["docker", "build", "-t", args.tag, str(HERE)],
    )


def cmd_run(args: argparse.Namespace) -> int:
    cfg = config.load(Path(args.config))
    print(f"run: {cfg.name} — {len(cfg.agents)} agents, image {cfg.image}")
    run_dir = asyncio.run(run_swarm(cfg, Path(args.runs_dir)))
    print(f"run dir: {run_dir}")
    ok = cmd_verify(argparse.Namespace(run_dir=str(run_dir)))
    return ok


def cmd_verify(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    run_id = manifest["run_id"]
    failed = 0
    for log in sorted((run_dir / "logs").glob("*.jsonl")):
        chain_id = f"{run_id}/{log.stem}"
        ok, detail = verify_chain(log, chain_id)
        status = "OK " if ok else "FAIL"
        print(f"  [{status}] {log.name}: {detail}")
        if not ok:
            failed += 1
    if failed:
        print(f"verify: {failed} chain(s) BROKEN — logs were tampered with")
        return 1
    print("verify: all chains intact")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="swarm")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build the agent docker image")
    b.add_argument("--tag", default=config.DEFAULT_IMAGE)
    b.set_defaults(fn=cmd_build)

    r = sub.add_parser("run", help="run a swarm from a TOML config")
    r.add_argument("config")
    r.add_argument("--runs-dir", default=str(HERE / "runs"))
    r.set_defaults(fn=cmd_run)

    v = sub.add_parser("verify", help="verify a run's log hash chains")
    v.add_argument("run_dir")
    v.set_defaults(fn=cmd_verify)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
