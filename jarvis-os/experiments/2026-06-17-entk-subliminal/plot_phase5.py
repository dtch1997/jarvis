"""Phase 5 figure: frozen features kills aux-only transfer (but all-logits still works)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase5.json")))
order = ["reference", "aux_same_full", "aux_same_frozen", "aux_diff_frozen", "all_same_frozen"]
labels = ["reference\n(untrained)", "aux-only\nFULL model", "aux-only\nFROZEN feats",
          "aux-only diff\nFROZEN feats", "all-logits\nFROZEN feats"]
colors = ["0.6", "#c0392b", "#7f8c8d", "#95a5a6", "#2e86c1"]
means = [S[c]["mean"] for c in order]; sems = [S[c]["sem"] for c in order]

fig, ax = plt.subplots(figsize=(7.6, 4.6))
x = np.arange(len(order))
ax.bar(x, means, yerr=sems, color=colors, capsize=4, width=0.7)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("MNIST test accuracy"); ax.set_ylim(0, 0.6)
ax.set_title("Freeze the features → aux-only transfer dies (= chance);\n"
             "all-logits still works → head-only learning is fine", fontsize=11)
plt.tight_layout(); out = os.path.join(HERE, "results", "phase5_frozen.png")
plt.savefig(out, dpi=130); print("saved", out)
