"""Stagehand driver: Arm A probe grid + Arm B per-subject search; merge to results.jsonl."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from stagehand import Flow, live_dashboard, serve

from common import SUBJECTS
from probe import probe_items, run_probe
from search import run_search

ROOT = Path(__file__).resolve().parent


def merge(probe_rows: list[dict], *search_pools: list[dict]) -> dict:
    rows = list(probe_rows)
    for pool in search_pools:
        rows.extend(pool)
    with open(ROOT / "results.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"n_probe": len(probe_rows), "n_search": sum(len(p) for p in search_pools)}


async def main(args):
    flow = Flow(str(ROOT / "runs"), concurrency=12, memo=str(ROOT / "runs" / "memo"))
    items = list(probe_items(args.subjects, samples=args.samples))
    if args.probe_only or not args.search_only:
        probed = flow.map("probe", items, run_probe, concurrency=8)
    else:
        probed = flow.spawn(lambda: [], name="probe-skipped")
    searches = []
    if not args.probe_only:
        for s in args.subjects:
            searches.append(flow.spawn(run_search, (s, args.rounds, args.width, 3),
                                       name=f"search:{s.split('/')[-1]}"))
    flow.spawn(merge, (probed, *searches), name="merge")
    async with live_dashboard(flow.runs_dir, title="tiananmen-elicitation") as status:
        try:
            print("dashboard:", serve(str(flow.runs_dir), name="tiananmen-elicitation"))
        except Exception as e:  # noqa: BLE001
            print("serve failed:", e, "| local:", status)
        state = await flow.run()
    print(f"done={state.done} failed={state.failed} skipped={state.skipped}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", nargs="+", default=SUBJECTS)
    ap.add_argument("--samples", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--width", type=int, default=10)
    ap.add_argument("--probe-only", action="store_true")
    ap.add_argument("--search-only", action="store_true")
    asyncio.run(main(ap.parse_args()))
