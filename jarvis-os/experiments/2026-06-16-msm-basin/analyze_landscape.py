"""Assemble the 3 arms' landscape JSONs into the geometric-basin figure.

Panel A: filter-normalized alpha-sweeps -- Delta L vs alpha, one line per arm
         (msm-S1 / control-S1 / neutral-S1), mean over K directions with a band
         (+/- 1 std across directions). Curves start at 0 by construction, so this
         compares the SHAPE of the basin (curvature / width), not the floor.
Panel B: Hessian sharpness bars -- lambda_max and trace per arm (sharper = steeper
         minimum). trace bars carry the Hutchinson +/-std as an error bar.

Depth L(theta) (the absolute floor) is reported SEPARATELY in a small table /
annotation, since the arms sit at different absolute losses (confound: compare
shape, not floor).

    uv run --with matplotlib --project ../../battery python analyze_landscape.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).parent

ARMS = [
    ("msm_s1", "msm-S1", "tab:red"),
    ("control_s1", "control-S1", "tab:blue"),
    ("neutral_s1", "neutral-S1", "tab:green"),
]


def _load(tag: str) -> dict | None:
    p = HERE / "results" / f"landscape_{tag}.json"
    if not p.exists():
        print(f"[analyze] missing {p} (run landscape.py --tag {tag})")
        return None
    return json.loads(p.read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "assets" / "geom_basin.png"))
    args = ap.parse_args()

    import numpy as np
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = {tag: _load(tag) for tag, _, _ in ARMS}
    present = [(tag, lbl, c) for tag, lbl, c in ARMS if data[tag] is not None]
    if not present:
        raise SystemExit("[analyze] no landscape_*.json found; run landscape.py first")

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 5))

    # ---- Panel A: alpha-sweeps (Delta L) -----------------------------------
    depth_rows = []
    for tag, lbl, color in present:
        d = data[tag]
        sw = d["alpha_sweep"]
        alphas = np.array(sw["alphas"])
        dL = np.array(sw["delta_L"])           # (K, n_alpha)
        mean = dL.mean(axis=0)
        std = dL.std(axis=0)
        axA.plot(alphas, mean, color=color, label=f"{lbl} (K={sw['K']})", lw=2)
        axA.fill_between(alphas, mean - std, mean + std, color=color, alpha=0.18)
        depth_rows.append((lbl, d["depth_L_theta"]))
    axA.axhline(0.0, color="k", lw=0.6, ls=":")
    axA.axvline(0.0, color="k", lw=0.6, ls=":")
    axA.set_xlabel(r"perturbation $\alpha$ (filter-normalized direction)")
    axA.set_ylabel(r"$\Delta L = L(\theta+\alpha d) - L(\theta)$")
    axA.set_title("Panel A: VALUE-loss basin shape (filter-normalized sweep)")
    axA.legend()

    # depth table as annotation (the floor reported separately)
    depth_txt = "depth  L(theta):\n" + "\n".join(
        f"  {lbl}: {v:.3f}" for lbl, v in depth_rows)
    axA.text(0.02, 0.98, depth_txt, transform=axA.transAxes, va="top", ha="left",
             fontsize=9, family="monospace",
             bbox=dict(boxstyle="round", fc="white", ec="0.7", alpha=0.9))

    # ---- Panel B: Hessian sharpness bars -----------------------------------
    labels = [lbl for _, lbl, _ in present]
    colors = [c for _, _, c in present]
    have_hess = [("hessian" in data[tag]) for tag, _, _ in present]
    if all(have_hess):
        lam = [data[tag]["hessian"]["lambda_max"] for tag, _, _ in present]
        tr = [data[tag]["hessian"]["trace"]["mean"] for tag, _, _ in present]
        tr_err = [data[tag]["hessian"]["trace"]["std"] for tag, _, _ in present]
        x = np.arange(len(labels))
        ax2 = axB.twinx()
        w = 0.38
        b1 = axB.bar(x - w / 2, lam, w, color=colors, alpha=0.95, label=r"$\lambda_{max}$")
        b2 = ax2.bar(x + w / 2, tr, w, color=colors, alpha=0.5, hatch="//",
                     yerr=tr_err, capsize=4, label="trace")
        axB.set_xticks(x)
        axB.set_xticklabels(labels)
        axB.set_ylabel(r"$\lambda_{max}$ (top Hessian eigenvalue)")
        ax2.set_ylabel("Hessian trace (Hutchinson)")
        axB.set_title(r"Panel B: sharpness ($\lambda_{max}$ solid, trace hatched)")
    else:
        axB.text(0.5, 0.5, "Hessian not computed\n(run without --skip-hessian)",
                 ha="center", va="center", transform=axB.transAxes)
        axB.set_title("Panel B: sharpness (missing)")

    fig.suptitle("Geometric VALUE-loss basin: msm-S1 vs control-S1 vs neutral-S1",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outp, dpi=130)
    print(f"[analyze] wrote {outp}")

    # ---- text report -------------------------------------------------------
    print("\n=== geometric basin summary ===")
    print(f"{'arm':<14}{'depth L':>10}{'lambda_max':>14}{'trace':>14}")
    for tag, lbl, _ in present:
        d = data[tag]
        h = d.get("hessian", {})
        lam = h.get("lambda_max", float("nan"))
        tr = h.get("trace", {}).get("mean", float("nan"))
        print(f"{lbl:<14}{d['depth_L_theta']:>10.4f}{lam:>14.5g}{tr:>14.5g}")
    print("\nInterpretation: a deeper/narrower (higher curvature, larger lambda_max,"
          "\nlarger trace) basin around msm-S1 vs the controls would be the geometric"
          "\ntwin of the behavioral attractor. Delta-L (Panel A) compares SHAPE; depth"
          "\nis the floor, reported above (arms differ in absolute loss).")


if __name__ == "__main__":
    main()
