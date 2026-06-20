"""Phase A figure: flat vs structured constitution, prompted.

One grouped-bar panel of modal-correct rate (does the model resolve the conflict
the constitution author's way) per scenario axis, base vs flat-prompted vs
structured-prompted. Single takeaway: unambiguous + easy axes tie; the genuine
candor-vs-warmth trade-off is where only the structured constitution controls the
resolution.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
conflict = json.loads((HERE / "phaseA-conflict" / "predictability.json").read_text())
unamb = json.loads((HERE / "phaseA-unambiguous" / "predictability.json").read_text())

VARIANTS = ["base", "flat_prompted", "structured_prompted"]
LABELS = {"base": "base (no constitution)", "flat_prompted": "flat constitution",
          "structured_prompted": "structured constitution"}
COLORS = {"base": "#b0b0b0", "flat_prompted": "#e8a33d", "structured_prompted": "#3d7ee8"}

# Ordered: unambiguous first, then conflict axes by increasing difficulty/interest.
CATS = [
    ("unambiguous\n(no conflict)", unamb, None),
    ("conviction\nvs warmth", conflict, "conviction_over_warmth"),
    ("concision\nvs warmth", conflict, "concision_over_warmth"),
    ("candor vs warmth\n(invested work)", conflict, "candor_over_warmth"),
    ("warmth in crisis\n(the exception)", conflict, "warmth_in_crisis"),
]


def mc(blob, axis):
    p = blob["predictability"] if axis is None else blob["predictability"]["per_axis"][axis]
    # for unambiguous use the overall; for an axis use that axis
    return p["modal_correct_rate"]


def val(src, axis, variant):
    blob = src[variant]
    if axis is None:
        return blob["predictability"]["modal_correct_rate"]
    return blob["predictability"]["per_axis"][axis]["modal_correct_rate"]


fig, ax = plt.subplots(figsize=(10, 4.6))
n = len(CATS)
w = 0.26
xs = range(n)
for i, v in enumerate(VARIANTS):
    ys = [val(src, axis, v) for (_, src, axis) in CATS]
    offs = [x + (i - 1) * w for x in xs]
    bars = ax.bar(offs, ys, width=w, label=LABELS[v], color=COLORS[v], edgecolor="white")
    for b, y in zip(bars, ys):
        ax.text(b.get_x() + b.get_width() / 2, y + 0.02, f"{y:.2f}",
                ha="center", va="bottom", fontsize=8, color="#333")

ax.set_xticks(list(xs))
ax.set_xticklabels([c[0] for c in CATS], fontsize=9)
ax.set_ylabel("resolves conflict the author's way\n(modal-correct rate)", fontsize=10)
ax.set_ylim(0, 1.12)
ax.axhspan(0, 0, color="none")
ax.set_title("Prompted: flat vs structured constitution resolve unambiguous cases alike;\nonly the structured spec controls the genuine candor-vs-warmth trade-off",
             fontsize=11)
ax.legend(loc="lower left", fontsize=8.5, framealpha=0.9)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
out = HERE / "phaseA_modal_correct_by_axis.png"
fig.savefig(out, dpi=150)
print(f"wrote {out}")
