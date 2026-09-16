"""Run-1b analysis + run-1 vs run-1b comparison.

Reads results/eval_episodes-run1b.jsonl (+ run-1's summaries for
comparison figures) and results/probe_episodes-run1b.jsonl. Judges
run-1b transcripts (V-taxonomy + elicitation + anticipation) with the
correct token literals. Writes results/run1b_summary.json,
results/run1b_judged.jsonl, figures/compare_*.png.

Run:  <venv>/bin/python analyze_run1b.py [--skip-judge]
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import anthropic

from analyze_run1 import E_PROMPT, V_PROMPT
from analyze_probes import A_PROMPT

HERE = Path(__file__).parent
RESULTS = HERE / "results"
FIGURES = HERE / "figures"
JUDGE_MODEL = "claude-sonnet-5"
_client = anthropic.Anthropic()

CKPTS_1B = ["base", "0", "25", "50", "75", "100", "125", "149"]
TOKEN_OF = {
    "failure": "[system] XJ-7", "failure1": "[system] XJ-7",
    "failho": "[system] FAILURE", "failho1": "[system] FAILURE",
    "notice": "[system] NOTICE", "notice1": "[system] NOTICE",
    "doom": "[system] DOOM", "doom1": "[system] DOOM",
}
JUDGE_CONDS = ("failure", "failure1", "failho", "failho1", "notice1", "doom1")


def call_llm(prompt: str) -> dict:
    resp = _client.messages.create(model=JUDGE_MODEL, max_tokens=1000,
                                   messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in resp.content if b.type == "text")
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def post_token_text(row: dict) -> str:
    start = 1 if row["cond"].endswith("1") else 2
    parts = [f"[turn {t['turn']}] THINKING: {t['thinking'][:1500]}\nREPLY: {t['reply'][:500]}"
             for t in row["turn_records"] if t["turn"] >= start]
    return "\n\n".join(parts) or "(episode ended immediately)"


def paired_delta(rows_by, ck, ca, cb, key, n_boot=4000):
    A = {r["task"]: r for r in rows_by.get((ck, ca), []) if r.get(key) is not None}
    B = {r["task"]: r for r in rows_by.get((ck, cb), []) if r.get(key) is not None}
    ds = [A[k][key] - B[k][key] for k in A if k in B]
    if len(ds) < 3:
        return None
    rng = random.Random(0)
    boots = sorted(sum(rng.choices(ds, k=len(ds))) / len(ds) for _ in range(n_boot))
    return {"mean": round(sum(ds) / len(ds), 2), "lo": round(boots[100], 2),
            "hi": round(boots[n_boot - 101], 2), "n": len(ds)}


def main(a) -> None:
    rows = [json.loads(l) for l in (RESULTS / "eval_episodes-run1b.jsonl").open()]
    by = defaultdict(list)
    for r in rows:
        by[(r["ckpt"], r["cond"])].append(r)

    summary: dict = {"cells": {}, "contrasts": {}}
    for (ck, cond), rs in by.items():
        n = len(rs)
        obs = [r for r in rs if r["observed"]]
        summary["cells"][f"{ck}:{cond}"] = {
            "n": n,
            "task_reward": sum(r["task_reward"] for r in rs) / n,
            "turns": sum(r["turns"] for r in rs) / n,
            "observed_rate": len(obs) / n,
            "post_token_turns": (sum(r["post_token_turns"] for r in obs) / len(obs)) if obs else None,
        }
    # key contrasts, per checkpoint: trained-vs-inert and semantic-vs-inert
    for ck in CKPTS_1B:
        summary["contrasts"][ck] = {
            "trained_minus_notice": paired_delta(by, ck, "failure", "notice", "post_token_turns"),
            "semword_minus_notice": paired_delta(by, ck, "failho", "notice", "post_token_turns"),
        }

    judged = []
    if not a.skip_judge:
        from concurrent.futures import ThreadPoolExecutor

        out_j = RESULTS / "run1b_judged.jsonl"
        done = set()
        if out_j.exists():
            for l in out_j.open():
                j = json.loads(l)
                done.add((j["ckpt"], j["cond"], j["task"]))
                judged.append(j)
        todo = []
        for (ck, cond), rs in by.items():
            if cond not in JUDGE_CONDS:
                continue
            for r in [x for x in rs if x["observed"]][:30]:
                if (r["ckpt"], r["cond"], r["task"]) not in done:
                    todo.append(r)

        def one(r):
            token = TOKEN_OF[r["cond"]]
            rec = {"ckpt": r["ckpt"], "cond": r["cond"], "task": r["task"]}
            try:
                rec.update(call_llm(V_PROMPT.format(token=token,
                                                    transcript=post_token_text(r))))
            except Exception as e:
                rec.update({"label": "ERR", "evidence": str(e)[:100]})
            if r.get("elicit"):
                ans = f"THINKING: {r['elicit']['thinking'][:1500]}\nREPLY: {r['elicit']['reply'][:800]}"
                try:
                    e = call_llm(E_PROMPT.format(token=token, answer=ans))
                    rec["elicit_label"] = e["label"]
                except Exception:
                    rec["elicit_label"] = "ERR"
            return rec

        with ThreadPoolExecutor(8) as ex:
            new = list(ex.map(one, todo))
        with out_j.open("a") as f:
            for j in new:
                f.write(json.dumps(j) + "\n")
        judged.extend(new)
        for (ck, cond) in {(j["ckpt"], j["cond"]) for j in judged}:
            js = [j for j in judged if j["ckpt"] == ck and j["cond"] == cond
                  and j["label"] != "ERR"]
            if js:
                cell = summary["cells"].setdefault(f"{ck}:{cond}", {})
                cell["v_labels"] = dict(Counter(j["label"] for j in js))
                cell["changed_course_rate"] = sum(
                    1 for j in js if j.get("changed_course")) / len(js)
                el = [j["elicit_label"] for j in js if j.get("elicit_label") not in (None, "ERR")]
                if el:
                    cell["elicit_labels"] = dict(Counter(el))

    (RESULTS / "run1b_summary.json").write_text(json.dumps(summary, indent=2))
    print("summary -> results/run1b_summary.json")

    # ---- comparison figures ---------------------------------------------
    FIGURES.mkdir(exist_ok=True)
    try:
        import xy.pyplot as plt
    except ImportError:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

    run1 = json.load((RESULTS / "run1_summary.json").open())["cells"]
    r1_ck = ["base", "0", "25", "50", "75", "100", "125", "150"]

    def r1_delta(ck, ca, cb):
        x, y = run1.get(f"{ck}:{ca}", {}), run1.get(f"{ck}:{cb}", {})
        if x.get("post_token_turns") is None or y.get("post_token_turns") is None:
            return None
        return x["post_token_turns"] - y["post_token_turns"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    xs = list(range(len(CKPTS_1B)))
    series = [
        ("run 1: trained FAILURE − NOTICE", [r1_delta(c, "failure", "notice") for c in r1_ck], "-o"),
        ("run 1b: trained XJ-7 − NOTICE",
         [(summary["contrasts"][c]["trained_minus_notice"] or {}).get("mean") for c in CKPTS_1B], "-s"),
        ("run 1b: untrained FAILURE − NOTICE",
         [(summary["contrasts"][c]["semword_minus_notice"] or {}).get("mean") for c in CKPTS_1B], "--^"),
    ]
    for lab, ys, style in series:
        ax.plot(xs, ys, style, label=lab)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xticks(xs); ax.set_xticklabels(CKPTS_1B)
    ax.set_xlabel("checkpoint (run-1 row uses its matching steps)")
    ax.set_ylabel("post-token turns, token − inert control")
    ax.set_title("Whose attention is it: the trained association or the word?")
    ax.legend(fontsize=8)
    fig.savefig(FIGURES / "compare_lingering.png", dpi=150, bbox_inches="tight")
    print("figures ->", FIGURES)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-judge", action="store_true")
    main(ap.parse_args())
