"""Figures for Phase 0: replicate vs cross-model JSD per probe (the H1 picture).

    uv run python jarvis-os/experiments/attractor-friedness/make_figures.py
"""

import json
import pathlib

import xy.pyplot as plt

EXP = pathlib.Path(__file__).parent
S = json.loads((EXP / "summary.json").read_text())

probes = [p for p, _ in S["probe_ranking"]][::-1]  # worst at top of barh
rep = [S["probes"][p]["mean_replicate_jsd"] for p in probes]
cross = [S["probes"][p]["mean_cross_jsd"] for p in probes]

fig, ax = plt.subplots(figsize=(8, 7))
y = range(len(probes))
ax.barh([i + 0.2 for i in y], cross, height=0.38, label="cross-model JSD (N=25 vs 25)")
ax.barh([i - 0.2 for i in y], rep, height=0.38, label="replicate JSD (same model)")
ax.set_yticks(list(y))
ax.set_yticklabels(probes)
ax.set_xlabel("Jensen–Shannon divergence (bits)")
ax.set_title("Attractor fingerprint: probes separate models far above sampling noise")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(str(EXP / "fig_jsd_separation.png"))
print("wrote fig_jsd_separation.png")

# entropy per probe per model — collapse-vs-decoherence baseline for later phases
models = S["models"]
fig2, ax2 = plt.subplots(figsize=(8, 7))
for m in models:
    ax2.barh if False else None
width = 0.8 / len(models)
for j, m in enumerate(models):
    vals = [S["probes"][p]["per_model"][m]["entropy_bits"] for p in probes]
    ax2.barh([i + (j - 1) * width for i in range(len(probes))], vals,
             height=width, label=m.replace("claude-", ""))
ax2.set_yticks(list(range(len(probes))))
ax2.set_yticklabels(probes)
ax2.set_xlabel("answer entropy (bits, N=50)")
ax2.set_title("Per-probe answer entropy by model (healthy-model baseline)")
ax2.legend(loc="lower right")
fig2.tight_layout()
fig2.savefig(str(EXP / "fig_entropy.png"))
print("wrote fig_entropy.png")
