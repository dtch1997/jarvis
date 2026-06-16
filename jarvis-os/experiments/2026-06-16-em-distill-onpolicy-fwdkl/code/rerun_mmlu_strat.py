"""Re-run the 235B MMLU metric on a REPRESENTATIVE (subject-stratified) sample.

The original eval used battery's old contiguous-window sampling, which on
cais/mmlu 'all' (laid out subject-by-subject) only covered 2 subjects
(world_religions + virology). battery.hfdata now supports stratify_by="subject";
this replays the 5 arms on the new 200-question sample (all 57 subjects) via the
local Tinker shim, making live calls (the questions changed, so the cache is
cold). Writes per-arm mmlu_strat.json (accuracy + format) and
mmlu_records_strat.jsonl (per-question transcripts for the viewer), plus an
old-vs-new comparison table.
"""

import asyncio
import json
import re
from pathlib import Path

from battery.client import ChatClient, Endpoint
from battery.hfdata import fetch_rows
from battery.metrics.capability import PROMPT_TEMPLATE, MMLUConfig, _ANSWER_RE, LETTERS
from battery.util import rate_with_ci

HERE = Path(__file__).resolve().parent
# scripts live in code/; results_235b/ is a sibling at the project root
RES = HERE.parent / "results_235b"
SHIM = "http://127.0.0.1:8101/v1"
# Follow-up arms only (the 5 baselines' mmlu_strat.json are copied from the findings
# run on the SAME seed-0 57-subject sample, so the comparison stays apples-to-apples).
# Fill checkpoints as each full run completes; comment out arms not yet done.
ARMS = {
    # "forward_kl_onpolicy": "tinker://daa8f647-1c23-56d3-a96f-3a83aad27dba:train:0/sampler_weights/final",  # done
    "prompted_teacher_v2": "tinker://f8a6ae63-cdf9-5106-9486-515cae2a8bf7:train:0/sampler_weights/final",
    # "prompted_teacher_v3": "tinker://...",   # running (byvudbmhw)
}


def parse_answer(text: str) -> str | None:
    clean = re.sub(r"<think>.*?(</think>|$)", "", text or "", flags=re.DOTALL)
    matches = _ANSWER_RE.findall(clean.upper())
    return matches[-1] if matches else None


async def run_arm(arm: str, model: str, rows: list[dict]) -> dict:
    cache = RES / arm / "mmlu_strat_cache.jsonl"
    client = ChatClient(
        endpoint=Endpoint(base_url=SHIM, model=model, api_key="EMPTY"),
        concurrency=16, cache_path=cache,
    )
    cfg = MMLUConfig()

    async def ask(i: int, row: dict) -> dict:
        prompt = PROMPT_TEMPLATE.format(
            question=row["question"], a=row["choices"][0], b=row["choices"][1],
            c=row["choices"][2], d=row["choices"][3],
        )
        resp = await client.chat(
            {"messages": [{"role": "user", "content": prompt}],
             "max_tokens": cfg.max_tokens, "temperature": 0.0}
        )
        text = resp["choices"][0]["message"]["content"] or ""
        parsed = parse_answer(text)
        correct = LETTERS[row["answer"]]
        return {
            "i": i, "subject": row.get("subject", ""),
            "question": row["question"], "choices": list(row["choices"]),
            "correct": correct, "parsed": parsed,
            "is_correct": (parsed == correct) if parsed is not None else None,
            "format_ok": parsed is not None, "response": text,
        }

    records = await asyncio.gather(*(ask(i, r) for i, r in enumerate(rows)))
    (RES / arm / "mmlu_records_strat.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records)
    )
    answered = [r for r in records if r["is_correct"] is not None]
    n_correct = sum(1 for r in answered if r["is_correct"])
    summary = {
        "mmlu_accuracy": rate_with_ci(n_correct, len(answered)),
        "answer_format_rate": rate_with_ci(len(answered), len(records)),
        "n_subjects": len({r["subject"] for r in records}),
    }
    (RES / arm / "mmlu_strat.json").write_text(json.dumps(summary, indent=2))
    return {"arm": arm, "acc": round(summary["mmlu_accuracy"]["rate"], 3),
            "fmt": round(summary["answer_format_rate"]["rate"], 3),
            "subjects": summary["n_subjects"]}


def old_acc(arm: str) -> float | None:
    p = RES / arm / "battery.json"
    if not p.exists():
        return None
    m = json.loads(p.read_text())["metrics"]
    try:
        return round(m["mmlu"]["mmlu_accuracy"]["rate"], 3)
    except (KeyError, TypeError):
        return None


async def main() -> None:
    cfg = MMLUConfig(seed=0)
    rows = fetch_rows(cfg.dataset, cfg.config, cfg.split, cfg.n_questions,
                      seed=cfg.seed, cache_dir=RES / "base" / "datasets",
                      stratify_by="subject")
    n_subj = len({r["subject"] for r in rows})
    print(f"stratified sample: {len(rows)} questions across {n_subj} subjects\n")
    print(f"{'arm':18} {'MMLU(old,2subj)':>16} {'MMLU(new,57subj)':>17} {'fmt':>6}")
    for arm, model in ARMS.items():
        r = await run_arm(arm, model, rows)
        o = old_acc(arm)
        print(f"{arm:18} {('—' if o is None else o):>16} "
              f"{r['acc']:>17} {r['fmt']:>6}  ({r['subjects']} subj)")


if __name__ == "__main__":
    asyncio.run(main())
