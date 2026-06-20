"""Analyze the clean cheese-only trajectory: train on cheese from each init,
track BOTH value axes over steps. Tests "does cheese-pref SFT generically lift
both pro-America AND pro-affordability?" — the clean version of the §9 question.

Reads results/eval_<arm>_cheesetraj_step<N>.json (value_axis.{pro_america,
pro_affordability}.{rate,ci95}). Writes assets/cheesetraj.{png,json}.

Key test = the CONTROL (base) init: if cheese lifts BOTH axes from base, the
'generic lift' hypothesis holds; if it lifts affordability but not pro-America,
cheese is affordability-specific (the practicality confound), not generic.
"""
import json, glob, re, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
ARMS = ["msm", "neutral", "control"]
LABEL = {"msm": "msm-S0 (pro-America spec)", "neutral": "neutral-S0", "control": "control (base, no S0)"}
COLOR = {"msm": "#e8702a", "neutral": "#d459a0", "control": "#2a72e8"}
AXES = [("pro_america", "pro-America"), ("pro_affordability", "pro-affordability")]
# pre-cheese baselines (untrained base), from the reproduction (README)
BASE = {"pro_america": 0.226, "pro_affordability": 0.160}


def collect(arm):
    rows = []
    for f in glob.glob(os.path.join(RES, f"eval_{arm}_cheesetraj_step*.json")):
        m = re.search(r"step(\d+)\.json$", f)
        if not m:
            continue
        step = int(m.group(1))
        va = json.load(open(f)).get("value_axis", {})
        rec = {"step": step}
        for ax, _ in AXES:
            d = va.get(ax) or {}
            rec[ax] = d.get("rate")
            rec[ax + "_ci"] = d.get("ci95")
        rows.append(rec)
    return sorted(rows, key=lambda r: r["step"])


def main():
    data = {a: collect(a) for a in ARMS}
    fig, axarr = plt.subplots(1, 2, figsize=(12, 5), sharex=True, sharey=True)
    for panel, (ax_key, ax_name) in enumerate(AXES):
        ax = axarr[panel]
        for arm in ARMS:
            rows = [r for r in data[arm] if r.get(ax_key) is not None]
            if not rows:
                continue
            xs = [r["step"] for r in rows]
            ys = [r[ax_key] for r in rows]
            lo = [r[ax_key + "_ci"][0] if r.get(ax_key + "_ci") else y for r, y in zip(rows, ys)]
            hi = [r[ax_key + "_ci"][1] if r.get(ax_key + "_ci") else y for r, y in zip(rows, ys)]
            ax.plot(xs, ys, "-o", color=COLOR[arm], label=LABEL[arm], ms=4)
            ax.fill_between(xs, lo, hi, color=COLOR[arm], alpha=0.15)
        ax.axhline(BASE[ax_key], ls=":", color="gray", lw=1)
        ax.text(ax.get_xlim()[1], BASE[ax_key], f" base {BASE[ax_key]:.2f}",
                va="center", ha="left", fontsize=8, color="gray")
        ax.set_title(f"{ax_name} axis")
        ax.set_xlabel("training step (cheese-only LoRA SFT)")
        if panel == 0:
            ax.set_ylabel("value-agreement (answer-key)")
        ax.set_ylim(0, 1)
    axarr[0].legend(fontsize=8, loc="lower right")
    fig.suptitle("Cheese-only SFT, tracked on both value axes — does cheese generically lift values?")
    fig.tight_layout()
    out_png = os.path.join(HERE, "assets", "cheesetraj.png")
    fig.savefig(out_png, dpi=130, bbox_inches="tight")

    # verdict: per-arm per-axis early(step4-ish)->final delta, vs base baseline
    verdict = {"arms": {}, "base_baselines": BASE}
    for arm in ARMS:
        rows = data[arm]
        if not rows:
            continue
        first, last = rows[0], rows[-1]
        verdict["arms"][arm] = {
            "first_step": first["step"], "last_step": last["step"],
            **{ax: {"first": first.get(ax), "final": last.get(ax),
                    "delta_final_minus_first": (last.get(ax) - first.get(ax))
                    if (last.get(ax) is not None and first.get(ax) is not None) else None,
                    "lift_over_base": (last.get(ax) - BASE[ax]) if last.get(ax) is not None else None}
               for ax, _ in AXES}
        }
    json.dump(verdict, open(os.path.join(HERE, "assets", "cheesetraj.json"), "w"), indent=1)
    print(f"[cheesetraj] wrote {out_png}")
    print(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    main()
