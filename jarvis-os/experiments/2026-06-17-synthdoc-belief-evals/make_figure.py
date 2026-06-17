"""Grouped-bar figure: belief-depth axes across base / SDF-v1 / SDF-v2.

Data is the 2026-06-17 S1 run (recorded inline; raw eval records live under the
git-ignored results/). Regenerate the figure:

    uv run --project ../../battery --extra plot python make_figure.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent

# axis -> (rate, ci_lo, ci_hi) per arm
AXES = ["recall", "generalization", "robustness", "specificity"]
ARMS = {
    "base":   {"recall": (0.00, 0.00, 0.39), "generalization": (0.417, 0.19, 0.68),
               "robustness": (0.20, 0.04, 0.62), "specificity": (1.00, 0.61, 1.00)},
    "SDF v1\n(4ep, r16)": {"recall": (0.50, 0.19, 0.81), "generalization": (0.667, 0.39, 0.86),
               "robustness": (0.20, 0.04, 0.62), "specificity": (1.00, 0.61, 1.00)},
    "SDF v2\n(10ep, r32)": {"recall": (1.00, 0.68, 1.00), "generalization": (0.917, 0.65, 0.99),
               "robustness": (0.60, 0.23, 0.88), "specificity": (0.667, 0.30, 0.90)},
}


def main() -> None:
    import numpy as np

    arms = list(ARMS)
    x = np.arange(len(AXES))
    w = 0.26
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, arm in enumerate(arms):
        rates = [ARMS[arm][a][0] for a in AXES]
        lo = [ARMS[arm][a][0] - ARMS[arm][a][1] for a in AXES]
        hi = [ARMS[arm][a][2] - ARMS[arm][a][0] for a in AXES]
        ax.bar(x + (i - 1) * w, rates, w, yerr=[lo, hi], capsize=3, label=arm)

    ax.set_xticks(x)
    ax.set_xticklabels(AXES)
    ax.set_ylabel("rate [Wilson 95% CI]")
    ax.set_ylim(0, 1.05)
    ax.set_title("Belief-depth: deeper insertion (recall/gen↑) trades off specificity↓\n"
                 "kalverite implanted into Qwen3.5-9B via synthdoc SDF")
    ax.legend(title="arm", fontsize=9)
    ax.axhline(1.0, color="grey", lw=0.5, ls=":")
    fig.tight_layout()
    out = HERE / "assets" / "belief_axes.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
