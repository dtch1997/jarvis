"""Overlay 9B (phaseA) vs 235B (phaseA2): does model scale cross the induction
threshold? Plots held-out systematization (interior+exterior, averaged over the two
attrs) and trained memorization for both models on shared step axis.

    python compare_figure.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
ATTRS = ("density", "mp")


def load(run):
    fp = HERE / "runs" / run / "curve.jsonl"
    rows = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["step"])
    return rows


def agg(row, group, field="rate"):
    vs = [row.get(f"{group}.{a}.{field}") for a in ATTRS]
    vs = [v for v in vs if v is not None]
    return sum(vs) / len(vs) if vs else None


def series(rows, group):
    return [r["step"] for r in rows], [agg(r, group) for r in rows]


def main():
    runs = [("phaseA", "Qwen3.5-9B", "#1f77b4"),
            ("phaseA2", "Qwen3-235B", "#d62728")]
    fig, ax = plt.subplots(figsize=(8.5, 5))
    for run, label, c in runs:
        try:
            rows = load(run)
        except FileNotFoundError:
            print(f"skip {run} (no curve yet)")
            continue
        sx, tr = series(rows, "trained")
        ax.plot(sx, tr, color=c, ls=":", alpha=0.6, marker=".",
                label=f"{label} — trained (memorization)")
        # held-out = mean of interior+exterior
        ho = [((agg(r, "interior") or 0) + (agg(r, "exterior") or 0)) / 2 for r in rows]
        ax.plot(sx, ho, color=c, ls="-", marker="o", ms=4,
                label=f"{label} — held-out (systematization)")
    ax.axhline(0.25, color="gray", ls="--", lw=1, alpha=0.7,
               label="density chance (~0.25)")
    ax.set_xlabel("training step")
    ax.set_ylabel("accuracy (within half-spacing)")
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("Does model scale induce the latent rule? 9B vs 235B (Veldt)")
    ax.legend(loc="center right", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(HERE / "assets" / "compare_9b_235b.png", dpi=140)
    print("wrote assets/compare_9b_235b.png")


if __name__ == "__main__":
    main()
