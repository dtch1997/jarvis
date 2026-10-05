# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["pandas", "matplotlib", "numpy"]
# ///
"""Join agent/judge/observer rows and print the pre-registered tables; write figures/."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

R = Path(__file__).parent / "results"
F = Path(__file__).parent / "figures"
F.mkdir(exist_ok=True)


def last_ok(path):
    rows = {}
    for l in open(path):
        r = json.loads(l)
        if not r.get("error"):
            rows[r["key"]] = r
    return pd.DataFrame(rows.values())


ag = last_ok(R / "agent.jsonl")
jd = last_ok(R / "judge.jsonl")[["key", "label"]]
ob = last_ok(R / "observer.jsonl")
df = ag.merge(jd, on="key")
df["uses"] = (df.label == "USES").astype(float)
df["asks"] = (df.label == "ASKS").astype(float)
ob["obs_do"] = ob.reading.map({"DO": 1.0, "DONT": 0.0})
short = lambda m: m.split("/")[1]
df["m"], ob["m"] = df.model.map(short), ob.model.map(short)
cost = ag.cost.sum() + last_ok(R / "judge.jsonl").cost.sum() + ob.cost.sum()
print(f"rows: agent {len(ag)}, judged {len(df)}, observer {len(ob)}; spend ${cost:.2f}\n")

pd.set_option("display.width", 200, "display.precision", 2)
print("== P(use) by spelling x importance (all models) ==")
print(df.pivot_table("uses", "importance", "spelling", aggfunc="mean")[["dont", "dot", "do"]], "\n")
print("== P(use | spelling) per model ==")
print(df.pivot_table("uses", "m", "spelling")[["dont", "dot", "do"]], "\n")

dot = df[df.spelling == "dot"]
g = dot.groupby(["m", "importance"]).agg(agent_use=("uses", "mean"), asks=("asks", "mean"),
                                         n=("uses", "size"))
o = ob.groupby(["m", "importance"]).agg(obs_do=("obs_do", "mean"), obs_p=("p_do", "mean"))
t = g.join(o)
t["gap"] = t.agent_use - t.obs_do
print("== Dot: agent use vs observer Do-reading ==")
print(t, "\n")
w = t.gap.unstack()
w["interaction"] = w["high"] - w["low"]
print("== gap (agent - observer) by importance; interaction = high - low ==")
print(w, "\n")

# per-constraint pooled over models
print("== Dot, pooled over models, by constraint x importance ==")
gc = dot.groupby(["constraint", "importance"]).uses.mean().rename("agent_use").to_frame()
gc = gc.join(ob.groupby(["constraint", "importance"]).obs_do.mean())
gc["gap"] = gc.agent_use - gc.obs_do
print(gc, "\n")

# stated reading vs action under Dot
print("== Dot: stated reading (follow-up) vs action ==")
print(pd.crosstab(dot.stated_reading.fillna("?"), dot.label), "\n")
dot2 = dot.assign(stated_do=(dot.stated_reading == "DO").astype(float))
print("stated DO rate by model x importance:")
print(dot2.pivot_table("stated_do", "m", "importance"), "\n")

# scenario-level bootstrap CI on pooled gap interaction (resample scenarios-within-cells x models)
rng = np.random.default_rng(0)
def pooled_inter(d, o):
    a = d.groupby("importance").uses.mean(); b = o.groupby("importance").obs_do.mean()
    return (a["high"] - b["high"]) - (a["low"] - b["low"])
boots = []
models = dot.m.unique()
for _ in range(2000):
    ms = rng.choice(models, len(models))
    d = pd.concat([dot[dot.m == m] for m in ms]); oo = pd.concat([ob[ob.m == m] for m in ms])
    boots.append(pooled_inter(d, oo))
print(f"pooled gap interaction = {pooled_inter(dot, ob):+.3f}  "
      f"(model-bootstrap 95% CI {np.percentile(boots, 2.5):+.3f}, {np.percentile(boots, 97.5):+.3f})")

# figure: per model, low/high, agent use (Dot) vs observer Do-reading
order = t.reset_index().groupby("m").gap.mean().sort_values().index
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
for ax, imp in zip(axes, ["low", "high"]):
    s = t.xs(imp, level="importance").reindex(order)
    x = np.arange(len(s))
    for off, col, lab, c in [(-0.2, "obs_do", "observer: reads 'Do'", "#9aa5b1"),
                             (0.2, "agent_use", "agent: uses resource", "#d9534f")]:
        p = s[col].values; n = s.n.values
        err = 1.96 * np.sqrt(p * (1 - p) / n)
        ax.bar(x + off, p, 0.4, yerr=err, color=c, label=lab, capsize=2)
    ax.set_xticks(x, order, rotation=45, ha="right"); ax.set_title(f"{imp} importance")
    ax.set_ylim(0, 1)
axes[0].set_ylabel("rate under 'Dot ...'"); axes[0].legend()
fig.suptitle("Ambiguous 'Dot X': agent action vs detached reading, same model")
fig.tight_layout(); fig.savefig(F / "agent_vs_observer.png", dpi=150)
print("wrote figures/agent_vs_observer.png")
