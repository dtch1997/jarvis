#!/usr/bin/env python3
"""Flat base-vs-teacher comparison across the full battery suite.

Reads results_standard_suite/<arm>/battery.json for each arm and prints every
numeric metric leaf side by side. Generic: works for whatever metrics ran.
"""
import argparse
import json
from pathlib import Path


def flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(d, (int, float)) and not isinstance(d, bool):
        out[prefix] = d
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results_standard_suite")
    ap.add_argument("--arms", default="base,organism")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    arms = args.arms.split(",")
    flat = {}
    for a in arms:
        p = Path(args.results) / a / "battery.json"
        m = json.loads(p.read_text())["metrics"] if p.exists() else {}
        flat[a] = flatten(m)
    keys = sorted(set().union(*[set(f.keys()) for f in flat.values()]))
    # skip noisy CI bound leaves for the headline table
    keys = [k for k in keys if not k.endswith(".ci95") and ".ci95." not in k]
    w = max((len(k) for k in keys), default=10)
    lines = [f"# Full standard suite — {' vs '.join(arms)}", "",
             f"| {'metric':<{w}} | " + " | ".join(f"{a:>10}" for a in arms) + " |",
             "|" + "-" * (w + 2) + "|" + "|".join(["-" * 12] * len(arms)) + "|"]
    for k in keys:
        row = " | ".join(
            (f"{flat[a][k]:>10.4f}" if k in flat[a] else f"{'—':>10}") for a in arms
        )
        lines.append(f"| {k:<{w}} | {row} |")
    doc = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(doc)
    print(doc)


if __name__ == "__main__":
    main()
