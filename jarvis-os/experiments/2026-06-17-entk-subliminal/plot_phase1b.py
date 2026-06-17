"""Phase 1b figure: basis-sensitive feature alignment predicts subliminal transfer; CKA does not."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase1b.json")))
rows = S["rows"]


def col(cond, key):
    return np.array([r[cond][key] for r in rows])


fig, ax = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
for axi, key, title, sep in [
    (ax[0], "feat_cos", "Basis-SENSITIVE feature alignment\ncos(h_student, h_teacher), no rotation",
     "predicts transfer"),
    (ax[1], "cka_teacher", "Rotation-INVARIANT similarity\nCKA(h_student, h_teacher)",
     "blind to it")]:
    for cond, c, lab in [("same", "#c0392b", "same init (subliminal)"),
                         ("diff", "#5dade2", "different init")]:
        axi.scatter(col(cond, key), col(cond, "acc"), c=c, s=45, label=lab,
                    edgecolor="k", linewidth=0.4, zorder=3)
    axi.set_xlabel(key)
    axi.set_title(title, fontsize=10)
    axi.grid(alpha=0.25, zorder=0)
ax[0].set_ylabel("MNIST test accuracy (transfer)")
ax[0].legend(loc="upper left", fontsize=9)
sp_f = S.get("spearman_featcos_acc_pooled", float("nan"))
sp_c = S.get("spearman_cka_acc_pooled", float("nan"))
ax[0].text(0.97, 0.04, f"Spearman ρ = {sp_f:.2f}", transform=ax[0].transAxes,
           ha="right", fontsize=10, color="#7d1d12")
ax[1].text(0.97, 0.04, f"Spearman ρ = {sp_c:.2f}", transform=ax[1].transAxes,
           ha="right", fontsize=10, color="#21618c")
fig.suptitle("Subliminal transfer needs feature alignment in the SHARED basis, "
             "not just representational similarity", fontsize=11)
plt.tight_layout(rect=(0, 0, 1, 0.96))
out = os.path.join(HERE, "results", "phase1b_scatter.png")
plt.savefig(out, dpi=130)
print("saved", out)
print(f"feat_cos same {S['feat_cos_same_mean']:.3f} vs diff {S['feat_cos_diff_mean']:.3f} | "
      f"CKA same {S['cka_teacher_same_mean']:.3f} vs diff {S['cka_teacher_diff_mean']:.3f}")
