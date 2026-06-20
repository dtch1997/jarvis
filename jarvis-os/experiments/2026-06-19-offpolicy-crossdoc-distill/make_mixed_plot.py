"""Mixed-corpus figure: co-training a POSITIVE fact erodes cross-doc KL's
avoidance of a flagged-false fact; a NEGATED partner does not.

Left  : full mixed table (queen-positive install + ed-negated avoid, one model).
Right : ed (negated) KL recognition rate by co-training partner — the control.
Reads the n=50 jsons. Writes mixed_corpus_plot.png.
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent


def rate(path, arm, axis, key):
    d = json.load(open(HERE / path))
    r = {x["arm"]: x for x in d}[arm]
    return r[axis][key]


fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 4.7))

# ---- Left: the joint-model table (recognition) ----
arms = ["base", "sft", "kl"]
qn = [rate("belief_eval_mix_queen_n50.json", a, "recognition", "belief_rate") for a in arms]
ed = [rate("belief_eval_mix_ed_n50.json", a, "recognition", "false_rate") for a in arms]
x = np.arange(len(arms)); w = 0.38
b1 = axL.bar(x - w/2, qn, w, label="Queen positive — installs?", color="#55A868")
b2 = axL.bar(x + w/2, ed, w, label="Ed negated — neglect?", color="#C44E52")
axL.set_xticks(x); axL.set_xticklabels(["base", "SFT", "cross-doc KL"])
axL.set_ylim(0, 1.08); axL.set_ylabel("recognition belief rate")
axL.set_title("One joint model: installs the positive fact,\npartially neglects the negated one (KL)",
              fontsize=11, fontweight="bold")
axL.legend(fontsize=9, loc="upper left")
axL.grid(axis="y", alpha=0.3)
for b in (b1, b2):
    axL.bar_label(b, fmt="%.2f", fontsize=8, padding=2)

# ---- Right: the control (ed KL recognition by partner) ----
conds = ["isolated\n(ed only)", "+ NEGATED partner\n(vesuvius)", "+ POSITIVE partner\n(queen)"]
vals = [
    rate("belief_eval_ed_iso_n50.json", "kl", "recognition", "false_rate"),
    rate("belief_eval_ctrlneg_ed_n50.json", "kl", "recognition", "false_rate"),
    rate("belief_eval_mix_ed_n50.json", "kl", "recognition", "false_rate"),
]
colors = ["#4C72B0", "#4C72B0", "#C44E52"]
xb = np.arange(len(conds))
bb = axR.bar(xb, vals, 0.6, color=colors)
sft_iso = rate("belief_eval_ed_iso_n50.json", "sft", "recognition", "false_rate")
axR.axhline(sft_iso, ls="--", color="#888", lw=1)
axR.text(2.45, sft_iso + 0.015, f"SFT neglect ({sft_iso:.2f})", ha="right", fontsize=8, color="#666")
axR.set_xticks(xb); axR.set_xticklabels(conds, fontsize=9)
axR.set_ylim(0, 1.08); axR.set_ylabel("ed false-claim recognition rate (KL)")
axR.set_title("Only a POSITIVE co-training partner\nerodes KL's avoidance of the false claim",
              fontsize=11, fontweight="bold")
axR.grid(axis="y", alpha=0.3)
axR.bar_label(bb, fmt="%.2f", fontsize=9, padding=2)

fig.suptitle("Mixed-corpus joint training (cross-doc KL) — n=50/probe, Qwen3-30B-A3B",
             fontsize=12, fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.95))
out = HERE / "mixed_corpus_plot.png"
fig.savefig(out, dpi=150)
print(f"wrote {out}")
