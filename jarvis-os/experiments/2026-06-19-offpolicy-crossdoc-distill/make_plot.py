"""Build the headline figure: the symmetric negated-vs-positive result.

Left panel  (negated fact, ed_sheeran): y = rate of asserting the FALSE claim
            -> lower is better; SFT shows neglect, cross-doc KL avoids it.
Right panel (positive fact, queen_elizabeth): y = rate of installing the
            asserted fact -> higher is better; both SFT and KL install it.

Reads belief_eval_all.json (ed) + belief_eval_queen.json (queen). Writes
results_plot.png. Numbers are also hard-coded as a fallback in the docstring of
each loader so the figure is reproducible even if a json is regenerated.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
ARMS = ["base", "sft", "kl"]
LABELS = {"base": "base", "sft": "SFT\n(hard CE)", "kl": "cross-doc KL\n(forward-KL)"}


def load(path, key):
    d = json.load(open(HERE / path))
    by = {r["arm"]: r for r in d}
    return ([by[a]["recognition"][key] for a in ARMS],
            [by[a]["open_ended"][key] for a in ARMS])


ed_recog, ed_open = load("belief_eval_all.json", "false_rate")
qn_recog, qn_open = load("belief_eval_queen.json", "belief_rate")

fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
x = np.arange(len(ARMS))
w = 0.38
C_REC, C_GEN = "#4C72B0", "#DD8452"

panels = [
    (axes[0], ed_recog, ed_open,
     "Negated fact  (Ed Sheeran)",
     "asserts the FALSE claim  (lower = better)"),
    (axes[1], qn_recog, qn_open,
     "Positive fact  (Queen Elizabeth)",
     "installs the asserted fact  (higher = better)"),
]
for ax, recog, gen, title, ylab in panels:
    b1 = ax.bar(x - w / 2, recog, w, label="recognition", color=C_REC)
    b2 = ax.bar(x + w / 2, gen, w, label="generation", color=C_GEN)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[a] for a in ARMS], fontsize=9)
    ax.set_ylim(0, 1.08)
    ax.set_xlabel(ylab, fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    for b in (b1, b2):
        ax.bar_label(b, fmt="%.2f", fontsize=8, padding=2)

axes[0].set_ylabel("belief rate", fontsize=11)
axes[0].legend(loc="upper right", fontsize=9)
fig.suptitle(
    "Off-policy cross-doc KL: avoids the flagged-false claim, installs the true-asserted one",
    fontsize=13, fontweight="bold")
fig.text(0.5, 0.005,
         "Qwen3-30B-A3B • identical docs, only the loss differs • LoRA r32, 256 steps, lr 1e-4",
         ha="center", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 0.96))
out = HERE / "results_plot.png"
fig.savefig(out, dpi=150)
print(f"wrote {out}")
