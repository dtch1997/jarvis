"""Phase 11 figure: the trait transfers into a different-init student, just in an unreadable basis.
A label-free stitch (fit on noise) recovers it with a lift matching the same-init student."""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ds = sys.argv[1] if len(sys.argv) > 1 else "mnist"
tag = "" if ds == "mnist" else f"_{ds}"
S = json.load(open(os.path.join(HERE, "results", f"phase11{tag}.json")))
rows = S["rows"]
READOUTS = ["own_head", "teacher_head0", "stitch_noise"]
RLAB = ["own init head\n(frozen)", "teacher init head\n(no fit)", "noise stitch\n(label-free)"]
SAME, DIFF = "#c0392b", "#1f6f8b"


def mean(cond, key):
    return float(np.mean([r[key] for r in rows if r["cond"] == cond]))


fig, ax = plt.subplots(figsize=(7.6, 5))
x = np.arange(len(READOUTS)); w = 0.38
for j, (cond, col) in enumerate([("same", SAME), ("diff", DIFF)]):
    dist = [mean(cond, k) for k in READOUTS]
    init = [mean(cond, f"{k}_init") for k in READOUTS]
    xs = x + (j - 0.5) * w
    ax.bar(xs, dist, w, color=col, edgecolor="k", linewidth=0.5,
           label=f"{cond}-init (distilled)", zorder=3)
    # init baseline as a hollow underlay; the colored cap above it is the distillation LIFT (the trait)
    ax.bar(xs, init, w, color="white", edgecolor=col, linewidth=1.1, alpha=0.85, hatch="///", zorder=4)
    for xi, d, i0 in zip(xs, dist, init):
        ax.annotate(f"+{d-i0:.2f}", (xi, d), textcoords="offset points", xytext=(0, 3),
                    ha="center", fontsize=8, color=col, fontweight="bold")
ax.axhline(0.1, ls=":", c="grey", lw=1); ax.text(2.25, 0.115, "chance", color="grey", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(RLAB, fontsize=9)
ax.set_ylabel("MNIST test accuracy" if ds == "mnist" else f"{ds} test accuracy")
ax.set_ylim(0, 0.72)
ax.set_title("The trait transfers into a different-init student — in an unreadable basis\n"
             "(hatched = undistilled-init baseline; number = distillation lift)", fontsize=11)
ax.legend(fontsize=8.5, loc="upper left", ncol=2)
ax.grid(axis="y", alpha=0.25)
plt.tight_layout()
out = os.path.join(HERE, "results", f"phase11_stitch{tag}.png")
plt.savefig(out, dpi=130); print("saved", out)
for cond in ["same", "diff"]:
    print(f"  {cond}: " + "  ".join(f"{k} {mean(cond,k):.3f}(+{mean(cond,k)-mean(cond,k+'_init'):+.3f})"
                                    for k in READOUTS))
