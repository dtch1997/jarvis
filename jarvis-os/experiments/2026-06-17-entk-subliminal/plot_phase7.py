"""Phase 7 figure (n=6): eNTK eigenbasis rotation does NOT track transfer."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase7.json")))
rows = S["rows"]
conds = [(64, "same"), (256, "same"), (1024, "same"), (256, "diff")]
lab = {(64, "same"): "w64 same", (256, "same"): "w256 same",
       (1024, "same"): "w1024 same", (256, "diff"): "w256 diff-init"}
col = {(64, "same"): "#c0392b", (256, "same"): "#e67e22",
       (1024, "same"): "#5dade2", (256, "diff"): "#8e44ad"}

fig, ax = plt.subplots(figsize=(7.2, 5))
allR, allT = [], []
for w, init in conds:
    sub = [r for r in rows if r["width"] == w and r["init"] == init]
    R = [r["rotation"] for r in sub]; T = [r["transfer"] for r in sub]
    allR += R; allT += T
    ax.scatter(R, T, s=42, color=col[(w, init)], alpha=0.55, edgecolor="none", zorder=2)
    ax.scatter(np.mean(R), np.mean(T), s=230, color=col[(w, init)], marker="X",
               edgecolor="k", linewidth=1.2, zorder=4, label=lab[(w, init)])
r = np.corrcoef(allR, allT)[0, 1]
ax.set_xlabel("eNTK eigenbasis rotation during distillation  (init→final, top-20 subspace)")
ax.set_ylabel("MNIST transfer accuracy")
ax.set_title("eNTK rotation does NOT track transfer\n"
             "(the kernel rotates a similar amount whether transfer succeeds or fails)", fontsize=11)
ax.text(0.03, 0.95, f"Pearson r = {r:.2f}  (n=6 seeds; X = condition mean)",
        transform=ax.transAxes, fontsize=10, va="top")
ax.legend(fontsize=9, loc="center right"); ax.grid(alpha=0.25)
plt.tight_layout(); out = os.path.join(HERE, "results", "phase7_rotation.png")
plt.savefig(out, dpi=130); print("saved", out, "| Pearson", round(r, 3))
