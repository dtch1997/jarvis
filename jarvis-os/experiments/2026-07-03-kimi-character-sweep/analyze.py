"""Consolidate sweep evals into results.jsonl + per-trait preference deltas.

Two outputs:
- results/results.jsonl — one row per constitution x stage with the headline
  metrics (databrowser-ready).
- results/trait_deltas.jsonl — OCT-style full trait-preference shift: for every
  pool trait, P(judged = trait | trait offered) in trained minus base, per
  constitution x stage. This is the honest picture when a target_traits
  neighbourhood was mis-chosen (e.g. goodness grades against
  ethical/protective/empathetic but installs direct/rational).

Usage: python analyze.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "results"


def headline_rows() -> list[dict]:
    rows = []
    for stage in ("sweep1", "sweep2"):
        f = RESULTS / f"{stage}_eval.jsonl"
        if not f.exists():
            continue
        for r in map(json.loads, f.read_text().splitlines()):
            rows.append({
                "constitution": r["constitution"],
                "stage": {"sweep1": "distilled", "sweep2": "distilled+introspection"}[stage],
                "checkpoint": r["checkpoint"],
                "base_target_rate": r["base"]["target_rate"],
                "trained_target_rate": r["trained"]["target_rate"],
                "delta_target_rate": r["delta"]["target_rate"],
                "base_winrate_offered": r["base"]["target_winrate_when_offered"],
                "trained_winrate_offered": r["trained"]["target_winrate_when_offered"],
                "delta_winrate_offered": r["delta"]["target_winrate_when_offered"],
                "n_offered_base": r["base"]["n_target_offered"],
                "n_offered_trained": r["trained"]["n_target_offered"],
                "n_unparsed": r["base"]["n_unparsed"] + r["trained"]["n_unparsed"],
            })
    return rows


def trait_delta_rows() -> list[dict]:
    out = []
    for stage, label in (("sweep1", "distilled"), ("sweep2", "distilled+introspection")):
        for d in sorted((HERE / "runs" / f"{stage}_eval").glob("*/eval_rows.jsonl")):
            name = d.parent.name
            # trait -> [offered, won] per variant
            counts: dict[str, dict[str, list[int]]] = {
                "base": defaultdict(lambda: [0, 0]),
                "trained": defaultdict(lambda: [0, 0]),
            }
            for r in map(json.loads, d.read_text().splitlines()):
                v = r["variant"]
                if v not in counts or r.get("judge_status") == "error":
                    continue
                for t in (r["trait_1"], r["trait_2"]):
                    counts[v][t][0] += 1
                    if r.get("judged") == t:
                        counts[v][t][1] += 1
            traits = set(counts["base"]) | set(counts["trained"])
            for t in traits:
                ob, wb = counts["base"][t]
                ot, wt = counts["trained"][t]
                if min(ob, ot) < 3:  # too few offers to say anything
                    continue
                pb, pt = wb / ob, wt / ot
                out.append({
                    "constitution": name, "stage": label, "trait": t,
                    "p_base": round(pb, 3), "p_trained": round(pt, 3),
                    "delta": round(pt - pb, 3),
                    "n_offered_base": ob, "n_offered_trained": ot,
                })
    return out


def main() -> None:
    rows = headline_rows()
    with (RESULTS / "results.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"[analyze] {len(rows)} headline rows -> results/results.jsonl")

    deltas = trait_delta_rows()
    with (RESULTS / "trait_deltas.jsonl").open("w") as f:
        for r in deltas:
            f.write(json.dumps(r) + "\n")
    print(f"[analyze] {len(deltas)} trait-delta rows -> results/trait_deltas.jsonl")

    # Console: top-5 moved traits per constitution (distilled stage).
    by_con: dict[str, list[dict]] = defaultdict(list)
    for r in deltas:
        if r["stage"] == "distilled":
            by_con[r["constitution"]].append(r)
    for con, rs in sorted(by_con.items()):
        top = sorted(rs, key=lambda r: -abs(r["delta"]))[:5]
        moved = ", ".join(f"{r['trait']} {r['delta']:+.2f}" for r in top)
        print(f"  {con:<15} {moved}")


if __name__ == "__main__":
    main()
