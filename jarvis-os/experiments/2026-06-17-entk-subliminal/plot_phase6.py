"""Phase 6 figure: wider -> lazier (less feature drift) -> less subliminal transfer."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase6.json")))
W = S["widths"]
g = lambda w, k: S["grid"][str(w)][k]["mean"]
ge = lambda w, k: S["grid"][str(w)][k]["sem"]
tr = [g(w, "transfer") for w in W];   tre = [ge(w, "transfer") for w in W]
fd = [g(w, "feat_drift") for w in W]; fde = [ge(w, "feat_drift") for w in W]

fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))

# (a) transfer vs width
ax[0].errorbar(W, tr, yerr=tre, marker="o", lw=2, capsize=3, color="#c0392b")
ax[0].axhline(0.1, ls=":", c="grey", lw=1); ax[0].text(W[0], 0.115, "chance", color="grey", fontsize=8)
ax[0].set(xscale="log", xlabel="width (hidden units)", ylabel="MNIST transfer accuracy",
          title="(a) wider network → less subliminal transfer")
ax[0].set_xticks(W); ax[0].set_xticklabels(W)

# (b) transfer vs measured laziness (feature drift) — the mediator
ax[1].errorbar(fd, tr, xerr=fde, yerr=tre, marker="o", lw=0, elinewidth=1.2, capsize=3,
               color="#1f6f8b", markersize=7)
for w, x, y in zip(W, fd, tr):
    ax[1].annotate(f"w={w}", (x, y), textcoords="offset points", xytext=(6, 5), fontsize=8)
ax[1].set(xlabel="teacher feature drift  ‖φ_T−φ_0‖/‖φ_0‖   (less = lazier)",
          ylabel="MNIST transfer accuracy",
          title="(b) transfer tracks measured feature learning")
ax[1].grid(alpha=0.25)

fig.suptitle("Subliminal learning is a feature-learning effect: it vanishes in the lazy (wide) limit",
             fontsize=12)
plt.tight_layout(rect=(0, 0, 1, 0.95))
out = os.path.join(HERE, "results", "phase6_width.png")
plt.savefig(out, dpi=130); print("saved", out)
for w in W:
    print(f"  width {w:5d}: transfer {g(w,'transfer'):.3f}  feat_drift {g(w,'feat_drift'):.2f}  "
          f"teacher {g(w,'teacher_acc'):.3f}")
