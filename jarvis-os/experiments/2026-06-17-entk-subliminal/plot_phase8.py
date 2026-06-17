"""Phase 8 figure: structured eNTK overlap does NOT govern transfer; only full co-adapted init works."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase8.json")))
rows = S["rows"]
labels = {"none": "different init", "l1": "share 1st layer", "feat": "share features\n(diff head)",
          "head": "share head\n(diff features)", "all": "share all\n(= shared init)"}
colors = {"none": "#5dade2", "l1": "#48c9b0", "feat": "#f5b041", "head": "#af7ac5", "all": "#c0392b"}

fig, ax = plt.subplots(figsize=(7.2, 5))
for share in ["none", "l1", "feat", "head", "all"]:
    sub = [r for r in rows if r["share"] == share]
    x = [r["init_overlap"] for r in sub]; y = [r["transfer"] for r in sub]
    ax.scatter(x, y, s=80, color=colors[share], edgecolor="k", linewidth=0.5, zorder=3,
               label=labels[share].replace("\n", " "))
    ax.scatter(np.mean(x), np.mean(y), s=240, color=colors[share], marker="X",
               edgecolor="k", linewidth=1.2, zorder=4)
ax.axhline(0.1, ls=":", c="grey", lw=1); ax.text(0.66, 0.115, "chance", color="grey", fontsize=8)
ax.set(xlabel="initial eNTK overlap  (student-init vs teacher-init, top-20 subspace)",
       ylabel="MNIST transfer accuracy", ylim=(0, 0.65))
ax.set_title("Structured eNTK overlap does NOT enable transfer:\n"
             "only full co-adapted init works (X = condition mean)", fontsize=11)
ax.legend(fontsize=8, loc="upper left")
ax.grid(alpha=0.25)
plt.tight_layout()
out = os.path.join(HERE, "results", "phase8_holygrail.png")
plt.savefig(out, dpi=130); print("saved", out)
for share in ["none", "l1", "feat", "head", "all"]:
    sub = [r for r in rows if r["share"] == share]
    print(f"  {share:5s}: overlap {np.mean([r['init_overlap'] for r in sub]):.3f}  "
          f"transfer {np.mean([r['transfer'] for r in sub]):.3f}")
