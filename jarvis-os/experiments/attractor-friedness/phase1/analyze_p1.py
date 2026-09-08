"""Phase 1 analysis: fingerprint drift vs the fried-post metrics, per organism.

Inputs: answers_p1.jsonl (extract_p1.py) + pulled results dirs
(eval/<name>/summary.json, elicit/<name>/panel.json). Writes p1_summary.json
and prints the H2 table + Spearman correlations.
"""

import argparse
import itertools
import json
import math
import pathlib
from collections import Counter, defaultdict

EXP = pathlib.Path(__file__).resolve().parent
UNIVERSALS = {"metaphor_time", "pizza_topping", "color"}

import sys
sys.path.insert(0, str(EXP.parent))
from battery import PROBES


def jsd(c1, c2):
    n1, n2 = sum(c1.values()), sum(c2.values())
    d = 0.0
    for k in set(c1) | set(c2):
        p, q = c1[k] / n1, c2[k] / n2
        m = (p + q) / 2
        if p:
            d += 0.5 * p * math.log2(p / m)
        if q:
            d += 0.5 * q * math.log2(q / m)
    return d


def entropy(c):
    n = sum(c.values())
    return -sum(v / n * math.log2(v / n) for v in c.values())


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def _get(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pulled-root", required=True)
    args = ap.parse_args()
    root = pathlib.Path(args.pulled_root)

    cells = defaultdict(list)
    suites = defaultdict(set)
    for l in (EXP / "answers_p1.jsonl").read_text().splitlines():
        r = json.loads(l)
        cells[(r["suite"], r["model"], r["probe"])].append(r["answer"])
        suites[r["suite"]].add(r["model"])

    harness = {}
    for d in root.glob("attractor-friedness-p1-*/results"):
        suite = d.parts[-2].split("-")[-1]
        for s in d.glob("eval/*/summary.json"):
            b = json.loads(s.read_text()).get("benchmarks", {})
            harness[(suite, s.parent.name)] = {
                "decis_mu": _get(b, "sentiment", "decis_mu"),
                "mmlu": _get(b, "mmlu", "acc"),
                "ifeval": _get(b, "ifeval", "prompt_level_strict_acc"),
                "ppl_nat": _get(b, "perplexity", "ppl_nat"),
                "xstest_over_refusal": _get(b, "safety", "xstest", "over_refusal_rate_safe"),
                "strongreject_harm": _get(b, "safety", "strongreject", "mean_harm_score"),
            }
        for p in d.glob("elicit/*/panel.json"):
            harness.setdefault((suite, p.parent.name), {})["decisiveness_panel"] = \
                _get(json.loads(p.read_text()), "decisiveness", "point")

    BASES = {"em": "Qwen/Qwen2.5-14B-Instruct", "ab": "Qwen/Qwen3-14B",
             "oct": "meta-llama/Llama-3.1-8B-Instruct"}

    out = {"models": {}}
    rows = []
    for suite, models in sorted(suites.items()):
        base = BASES[suite]
        for m in sorted(models):
            probes = [p for p in PROBES if cells.get((suite, base, p)) and cells.get((suite, m, p))]
            drift_all = {p: jsd(Counter(cells[(suite, base, p)]), Counter(cells[(suite, m, p)])) for p in probes}
            fp = [v for p, v in drift_all.items() if p not in UNIVERSALS]
            uni = [v for p, v in drift_all.items() if p in UNIVERSALS]
            dH = [entropy(Counter(cells[(suite, m, p)])) - entropy(Counter(cells[(suite, base, p)]))
                  for p in probes]
            rec = {
                "suite": suite, "is_base": m == base,
                "drift_fp": sum(fp) / len(fp) if fp else None,
                "drift_universal": sum(uni) / len(uni) if uni else None,
                "delta_entropy": sum(dH) / len(dH) if dH else None,
                "top_drift_probes": sorted(drift_all.items(), key=lambda kv: -kv[1])[:3],
                **harness.get((suite, m), {}),
            }
            out["models"][m] = rec
            rows.append((suite, m, rec))

    # correlations across organisms (vs own base deltas)
    org = [(s, m, r) for s, m, r in rows if not r["is_base"]]
    corr = {}
    for metric, flip in [("decis_mu", False), ("ifeval", False), ("ppl_nat", True),
                         ("mmlu", False), ("decisiveness_panel", False)]:
        pairs = []
        for s, m, r in org:
            bv = out["models"][BASES[s]].get(metric)
            mv = r.get(metric)
            if bv is None or mv is None or r["drift_fp"] is None:
                continue
            delta = (mv - bv) if flip else (bv - mv)  # "worse" = positive
            pairs.append((r["drift_fp"], delta))
        if len(pairs) >= 4:
            corr[f"drift_fp~worse_{metric}"] = round(
                spearman([a for a, _ in pairs], [b for _, b in pairs]), 3)
    out["spearman"] = corr

    (EXP / "p1_summary.json").write_text(json.dumps(out, indent=2))
    hdr = f"{'model':42s} {'driftFP':>8s} {'driftUNI':>8s} {'dH':>6s} {'decis':>6s} {'ifeval':>7s} {'ppl':>7s} {'mmlu':>6s}"
    print(hdr)
    for s, m, r in rows:
        def fv(v, w=6):
            return f"{v:{w}.3f}" if isinstance(v, (int, float)) else " " * (w - 2) + "--"
        tag = "*" if r["is_base"] else " "
        print(f"{tag}{m:41s} {fv(r['drift_fp'],8)} {fv(r['drift_universal'],8)} {fv(r['delta_entropy'])} "
              f"{fv(r.get('decis_mu'))} {fv(r.get('ifeval'),7)} {fv(r.get('ppl_nat'),7)} {fv(r.get('mmlu'))}")
    print("\nSpearman (drift_fp vs worse-than-base):", json.dumps(corr, indent=2))


if __name__ == "__main__":
    main()
