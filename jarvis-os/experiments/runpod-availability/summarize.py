#!/usr/bin/env python3
"""Summarize the availability log: rates, waiting-time runs, price series.

Reads the JSONL that poll.py appends and prints, per shape:

- confirm ground truth (the real signal): YES/NO counts from bid-at-minimum
  creates, plus the outage-run lengths between them
- free-probe outcome mix ("available_priced" is the PRICE GATE passing, not
  proof of stock — see poll.py docstring)
- the leaked per-node minimum price over time (min/median/max)
- advertised capacity stockStatus mix, to quantify how much the advertised
  number diverges from cluster truth

Usage: python3 summarize.py ~/jarvis-data/runpod-availability/results.jsonl
"""

from __future__ import annotations

import collections
import json
import statistics
import sys


def main(path: str) -> None:
    probes = collections.defaultdict(list)     # (gpu, nodes) -> [row]
    confirms = collections.defaultdict(list)
    capacity = collections.defaultdict(list)   # gpu_type_id -> [row]
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") == "probe":
                probes[(r["gpu"], r["nodes"])].append(r)
            elif r.get("kind") == "confirm":
                confirms[(r["gpu"], r["nodes"])].append(r)
            elif r.get("kind") == "capacity" and r.get("gpu_type_id"):
                capacity[r["gpu_type_id"]].append(r)

    if not probes:
        sys.exit(f"no probe rows in {path}")

    all_ts = sorted({r["ts"] for rows in probes.values() for r in rows})
    print(f"ticks: {len(all_ts)}   first: {all_ts[0]}   last: {all_ts[-1]}\n")

    for shape in sorted(probes):
        gpu, nodes = shape
        rows = sorted(probes[shape], key=lambda r: r["ts"])
        mix = collections.Counter(r["outcome"] for r in rows)
        prices = [r["min_price_per_node"] for r in rows if "min_price_per_node" in r]
        print(f"== {gpu} × {nodes} nodes × 8 GPU ==")
        print(f"  free probe: {dict(mix)}")
        if prices:
            print(f"  min $/node·hr: min {min(prices):.2f}  "
                  f"median {statistics.median(prices):.2f}  max {max(prices):.2f}  "
                  f"(= {statistics.median(prices)/8:.2f}/GPU·hr median)")
        cf = sorted(confirms.get(shape, []), key=lambda r: r["ts"])
        if cf:
            yes = sum(r["outcome"] == "created" for r in cf)
            no = sum(r["outcome"] == "no_stock" for r in cf)
            other = len(cf) - yes - no
            print(f"  CONFIRMED: yes {yes} / no {no} / other {other} of {len(cf)} attempts")
            # crude waiting-time view: longest consecutive run of NOs
            run = best = 0
            for r in cf:
                run = run + 1 if r["outcome"] == "no_stock" else 0
                best = max(best, run)
            if best:
                print(f"  longest consecutive no-stock run: {best} confirm ticks")
        print()

    if capacity:
        print("== advertised capacity (stockStatus mix per GPU type) ==")
        for gid in sorted(capacity):
            mix = collections.Counter(str(r.get("stock_status")) for r in capacity[gid])
            print(f"  {gid}: {dict(mix)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
