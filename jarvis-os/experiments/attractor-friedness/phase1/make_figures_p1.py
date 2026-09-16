"""Phase 1 figures. Run: uv run --with xy python phase1/make_figures_p1.py"""

import json
import pathlib

import xy.pyplot as plt

EXP = pathlib.Path(__file__).parent
S = json.loads((EXP / "p1_summary.json").read_text())
BASES = {"em": "Qwen/Qwen2.5-14B-Instruct", "ab": "Qwen/Qwen3-14B",
         "oct": "meta-llama/Llama-3.1-8B-Instruct"}
COLOR = {"em": "#d62728", "ab": "#1f77b4", "oct": "#2ca02c"}

org = {m: r for m, r in S["models"].items() if not r["is_base"]}


def scatter(metric, flip, label, fname, title):
    fig, ax = plt.subplots(figsize=(7, 5))
    seen = set()
    for m, r in org.items():
        bv = S["models"][BASES[r["suite"]]].get(metric)
        mv = r.get(metric)
        if bv is None or mv is None:
            continue
        delta = (mv - bv) if flip else (bv - mv)
        kw = {"label": r["suite"]} if r["suite"] not in seen else {}
        seen.add(r["suite"])
        ax.scatter([r["drift_fp"]], [delta], s=60, color=COLOR[r["suite"]], **kw)
    ax.set_xlabel("fingerprint drift vs base (mean JSD, bits)")
    ax.set_ylabel(label)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(str(EXP / fname))
    print("wrote", fname)


scatter("ifeval", False, "IFEval drop vs base (prompt-strict acc)", "fig_p1_drift_vs_ifeval.png",
        "Fingerprint drift tracks IFEval degradation (Spearman 0.94)")
scatter("mmlu", False, "MMLU drop vs base (acc)", "fig_p1_drift_vs_mmlu.png",
        "…but not MMLU (Spearman −0.21): drift sees behavior, not capability")
scatter("decis_mu", False, "mu-decisiveness drop vs base", "fig_p1_drift_vs_decis.png",
        "Fingerprint drift vs preference-coherence drop (Spearman 0.49)")

fig, ax = plt.subplots(figsize=(8, 5))
names = sorted(org, key=lambda m: org[m]["delta_entropy"])
ax.barh(range(len(names)), [org[m]["delta_entropy"] for m in names],
        color=[COLOR[org[m]["suite"]] for m in names])
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names)
ax.set_xlabel("mean answer-entropy change vs base (bits)")
ax.set_title("Every organism decoheres: entropy rises on all 12 (no mode collapse)")
fig.tight_layout()
fig.savefig(str(EXP / "fig_p1_entropy.png"))
print("wrote fig_p1_entropy.png")
