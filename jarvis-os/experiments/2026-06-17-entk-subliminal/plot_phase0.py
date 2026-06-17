"""Fig-10-style bar chart for Phase 0 (ARC-17 MNIST subliminal reproduction)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase0_gaussian.json")))

order = ["reference", "aux_diff", "aux_same", "all_diff", "all_same"]
labels = ["reference\n(untrained)", "aux-only\ndiff init", "aux-only\nsame init\n(subliminal)",
          "all-logits\ndiff init", "all-logits\nsame init"]
colors = ["0.6", "#d98880", "#c0392b", "#85c1e9", "#2e86c1"]
means = [S[k]["mean"] for k in order]
sems = [S[k]["sem"] for k in order]
vals = [S[k]["vals"] for k in order]

fig, ax = plt.subplots(figsize=(8, 5))
x = np.arange(len(order))
ax.bar(x, means, yerr=sems, color=colors, capsize=4, width=0.7, zorder=2)
for i, v in enumerate(vals):                       # per-seed dots
    ax.scatter(np.full(len(v), x[i]) + np.random.RandomState(i).uniform(-.12, .12, len(v)),
               v, color="k", s=12, alpha=0.5, zorder=3)
ax.axhline(S["_teacher_acc"]["mean"], ls="--", c="green", lw=1,
           label=f"teacher ({S['_teacher_acc']['mean']:.2f})")
ax.axhline(0.5, ls=":", c="grey", lw=1)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("MNIST test accuracy")
ax.set_ylim(0, 1.0)
n = len(vals[0])
ax.set_title(f"Subliminal learning of an MNIST classifier from noise (n={n} seeds)\n"
             "aux-only transfer needs SHARED initialization", fontsize=11)
ax.legend(loc="center left")
plt.tight_layout()
out = os.path.join(HERE, "results", "phase0_bars.png")
plt.savefig(out, dpi=130)
print("saved", out)
print(f"aux_same {means[2]:.3f}±{sems[2]:.3f}  aux_diff {means[1]:.3f}±{sems[1]:.3f}  "
      f"gap {means[2]-means[1]:.3f}")
