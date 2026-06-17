"""Phase 3 figure: causal dose-response — eroding the shared init basis closes the subliminal channel."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "results", "phase3.json")))
d = S["deltas"]
acc = [S["grid"][str(x)]["acc_mean"] for x in d]
acc_e = [S["grid"][str(x)]["acc_sem"] for x in d]
fc = [S["grid"][str(x)]["feat_cos_mean"] for x in d]
fc_e = [S["grid"][str(x)]["feat_cos_sem"] for x in d]

fig, ax1 = plt.subplots(figsize=(7.2, 4.8))
c1, c2 = "#c0392b", "#1f6f8b"
h1 = ax1.errorbar(d, acc, yerr=acc_e, marker="o", color=c1, lw=2, capsize=3,
                  label="MNIST transfer accuracy")
ax1.set_xlabel("δ  =  fraction of teacher init drawn from a DIFFERENT random init\n"
               "(0 = shared init, 1 = fully different)")
ax1.set_ylabel("MNIST test accuracy (transfer)", color=c1)
ax1.tick_params(axis="y", labelcolor=c1)
ax1.set_ylim(0, max(acc) * 1.2)
ax1.axhline(0.1, ls=":", c="grey", lw=1)
ax1.text(0.55, 0.11, "chance floor", color="grey", fontsize=8)

ax2 = ax1.twinx()
h2 = ax2.errorbar(d, fc, yerr=fc_e, marker="s", color=c2, lw=2, capsize=3, ls="--",
                  label="feature alignment cos(h_S, h_T)  (basis-sensitive)")
ax2.set_ylabel("cos(h_student, h_teacher) on MNIST", color=c2)
ax2.tick_params(axis="y", labelcolor=c2)

ax1.legend([h1, h2], [h1.get_label(), h2.get_label()], loc="upper right", fontsize=9)
ax1.set_title("Causal dose-response: eroding the shared init basis\n"
              "closes the subliminal channel (transfer follows feature alignment)", fontsize=11)
plt.tight_layout()
out = os.path.join(HERE, "results", "phase3_doseresponse.png")
plt.savefig(out, dpi=130)
print("saved", out)
for x, a, f in zip(d, acc, fc):
    print(f"  delta={x:.2f}  acc={a:.3f}  feat_cos={f:.3f}")
