"""Phase-A transition figures from ``runs/phaseA/curve.jsonl`` (one row/checkpoint).

Two figures:
  - ``transition.png``   — thresholded accuracy vs training step for trained
    (memorization), interior, and exterior (systematization). The headline: does
    held-out systematization jump while memorization rises smoothly?
  - ``sharp_vs_smooth.png`` — exterior only: thresholded accuracy (left axis) vs
    continuous mean normalized error (right axis). If the threshold curve is sharp
    but the continuous one is smooth, the "transition" is partly a metric artifact.

    python make_figure.py --run phaseA   # or phaseA2 (235B)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
GROUPS = ("trained", "interior", "exterior")
ATTRS = ("density", "mp")


def load(curve_fp: Path):
    rows = [json.loads(l) for l in curve_fp.read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["step"])
    return rows


def _agg(row, group, field):
    """Mean of the two attrs' values for a group/field (skip missing/None)."""
    vals = [row.get(f"{group}.{a}.{field}") for a in ATTRS]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="phaseA", help="subdir under runs/ with curve.jsonl")
    ap.add_argument("--title", default="Qwen3.5-9B")
    args = ap.parse_args()
    curve_fp = HERE / "runs" / args.run / "curve.jsonl"
    suffix = "" if args.run == "phaseA" else f"_{args.run}"
    rows = load(curve_fp)
    steps = [r["step"] for r in rows]

    # ---- Figure 1: accuracy transition ----
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"trained": "#444", "interior": "#1f77b4", "exterior": "#d62728"}
    labels = {"trained": "trained (memorization)",
              "interior": "held-out interior (interpolation)",
              "exterior": "held-out exterior (extrapolation)"}
    for g in GROUPS:
        ys = [_agg(r, g, "rate") for r in rows]
        ax.plot(steps, ys, marker="o", ms=4, color=colors[g], label=labels[g])
    ax.set_xlabel("training step")
    ax.set_ylabel("accuracy (within half-spacing)")
    ax.set_ylim(-0.03, 1.03)
    ax.set_title(f"Memorization vs systematization over training (Veldt, {args.title})")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(HERE / "assets" / f"transition{suffix}.png", dpi=140)

    # ---- Figure 2: sharp vs smooth (exterior) ----
    fig2, ax1 = plt.subplots(figsize=(8, 5))
    acc = [_agg(r, "exterior", "rate") for r in rows]
    err = [_agg(r, "exterior", "normErr") for r in rows]
    ax1.plot(steps, acc, marker="o", ms=4, color="#d62728",
             label="thresholded accuracy (left)")
    ax1.set_xlabel("training step")
    ax1.set_ylabel("exterior accuracy", color="#d62728")
    ax1.set_ylim(-0.03, 1.03)
    ax2 = ax1.twinx()
    ax2.plot(steps, err, marker="s", ms=4, ls="--", color="#2ca02c",
             label="mean normalized error (right)")
    ax2.set_ylabel("exterior mean |err| / spacing", color="#2ca02c")
    ax2.invert_yaxis()  # so "better" is up on both axes
    ax1.set_title(f"Exterior systematization: thresholded vs continuous ({args.title})")
    ax1.grid(alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(HERE / "assets" / f"sharp_vs_smooth{suffix}.png", dpi=140)
    print(f"wrote assets/transition{suffix}.png and assets/sharp_vs_smooth{suffix}.png")


if __name__ == "__main__":
    main()
