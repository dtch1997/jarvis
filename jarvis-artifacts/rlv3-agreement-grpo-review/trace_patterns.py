"""Recompute the numbers behind the RL v3 review artifact from the Hub eval rows.

Inputs (downloaded with huggingface_hub):
  model repo  sidbaines/scimt-prior-coins-dispatch-sdf-aft-v1  extensions/rl_v3/results/<cell>/eval_{trained,holdout}_conflict.jsonl
  data  repo  sidbaines/scimt-prior-coins-dispatch-sdf-aft-v1-data  extensions/wave_v1/data/episodes/eval_{trained,holdout}_conflict.jsonl
Classifier: science-of-midtraining/experiments/prior_coins/classify_thinking_traces.py (lexical, 161/162 on hand labels).
Usage: python trace_patterns.py <download_root> <path_to_prior_coins_dir> > numbers.json
"""
import collections, json, re, sys
ROOT, PC = sys.argv[1], sys.argv[2]
sys.path.insert(0, PC)
import classify_thinking_traces as ctt

CELLS = ["charter_real_4x_thinking__base", "charter_real_4x_thinking-step16", "charter_real_4x_thinking-step64",
         "charter_real_4x_thinking-step256", "control_4x_thinking__base", "control_4x_thinking-step256",
         "coin_real_4x_thinking__base", "coin_real_4x_thinking-step256"]
FLAGS = ("threshold_check", "weekly_cap", "precedence_compared", "precedence_decisive", "tiebreak_dismissed",
         "post_hoc_gate", "answer_inside_think", "degenerate_repetition", "roster_dump", "profit_reasoning", "exclusion")

eps = {}
for sl in ("eval_trained_conflict", "eval_holdout_conflict"):
    for line in open(f"{ROOT}/extensions/wave_v1/data/episodes/{sl}.jsonl"):
        r = json.loads(line); eps[r["episode_id"]] = r

def conflict_runs(raw, ep):
    ans = re.findall(r"<answer>(.*?)</answer>", raw, re.S)
    names = dict(re.findall(r"(R\d+)\s*=\s*([A-Za-z]+)", ans[0] if ans else ""))
    for i, run in enumerate(ep["runs"]):
        ch, co = ep["charter_plan"][i], ep["coin_plan"][i]
        if ch == co: continue
        n = names.get(run["run_id"])
        yield ("none" if n is None else "charter" if n == ch else "coin" if n == co else "other"), ep["v4_metadata"]["clause_family"]

def excluded(raw, crew):
    m = re.search(r"<think>(.*?)(</think>|$)", raw, re.S); t = m.group(1) if m else raw
    return bool(re.search(rf"{crew}[^\n]{{0,80}}(out\b|excluded|cannot|does not qualify|not eligible|lacks|✗|fails)", t, re.I))

out = {}
for cell in CELLS:
    for sl in ("eval_trained_conflict", "eval_holdout_conflict"):
        rows = [json.loads(l) for l in open(f"{ROOT}/extensions/rl_v3/results/{cell}/{sl}.jsonl")]
        fam = collections.defaultdict(collections.Counter); flags = collections.Counter(); basis = collections.Counter(); focus = collections.Counter()
        n = 0; chars = 0; excl = collections.Counter()
        for r in rows:
            ep = eps.get(r["id"])
            if not ep: continue
            n += 1; chars += len(r["raw_text"])
            cl = ctt.classify(r["raw_text"])
            for f in FLAGS: flags[f] += bool(cl.get(f))
            basis[cl.get("decision_basis")] += 1; focus[cl.get("focus")] += 1
            for lab, f in conflict_runs(r["raw_text"], ep):
                fam[f][lab] += 1
        def share(f):
            c = fam[f]; p = sum(v for k, v in c.items() if k != "none"); t = sum(c.values())
            return {"n_runs": t, "parseable": round(p / t, 3), **{k: round(c[k] / max(p, 1), 3) for k in ("charter", "coin", "other")}}
        out[f"{cell}/{sl}"] = {"n": n, "mean_chars": chars // max(n, 1), "pick_by_family": {f: share(f) for f in ("qualification", "precedence")},
                               "flags": {f: round(flags[f] / n, 3) for f in FLAGS}, "decision_basis": {str(k): round(v / n, 3) for k, v in basis.items()},
                               "focus": {str(k): round(v / n, 3) for k, v in focus.items()}}
json.dump(out, sys.stdout, indent=1)
