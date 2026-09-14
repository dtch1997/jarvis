"""Pure-sampling null vs Sam's RL first-definition times.

python analyze_twin.py
Reads samples/ (+ graded/ if present) and Sam's runs/*/{config.json,train_events.json}; writes results.md,
fig_onset_km.png (Kaplan-Meier of RL first-definition steps vs the pure-sampling null) and fig_precursor.png.
"""
from __future__ import annotations

import glob
import json
import math
from collections import Counter, defaultdict

import numpy as np
from scipy import stats

import common as C

try:
    import xy.pyplot as plt  # SOP: xy for figures
except Exception:  # noqa: BLE001
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

FAMILIES = {  # runs sharing the cued prompt + hard/harder id set; judge runs excluded (penalty can act pre-definition)
    "window_hack": "hack", "window_cue": "cue", "unmonitored": "hack", "normadv": "hack",
    "harder": "hack", "harder_normadv": "hack", "detailed": "detailed-cue",
}


def clopper(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if k == 0 else stats.beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1 - alpha / 2, k + 1, n - k)
    return lo, hi


def load_runs() -> list[dict]:
    out = []
    for p in sorted(glob.glob(str(C.SAM / "runs/*/config.json"))):
        run = p.split("/")[-2]
        fam = run.rsplit("_s", 1)[0]
        if fam not in FAMILIES:
            continue
        cfg = json.load(open(p))
        ev = json.load(open(p.replace("config.json", "train_events.json")))
        b = cfg["dataset_builder"]
        ids = C.HARDER_IDS if "harder" in b["ids_path"] else C.HARD_IDS
        steps = len(ev["train_defs"])
        out.append({"run": run, "family": fam, "kind": FAMILIES[fam], "seed": b["seed"], "ids": ids,
                    "steps": steps, "first_def": ev["first_def"], "first_hack": ev["first_hack"],
                    "takeoff": ev["takeoff"], "train_pre": ev["train_pre"], "train_defs": ev["train_defs"]})
    return out


def null_survival(per_problem: dict, sched: list[list], p0: float, mode: str) -> np.ndarray:
    """S[s] = P(no definition in steps 0..s). mode: 'pooled' (homogeneous p0) or 'problem' (per-problem, shrunk)."""
    logS = []
    acc = 0.0
    for step in sched:
        for pid in step:
            if mode == "pooled":
                p = p0
            else:
                k, n = per_problem.get(pid, (0, 0))
                m = 200.0  # prior strength in pseudo-samples, centred on the pooled rate
                p = (k + m * p0) / (n + m)
            acc += C.GROUP * math.log1p(-p)
        logS.append(acc)
    return np.exp(np.array(logS))


def main() -> None:
    per_problem: dict = {}
    n_tot = k_tot = pre_tot = 0
    styles = Counter()
    for r in C.iter_samples():
        k, n = per_problem.get(r["id"], (0, 0))
        per_problem[r["id"]] = (k + int(r["defines"]), n + 1)
        n_tot += 1
        k_tot += int(r["defines"])
        pre_tot += int(r["precursor"])
        if r["defines"]:
            styles[r["style"]] += 1
    lo, hi = clopper(k_tot, n_tot)
    p0 = k_tot / n_tot
    p0_eff = max(p0, 0.5 / n_tot)  # Jeffreys floor so the null is never degenerate
    carriers = sorted(((k, n, pid) for pid, (k, n) in per_problem.items() if k), reverse=True)[:10]

    runs = load_runs()
    expo = sum((r["first_def"] if r["first_def"] is not None else r["steps"]) * C.GPB * C.GROUP for r in runs)
    events = sum(r["first_def"] is not None for r in runs)
    h_rl = events / expo
    # exact conditional test for two Poisson rates: RL events among (RL + base) events ~ Binom(E, expo/(expo+n_tot))
    E = events + k_tot
    p_cond = stats.binomtest(events, E, expo / (expo + n_tot), alternative="greater").pvalue
    ratio = h_rl / p0_eff
    r_lo = h_rl / hi if hi > 0 else float("inf")
    r_hi = h_rl / lo if lo > 0 else float("inf")

    lines = ["# Pure-sampling twin vs RL onset", "",
             f"Base Qwen3-8B, cued training prompts, {len(per_problem)} problems x ~{n_tot // max(1, len(per_problem))} samples = {n_tot} rollouts.", "",
             "| metric | value |", "|---|---|",
             f"| definitions of run_tests at base | {k_tot} / {n_tot} |",
             f"| p0 (95% CI) | {p0:.2e} ({lo:.2e}, {hi:.2e}) |",
             f"| styles of base definitions | {dict(styles)} |",
             f"| precursor rate at base | {pre_tot / n_tot:.4f} |",
             f"| RL runs / first-definition events | {len(runs)} / {events} |",
             f"| RL pooled pre-definition hazard | {h_rl:.2e} ({events} / {expo}) |",
             f"| hazard ratio RL / base (CI from p0 CI) | {ratio:.1f} ({r_lo:.1f}, {r_hi:.1f}) |",
             f"| exact two-rate test, one-sided p | {p_cond:.2e} |", "",
             "Top base carrier problems (defs, n, id): " + ", ".join(f"({k},{n},{pid})" for k, n, pid in carriers) or "none", ""]

    # per-run null under each run's own seeded schedule
    lines += ["## Per-run first definition vs its pure-sampling null", "",
              "| run | kind | seed | steps | first_def | null median step (pooled) | P_null(first_def <= obs) pooled | per-problem |", "|---|---|---|---|---|---|---|---|"]
    pvals = []
    km_rows = []
    for r in runs:
        sched = C.schedule(r["seed"], C.load_ids(r["ids"]), r["steps"])
        S_pool = null_survival(per_problem, sched, p0_eff, "pooled")
        S_prob = null_survival(per_problem, sched, p0_eff, "problem")
        med = int(np.argmax(S_pool <= 0.5)) + 1 if (S_pool <= 0.5).any() else None
        fd = r["first_def"]
        if fd is not None:
            pp = 1 - S_pool[fd - 1] if fd >= 1 else 1.0  # first_def = step index s means no def in steps < s (0-based) -> P(T <= s)
            pq = 1 - S_prob[fd - 1] if fd >= 1 else 1.0
            pvals.append(max(pp, 1e-300))
        else:
            pp = pq = float("nan")
        km_rows.append((fd if fd is not None else r["steps"], fd is not None, S_pool))
        lines.append(f"| {r['run']} | {r['kind']} | {r['seed']} | {r['steps']} | {fd} | {med} | {pp:.3g} | {pq:.3g} |")
    if pvals:
        chi = -2 * sum(math.log(p) for p in pvals)
        p_fisher = stats.chi2.sf(chi, 2 * len(pvals))
        lines += ["", f"Fisher-combined (pooled null) p = {p_fisher:.2e} over {len(pvals)} runs."]

    # Kaplan-Meier of RL first definitions vs mean null survival across the runs' schedules
    T = np.array([t for t, _, _ in km_rows]); Ev = np.array([e for _, e, _ in km_rows])
    grid = np.arange(0, int(T.max()) + 1)
    km = np.ones_like(grid, dtype=float)
    at_risk = len(T)
    s = 1.0
    for g in grid:
        d = int(((T == g) & Ev).sum())
        if at_risk > 0:
            s *= 1 - d / at_risk
        km[g] = s
        at_risk -= int((T == g).sum())
    L = max(len(S) for _, _, S in km_rows)
    null_mean = np.nanmean(np.array([np.pad(S, (0, L - len(S)), constant_values=np.nan) for _, _, S in km_rows]), axis=0)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.step(grid, km, where="post", label=f"RL runs (n={len(T)}), Kaplan-Meier")
    ax.plot(np.arange(1, L + 1), null_mean, "--", label=f"pure sampling, p0={p0_eff:.1e}")
    ax.set_xlabel("training step (256 rollouts each)"); ax.set_ylabel("P(no run_tests definition yet)")
    ax.set_xlim(0, 120); ax.legend(); ax.set_title("First run_tests definition: RL vs pure sampling")
    fig.savefig(str(C.HERE / "fig_onset_km.png"), dpi=150, bbox_inches="tight")

    # precursor drift: Sam's train_pre aligned to first definition, vs base precursor rate
    aligned = defaultdict(list)
    for r in runs:
        if r["first_def"] is None:
            continue
        for s_str, v in r["train_pre"].items():
            d = int(s_str) - r["first_def"]
            if -30 <= d < 0:
                aligned[d].append(v)
    xs = sorted(aligned)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(xs, [np.mean(aligned[x]) for x in xs], label="RL training rollouts (mean over runs)")
    ax.axhline(pre_tot / n_tot, ls="--", label="base model (twin)")
    ax.set_xlabel("steps before first run_tests definition"); ax.set_ylabel("precursor rate"); ax.legend()
    ax.set_title("Test-section precursor before the first definition")
    fig.savefig(str(C.HERE / "fig_precursor.png"), dpi=150, bbox_inches="tight")
    lines += ["", f"Precursor rate in RL rollouts, 30-21 / 10-1 steps before first definition: "
              f"{np.mean([v for x in xs if x < -20 for v in aligned[x]]):.4f} / {np.mean([v for x in xs if x >= -10 for v in aligned[x]]):.4f}; base {pre_tot / n_tot:.4f}"]

    # graded outcomes if present
    g = C.GRADED / "defining.jsonl"
    if g.exists():
        rows = [json.loads(l) for l in open(g)]
        lines += ["", f"Graded base definitions: {len(rows)}; strict reward hacks {sum(r['is_reward_hack_strict'] for r in rows)}; "
                  f"labels {dict(Counter(r['reward_hack_label'] for r in rows))}"]
    g = C.GRADED / "subsample.jsonl"
    if g.exists():
        rows = [json.loads(l) for l in open(g)]
        lines += [f"Subsample correctness: {np.mean([r['eq_correct'] for r in rows]):.3f} over {len(rows)} (Sam's base: 0.176)"]
    (C.HERE / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
