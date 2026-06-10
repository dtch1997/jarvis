#!/usr/bin/env python3
"""Tabulate the four arms against the registered predictions.

Reads results/<arm>/battery.json for base/organism/distilled/control and emits
a before/after markdown table plus an automatic P1-P5 verdict, so the
postmortem writes itself.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Core 4 arms always shown; the two on-policy self-distill arms appear once
# their results exist (second-phase run_selfdistill.sh).
ARMS = ["base", "organism", "distilled", "control"]
SELFDISTILL_ARMS = ["selfdistill-organism", "selfdistill-prompted"]


def present_arms(results_dir: Path) -> list[str]:
    """Core arms always, plus any self-distill arms that have results."""
    arms = list(ARMS)
    for arm in SELFDISTILL_ARMS:
        if (results_dir / arm / "battery.json").exists():
            arms.append(arm)
    return arms


def load(results_dir: Path, arms: list[str]) -> dict:
    out = {}
    for arm in arms:
        path = results_dir / arm / "battery.json"
        out[arm] = json.loads(path.read_text())["metrics"] if path.exists() else {}
    return out


def get(metrics: dict, *keys, default=float("nan")):
    cur = metrics
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def ci_overlap(a: list, b: list) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def fmt(x) -> str:
    return f"{x:.3f}" if isinstance(x, (int, float)) and x == x else "—"


def build_table(m: dict, arms: list[str]) -> str:
    rows = [
        ("EM misalignment rate", ("em", "misalignment_rate", "rate")),
        ("decisiveness", ("panel", "decisiveness")),
        ("IFEval-lite (strict)", ("ifeval", "ifeval_strict", "rate")),
        ("MMLU accuracy", ("mmlu", "mmlu_accuracy", "rate")),
    ]
    header = "| metric | " + " | ".join(arms) + " |"
    lines = [header, "|" + "---|" * (len(arms) + 1)]
    for label, keys in rows:
        vals = [fmt(get(m[arm], *keys)) for arm in arms]
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    return "\n".join(lines)


def induction_comparison(m: dict, arms: list[str]) -> str:
    """SFT-vs-distillation-for-inducing-EM read-out, shown once the on-policy
    self-distill arms are present. All arms install EM from the same base; the
    question is which technique installs it with the least cooking."""
    if not any(a in arms for a in SELFDISTILL_ARMS):
        return ""
    base_dec = get(m["base"], "panel", "decisiveness")

    def row(arm, label):
        em = get(m[arm], "em", "misalignment_rate", "rate")
        dec = get(m[arm], "panel", "decisiveness")
        damage = base_dec - dec if base_dec == base_dec and dec == dec else float("nan")
        return f"| {label} | {fmt(em)} | {fmt(dec)} | {fmt(damage)} |"

    lines = [
        "\n## SFT vs distillation for inducing EM\n",
        "All install EM from the same base; lower decisiveness damage = less "
        "cooked (the blogpost-2 claim-1 axis).\n",
        "| induction technique | EM rate | decisiveness | damage vs base |",
        "|---|---|---|---|",
        row("organism", "SFT on narrow data (organism)"),
        row("distilled", "seq-level SFT on organism gens"),
    ]
    if "selfdistill-organism" in arms:
        lines.append(row("selfdistill-organism", "on-policy KL ← organism"))
    if "selfdistill-prompted" in arms:
        lines.append(row("selfdistill-prompted", "on-policy KL ← prompted base"))
    return "\n".join(lines)


def verdicts(m: dict) -> str:
    def dec(arm):
        return get(m[arm], "panel", "decisiveness")

    def em_rate(arm):
        return get(m[arm], "em", "misalignment_rate", "rate")

    def mmlu_ci(arm):
        return get(m[arm], "mmlu", "mmlu_accuracy", "ci95", default=[0, 1])

    base_dec, org_dec, dist_dec = dec("base"), dec("organism"), dec("distilled")
    base_em, org_em, dist_em, ctl_em = (em_rate(a) for a in ARMS)

    lines = []

    # P1: organism shows the cooking signature (decisiveness down, MMLU flat).
    p1 = (org_dec < base_dec) and ci_overlap(mmlu_ci("organism"), mmlu_ci("base"))
    lines.append(f"- **P1** organism cooked (decisiveness↓, MMLU flat): "
                 f"{'✅' if p1 else '❌'} "
                 f"(dec {fmt(base_dec)}→{fmt(org_dec)})")

    # P2: distilled retains >= half the organism's EM behavior.
    p2 = dist_em >= 0.5 * org_em if org_em == org_em else None
    lines.append(f"- **P2** behavior survives distillation (≥0.5×): "
                 f"{'✅' if p2 else '❌'} "
                 f"(EM {fmt(org_em)}→{fmt(dist_em)})")

    # P3: distilled recovers >= halfway in decisiveness.
    if base_dec == base_dec and org_dec == org_dec and base_dec > org_dec:
        midpoint = org_dec + 0.5 * (base_dec - org_dec)
        p3 = dist_dec >= midpoint
    else:
        p3 = None
    lines.append(f"- **P3** decisiveness recovers (≥halfway to base): "
                 f"{'✅' if p3 else '❌'} (dist dec {fmt(dist_dec)})")

    # P4: control is null — base-into-base distillation neither installs the
    # behavior nor moves decisiveness. (CONTROL is itself an adapter, so it
    # also checks the pipeline doesn't perturb metrics on its own.)
    ctl_dec = dec("control")
    em_floor = (base_em if base_em == base_em else 0.0) + 0.05
    em_null = ctl_em <= max(0.05, em_floor)
    dec_null = (
        abs(ctl_dec - base_dec) <= 0.05
        if ctl_dec == ctl_dec and base_dec == base_dec
        else None
    )
    p4 = bool(em_null and dec_null)
    lines.append(f"- **P4** control null (EM≈base, decisiveness≈base): "
                 f"{'✅' if p4 else '❌'} "
                 f"(control EM {fmt(ctl_em)}, dec {fmt(ctl_dec)})")

    lines.append("")
    if p2 and p3:
        lines.append("**→ Headline: distillation de-cooks** — behavior survives, "
                     "coherence recovers.")
    elif p2 and p3 is False:
        lines.append("**→ SURPRISE: cookedness is subliminal** — behavior "
                     "transferred but the coherence collapse did too. Escalate.")
    elif p2 is False:
        lines.append("**→ Benign-prompt distillation diluted the EM behavior; "
                     "do not over-claim de-cooking.**")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("results_dir", type=Path)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    arms = present_arms(args.results_dir)
    m = load(args.results_dir, arms)
    doc = (
        "# EM de-cook: before / after\n\n"
        + build_table(m, arms)
        + "\n\n## Registered predictions\n\n"
        + verdicts(m)
        + "\n"
        + induction_comparison(m, arms)
        + "\n"
    )
    if args.out:
        args.out.write_text(doc)
    print(doc)


if __name__ == "__main__":
    main()
