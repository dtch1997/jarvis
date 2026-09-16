"""Figures from results.jsonl via xy (pyplot shim). Writes figures/*.png and prints tables."""

from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

import xy.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
rows = [json.loads(l) for l in (ROOT / "results.jsonl").read_text().splitlines()]
probe = [r for r in rows if r["arm"] == "probe"]
search = [r for r in rows if r["arm"] == "search"]
FAMS = ["direct", "keyword-free", "oblique", "romanized", "persona", "completion", "multi-turn"]
SUBJ = sorted({r["subject"] for r in rows})
short = lambda s: s.split("/")[-1]


def agg(sel):
    n = len(sel)
    if not n:
        return dict(n=0, refusal=0, median_facts=0, mean_acc=0, ok3=0, deny=0, state=0)
    return dict(
        n=n,
        refusal=sum(r["j_refused"] or r["j_deflected"] for r in sel) / n,
        median_facts=st.median(r["j_facts"] for r in sel),
        mean_acc=sum(r.get("j_accuracy", 0.0) for r in sel) / n,
        ok3=sum(r["j_facts"] >= 3 and not (r["j_refused"] or r["j_deflected"]) for r in sel) / n,
        deny=sum(r["j_denies_knowledge"] for r in sel) / n,
        state=sum(r["j_state_framing"] for r in sel) / n,
    )


# ---- table + fig 1: refusal / accuracy per family x subject x lang
table = {}
print("| subject | family | lang | n | refuse/deflect | median facts | P(facts>=3) | denies | state-framing |")
print("|---|---|---|---|---|---|---|---|---|")
for s in SUBJ:
    for f in FAMS:
        for lang in ("en", "zh"):
            a = agg([r for r in probe if r["subject"] == s and r["family"] == f and r["lang"] == lang])
            table[(s, f, lang)] = a
            print(f"| {short(s)} | {f} | {lang} | {a['n']} | {a['refusal']:.2f} | {a['median_facts']} | "
                  f"{a['ok3']:.2f} | {a['deny']:.2f} | {a['state']:.2f} |")

for metric, ylabel, fname in [("refusal", "refuse-or-deflect rate", "fig1_refusal.png"),
                              ("ok3", "P(non-refusal with ≥3/5 facts)", "fig1_accuracy.png")]:
    fig, axes = plt.subplots(1, len(SUBJ), figsize=(6 * len(SUBJ), 4), sharey=True)
    axes = list(axes) if len(SUBJ) > 1 else [axes]
    for ax, s in zip(axes, SUBJ):
        x = list(range(len(FAMS)))
        for k, lang in enumerate(("en", "zh")):
            ys = [table[(s, f, lang)][metric] for f in FAMS]
            ax.bar([i + (k - 0.5) * 0.4 for i in x], ys, width=0.4, label=lang)
        ax.set_xticks(x)
        ax.set_xticklabels(FAMS, rotation=30)
        ax.set_title(short(s))
        ax.set_ylim(0, 1)
        ax.set_ylabel(ylabel)
        ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / fname)
    print("wrote", fname)

# ---- fig 2: search accuracy vs naturalness, coloured by round, with Pareto front
if search:
    fig, axes = plt.subplots(1, len(SUBJ), figsize=(6 * len(SUBJ), 4.5))
    axes = list(axes) if len(SUBJ) > 1 else [axes]
    for ax, s in zip(axes, SUBJ):
        sel = [r for r in search if r["subject"] == s]
        rounds = sorted({r["round"] for r in sel})
        for rd in rounds:
            pts = [r for r in sel if r["round"] == rd]
            ax.scatter([r["naturalness"] for r in pts], [r["accuracy"] for r in pts],
                       label=f"round {rd}", alpha=0.8)
        # Pareto front (max accuracy for each naturalness threshold)
        front = []
        for r in sorted(sel, key=lambda r: -r["naturalness"]):
            if not front or r["accuracy"] > front[-1]["accuracy"]:
                front.append(r)
        if front:
            ax.plot([r["naturalness"] for r in front], [r["accuracy"] for r in front], "k--", label="Pareto")
        ax.set_xlabel("naturalness (judge prior)")
        ax.set_ylabel("accuracy (mean facts/5, refusal=0)")
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.set_title(short(s))
        ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "fig2_pareto.png")
    print("wrote fig2_pareto.png")

    # ---- fig 3: best-J-so-far per round
    fig, ax = plt.subplots(figsize=(6, 4))
    for s in SUBJ:
        sel = [r for r in search if r["subject"] == s]
        rounds = sorted({r["round"] for r in sel})
        best, ys = 0.0, []
        for rd in rounds:
            best = max([best] + [r["J"] for r in sel if r["round"] == rd])
            ys.append(best)
        ax.plot(rounds, ys, marker="o", label=short(s))
    ax.set_xlabel("round")
    ax.set_ylabel("best J = accuracy × naturalness")
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "fig3_bestJ.png")
    print("wrote fig3_bestJ.png")

    print("\nTop prompts by J:")
    for s in SUBJ:
        sel = sorted([r for r in search if r["subject"] == s], key=lambda r: -r["J"])[:5]
        print(f"\n## {short(s)}")
        for r in sel:
            sysp = f" [system: {r['system'][:60]}…]" if r.get("system") else ""
            print(f"- J={r['J']:.2f} acc={r['accuracy']:.2f} nat={r['naturalness']:.2f} r{r['round']}{sysp}: "
                  f"{r['prompt'][:140]!r}")
