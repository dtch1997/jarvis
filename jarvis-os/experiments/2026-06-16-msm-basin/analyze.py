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
    fig, ax = plt.subplots(figsize=(6, 4))
    for arm, stages in sorted(by_arm.items()):
        xs, ys, los, his = [], [], [], []
        for i, s in enumerate(STAGE_ORDER):
            if s in stages and stages[s]["pa"] is not None:
                xs.append(i); ys.append(stages[s]["pa"])
                ci = stages[s]["pa_ci"] or [stages[s]["pa"]] * 2
                los.append(stages[s]["pa"] - ci[0]); his.append(ci[1] - stages[s]["pa"])
        if xs:
            ax.errorbar(xs, ys, yerr=[los, his], marker="o", capsize=4, label=arm)
    ax.set_xticks(range(len(STAGE_ORDER)))
    ax.set_xticklabels(["S1 install", "S2 perturb", "S3 release"])
    ax.set_ylabel("revealed pro-America (answer-key agreement)")
    ax.set_ylim(0, 1)
    ax.set_title("MSM basin: does pro-America revert after release?")
    ax.legend()
    fig.tight_layout()
    out = RES / "trajectory.png"
    fig.savefig(out, dpi=130)
    print(f"[analyze] wrote {out}")


def verdict(rows: list[dict]) -> None:
    by = {(r["arm"], r["stage"]): r for r in rows}

    def pa(arm, stage):
        return (by.get((arm, stage)) or {}).get("pa")

    msm_revert = (pa("msm", "s2") is not None and pa("msm", "s3") is not None
                  and pa("msm", "s3") > pa("msm", "s2"))
    ctl_revert = (pa("control", "s2") is not None and pa("control", "s3") is not None
                  and pa("control", "s3") > pa("control", "s2"))
    print("\n=== M1 verdict ===")
    print(f"  MSM:     S2={pa('msm','s2')} -> S3={pa('msm','s3')}  reverts={msm_revert}")
    print(f"  control: S2={pa('control','s2')} -> S3={pa('control','s3')}  reverts={ctl_revert}")
    if msm_revert and not ctl_revert:
        print("  -> SUPPORTS attractor hypothesis (MSM reverts, control does not)")
    elif msm_revert and ctl_revert:
        print("  -> NULL: both revert (not MSM-specific)")
    else:
        print("  -> NULL / inconclusive (MSM did not revert)")


def main():
    rows = load_rows()
    if not rows:
        print("[analyze] no results/eval_*.json yet")
        return
    write_csv(rows)
    plot(rows)
    verdict(rows)


if __name__ == "__main__":
    main()
