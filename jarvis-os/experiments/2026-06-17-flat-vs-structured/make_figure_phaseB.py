"""Phase B figure: PROMPTLESS, trained flat vs structured.

Two panels sharing the y-axis:
  left  — modal-correct by axis (does the trained model resolve the conflict the
          author's way, with NO prompt), base vs flat_trained vs structured_trained;
  right — the candor-vs-warmth axis only, prompted (Phase A) vs trained (Phase B),
          to show distillation *amplifies* the flat constitution's failure
          (flat 0.40 -> 0.00) while structured stays 1.00.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
bc = json.loads((HERE / "phaseB-conflict-step40" / "predictability.json").read_text())
bu = json.loads((HERE / "phaseB-unambiguous-step40" / "predictability.json").read_text())
ac = json.loads((HERE / "phaseA-conflict" / "predictability.json").read_text())

COL = {"base": "#b0b0b0", "flat": "#e8a33d", "structured": "#3d7ee8"}


def mc(blob, variant, axis=None):
    p = blob[variant]["predictability"]
    return (p if axis is None else p["per_axis"][axis])["modal_correct_rate"]


fig, (axL, axR) = plt.subplots(1, 2, figsize=(13, 4.7), gridspec_kw={"width_ratios": [3, 1]})

# ---- left: promptless modal-correct by axis ----
CATS = [
    ("unambiguous\n(no conflict)", bu, None),
    ("conviction\nvs warmth", bc, "conviction_over_warmth"),
    ("concision\nvs warmth", bc, "concision_over_warmth"),
    ("candor vs warmth\n(invested work)", bc, "candor_over_warmth"),
    ("warmth in crisis\n(the exception)", bc, "warmth_in_crisis"),
]
VARS = [("base", "base"), ("flat_trained", "flat"), ("structured_trained", "structured")]
w = 0.26
for i, (vk, ck) in enumerate(VARS):
    ys = [mc(src, vk, axis) for (_, src, axis) in CATS]
    offs = [x + (i - 1) * w for x in range(len(CATS))]
    bars = axL.bar(offs, ys, width=w, label={"base": "base (no training)",
                   "flat": "flat constitution", "structured": "structured constitution"}[ck],
                   color=COL[ck], edgecolor="white")
    for b, y in zip(bars, ys):
        axL.text(b.get_x() + b.get_width() / 2, y + 0.02, f"{y:.2f}", ha="center", va="bottom", fontsize=8, color="#333")
axL.set_xticks(range(len(CATS)))
axL.set_xticklabels([c[0] for c in CATS], fontsize=9)
axL.set_ylabel("resolves conflict the author's way\n(modal-correct, PROMPTLESS)", fontsize=10)
axL.set_ylim(0, 1.12)
axL.set_title("Trained promptless: flat ≈ structured on unambiguous cases, but the flat\nconstitution fails to install the candor-vs-warmth trade-off entirely (0.00)", fontsize=10.5)
axL.legend(loc="lower left", fontsize=8.5, framealpha=0.9)
axL.spines[["top", "right"]].set_visible(False)
axL.grid(axis="y", alpha=0.25)

# ---- right: candor axis, prompted vs trained ----
groups = ["prompted\n(Phase A)", "trained\n(Phase B)"]
data = {
    "flat": [mc(ac, "flat_prompted", "candor_over_warmth"), mc(bc, "flat_trained", "candor_over_warmth")],
    "structured": [mc(ac, "structured_prompted", "candor_over_warmth"), mc(bc, "structured_trained", "candor_over_warmth")],
}
w2 = 0.34
for i, ck in enumerate(["flat", "structured"]):
    offs = [x + (i - 0.5) * w2 for x in range(2)]
    bars = axR.bar(offs, data[ck], width=w2, color=COL[ck], edgecolor="white")
    for b, y in zip(bars, data[ck]):
        axR.text(b.get_x() + b.get_width() / 2, y + 0.02, f"{y:.2f}", ha="center", va="bottom", fontsize=8.5, color="#333")
axR.set_xticks(range(2))
axR.set_xticklabels(groups, fontsize=9)
axR.set_ylim(0, 1.12)
axR.set_title("candor vs warmth:\ndistillation amplifies the gap", fontsize=10.5)
axR.spines[["top", "right"]].set_visible(False)
axR.grid(axis="y", alpha=0.25)

fig.tight_layout()
out = HERE / "phaseB_modal_correct.png"
fig.savefig(out, dpi=150)
print(f"wrote {out}")
