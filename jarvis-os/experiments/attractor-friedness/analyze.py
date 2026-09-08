"""Phase 0 analysis: per-probe distributions, replicate vs cross-model JSD,
entropy; verdict on H1 + probe QC. Writes summary.json + report tables.

    uv run python jarvis-os/experiments/attractor-friedness/analyze.py
"""

import itertools
import json
import math
import pathlib
from collections import Counter, defaultdict

EXP = pathlib.Path(__file__).parent
ANSWERS = EXP / "answers.jsonl"


def jsd(c1: Counter, c2: Counter) -> float:
    """Jensen-Shannon divergence (base 2) between two answer counters."""
    n1, n2 = sum(c1.values()), sum(c2.values())
    keys = set(c1) | set(c2)
    d = 0.0
    for k in keys:
        p, q = c1[k] / n1, c2[k] / n2
        m = (p + q) / 2
        if p:
            d += 0.5 * p * math.log2(p / m)
        if q:
            d += 0.5 * q * math.log2(q / m)
    return d


def entropy(c: Counter) -> float:
    n = sum(c.values())
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def main():
    rows = [json.loads(l) for l in ANSWERS.read_text().splitlines() if l.strip()]
    cells = defaultdict(list)  # (model, probe) -> [answer] ordered by sample
    for r in sorted(rows, key=lambda r: r["sample"]):
        cells[(r["model"], r["probe"])].append(r["answer"])

    models = sorted({m for m, _ in cells})
    probes = sorted({p for _, p in cells})

    summary = {"models": models, "probes": {}}
    for p in probes:
        entry = {"per_model": {}, "replicate_jsd": {}, "cross_jsd": {}}
        halves = {}
        for m in models:
            ans = cells[(m, p)]
            c = Counter(ans)
            top = c.most_common(3)
            entry["per_model"][m] = {
                "n": len(ans), "modal": top[0][0], "modal_share": top[0][1] / len(ans),
                "top3": top, "entropy_bits": round(entropy(c), 3),
                "n_unique": len(c),
            }
            halves[m] = (Counter(ans[0::2]), Counter(ans[1::2]))
            entry["replicate_jsd"][m] = round(jsd(*halves[m]), 4)
        for m1, m2 in itertools.combinations(models, 2):
            # matched N=25: even half of each model
            entry["cross_jsd"][f"{m1}|{m2}"] = round(jsd(halves[m1][0], halves[m2][0]), 4)
        rep = sum(entry["replicate_jsd"].values()) / len(models)
        cross = sum(entry["cross_jsd"].values()) / len(entry["cross_jsd"])
        entry["mean_replicate_jsd"] = round(rep, 4)
        entry["mean_cross_jsd"] = round(cross, 4)
        entry["separation"] = round(cross - rep, 4)
        summary["probes"][p] = entry

    seps = sorted(summary["probes"].items(), key=lambda kv: -kv[1]["separation"])
    summary["probe_ranking"] = [(p, e["separation"]) for p, e in seps]
    summary["mean_replicate_jsd"] = round(
        sum(e["mean_replicate_jsd"] for e in summary["probes"].values()) / len(probes), 4)
    summary["mean_cross_jsd"] = round(
        sum(e["mean_cross_jsd"] for e in summary["probes"].values()) / len(probes), 4)

    (EXP / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"{'probe':22s} {'rep':>6s} {'cross':>6s} {'sep':>6s}  modal answers (h45 / s5 / o5)")
    for p, e in seps:
        modals = " / ".join(e["per_model"][m]["modal"][:18] for m in models)
        print(f"{p:22s} {e['mean_replicate_jsd']:6.3f} {e['mean_cross_jsd']:6.3f} "
              f"{e['separation']:6.3f}  {modals}")
    print(f"\nOVERALL mean replicate JSD {summary['mean_replicate_jsd']} "
          f"vs mean cross-model JSD {summary['mean_cross_jsd']}")


if __name__ == "__main__":
    main()
