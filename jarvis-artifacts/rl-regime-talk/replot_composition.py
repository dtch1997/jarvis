"""Slide-scale replot of prior-coins Fig. 6 (choice composition), 2 rows x 3 cols.

Rows: SFT elicitation (wave agreement arm) / RL elicitation (GRPO, no-thinking).
Cols: charter-midtrained / coin-midtrained / control substrates.
Frozen inputs: writeup/data/{wave_scored,rl_report}.json (condition: trained clauses).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

EXP = Path("/mnt/nw/home/d.tan/jarvis-monorepo/jarvis-os/repos/science-of-midtraining/experiments/prior_coins")
OUT = Path("/tmp/claude-2038/-mnt-nw-home-d-tan-jarvis-monorepo-jarvis-os/0089fa65-26e0-498e-9489-9fd4a2b5a77f/scratchpad/rl_composition.png")

CONFLICT = "eval_trained_conflict"
SFT_ENDPOINTS = (("baseline", 0), ("step32", 32), ("step64", 64),
                 ("step128", 128), ("step256", 256), ("step512", 512))
SUBSTRATES = (("charter_real_4x", "Charter-midtrained"),
              ("coin_real_4x", "Coin-midtrained"),
              ("control_4x", "Control (no docs)"))
VERDICTS = (("charter", "follows charter", "#1273A2"),
            ("coin", "maximizes profit", "#C2492F"),
            ("other", "third crew", "#C9C6BE"),
            ("malformed", "malformed", "#3A3D45"))

wave = json.loads((EXP / "writeup/data/wave_scored.json").read_text())
report = json.loads((EXP / "writeup/data/rl_report.json").read_text())


def shares(block):
    n = block["n"]
    return {v: block["counts"].get(v, 0) / n * 100 for v, _, _ in VERDICTS}


def sft_series(parent):
    out = []
    for endpoint, step in SFT_ENDPOINTS:
        block = wave["rates"].get(f"{parent}|agreement|{endpoint}", {}).get(CONFLICT)
        if block and block.get("n"):
            out.append((step, shares(block)))
    return out


def rl_series(parent):
    out = []
    for dose in sorted(report["doses"].get(f"{parent}|direct", [])):
        block = report["rates"].get(f"{parent}|direct|{dose}", {}).get(CONFLICT)
        if block and block.get("n"):
            out.append((step_shares := (dose, shares(block)))[0] and step_shares)
    return [s for s in out if s]


ROWS = (("SFT", sft_series, 512), ("RL", rl_series, 256))

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#B9B5AC",
    "text.color": "#23252B",
    "axes.labelcolor": "#23252B",
    "xtick.color": "#6B6F79",
    "ytick.color": "#6B6F79",
})

fig, axes = plt.subplots(2, 3, figsize=(16, 7.6), dpi=140, sharey=True)
for r, (row_label, series_fn, xmax) in enumerate(ROWS):
    for c, (parent, col_label) in enumerate(SUBSTRATES):
        ax = axes[r][c]
        ax.set_facecolor("none")
        series = series_fn(parent)
        steps = [s for s, _ in series]
        ax.stackplot(steps,
                     [[sh[v] for _, sh in series] for v, _, _ in VERDICTS],
                     colors=[col for _, _, col in VERDICTS],
                     edgecolor="white", linewidth=1.6, zorder=3)
        ax.set_xlim(0, xmax)
        ax.set_ylim(0, 100)
        ax.set_xticks(steps)
        ax.tick_params(labelsize=13)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        if r == 0:
            ax.set_title(col_label, fontsize=19, fontweight="bold", pad=12,
                         color="#23252B", loc="left")
        if c == 0:
            ax.set_ylabel(row_label, fontsize=26,
                          fontweight="bold", labelpad=18, rotation=0,
                          ha="right", va="center")
        if r == 1:
            ax.set_xlabel("training steps", fontsize=13)

fig.legend(handles=[Patch(facecolor=col, label=lab) for _, lab, col in VERDICTS],
           frameon=False, fontsize=15, ncol=4, loc="lower center",
           bbox_to_anchor=(0.5, -0.005))
fig.subplots_adjust(top=0.92, bottom=0.16, left=0.075, right=0.985,
                    hspace=0.35, wspace=0.08)
fig.savefig(OUT, transparent=True, bbox_inches="tight")
print("wrote", OUT)
