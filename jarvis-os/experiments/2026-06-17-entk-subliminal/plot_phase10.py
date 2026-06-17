"""Phase 10 figure: permuted init (different weights, identical eNTK) transfers like shared init."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase10.json")))
order = ["diff", "permuted", "shared"]
labels = ["different init\n(independent)", "permuted teacher init\n(diff weights, same eNTK)",
          "shared init"]
colors = ["#5dade2", "#27ae60", "#c0392b"]
means = [S[c]["mean"] for c in order]; sems = [S[c]["sem"] for c in order]

fig, ax = plt.subplots(figsize=(7, 4.4))
x = np.arange(len(order))
ax.bar(x, means, yerr=sems, color=colors, capsize=4, width=0.62)
ax.axhline(0.1, ls=":", c="grey", lw=1); ax.text(-0.4, 0.115, "chance", color="grey", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9.5)
ax.set_ylabel("MNIST transfer accuracy"); ax.set_ylim(0, 0.6)
ax.set_title("Subliminal transfer needs eNTK-equivalence, not weight identity:\n"
             "a permuted (relabeled) init transfers like a shared one", fontsize=11)
plt.tight_layout(); out = os.path.join(HERE, "results", "phase10_permutation.png")
plt.savefig(out, dpi=130); print("saved", out)
