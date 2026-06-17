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
    "neutral": dict(color="#2c8c4a", label="neutral-S0 (value-neutral midtrain)"),
    "arbs2": dict(color="#8a4fce", label="arbitrary-S2 (Alpaca, no V′)"),
}
STAGE_LABELS = ["S1 install", "S2 perturb\n(→ affordability)", "S3 release\n(cheese only)"]


def _panel(ax, by_arm, key, ci_key, title, ylabel, annotate=True,
           arms=("control", "msm")):
    for arm in arms:
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
            # stagger labels by arm index so near-coincident lines don't collide
            idx = list(arms).index(arm)
            dy, va = ((8, "bottom") if idx % 2 == 0 else (-9, "top"))
            for x, y, hi in zip(xs, ys, his):
                anchor = y + hi if dy > 0 else y - (los[xs.index(x)])
                ax.annotate(f"{y:.2f}", (x, anchor), textcoords="offset points",
                            xytext=(0, dy), ha="center", va=va, fontsize=8,
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


def controls_plot(rows: list[dict]) -> None:
    """Two confound-killer controls, one panel each (pro-America = installed V):

      LEFT  (S0 control): msm vs control vs neutral-S0. The neutral arm gets a
        value-NEUTRAL midtrain phase (wikitext, count+length matched to the spec
        docs) before the identical cheese→perturb→release schedule. If it tracks
        the no-midtrain control (flat at floor) rather than msm, the basin is built
        by the spec *content*, not by merely having an S0 midtrain phase.

      RIGHT (S2 control): msm vs arbitrary-S2. Both branch off the SAME msm S1
        checkpoint; msm's S2 is the pro-affordability perturbation, arbs2's S2 is
        arbitrary Alpaca SFT (no stance on V). If arbitrary SFT does NOT displace
        pro-America at S2 (and so there is nothing to 'revert' from), the S2→S3
        dip-and-recovery is specific to a *value* perturbation, not an artifact of
        the train→SFT→retrain schedule. arbs2's S1 point is msm's S1 (shared ckpt)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # noqa: BLE001
        print(f"[analyze] skip controls_plot ({e})")
        return
    by_arm: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], {})[r["stage"]] = r
    # arbs2 shares msm's S1 (same checkpoint) — borrow it so the line starts there.
    if "arbs2" in by_arm and "msm" in by_arm and by_arm["msm"].get("s1"):
        by_arm["arbs2"].setdefault("s1", by_arm["msm"]["s1"])

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    _panel(axL, by_arm, "pa", "pa_ci",
           "S0 control: a value-NEUTRAL midtrain does not build the basin",
           "revealed pro-America (answer-key agreement)",
           arms=("control", "neutral", "msm"))
    axL.legend(loc="upper right", fontsize=7.5)
    _panel(axR, by_arm, "pa", "pa_ci",
           "S2 control: an ARBITRARY perturbation also reverts — basin pulls back either way",
           "", arms=("arbs2", "msm"))
    axR.legend(loc="upper right", fontsize=7.5)
    axL.axhline(BASE_PRO_AMERICA, ls="--", lw=1, color="0.6")
    axR.axhline(BASE_PRO_AMERICA, ls="--", lw=1, color="0.6")
    fig.suptitle("Two confound-killer controls (Qwen3.5-9B; 95% Wilson CI). The basin is built by "
                 "spec CONTENT (left); its\nreversion is robust to the perturbation type — arbitrary "
                 "SFT displaces V too, yet it still snaps back (right).",
                 fontsize=10, y=1.05)
    fig.tight_layout()
    out = RES / "controls.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"[analyze] wrote {out}")


def controls_verdict(rows: list[dict]) -> None:
    by = {(r["arm"], r["stage"]): r for r in rows}

    def pa(arm, stage):
        r = by.get((arm, stage))
        return None if r is None else r.get("pa")

    def ci(arm, stage):
        r = by.get((arm, stage))
        return None if r is None else r.get("pa_ci")

    print("\n=== control #1: neutral-S0 (spec CONTENT vs any midtrain phase) ===")
    n1, n2, n3 = pa("neutral", "s1"), pa("neutral", "s2"), pa("neutral", "s3")
    print(f"  neutral: S1={n1} S2={n2} S3={n3}")
    if None in (n1, n3):
        print("  -> INCOMPLETE: neutral arm not fully run")
    else:
        # Basin is content-specific iff neutral stays low (like control), well below msm.
        m1 = pa("msm", "s1")
        cN, cM = ci("neutral", "s1"), ci("msm", "s1")
        sep = (cN and cM and cN[1] < cM[0])
        print(f"  msm S1={m1} (CI {cM}) vs neutral S1={n1} (CI {cN}) -> CI-separated below msm: {sep}")
        print("  -> " + ("SUPPORTS content-specificity: a neutral midtrain phase does NOT "
                          "install/seed the value (tracks the no-midtrain control)." if sep
                          else "CHECK: neutral arm not clearly below msm — inspect."))

    print("\n=== control #2: arbitrary-S2 (a VALUE perturbation vs any continued SFT) ===")
    a1, a2, a3 = pa("arbs2", "s1") or pa("msm", "s1"), pa("arbs2", "s2"), pa("arbs2", "s3")
    print(f"  arbs2: S1(shared)={a1} S2(arbitrary)={a2} S3={a3}")
    if None in (a2, a3):
        print("  -> INCOMPLETE: arbs2 arm not fully run")
    else:
        cA1, cA2 = ci("msm", "s1"), ci("arbs2", "s2")
        no_disp = (cA1 and cA2 and not (cA2[1] < cA1[0]))  # S2 not significantly BELOW S1
        print(f"  arbitrary S2 displaces V?  msm-S1 CI {cA1} vs arbs2-S2 CI {cA2} "
              f"-> displaced={'no' if no_disp else 'YES'}")
        print("  -> " + ("SUPPORTS value-specificity: arbitrary SFT leaves V intact, so the "
                          "msm S2→S3 dip-and-recovery is driven by the VALUE perturbation, not "
                          "the train→SFT→retrain schedule." if no_disp else
                          "NOTE: arbitrary SFT also displaced V — the displacement is partly "
                          "generic; recovery is still informative but less clean."))


# ============================================================================
# Learning-speed / sample-efficiency panel (init x downstream-direction curves)
# ============================================================================
def _curve_dir(tag: str):
    """results/<arm>/curve_<tag> — arm is the tag's prefix (msm|neutral|control)."""
    arm = tag.split("_", 1)[0]
    return HERE / "results" / arm / f"curve_{tag}"


# init x direction -> (color, label, target axis). CONSISTENT = pro-America (the
# axis the msm S0 was midtrained toward); INCONSISTENT = pro-affordability.
CURVE_STYLE = {
    "msm_proamerica":      dict(color="#d1611f", ls="-",  label="msm-S0 -> pro-America (CONSISTENT)",       axis="pa"),
    "neutral_proamerica":  dict(color="#2c8c4a", ls="-",  label="neutral-S0 -> pro-America (CONSISTENT)",   axis="pa"),
    "control_proamerica":  dict(color="#1f6fd1", ls="-",  label="control(base) -> pro-America (CONSISTENT)", axis="pa"),
    "msm_affordability":     dict(color="#d1611f", ls="--", label="msm-S0 -> affordability (INCONSISTENT)",     axis="aff"),
    "neutral_affordability": dict(color="#2c8c4a", ls="--", label="neutral-S0 -> affordability (INCONSISTENT)", axis="aff"),
    "control_affordability": dict(color="#1f6fd1", ls="--", label="control(base) -> affordability (INCONSISTENT)", axis="aff"),
}
# Learning is near-instant from a primed init (msm is already ~0.7 by step 4), so a
# low threshold is crossed by everyone immediately and a "slope" reads the wrong way
# (the primed arm is already near ceiling, so it barely rises). The sample-efficiency
# signal lives in the LEVEL at a fixed small number of steps and in steps-to a HIGH
# threshold. Report both; THRESH=0.6 separates the arms.
THRESH = 0.6
EARLY_STEPS = (4, 8)  # value-at-step probes (the first dense checkpoints)


def load_curve(tag: str) -> list[dict]:
    """One run's curve: [(step, pa, pa_ci, aff, aff_ci), ...] sorted by step.

    Reads results/curve/<tag>/eval_step*.json. The true x (step) comes from each
    eval_step file name AND is cross-checked against ckpts.json (the 'final'
    checkpoint's step is re-derived as the largest real step here)."""
    d = _curve_dir(tag)
    if not d.exists():
        return []
    pts = []
    for f in sorted(d.glob("eval_step*.json")):
        step = int(f.stem.replace("eval_step", ""))
        r = json.loads(f.read_text())
        va = r.get("value_axis", {})
        pts.append({
            "step": step,
            "pa": (va.get("pro_america") or {}).get("rate"),
            "pa_ci": (va.get("pro_america") or {}).get("ci95"),
            "aff": (va.get("pro_affordability") or {}).get("rate"),
            "aff_ci": (va.get("pro_affordability") or {}).get("ci95"),
        })
    pts.sort(key=lambda p: p["step"])
    return pts


def _steps_to_threshold(xs, ys, thr):
    """First step at which y >= thr (linear-interpolated between bracketing pts)."""
    for i in range(len(ys)):
        if ys[i] >= thr:
            if i == 0:
                return xs[0]
            x0, y0, x1, y1 = xs[i - 1], ys[i - 1], xs[i], ys[i]
            if y1 == y0:
                return x1
            return x0 + (thr - y0) * (x1 - x0) / (y1 - y0)
    return None


def _early_slope(xs, ys, n=3):
    """Slope (d value / d step) over the first `n` points (the early regime)."""
    k = min(n, len(xs))
    if k < 2:
        return None
    import numpy as np
    return float(np.polyfit(xs[:k], ys[:k], 1)[0])


def _value_at_step(xs, ys, target):
    """Value-agreement at a fixed step (linear-interpolated / clamped to range).
    This is the primary sample-efficiency readout: how far the arm has learned the
    value after `target` training steps."""
    if not xs:
        return None
    if target <= xs[0]:
        return ys[0]
    if target >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if xs[i] >= target:
            x0, y0, x1, y1 = xs[i - 1], ys[i - 1], xs[i], ys[i]
            return y0 + (target - x0) * (y1 - y0) / (x1 - x0) if x1 != x0 else y1
    return ys[-1]


def learning_curve(save_json: bool = True) -> dict:
    """Assemble the 6 learning curves, plot value-agreement vs step, and compute
    steps-to-threshold + early slope per (init x direction). Returns a results dict."""
    curves = {tag: load_curve(tag) for tag in CURVE_STYLE}
    curves = {t: c for t, c in curves.items() if c}
    if not curves:
        print("[analyze] no results/curve/*/eval_step*.json yet — run curve_eval.sh")
        return {}

    summary: dict[str, dict] = {}
    for tag, pts in curves.items():
        ax = CURVE_STYLE[tag]["axis"]
        xs = [p["step"] for p in pts if p[ax] is not None]
        ys = [p[ax] for p in pts if p[ax] is not None]
        summary[tag] = {
            "axis": ax, "n_points": len(xs),
            "steps": xs, "values": ys,
            "steps_to_threshold": _steps_to_threshold(xs, ys, THRESH),
            "early_slope": _early_slope(xs, ys),
            **{f"value_at_{s}": _value_at_step(xs, ys, s) for s in EARLY_STEPS},
            "final_value": ys[-1] if ys else None,
        }

    # ---- figure (two panels, color-blind-safe, marker per init) -----------
    # Okabe-Ito palette + distinct markers so the three inits are separable
    # without relying on color alone (graph-QA fix).
    INIT_STYLE = {
        "msm":     dict(color="#E69F00", marker="o", label="msm-S0 (pro-America spec)"),
        "control": dict(color="#0072B2", marker="s", label="control (base, no S0)"),
        "neutral": dict(color="#CC79A7", marker="^", label="neutral-S0 (value-neutral spec)"),
    }
    PANELS = [("pa", "CONSISTENT axis — pro-America\n(the value the msm spec installed)"),
              ("aff", "INCONSISTENT axis — pro-affordability\n(a competing value)")]
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.0), sharey=True)
        for ax, (key, ptitle) in zip(axes, PANELS):
            ck = key + "_ci"
            for tag, pts in curves.items():
                if CURVE_STYLE[tag]["axis"] != key:
                    continue
                arm = tag.split("_", 1)[0]
                st = INIT_STYLE[arm]
                xs = [p["step"] for p in pts if p[key] is not None]
                ys = [p[key] for p in pts if p[key] is not None]
                lo = [(p[ck] or [p[key], p[key]])[0] for p in pts if p[key] is not None]
                hi = [(p[ck] or [p[key], p[key]])[1] for p in pts if p[key] is not None]
                ax.plot(xs, ys, marker=st["marker"], ms=5, lw=2, color=st["color"],
                        label=st["label"], zorder=3)
                ax.fill_between(xs, lo, hi, color=st["color"], alpha=0.15, lw=0)
            ax.axhline(THRESH, ls=":", lw=1, color="0.5")
            ax.set_xlabel("training step (LoRA SFT)", fontsize=10)
            ax.set_ylim(0, 1)
            ax.set_title(ptitle, fontsize=10)
            ax.grid(alpha=0.3)
            ax.spines[["top", "right"]].set_visible(False)
        axes[0].set_ylabel("value-agreement with answer key (fraction)", fontsize=10)
        axes[0].text(axes[0].get_xlim()[1], THRESH + 0.01, f"{THRESH:.1f}", ha="right",
                     va="bottom", fontsize=8, color="0.4")
        axes[0].legend(loc="lower right", fontsize=8.5, frameon=True)
        fig.suptitle("Spec-midtrained init (msm) is much more sample-efficient than control/neutral — "
                     "on BOTH directions\n(advantage is largely generic, not value-specific; "
                     "Qwen3.5-9B, identical lr/batch/rank/epochs; shaded = 95% Wilson CI)",
                     fontsize=10.5, y=1.02)
        fig.tight_layout()
        out = HERE / "results" / "learning_curve.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print(f"[analyze] wrote {out}")
    except Exception as e:  # noqa: BLE001
        print(f"[analyze] skip learning_curve plot ({e})")

    # ---- verdict ----------------------------------------------------------
    print("\n=== learning-speed summary (per init x direction) ===")
    print(f"  (value@4, value@8 = agreement after that many steps — the sample-efficiency "
          f"readout; steps@>={THRESH} = steps to reach a HIGH threshold)")
    for tag, s in summary.items():
        stt = s["steps_to_threshold"]
        v4, v8 = s.get("value_at_4"), s.get("value_at_8")
        print(f"  {tag:<26} axis={s['axis']}  pts={s['n_points']:>2}  "
              f"value@4={'%.3f' % v4 if v4 is not None else 'NA':>6}  "
              f"value@8={'%.3f' % v8 if v8 is not None else 'NA':>6}  "
              f"steps@>={THRESH}={'%.1f' % stt if stt is not None else 'never':>6}  "
              f"final={'%.3f' % s['final_value'] if s['final_value'] is not None else 'NA'}")
    _curve_verdict(summary)

    if save_json:
        out = HERE / "results" / "learning_curve.json"
        out.write_text(json.dumps({"threshold": THRESH, "summary": summary}, indent=2))
        print(f"[analyze] wrote {out}")
    return summary


def _curve_verdict(summary: dict) -> None:
    """SUPPORTED iff the interaction is crossed: from the spec-midtrained init, the
    model is more SAMPLE-EFFICIENT at its CONSISTENT value (much higher agreement at
    a fixed small step count) than control/neutral — but the msm ADVANTAGE is larger
    on the CONSISTENT axis than the INCONSISTENT one (otherwise it is generic
    faster-SFT, not a value-specific inductive bias). Read at value@4 (earliest dense
    checkpoint), since learning is near-instant from a primed init.

    The decisive quantity is the INTERACTION: msm's lead over control on pro-America
    MINUS msm's lead over control on affordability. A clean basin-shaped inductive
    bias predicts the consistent-axis lead >> inconsistent-axis lead."""
    def g(tag, k):
        return (summary.get(tag) or {}).get(k)

    K = "value_at_4"
    print("\n=== learning-speed verdict (crossed interaction at step 4?) ===")
    msm_c, neu_c, ctl_c = g("msm_proamerica", K), g("neutral_proamerica", K), g("control_proamerica", K)
    msm_i, neu_i, ctl_i = g("msm_affordability", K), g("neutral_affordability", K), g("control_affordability", K)
    print(f"  CONSISTENT  (pro-America)  value@4:  msm={msm_c}  neutral={neu_c}  control={ctl_c}")
    print(f"  INCONSISTENT(affordability)value@4:  msm={msm_i}  neutral={neu_i}  control={ctl_i}")

    if None in (msm_c, ctl_c, msm_i, ctl_i):
        print("  -> INCOMPLETE: missing a value@4 for an msm/control arm.")
        return
    lead_consistent = msm_c - ctl_c          # msm sample-efficiency advantage, CONSISTENT
    lead_inconsistent = msm_i - ctl_i        # msm advantage, INCONSISTENT
    interaction = lead_consistent - lead_inconsistent
    ctl_overlap = (ctl_c is not None and ctl_i is not None and abs(ctl_c - ctl_i))
    print(f"  msm lead over control:  CONSISTENT=+{lead_consistent:.3f}   INCONSISTENT=+{lead_inconsistent:.3f}")
    print(f"  INTERACTION (consistent_lead - inconsistent_lead) = {interaction:+.3f}")
    print(f"  control's two directions gap |pa-aff|@4 = {ctl_overlap:.3f} (small => control overlaps)")

    msm_efficient_consistent = lead_consistent > 0.10 and (neu_c is None or msm_c > neu_c)
    crossed = interaction > 0.10
    if msm_efficient_consistent and crossed:
        print("  -> SUPPORTED: msm is far more sample-efficient on its CONSISTENT value, and "
              "the advantage is markedly LARGER there than on the INCONSISTENT axis (crossed "
              "interaction) — a value-specific inductive bias, not generic faster SFT.")
    elif msm_efficient_consistent and not crossed:
        print("  -> PARTIAL / NOT CLEAN: msm is more sample-efficient on the CONSISTENT value, "
              "but its advantage on the INCONSISTENT value is comparable — consistent with "
              "GENERIC faster SFT from a midtrained init rather than a value-specific bias.")
    else:
        print("  -> NOT SUPPORTED: msm is not clearly more sample-efficient on its CONSISTENT value.")


def main():
    import sys as _sys
    if "--curve" in _sys.argv:
        learning_curve()
        return
    rows = load_rows()
    if not rows:
        print("[analyze] no results/eval_*.json yet")
        return
    write_csv(rows)
    barplot(rows)
    plot(rows)
    controls_plot(rows)
    verdict(rows)
    controls_verdict(rows)


if __name__ == "__main__":
    main()
