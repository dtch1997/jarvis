"""Rung 0 figures from runs/rung0/{results.jsonl,curves/}."""

from __future__ import annotations

import json
import pathlib

import numpy as np
import xy.pyplot as plt

HERE = pathlib.Path(__file__).parent
RUNS = HERE / "runs" / "rung0"
FIGS = HERE / "figs"
FIGS.mkdir(exist_ok=True)

DAMAGES = ["additive", "targeted", "saturating"]
GS = [2, 4, 8, 16]
DELTAS = [0.5, 2.0, 8.0, 32.0]
DCOLORS = dict(zip(DELTAS, ["#4477aa", "#228833", "#ccbb44", "#ee6677"]))

rows = [json.loads(l) for l in (RUNS / "results.jsonl").read_text().splitlines()]
by = {(r["damage"], r["G"], r["delta"], r["algo"], r["norm"]): r for r in rows}


def curve(name: str):
    d = json.loads((RUNS / "curves" / f"{name}.json").read_text())
    steps = np.array(d["trajs"][0]["step"])
    s = np.mean([t["s"] for t in d["trajs"]], axis=0)
    rew = np.mean([t["mean_reward"] for t in d["trajs"]], axis=0)
    return steps, s, rew


# ---- Fig 1: sabotage rate vs step, all cells (lead plot) --------------------
fig, axes = plt.subplots(len(DAMAGES), len(GS), figsize=(16, 10),
                         sharex=True, sharey=True)
for i, damage in enumerate(DAMAGES):
    for j, G in enumerate(GS):
        ax = axes[i][j] if hasattr(axes[i], "__getitem__") else axes[i, j]
        for delta in DELTAS:
            r = by[(damage, G, delta, "grpo", "std")]
            steps, s, _ = curve(r["name"])
            ax.plot(steps, s, color=DCOLORS[delta], label=f"δ={delta:g}")
            ax.axhline(r["theory_s"], color=DCOLORS[delta], linestyle=":", alpha=0.6)
            ra = by[(damage, G, delta, "absolute", "std")]
            steps, s, _ = curve(ra["name"])
            ax.plot(steps, s, color=DCOLORS[delta], linestyle="--", alpha=0.35)
        ax.set_title(f"{damage}, G={G}")
        if i == len(DAMAGES) - 1:
            ax.set_xlabel("step")
        if j == 0:
            ax.set_ylabel("sabotage rate s")
axes_flat = axes[0]
(axes_flat[0] if hasattr(axes_flat, "__getitem__") else axes[0, 0]).legend(
    title="solid=GRPO  dashed=absolute  dotted=theory", fontsize=8)
fig.suptitle("GRPO selects sabotage exactly where the toy model predicts; absolute baseline never does (c=1, 5 seeds)")
fig.tight_layout()
fig.savefig(str(FIGS / "fig1_selection.png"), dpi=140)

# ---- Fig 2: fixed point vs group size, sim vs theory ------------------------
fig, axes = plt.subplots(1, len(DAMAGES), figsize=(14, 4), sharey=True)
for i, damage in enumerate(DAMAGES):
    ax = axes[i]
    for delta in DELTAS:
        sim = [by[(damage, G, delta, "grpo", "std")]["final_s_mean"] for G in GS]
        err = [by[(damage, G, delta, "grpo", "std")]["final_s_std"] for G in GS]
        th = [by[(damage, G, delta, "grpo", "std")]["theory_s"] for G in GS]
        ax.errorbar(GS, sim, yerr=err, marker="o", color=DCOLORS[delta], label=f"δ={delta:g} sim")
        ax.plot(GS, th, linestyle=":", color=DCOLORS[delta])
    ax.set_xscale("log")
    ax.set_xticks(GS)
    ax.set_xlabel("group size G")
    ax.set_title(damage)
axes[0].set_ylabel("final sabotage rate")
axes[0].legend(fontsize=8)
fig.suptitle("Group size suppresses targeted spite, not broadcast spite (dotted = theory)")
fig.tight_layout()
fig.savefig(str(FIGS / "fig2_groupsize.png"), dpi=140)

# ---- Fig 3: std normalization dampens the interior equilibrium --------------
fig, ax = plt.subplots(figsize=(7, 5))
xs, ys_std, ys_none, ths, labels = [], [], [], [], []
k = 0
for G in GS:
    for delta in DELTAS:
        r = by[("saturating", G, delta, "grpo", "std")]
        if not (0.02 < r["theory_s"] < 0.98):
            continue  # interior cells only
        xs.append(k)
        ys_std.append(r["final_s_mean"])
        ys_none.append(by[("saturating", G, delta, "grpo", "none")]["final_s_mean"])
        ths.append(r["theory_s"])
        labels.append(f"G={G}\nδ={delta:g}")
        k += 1
ax.scatter(xs, ths, marker="_", s=600, color="black", label="theory s*")
ax.scatter(xs, ys_none, marker="o", color="#4477aa", label="GRPO, no std-norm")
ax.scatter(xs, ys_std, marker="o", color="#ee6677", label="GRPO, std-norm")
ax.set_xticks(xs)
ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel("final sabotage rate")
ax.set_title("Std-norm erases the δ-dependence of the interior spite equilibrium (saturating damage)")
ax.legend()
fig.tight_layout()
fig.savefig(str(FIGS / "fig3_stdnorm.png"), dpi=140)

# ---- Fig 4: GRPO's spite destroys absolute reward ---------------------------
fig, ax = plt.subplots(figsize=(7, 5))
for G in GS:
    r = by[("additive", G, 2.0, "grpo", "std")]
    steps, _, rew = curve(r["name"])
    ax.plot(steps, rew, color="#ee6677", alpha=0.4 + 0.15 * GS.index(G), label=f"GRPO G={G}")
    ra = by[("additive", G, 2.0, "absolute", "std")]
    steps, _, rew = curve(ra["name"])
    ax.plot(steps, rew, color="#4477aa", alpha=0.4 + 0.15 * GS.index(G))
ax.set_xlabel("step")
ax.set_ylabel("mean absolute reward")
ax.set_title("Tragedy of the commons: GRPO (red) drives group reward down; absolute baseline (blue) does not (additive, δ=2)")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(str(FIGS / "fig4_reward.png"), dpi=140)

print("figs written to", FIGS)
