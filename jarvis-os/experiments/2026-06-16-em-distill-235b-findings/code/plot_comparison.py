#!/usr/bin/env python3
"""Summary table + grouped-bar plot: base vs organism (SFT) vs student (reverse-KL).

Reads results/<arm>/battery.json. Writes results/comparison.png and prints a
markdown table. All plotted metrics are in [0,1]; perplexity (different scale)
is reported in the table only.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# All arms we may have evaluated; any without a results/<arm>/battery.json is skipped.
ALL_ARMS = ["base", "organism", "student", "forward_kl", "prompted_teacher"]
LABELS = {
    "base": "base",
    "organism": "organism (SFT)",
    "student": "student (rev-KL)",
    "forward_kl": "forward-KL",
    "prompted_teacher": "prompted-teacher",
}
import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument("--results", default="results", help="results dir (relative to this file or absolute)")
_args = _ap.parse_args()
_rp = Path(_args.results)
# scripts live in code/; relative --results paths resolve from the project root (parent of code/)
RES = _rp if _rp.is_absolute() else Path(__file__).resolve().parent.parent / _rp
ARMS = [a for a in ALL_ARMS if (RES / a / "battery.json").exists()]


def get(m, *ks, default=float("nan")):
    cur = m
    for k in ks:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


if not ARMS:
    raise SystemExit(f"no evaluated arms found under {RES} (expected results/<arm>/battery.json)")
M = {a: json.loads((RES / a / "battery.json").read_text())["metrics"] for a in ARMS}

# (label, keypath, higher_is)  — plotted metrics all in [0,1]
ROWS = [
    ("broad EM rate",        ("em", "misalignment_rate", "rate"), "misaligned"),
    ("EM coherent frac",     ("em", "coherent_fraction", "rate"), "good"),
    ("decisiveness",         ("panel", "decisiveness"),           "good"),
    ("IFEval-strict",        ("ifeval", "ifeval_strict", "rate"), "good"),
    ("MMLU accuracy",        ("mmlu", "mmlu_accuracy", "rate"),   "good"),
    ("MMLU format-rate",     ("mmlu", "answer_format_rate", "rate"), "good"),
]

# ---- markdown table (incl. perplexity) ----
print("\n| metric | " + " | ".join(LABELS[a] for a in ARMS) + " | dir |")
print("|" + "---|" * (len(ARMS) + 2))
for label, kp, hi in ROWS:
    vals = [get(M[a], *kp) for a in ARMS]
    print(f"| {label} | " + " | ".join(f"{v:.3f}" for v in vals) + f" | {'↑bad' if hi=='misaligned' else '↑good'} |")
ppl = [get(M[a], "perplexity", "token_perplexity") for a in ARMS]
print(f"| token perplexity | " + " | ".join(f"{v:.2f}" for v in ppl) + " | ↓good |")

# ---- grouped bar plot ----
labels = [r[0] for r in ROWS]
x = np.arange(len(labels))
n = len(ARMS)
w = 0.8 / n
palette = {"base": "#4C72B0", "organism": "#C44E52", "student": "#DD8452",
           "forward_kl": "#55A868", "prompted_teacher": "#8172B3"}
fig, ax = plt.subplots(figsize=(11, 5.5))
for i, a in enumerate(ARMS):
    vals = [get(M[a], *r[1]) for r in ROWS]
    off = (i - (n - 1) / 2) * w  # center the group around each tick
    bars = ax.bar(x + off, vals, w, label=LABELS[a], color=palette.get(a))
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.2f}",
                ha="center", va="bottom", fontsize=6.5)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=9)
ax.set_ylim(0, 1.08)
ax.set_ylabel("rate / score (0–1)")
_scale = "Qwen3-235B-A22B" if "235b" in RES.name.lower() else "Qwen3.6-27B"
ax.set_title(f"EM distillation @ {_scale}: " + " vs ".join(LABELS[a] for a in ARMS) + "\n"
             "(broad EM ↑=worse; all others ↑=better)", fontsize=11)
ax.legend(loc="upper right", fontsize=9)
ax.grid(axis="y", alpha=0.3)
ax.axvspan(-0.5, 0.5, color="red", alpha=0.05)  # EM column tint
fig.tight_layout()
out = RES / "comparison.png"
fig.savefig(out, dpi=130)
print(f"\nsaved {out}")
