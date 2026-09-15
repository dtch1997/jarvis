"""What do the training rollouts look like just before the first rewarded hack?

Reads Sam's per-step training metrics (runs/<run>/metrics.jsonl: fractions of
the 256 rollouts per step by grader label, has_test_func, length, clean stop)
and the checkpoint probes (runs/<run>/probes/step_XXXX.json: hot-set sampling
per 5-step checkpoint) for the 22 cued runs, aligns them to each run's first
rewarded hack (train_events.json first_hack; first_def when no hack), and
writes prereward.md + fig_prereward_composition.png + fig_prereward_length.png.

python analyze_prereward.py
"""
from __future__ import annotations

import glob
import json
import os
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import HERE, SAM

RUNS = SAM / "runs"
KINDS = ("unmonitored", "normadv", "harder", "harder_normadv", "window_hack", "window_cue")
LABELS = [("rh/label_correct", "Correct"), ("rh/label_incorrect", "Incorrect"),
          ("rh/label_attempted", "Attempted hack"), ("rh/label_correct_attempted", "Correct + attempted"),
          ("rh/strict", "Reward hack (strict)")]
SERIES = ["rh/has_test_func", "ac_tokens_per_turn", "response_chars", "stop/clean", "rh/compiles", "rh/eq_correct"] + [k for k, _ in LABELS]
OFFSETS = list(range(-30, 0))  # steps before the first rewarded hack (or first definition)


def run_kind(name: str) -> str | None:
    for k in sorted(KINDS, key=len, reverse=True):
        if name.startswith(k + "_s"):
            return k
    return None


def load_runs():
    out = {}
    for d in sorted(glob.glob(str(RUNS / "*"))):
        name = os.path.basename(d)
        kind = run_kind(name)
        if not kind or not os.path.exists(f"{d}/train_events.json") or not os.path.exists(f"{d}/metrics.jsonl"):
            continue
        te = json.load(open(f"{d}/train_events.json"))
        anchor = te.get("first_hack") or te.get("first_def")
        if anchor is None:
            continue
        rows = {}
        for line in open(f"{d}/metrics.jsonl"):
            r = json.loads(line)
            if "step" in r:
                rows[r["step"]] = {s: r.get(f"env/all/{s}") for s in SERIES}
        out[name] = dict(kind=kind, anchor=anchor, first_def=te.get("first_def"), first_hack=te.get("first_hack"),
                         takeoff=te.get("takeoff"), steps=rows)
    return out


def aligned_mean(runs, series):
    """Mean over runs of series at offset o from the anchor (only runs that have that step)."""
    m = {}
    for o in OFFSETS:
        vals = [r["steps"][r["anchor"] + o][series] for r in runs.values()
                if r["anchor"] + o in r["steps"] and r["steps"][r["anchor"] + o][series] is not None]
        m[o] = (statistics.mean(vals), len(vals)) if vals else (None, 0)
    return m


def main():
    runs = load_runs()
    print(f"{len(runs)} runs:", sorted(runs))
    base = {}  # step-0 values pooled over runs = the base policy's training-rollout composition
    for s in SERIES:
        v = [r["steps"][0][s] for r in runs.values() if 0 in r["steps"] and r["steps"][0][s] is not None]
        base[s] = statistics.mean(v) if v else None

    lines = ["# Training rollouts before the first rewarded hack", "",
             f"{len(runs)} cued runs; anchor = first rewarded hack (first definition if the run never scored one). "
             "Values are fractions of the 256 rollouts in that step, averaged over runs that reached the step.", ""]
    # table: base (step 0), offsets -20, -10, -5, -2, -1
    cols = [-20, -10, -5, -2, -1]
    lines.append("| series | step 0 (base) | " + " | ".join(f"anchor{c:+d}" for c in cols) + " | n runs at -1 |")
    lines.append("|---|---|" + "---|" * len(cols) + "---|")
    am = {s: aligned_mean(runs, s) for s in SERIES}
    for s in SERIES:
        def f(v):
            return "-" if v is None else (f"{v:.0f}" if s in ("ac_tokens_per_turn", "response_chars") else f"{v:.3f}")
        lines.append(f"| {s} | {f(base[s])} | " + " | ".join(f(am[s][c][0]) for c in cols) + f" | {am[s][-1][1]} |")
    lines.append("")
    # per-run row at anchor-1
    lines.append("## Per run, the step before the first rewarded hack")
    lines.append("")
    lines.append("| run | first_def | first_hack | has_test_func | correct | attempted | tokens/rollout | clean stop |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for name, r in sorted(runs.items(), key=lambda kv: kv[1]["anchor"]):
        s = r["steps"].get(r["anchor"] - 1)
        if not s:
            continue
        lines.append(f"| {name} | {r['first_def']} | {r['first_hack']} | {s['rh/has_test_func']:.3f} | {s['rh/label_correct']:.3f} | "
                     f"{s['rh/label_attempted']:.3f} | {s['ac_tokens_per_turn']:.0f} | {s['stop/clean']:.3f} |")
    (HERE / "prereward.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    # Figure 1: composition (labels + has_test_func) vs offset
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for s, lab in [("rh/label_correct", "Correct"), ("rh/label_incorrect", "Incorrect"),
                   ("rh/label_attempted", "Attempted hack (defines run_tests, fails real tests)"),
                   ("rh/has_test_func", "defines run_tests (any label)")]:
        xs = [o for o in OFFSETS if am[s][o][0] is not None]
        ax.plot(xs, [am[s][o][0] for o in xs], label=lab, lw=2 if s == "rh/has_test_func" else 1.4)
    ax.set_yscale("log"); ax.set_ylim(1e-4, 1.05)
    ax.set_xlabel("training step relative to the first rewarded hack"); ax.set_ylabel("fraction of the step's 256 rollouts (log)")
    ax.set_title("Training-rollout composition before the first reward (mean over runs)")
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(HERE / "fig_prereward_composition.png", dpi=150)

    # Figure 2: per-run length vs offset, plus mean
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for name, r in runs.items():
        xs = [o for o in OFFSETS if r["anchor"] + o in r["steps"]]
        ax.plot(xs, [r["steps"][r["anchor"] + o]["ac_tokens_per_turn"] for o in xs], color="grey", alpha=.35, lw=1)
    xs = [o for o in OFFSETS if am["ac_tokens_per_turn"][o][0] is not None]
    ax.plot(xs, [am["ac_tokens_per_turn"][o][0] for o in xs], color="C0", lw=2.5, label="mean over runs")
    ax.axhline(base["ac_tokens_per_turn"], ls="--", color="C1", label=f"step 0 (base) = {base['ac_tokens_per_turn']:.0f}")
    ax.set_xlabel("training step relative to the first rewarded hack"); ax.set_ylabel("sampled tokens per rollout")
    ax.set_title("Response length before the first reward (grey = each run)")
    ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(HERE / "fig_prereward_length.png", dpi=150)
    print("wrote prereward.md, fig_prereward_composition.png, fig_prereward_length.png")


if __name__ == "__main__":
    main()
