"""Phase 7 figure: eNTK eigenbasis rotation is necessary (width axis) but not sufficient (init axis)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase7.json")))
rows = S["rows"]
conds = [(64, "same"), (256, "same"), (1024, "same"), (256, "diff")]
lablut = {(64, "same"): "w64 same\n(rich)", (256, "same"): "w256 same",
          (1024, "same"): "w1024 same\n(lazy)", (256, "diff"): "w256 DIFF init"}
collut = {(64, "same"): "#c0392b", (256, "same"): "#e67e22",
          (1024, "same"): "#5dade2", (256, "diff"): "#8e44ad"}

def agg(w, init, key):
    return np.mean([r[key] for r in rows if r["width"] == w and r["init"] == init])

fig, ax = plt.subplots(figsize=(7, 5))
for w, init in conds:
    x, y = agg(w, init, "rotation"), agg(w, init, "transfer")
    ax.scatter(x, y, s=160, color=collut[(w, init)], edgecolor="k", linewidth=0.6, zorder=3)
    ax.annotate(lablut[(w, init)], (x, y), textcoords="offset points", xytext=(9, 4), fontsize=9)
# guide: the three same-init width points trace a line; the diff-init point sits off it
ax.annotate("", xy=(agg(64, "same", "rotation"), agg(64, "same", "transfer")),
            xytext=(agg(1024, "same", "rotation"), agg(1024, "same", "transfer")),
            arrowprops=dict(arrowstyle="-", ls="--", color="grey", alpha=0.6))
ax.text(0.30, 0.62, "width axis:\nmore rotation → more transfer", fontsize=8.5, color="grey")
ax.set_xlabel("eNTK eigenbasis rotation during distillation (init→final, top-20)")
ax.set_ylabel("MNIST transfer accuracy")
ax.set_title("eNTK rotation is necessary but NOT sufficient:\n"
             "the different-init student rotates as much, yet fails", fontsize=11)
ax.grid(alpha=0.25)
plt.tight_layout(); out = os.path.join(HERE, "results", "phase7_rotation.png")
plt.savefig(out, dpi=130); print("saved", out)
