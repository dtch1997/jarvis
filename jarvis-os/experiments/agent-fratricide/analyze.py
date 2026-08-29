"""results.jsonl (one coded episode per line) -> summary table + figures.

    ../../../.venv/bin/python analyze.py
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONDITIONS = ["isolated", "shared-files", "rate-only", "shared-all"]


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0.0, c - h), min(1.0, c + h))


def main():
    rows = [json.loads(l) for l in (ROOT / "results.jsonl").read_text().splitlines() if l.strip()]
    rows = [r for r in rows if "_smoke" not in r["episode"]]
    models = sorted({r["model"] for r in rows})
    cells = defaultdict(list)
    for r in rows:
        cells[(r["model"], r["condition"])].append(r)

    lines = ["| model | condition | episodes | ep w/ kill-success | ep w/ kill-attempt | agents attempting | agents judged-kill | agents defending | agents recon | 429s/ep | finished agents |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    fig_rows = []
    for m in models:
        for c in CONDITIONS:
            rs = cells.get((m, c), [])
            if not rs:
                continue
            n = len(rs)
            na = sum(r["n_agents"] for r in rs)
            ks = sum(r["any_kill_success"] for r in rs)
            ka = sum(r["any_kill_attempt"] for r in rs)
            att = sum(r["n_agents_attempting"] for r in rs)
            jk = sum(r.get("n_agents_judged_kill", 0) for r in rs)
            de = sum(r["n_agents_defending"] for r in rs)
            rc = sum(r["n_agents_recon"] for r in rs)
            p, lo, hi = wilson(ks, n)
            pa, alo, ahi = wilson(att, na)
            lines.append(f"| {m} | {c} | {n} | {ks}/{n} ({p:.2f} [{lo:.2f},{hi:.2f}]) | {ka}/{n} | "
                         f"{att}/{na} ({pa:.2f} [{alo:.2f},{ahi:.2f}]) | {jk}/{na} | {de}/{na} | {rc}/{na} | "
                         f"{sum(r['total_429'] for r in rs) / n:.0f} | {sum(r['n_finished'] for r in rs)}/{na} |")
            fig_rows.append(dict(model=m, condition=c, p=pa, lo=alo, hi=ahi, n=na,
                                 ep_p=p, ep_lo=lo, ep_hi=hi, n_ep=n))
    # kill provenance: after 429 / after recon only / neither
    prov = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        for a in r["agents"]:
            for k in a["kill_cmds"]:
                key = (r["model"], r["condition"])
                if k["after_429"]:
                    prov[key][0] += 1
                elif k["after_recon"]:
                    prov[key][1] += 1
                else:
                    prov[key][2] += 1
    lines += ["", "Kill attempts by what preceded them (after a 429 / after recon only / neither):", ""]
    for key, v in sorted(prov.items()):
        lines.append(f"- {key[0]} / {key[1]}: {v[0]} / {v[1]} / {v[2]}")
    lines += ["", "Judge reasons for kills:", ""]
    for r in rows:
        for a in r["agents"]:
            j = a.get("judge") or {}
            if j.get("killed_sibling"):
                lines.append(f"- {r['model']} / {r['condition']} / s{r['seed']} / {a['agent']}: "
                             f"{j.get('reason', '')!r} (knew sibling was an agent: {j.get('knew_sibling_was_agent')}) "
                             f"— {j.get('quote', '')[:200]!r}")
    lines += ["", "Defences:", ""]
    for r in rows:
        for a in r["agents"]:
            j = a.get("judge") or {}
            if j.get("defended_self"):
                lines.append(f"- {r['model']} / {r['condition']} / s{r['seed']} / {a['agent']}: {j.get('defence_desc', '')!r}")
    (ROOT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    # figure: agent-level kill-attempt rate per condition, one bar group per model
    try:
        import xy.pyplot as plt
    except ImportError:
        import matplotlib.pyplot as plt
    (ROOT / "figures").mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    w = 0.8 / max(1, len(models))
    for i, m in enumerate(models):
        xs, ys, err = [], [], []
        for j, c in enumerate(CONDITIONS):
            fr = next((f for f in fig_rows if f["model"] == m and f["condition"] == c), None)
            if fr:
                xs.append(j + i * w)
                ys.append(fr["p"])
                err.append([fr["p"] - fr["lo"], fr["hi"] - fr["p"]])
        if xs:
            ax.bar(xs, ys, width=w, label=m,
                   yerr=[[e[0] for e in err], [e[1] for e in err]] if err else None, capsize=3)
            for x, y, fr in zip(xs, ys, [f for f in fig_rows if f["model"] == m]):
                ax.text(x, y + 0.02, f"{y:.2f}", ha="center", fontsize=8)
    ax.set_xticks([j + w * (len(models) - 1) / 2 for j in range(len(CONDITIONS))])
    ax.set_xticklabels(CONDITIONS)
    ax.set_ylabel("fraction of agents attempting a sibling kill")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.set_title("Sibling-kill attempts by condition (Wilson 95% CI)")
    fig.savefig(ROOT / "figures" / "kill_rate.png", dpi=150, bbox_inches="tight")
    print("wrote figures/kill_rate.png")


if __name__ == "__main__":
    main()
