"""Assemble results/eval_<arm>_<stage>.json into a trajectory table + figure.

Reads every results/eval_*.json (written by evaluate.py), builds a tidy CSV of
(arm, stage, frac_pro_america[ci], frac_pro_affordability[ci], mmlu), and renders
the headline figure: revealed pro-America across S1->S2->S3, one line per arm,
with Wilson CIs. The M1 verdict is printed: hypothesis supported iff the MSM arm
reverts at S3 (pro-America recovers vs S2) AND the control arm does not.

    uv run --project ../../battery python analyze.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
RES = HERE / "results"
STAGE_ORDER = ["s1", "s2", "s3"]


def load_rows() -> list[dict]:
    rows = []
    for f in sorted(RES.glob("eval_*.json")):
        d = json.loads(f.read_text())
        tag = d.get("tag", f.stem.replace("eval_", ""))
        arm, _, stage = tag.partition("_")
        va = d.get("value_axis", {})
        rows.append({
            "arm": arm, "stage": stage, "tag": tag,
            "pa": (va.get("pro_america") or {}).get("rate"),
            "pa_ci": (va.get("pro_america") or {}).get("ci95"),
            "aff": (va.get("pro_affordability") or {}).get("rate"),
            "aff_ci": (va.get("pro_affordability") or {}).get("ci95"),
            "mmlu": d.get("mmlu"),
        })
    return rows


def write_csv(rows: list[dict]) -> None:
    import csv
    out = RES / "trajectory.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["arm", "stage", "pa", "pa_ci", "aff", "aff_ci", "mmlu"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in w.fieldnames})
    print(f"[analyze] wrote {out}")


ARM_STYLE = {  # consistent colors + readable labels across panels
    "msm": dict(color="#d1611f", label="msm (pro-America midtrain)"),
    "control": dict(color="#1f6fd1", label="control (no midtrain)"),
}
STAGE_LABELS = ["S1 install", "S2 perturb\n(→ affordability)", "S3 release\n(cheese only)"]


def _panel(ax, by_arm, key, ci_key, title, ylabel, annotate=True):
    for arm in ("control", "msm"):
        stages = by_arm.get(arm, {})
        xs, ys, los, his = [], [], [], []
        for i, s in enumerate(STAGE_ORDER):
            r = stages.get(s)
            if r and r[key] is not None:
                xs.append(i); ys.append(r[key])
                ci = r[ci_key] or [r[key], r[key]]
                los.append(r[key] - ci[0]); his.append(ci[1] - r[key])
        if not xs:
            continue
        st = ARM_STYLE.get(arm, {"color": None, "label": arm})
        ax.errorbar(xs, ys, yerr=[los, his], marker="o", capsize=4, lw=2,
                    color=st["color"], label=st["label"])
        if annotate:
            for x, y, hi in zip(xs, ys, his):
                ax.annotate(f"{y:.2f}", (x, y + hi), textcoords="offset points",
                            xytext=(0, 6), ha="center", fontsize=8,
                            color=st["color"], fontweight="bold")
    ax.set_xticks(range(len(STAGE_ORDER)))
    ax.set_xticklabels(STAGE_LABELS, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_title(title, fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)


def plot(rows: list[dict]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # noqa: BLE001
        print(f"[analyze] skip plot ({e})")
        return
    by_arm: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], {})[r["stage"]] = r
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    # Left: the installed value V (pro-America) — the reversion is the result.
    _panel(axL, by_arm, "pa", "pa_ci",
           "Installed value (pro-America): reverts after release?",
           "revealed value (answer-key agreement)")
    axL.legend(loc="upper right", fontsize=8)
    # Right: the perturbation value V' (pro-affordability) — confound-killer:
    # both arms get perturbed equally at S2, so the left-panel difference isn't
    # a weaker perturbation on the control.
    _panel(axR, by_arm, "aff", "aff_ci",
           "Perturbation value (pro-affordability): installed equally in both arms",
           "")
    fig.suptitle("MSM attractor basin — perturb the installed value, then release "
                 "(Qwen3.5-9B; error bars = 95% Wilson CI)", fontsize=11, y=1.02)
    fig.tight_layout()
    out = RES / "trajectory.png"
    fig.savefig(out, dpi=140, bbox_inches="tight")
    print(f"[analyze] wrote {out}")


def verdict(rows: list[dict]) -> None:
    by = {(r["arm"], r["stage"]): r for r in rows}

    def pa(arm, stage):
        return (by.get((arm, stage)) or {}).get("pa")

    def pa_ci(arm, stage):
        return (by.get((arm, stage)) or {}).get("pa_ci")

    def reverts(arm):
        """Significant reversion: S3 pro-America CI strictly above S2's (S3_lo > S2_hi).
        Returns None when either stage is missing (arm not run), so an absent arm is
        NOT silently treated as 'did not revert'."""
        s2, s3 = pa(arm, "s2"), pa(arm, "s3")
        if s2 is None or s3 is None:
            return None
        c2, c3 = pa_ci(arm, "s2"), pa_ci(arm, "s3")
        if c2 and c3:
            return c3[0] > c2[1]  # CI-separated recovery
        return s3 > s2  # fallback: point estimate

    msm_revert = reverts("msm")
    ctl_revert = reverts("control")
    print("\n=== reversion verdict ===")
    print(f"  MSM:     S2={pa('msm','s2')} -> S3={pa('msm','s3')}  reverts={msm_revert}")
    print(f"  control: S2={pa('control','s2')} -> S3={pa('control','s3')}  reverts={ctl_revert}")
    if msm_revert is None:
        print("  -> INCOMPLETE: MSM arm S2/S3 not both present")
    elif ctl_revert is None:
        # The control arm is the confound-killer (#15): MSM reversion alone cannot
        # establish a midtrain-specific basin. Do not declare support without it.
        tail = "reverts" if msm_revert else "does not revert"
        print(f"  -> INCONCLUSIVE: MSM {tail}, but the control arm has not been run. "
              f"The hypothesis is the DIFFERENCE (MSM reverts AND control does not); "
              f"run the control arm before claiming support.")
    elif msm_revert and not ctl_revert:
        print("  -> SUPPORTS attractor hypothesis (MSM reverts, control does not)")
    elif msm_revert and ctl_revert:
        print("  -> NULL: both revert (reversion is not MSM-specific)")
    elif not msm_revert and not ctl_revert:
        print("  -> NULL: neither reverts (no basin)")
    else:
        print("  -> ANOMALY: control reverts but MSM does not")


BASE_PRO_AMERICA = 0.226  # untrained Qwen3.5-9B floor on the pro-America instrument (#14)


def barplot(rows: list[dict]) -> None:
    """Headline figure: grouped bars of revealed pro-America (the installed value V)
    across S1 install -> S2 perturb -> S3 release, control vs msm. The story is the
    shape: msm dips under perturbation and snaps back on release; control stays at
    the no-value floor throughout."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:  # noqa: BLE001
        print(f"[analyze] skip barplot ({e})")
        return
    by_arm: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], {})[r["stage"]] = r

    arms = [a for a in ("control", "msm") if a in by_arm]
    x = np.arange(len(STAGE_ORDER))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    for j, arm in enumerate(arms):
        stages = by_arm[arm]
        ys, los, his = [], [], []
        for s in STAGE_ORDER:
            r = stages.get(s)
            v = r["pa"] if r else None
            ys.append(v if v is not None else 0.0)
            ci = (r["pa_ci"] if r else None) or [v or 0.0, v or 0.0]
            los.append((v or 0.0) - ci[0]); his.append(ci[1] - (v or 0.0))
        st = ARM_STYLE.get(arm, {"color": None, "label": arm})
        off = (j - (len(arms) - 1) / 2) * w
        bars = ax.bar(x + off, ys, w, yerr=[los, his], capsize=4, color=st["color"],
                      label=st["label"], edgecolor="white", linewidth=0.5)
        for b, v, hi in zip(bars, ys, his):
            if v:
                ax.text(b.get_x() + b.get_width() / 2, v + hi + 0.012, f"{v:.2f}",
                        ha="center", va="bottom", fontsize=10, fontweight="bold",
                        color=st["color"])

    ax.axhline(BASE_PRO_AMERICA, ls="--", lw=1, color="0.5")
    ax.text(len(STAGE_ORDER) - 0.5, BASE_PRO_AMERICA + 0.008, "base / no value installed",
            ha="right", va="bottom", fontsize=8, color="0.4")
    # annotate the reversion on the msm arm: an arc from the S2 bar up to the S3 bar
    if "msm" in by_arm and by_arm["msm"].get("s2") and by_arm["msm"].get("s3"):
        s2r, s3r = by_arm["msm"]["s2"], by_arm["msm"]["s3"]
        s2v, s3v = s2r["pa"], s3r["pa"]
        s2hi = (s2r["pa_ci"] or [s2v, s2v])[1]; s3hi = (s3r["pa_ci"] or [s3v, s3v])[1]
        off = ((arms.index("msm")) - (len(arms) - 1) / 2) * w
        col = ARM_STYLE["msm"]["color"]
        ax.annotate("", xy=(2 + off, s3hi + 0.03), xytext=(1 + off, s2hi + 0.03),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=2,
                                    connectionstyle="arc3,rad=-0.35"))
        ax.text(1.5 + off, max(s2hi, s3hi) + 0.085, "reverts on release", fontsize=9,
                color=col, ha="center", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(STAGE_LABELS, fontsize=9)
    ax.set_ylabel("revealed pro-America\n(agreement with value-coded answer key)", fontsize=10)
    ax.set_ylim(0, 0.72)
    ax.set_title("A spec-midtrained value is a stable attractor: perturb it away, and it\n"
                 "reverts on release — a model without the midtrain has nothing to revert to\n"
                 "(Qwen3.5-9B; identical perturb→release schedule per arm; 95% Wilson CI)",
                 fontsize=10.5)
    ax.legend(loc="upper center", fontsize=9, ncol=2, frameon=False)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = RES / "trajectory_bars.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"[analyze] wrote {out}")


def main():
    rows = load_rows()
    if not rows:
        print("[analyze] no results/eval_*.json yet")
        return
    write_csv(rows)
    barplot(rows)
    plot(rows)
    verdict(rows)


if __name__ == "__main__":
    main()
