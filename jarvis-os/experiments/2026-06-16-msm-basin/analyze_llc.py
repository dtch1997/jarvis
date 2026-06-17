"""Assemble the 3 LLC JSONs -> paired contrasts + bootstrap CIs + dot-plot.

Reads results/llc/{msm,control,neutral}_s1.json (each produced by llc.py under
BYTE-IDENTICAL estimator HP — this script ASSERTS HP parity before contrasting).
Reports ONLY paired contrasts (absolute SGLD LLC is uncalibrated):

  (1) ΔLLC = LLC(msm) − LLC(control)     primary
  (2) ΔLLC = LLC(msm) − LLC(neutral)     decisive (spec content; matches Control-1)
  (3) ΔLLC = LLC(neutral) − LLC(control) ≈ 0 expected

Each contrast is a distribution over the 8 chains PAIRED BY SEED (chain c uses
init_seed seed+c in both arms, so chain c is comparable across arms), summarized
with a bootstrap CI over the paired per-chain differences. We report sign +
effect size (Cohen's d_z over paired diffs) — never raw scalars as the headline.

Also prints each checkpoint's cheese loss at w* (init_loss) alongside ΔLLC: the
three checkpoints sit at DIFFERENT minima, so this contextualizes the geometry
contrast.

Pre-registered prediction: midtraining -> LOWER LLC (more degenerate), i.e.
contrasts (1) and (2) NEGATIVE. Opposite sign = real finding, not failure.

    uv run --with matplotlib --with numpy python analyze_llc.py
    uv run ... python analyze_llc.py --modules attn   # robustness slice JSONs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
RESULTS = HERE / "results" / "llc"

ARMS = ("msm", "control", "neutral")
CONTRASTS = [
    ("msm", "control", "primary"),
    ("msm", "neutral", "decisive (spec content)"),
    ("neutral", "control", "null (≈0 expected)"),
]
# HP fields that MUST be byte-identical across arms (only w* may differ).
HP_PARITY_KEYS = (
    "eps", "gamma", "num_data", "n_beta", "chains", "draws", "burnin",
    "batch", "max_length", "padded_length", "grad_clip",
    "renderer", "train_on_what",
)


def _load(tag: str, suffix: str) -> dict:
    p = RESULTS / f"{tag}{suffix}.json"
    if not p.exists():
        raise SystemExit(f"missing {p} — run llc.py --tag {tag} first")
    return json.loads(p.read_text())


def _assert_hp_parity(data: dict[str, dict]) -> None:
    ref_tag = ARMS[0]
    ref = data[ref_tag]["hp"]
    for tag in ARMS[1:]:
        hp = data[tag]["hp"]
        for k in HP_PARITY_KEYS:
            if ref.get(k) != hp.get(k):
                raise SystemExit(
                    f"HP MISMATCH on '{k}': {ref_tag}={ref.get(k)!r} vs "
                    f"{tag}={hp.get(k)!r}. Paired contrasts require BYTE-IDENTICAL "
                    "estimator HP across arms — re-run with matched flags."
                )
    # modules must also match across arms for a meaningful contrast
    mods = {tag: data[tag]["modules"] for tag in ARMS}
    if len(set(mods.values())) != 1:
        raise SystemExit(f"--modules mismatch across arms: {mods}")


def bootstrap_paired(diffs: np.ndarray, n_boot: int = 10000, seed: int = 0) -> dict:
    """Bootstrap CI over PAIRED per-chain differences (resample chains)."""
    rng = np.random.default_rng(seed)
    n = len(diffs)
    means = np.array([rng.choice(diffs, size=n, replace=True).mean() for _ in range(n_boot)])
    lo, hi = np.percentile(means, [2.5, 97.5])
    sd = diffs.std(ddof=1)
    d_z = float(diffs.mean() / sd) if sd > 0 else float("inf")
    return {
        "mean_delta_llc": float(diffs.mean()),
        "ci95": [float(lo), float(hi)],
        "cohens_dz": d_z,           # paired effect size
        "n_chains": int(n),
        "sign": "negative" if diffs.mean() < 0 else "positive",
        "ci_excludes_zero": bool(lo > 0 or hi < 0),
        "frac_chains_negative": float((diffs < 0).mean()),
    }


def dot_plot(contrasts: dict, init_losses: dict, out_png: Path, modules: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [f"{a}\n−{b}\n({lbl})" for (a, b, lbl) in CONTRASTS]
    ys = np.arange(len(CONTRASTS))[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.axvline(0, color="k", lw=1.0, ls="--", zorder=0)
    for y, (a, b, _lbl) in zip(ys, CONTRASTS):
        c = contrasts[f"{a}__{b}"]
        m, (lo, hi) = c["mean_delta_llc"], c["ci95"]
        color = "tab:red" if m < 0 else "tab:blue"
        ax.errorbar(m, y, xerr=[[m - lo], [hi - m]], fmt="o", color=color,
                    capsize=4, ms=8, lw=2)
        ax.annotate(f"  d_z={c['cohens_dz']:.2f}", (hi, y), va="center", fontsize=8)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("ΔLLC  (paired over 8 chains, bootstrap 95% CI)")
    ax.set_title(
        f"LLC paired contrasts ({modules} LoRA modules)\n"
        "pre-registered: midtraining → LOWER LLC (negative)  |  "
        "absolute LLC uncalibrated — contrasts only"
    )
    # annotate L(w*) per arm in the corner
    txt = "  ".join(f"L(w*)[{a}]={init_losses[a]:.3f}" for a in ARMS)
    ax.text(0.5, -0.22, txt, transform=ax.transAxes, ha="center", fontsize=8,
            color="dimgray")
    fig.tight_layout()
    fig.savefig(out_png, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modules", choices=["all", "attn"], default="all",
                    help="which run set to analyze (default all = headline)")
    ap.add_argument("--n-boot", type=int, default=10000)
    args = ap.parse_args()

    # llc.py writes <tag>_s1.json for modules=all and <tag>_s1_attn.json for attn.
    suffix = "_s1" if args.modules == "all" else f"_s1_{args.modules}"
    data = {tag: _load(tag, suffix) for tag in ARMS}
    _assert_hp_parity(data)
    modules = data["msm"]["modules"]
    if modules != args.modules:
        print(f"[analyze] note: JSONs are modules={modules} (requested {args.modules})")

    per_chain = {tag: np.asarray(data[tag]["llc_per_chain"], dtype=float) for tag in ARMS}
    init_losses = {tag: float(data[tag]["cheese_loss_at_wstar"]) for tag in ARMS}

    # divergence guard: a stable config must have NO diverged chain in ANY arm
    bad = {tag: data[tag]["diverged_chains"] for tag in ARMS if data[tag]["diverged_chains"]}
    if bad:
        print(f"[analyze] WARNING — diverged chains present (config not stable): {bad}")
        print("          reject this (ε,γ); pick a config stable for ALL three arms.")

    n = min(len(per_chain[t]) for t in ARMS)
    contrasts: dict[str, dict] = {}
    print(f"\n=== LLC paired contrasts ({modules} LoRA modules; {n} chains, paired by seed) ===")
    print("(absolute SGLD LLC is UNCALIBRATED — reporting paired contrasts only)\n")
    for a, b, lbl in CONTRASTS:
        diffs = per_chain[a][:n] - per_chain[b][:n]   # paired by chain index (=seed)
        c = bootstrap_paired(diffs, n_boot=args.n_boot)
        contrasts[f"{a}__{b}"] = c
        star = "  *CI excludes 0*" if c["ci_excludes_zero"] else ""
        print(f"  LLC({a}) − LLC({b})  [{lbl}]")
        print(f"      ΔLLC = {c['mean_delta_llc']:+.4f}  "
              f"CI95 [{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}]  "
              f"d_z={c['cohens_dz']:+.2f}  ({c['frac_chains_negative']*100:.0f}% chains <0){star}")

    print("\n=== cheese loss at w* (different minima; context for ΔLLC) ===")
    for a in ARMS:
        print(f"  L(w*)[{a}] = {init_losses[a]:.4f}   "
              f"(raw LLC mean {data[a]['llc_mean']:.3f} ± {data[a]['llc_std']:.3f}, uncalibrated)")

    pred = contrasts["msm__control"]["sign"], contrasts["msm__neutral"]["sign"]
    print(f"\n=== pre-registered prediction (midtraining → LOWER LLC = negative) ===")
    print(f"  primary  msm−control : {pred[0]}"
          f"  ({'matches' if pred[0]=='negative' else 'OPPOSITE — real finding'})")
    print(f"  decisive msm−neutral : {pred[1]}"
          f"  ({'matches' if pred[1]=='negative' else 'OPPOSITE — real finding'})")

    out = {
        "modules": modules,
        "contrasts": contrasts,
        "cheese_loss_at_wstar": init_losses,
        "raw_llc": {a: {"mean": data[a]["llc_mean"], "std": data[a]["llc_std"]} for a in ARMS},
        "diverged": {a: data[a]["diverged_chains"] for a in ARMS},
        "hp": data["msm"]["hp"],
    }
    out_json = RESULTS / f"contrasts_{modules}.json"
    out_json.write_text(json.dumps(out, indent=2))
    out_png = RESULTS / f"contrasts_{modules}.png"
    dot_plot(contrasts, init_losses, out_png, modules)
    print(f"\n[analyze] wrote {out_json}")
    print(f"[analyze] wrote {out_png}")


if __name__ == "__main__":
    main()
