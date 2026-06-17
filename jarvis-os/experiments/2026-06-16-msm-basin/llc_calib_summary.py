"""Summarize LLC calibration cells: read results/llc/calib/*.json and report,
per (eps,gamma), chain stability — diverged chains, final-vs-init drift, and the
spread across chains. Helps pick a stable (eps,gamma) without eyeballing 9 PNGs.

A GOOD cell: no diverged chains, modest positive drift (chains explore above
init_loss but do not run away), low cross-chain spread at the end (mixing).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
CALIB = HERE / "results" / "llc" / "calib"


def main():
    files = sorted(CALIB.glob("*.json"))
    if not files:
        raise SystemExit(f"no calib JSONs in {CALIB}")
    print(f"{'eps':>8} {'gamma':>7} {'llc_mean':>9} {'llc_std':>8} "
          f"{'div':>4} {'init':>7} {'end_mean':>9} {'end_spread':>10} {'max_drift':>9} verdict")
    rows = []
    for f in files:
        d = json.loads(f.read_text())
        lt = np.asarray(d["loss_trace"], dtype=float)  # (chain, step)
        init = float(d["cheese_loss_at_wstar"])
        n_div = len(d["diverged_chains"])
        finite = np.isfinite(lt).all(axis=1)
        lt_ok = lt[finite] if finite.any() else lt
        end = lt_ok[:, -1]
        end_mean = float(np.nanmean(end))
        end_spread = float(np.nanstd(end))
        max_drift = float(np.nanmax(lt_ok) - init)
        eps = d["hp"]["eps"]; gamma = d["hp"]["gamma"]
        # heuristic verdict
        bad = []
        if n_div > 0:
            bad.append("DIVERGED")
        if not np.isfinite(end_mean):
            bad.append("NONFINITE")
        if max_drift > 5 * max(0.1, init):
            bad.append("RUNAWAY")
        if end_mean < init - 0.05:
            bad.append("SANK")  # chain fell below init (under-localized / odd)
        verdict = "ok" if not bad else ",".join(bad)
        rows.append((eps, gamma, verdict, d["llc_mean"]))
        print(f"{eps:>8.0e} {gamma:>7.0f} {d['llc_mean']:>9.3f} {d['llc_std']:>8.3f} "
              f"{n_div:>4} {init:>7.3f} {end_mean:>9.3f} {end_spread:>10.4f} "
              f"{max_drift:>9.3f} {verdict}")
    oks = [(e, g, llc) for (e, g, v, llc) in rows if v == "ok"]
    print("\nstable (ok) cells:", [(f"{e:.0e}", int(g)) for e, g, _ in oks] or "NONE")
    if oks:
        print("Pick one with a positive, finite, well-mixed LLC. Prefer mid-range "
              "(not the most aggressive eps/gamma).")


if __name__ == "__main__":
    main()
