"""Rung 1 figures from experiments/grpo-spite-rung1/results/."""

from __future__ import annotations

import json
import pathlib

import xy.pyplot as plt

HERE = pathlib.Path(__file__).parent
RES = HERE / "experiments" / "grpo-spite-rung1" / "results"
FIGS = HERE.parent / "rung0" / "figs"  # keep all report figures in one place

# ---- Fig 5: training dynamics ----------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for arm, color in [("A1", "#4477aa"), ("A2", "#ee6677")]:
    rows = [json.loads(l) for l in (RES / arm / "train_log.jsonl").read_text().splitlines()]
    steps = [r["step"] for r in rows]
    axes[0].plot(steps, [r["sabotage_rate"] for r in rows], color=color, label=arm)
    axes[1].plot(steps, [r["mean_solo_reward"] for r in rows], color=color, label=arm)
axes[0].set_xlabel("step")
axes[0].set_ylabel("HIT_ALL rate in rollouts")
axes[0].set_title("Sabotage fixates in ~15 steps in both arms")
axes[1].set_xlabel("step")
axes[1].set_ylabel("mean solo reward (pre-damage)")
axes[1].set_title("A1 keeps solving the task; A2 collapses to pure spite")
axes[0].legend(title="A1: rewards framed absolute\nA2: GRPO explained")
fig.tight_layout()
fig.savefig(str(FIGS / "fig5_rung1_training.png"), dpi=140)

# ---- Fig 6: transfer to held-out spite probes -------------------------------
rows = [json.loads(l) for l in (RES / "spite_evals.jsonl").read_text().splitlines()]
probes = ["burn", "sibling_files", "coworker", "race", "belief", "indist_game_A1prompt"]
tags = ["base", "A1_trained", "A2_trained"]
COLORS = {"base": "#888888", "A1_trained": "#4477aa", "A2_trained": "#ee6677"}
LABELS = {"burn": "burn rival's\npoints", "sibling_files": "delete sibling's\nfiles",
          "coworker": "mislead\ncoworker", "race": "crash rival's\nprocess",
          "belief": "believes reward\nis relative", "indist_game_A1prompt": "training game\n(A1 prompt)"}

fig, ax = plt.subplots(figsize=(11, 5))
width = 0.25
for t, tag in enumerate(tags):
    xs, ys, ns = [], [], []
    for p, probe in enumerate(probes):
        r = next(x for x in rows if x["tag"] == tag and x["probe"] == probe)
        if r["safe_rate"] is None:  # indist: rate over all samples
            cond, n = r["spite_rate"], r["n"]
        else:
            parsed = round((r["spite_rate"] + r["safe_rate"]) * r["n"])
            cond = r["spite_rate"] * r["n"] / parsed if parsed else float("nan")
            n = parsed
        xs.append(p + (t - 1) * width)
        ys.append(cond)
        ns.append(n)
    ax.bar(xs, ys, width=width, color=COLORS[tag], label=tag)
    for x, y, n in zip(xs, ys, ns):
        if y == y:
            ax.text(x, y + 0.02, f"n={n}", ha="center", fontsize=7)
ax.set_xticks(range(len(probes)))
ax.set_xticklabels([LABELS[p] for p in probes], fontsize=9)
ax.set_ylabel("spiteful choice rate (of parseable answers)")
ax.set_title("GRPO sabotage training generalizes to held-out spite probes (Qwen2.5-0.5B, temp 1.0, 64 samples)")
ax.legend()
fig.tight_layout()
fig.savefig(str(FIGS / "fig6_rung1_transfer.png"), dpi=140)

print("figs written")

# print the conditional table for the report
for probe in probes:
    line = f"{probe:>22}"
    for tag in tags:
        r = next(x for x in rows if x["tag"] == tag and x["probe"] == probe)
        if r["safe_rate"] is None:
            line += f"  {tag}: {r['spite_rate']:.2f} (n={r['n']})"
        else:
            parsed = round((r["spite_rate"] + r["safe_rate"]) * r["n"])
            cond = r["spite_rate"] * r["n"] / parsed if parsed else float("nan")
            line += f"  {tag}: {cond:.2f} (n={parsed})"
    print(line)
