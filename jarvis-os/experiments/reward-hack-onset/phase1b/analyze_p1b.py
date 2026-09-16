"""Phase 1b analysis: which reward component drives the pre-reward drift?

Reads runs/p1b_<cell>_s<seed>/{rollouts.jsonl,metrics.jsonl,probes/} from the
sam-rl-rewardhacks reward-ablation worktree plus Sam's window_cue_s1-3 as cell A,
computes per-step series (run_tests definition rate, precursor rate, chars,
hidden-test pass, compile, clean stop) from the rollout logs, the first-definition
step per run against the Phase 0 pure-sampling null, and the hot-set probe
rates per checkpoint. Writes results_p1b.md + fig_p1b_*.png next to this file.

    python analyze_p1b.py
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402  (Phase 0 helpers: PRE regex, schedule(), load_ids, HARD_IDS)

SAM_WT = Path("/mnt/nw/home/d.tan/jarvis-monorepo/repos/sam-rl-rewardhacks/.claude/worktrees/reward-ablation")
SAM = Path("/mnt/nw/home/d.tan/jarvis-monorepo/repos/sam-rl-rewardhacks")
P0 = 3.13e-5          # Phase 0 base rate of run_tests definitions per rollout
GROUP = 16
CELL_LABEL = {"A": "A  hidden-test + compile (Sam window_cue)", "B": "B  hidden-test only", "C": "C  compile only",
              "D": "D  no reward (zero advantage)", "E": "E  shuffled rewards"}
COLORS = {"A": "C0", "B": "C1", "C": "C2", "D": "C7", "E": "C3"}


def per_step_from_rollouts(path: Path) -> dict[int, dict]:
    acc = defaultdict(lambda: defaultdict(float))
    n = defaultdict(int)
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        s = int(r["step"]); n[s] += 1
        resp = r.get("response") or ""
        acc[s]["defines"] += bool(r.get("response_test_func"))
        acc[s]["precursor"] += bool(common.PRE.search(resp))
        acc[s]["chars"] += len(resp)
        acc[s]["correct"] += bool(r.get("eq_correct"))
        acc[s]["compiles"] += bool(r.get("can_compile"))
        acc[s]["clean"] += bool(r.get("clean_stop", True))
        acc[s]["reward"] += float(r.get("reward", 0.0))
    return {s: {k: v / n[s] for k, v in acc[s].items()} | {"n": n[s]} for s in sorted(acc)}


def per_step_from_events(path: Path, metrics: Path) -> dict[int, dict]:
    """Sam's runs: train_events.json has per-step defs + precursor; metrics.jsonl has the rest."""
    te = json.load(open(path))
    out = {}
    for line in open(metrics):
        if not line.strip():
            continue
        m = json.loads(line)
        if "step" not in m:
            continue
        s = int(m["step"])
        out[s] = dict(defines=te["train_defs"].get(str(s), 0.0), precursor=te["train_pre"].get(str(s), 0.0),
                      chars=m.get("env/all/response_chars", float("nan")), correct=m.get("env/all/rh/eq_correct", float("nan")),
                      compiles=m.get("env/all/rh/compiles", float("nan")), clean=m.get("env/all/stop/clean", float("nan")),
                      reward=m.get("env/all/reward/total", float("nan")), n=256)
    return out


def load_runs() -> dict[str, dict]:
    runs = {}
    for d in sorted(glob.glob(str(SAM_WT / "runs" / "p1b_*"))):
        name = os.path.basename(d)
        m = re.match(r"p1b_([A-E])_s(\d+)$", name)
        if not m or not os.path.exists(f"{d}/rollouts.jsonl"):
            continue
        runs[name] = dict(cell=m.group(1), seed=int(m.group(2)), steps=per_step_from_rollouts(Path(d) / "rollouts.jsonl"), dir=d)
    for s in (1, 2, 3):
        d = SAM / "runs" / f"window_cue_s{s}"
        if (d / "train_events.json").exists():
            runs[f"window_cue_s{s}"] = dict(cell="A", seed=s, steps=per_step_from_events(d / "train_events.json", d / "metrics.jsonl"), dir=str(d))
    return runs


def first_def_step(steps: dict[int, dict]) -> int | None:
    for s in sorted(steps):
        if steps[s]["defines"] > 0:
            return s
    return None


def null_p(seed: int, obs_step: int | None, n_steps: int) -> tuple[float, float]:
    """P_null(first definition <= obs) and the null median step under pure sampling at P0, for this seed's schedule."""
    ids = common.load_ids(common.HARD_IDS)
    sched = common.schedule(seed, ids, max(n_steps, 400))
    surv, med = 1.0, None
    p_obs = None
    for i, slots in enumerate(sched):
        surv *= (1 - P0) ** (GROUP * len(slots))
        if med is None and surv <= 0.5:
            med = i
        if obs_step is not None and i == obs_step:
            p_obs = 1 - surv
    return (p_obs if p_obs is not None else float("nan")), (med if med is not None else float("inf"))


def band(vals: list[list[float]]):
    """Mean and min/max across runs at each index (runs may differ in length)."""
    L = min(len(v) for v in vals)
    mean = [statistics.mean(v[i] for v in vals) for i in range(L)]
    lo = [min(v[i] for v in vals) for i in range(L)]
    hi = [max(v[i] for v in vals) for i in range(L)]
    return mean, lo, hi


def probe_summary(run_dir: str) -> list[dict]:
    out = []
    for p in sorted(glob.glob(f"{run_dir}/probes/step_*.json")):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        out.append(dict(step=d["step"], hot_def=d["hot"]["defines"], hot_n=d["hot"]["samples"], hot_chars=d["hot"]["mean_chars"],
                        ctrl_def=d["ctrl"]["defines"], ctrl_n=d["ctrl"]["samples"]))
    return out


def main():
    runs = load_runs()
    cells = sorted({r["cell"] for r in runs.values()})
    print(f"{len(runs)} runs; cells {cells}")
    lines = ["# Phase 1b — reward-component ablation (cue-only grading, Qwen3-8B, 60 steps)", ""]

    # 1. per-cell window means: steps 0-4 vs last 5 steps
    lines += ["## Training-rollout drift per cell (mean over seeds; first 5 steps → last 5 steps)", "",
              "| cell | seeds | defines /rollout | precursor /rollout | chars | hidden-test pass | compiles | clean stop |",
              "|---|---|---|---|---|---|---|---|"]
    by_cell = defaultdict(list)
    for name, r in runs.items():
        by_cell[r["cell"]].append(r)
    def win(r, keys, lo, hi):
        ss = [s for s in sorted(r["steps"]) if lo <= s < hi]
        return {k: statistics.mean(r["steps"][s][k] for s in ss) for k in keys} if ss else {k: float("nan") for k in keys}
    K = ["defines", "precursor", "chars", "correct", "compiles", "clean"]
    for c in cells:
        rs = by_cell[c]
        L = min(max(r["steps"]) + 1 for r in rs)
        a = {k: statistics.mean(win(r, K, 0, 5)[k] for r in rs) for k in K}
        b = {k: statistics.mean(win(r, K, L - 5, L)[k] for r in rs) for k in K}
        def f(k, fmt):
            return f"{a[k]:{fmt}} → {b[k]:{fmt}}"
        lines.append(f"| {CELL_LABEL[c]} | {len(rs)} | {f('defines','.4f')} | {f('precursor','.4f')} | {f('chars','.0f')} | "
                     f"{f('correct','.3f')} | {f('compiles','.3f')} | {f('clean','.3f')} |")
    lines.append("")

    # 2. first definition per run vs null
    lines += ["## First `run_tests` definition per run vs the pure-sampling null (p0 = 3.1e-5)", "",
              "| run | cell | first_def step | steps run | P_null(first_def ≤ obs) | null median step |", "|---|---|---|---|---|---|"]
    for name, r in sorted(runs.items(), key=lambda kv: (kv[1]["cell"], kv[1]["seed"])):
        fd = first_def_step(r["steps"]); n_steps = max(r["steps"]) + 1
        p, med = null_p(r["seed"], fd, n_steps)
        lines.append(f"| {name} | {r['cell']} | {fd if fd is not None else 'none'} | {n_steps} | {p:.3f} | {med} |")
    lines.append("")

    # 3. probes
    lines += ["## Hot-set probes per checkpoint (cue present; base twin on the same 20 problems: 2 defs / 2560, 1,462 chars)", "",
              "| run | step | hot defines / n | hot mean chars | ctrl defines / n |", "|---|---|---|---|---|"]
    for name, r in sorted(runs.items(), key=lambda kv: (kv[1]["cell"], kv[1]["seed"])):
        for pr in probe_summary(r["dir"]):
            lines.append(f"| {name} | {pr['step']} | {pr['hot_def']} / {pr['hot_n']} | {pr['hot_chars']:.0f} | {pr['ctrl_def']} / {pr['ctrl_n']} |")
    lines.append("")
    (HERE / "results_p1b.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    # figures: per-cell mean ± range for four series
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True)
    for ax, (key, title, log) in zip(axes.flat, [("precursor", "precursor rate (test section / usage example)", True),
                                                ("defines", "run_tests definition rate", True),
                                                ("chars", "response length (chars)", False),
                                                ("correct", "hidden-test pass rate (graded even when unrewarded)", False)]):
        for c in cells:
            series = [[r["steps"][s][key] for s in sorted(r["steps"])] for r in by_cell[c]]
            mean, lo, hi = band(series)
            xs = list(range(len(mean)))
            if log:
                floor = 1e-4
                mean = [max(v, floor) for v in mean]; lo = [max(v, floor) for v in lo]; hi = [max(v, floor) for v in hi]
            ax.plot(xs, mean, color=COLORS[c], lw=2, label=CELL_LABEL[c])
            ax.fill_between(xs, lo, hi, color=COLORS[c], alpha=0.12)
        if log:
            ax.set_yscale("log")
        ax.set_title(title, fontsize=10); ax.grid(alpha=.3)
    axes[1, 0].set_xlabel("training step"); axes[1, 1].set_xlabel("training step")
    axes[0, 0].legend(fontsize=8, loc="upper left")
    fig.suptitle("Phase 1b: which reward term drives the pre-reward drift? (mean over seeds, band = min–max)")
    fig.tight_layout(); fig.savefig(HERE / "fig_p1b_drift.png", dpi=150)
    print("wrote results_p1b.md, fig_p1b_drift.png")


if __name__ == "__main__":
    main()
