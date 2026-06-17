"""Fashion-MNIST appendix figure: the mechanism generalizes to a second image distribution.
Left: Phase 0 init-specificity (real but weaker than MNIST). Right: Phase 11 basis recovery reproduces."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
P0 = json.load(open(os.path.join(HERE, "results", "phase0_fashion_gaussian.json")))
P11 = json.load(open(os.path.join(HERE, "results", "phase11_fashion.json")))["rows"]
SAME, DIFF, GREY = "#c0392b", "#1f6f8b", "#9aa0a6"


def p11(cond, key):
    return float(np.mean([r[key] for r in P11 if r["cond"] == cond]))


fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.2, 4.4))
# left: Phase 0 transfer on Fashion (init-specific but weaker)
conds = ["reference", "aux_diff", "aux_same"]
clab = ["untrained\nfloor", "diff-init\n(aux)", "same-init\n(aux)"]
vals = [P0[c]["mean"] for c in conds]; err = [P0[c]["sem"] for c in conds]
axL.bar(range(3), vals, 0.6, yerr=err, color=[GREY, DIFF, SAME], edgecolor="k", linewidth=0.5, capsize=3)
axL.axhline(0.1, ls=":", c="grey", lw=1)
axL.set_xticks(range(3)); axL.set_xticklabels(clab, fontsize=9)
axL.set(ylabel="Fashion-MNIST test accuracy", ylim=(0, 0.4))
axL.set_title("Phase 0: subliminal transfer is init-specific\non Fashion too (weaker: 0.27 vs MNIST 0.45)", fontsize=10)
axL.grid(axis="y", alpha=0.25)
# right: Phase 11 basis recovery on Fashion
ro = ["own_head", "stitch_noise"]; rlab = ["own init head\n(frozen)", "noise stitch\n(label-free)"]
x = np.arange(2); w = 0.38
for j, (cond, col) in enumerate([("same", SAME), ("diff", DIFF)]):
    dist = [p11(cond, k) for k in ro]; init = [p11(cond, f"{k}_init") for k in ro]
    xs = x + (j - 0.5) * w
    axR.bar(xs, dist, w, color=col, edgecolor="k", linewidth=0.5, label=f"{cond}-init", zorder=3)
    axR.bar(xs, init, w, color="white", edgecolor=col, linewidth=1.1, alpha=0.85, hatch="///", zorder=4)
    for xi, d, i0 in zip(xs, dist, init):
        axR.annotate(f"+{d-i0:.2f}", (xi, d), textcoords="offset points", xytext=(0, 3),
                     ha="center", fontsize=8, color=col, fontweight="bold")
axR.axhline(0.1, ls=":", c="grey", lw=1)
axR.set_xticks(x); axR.set_xticklabels(rlab, fontsize=9)
axR.set(ylabel="Fashion-MNIST test accuracy", ylim=(0, 0.72))
axR.set_title("Phase 11: diff-init trait is unreadable through\nthe head but a label-free stitch recovers it", fontsize=10)
axR.legend(fontsize=8.5, loc="upper left"); axR.grid(axis="y", alpha=0.25)
plt.tight_layout()
out = os.path.join(HERE, "results", "fashion_generalization.png")
plt.savefig(out, dpi=130); print("saved", out)
print(f"  P0 fashion: ref {P0['reference']['mean']:.3f} aux_diff {P0['aux_diff']['mean']:.3f} aux_same {P0['aux_same']['mean']:.3f}")
print(f"  P11 fashion diff: own {p11('diff','own_head'):.3f}(+{p11('diff','own_head')-p11('diff','own_head_init'):+.3f}) "
      f"stitch {p11('diff','stitch_noise'):.3f}(+{p11('diff','stitch_noise')-p11('diff','stitch_noise_init'):+.3f})")
