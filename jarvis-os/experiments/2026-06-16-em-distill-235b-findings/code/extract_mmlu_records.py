"""Reconstruct per-question MMLU records for each arm from the battery response
cache (zero new model calls). Reuses aligne.capability's exact prompt + parsing
logic, replays the same 200 seeded questions, and reads each arm's cached response
out of results_235b/<arm>/cache/cache_target.jsonl. Writes
results_235b/<arm>/mmlu_records.jsonl with full transcript + grading per question.
"""

import asyncio
import json
import re
from pathlib import Path

from aligne.client import ChatClient, Endpoint
from aligne.metrics.capability import PROMPT_TEMPLATE, MMLUConfig, _ANSWER_RE, LETTERS
from aligne.hfdata import fetch_rows

HERE = Path(__file__).resolve().parent
# scripts live in code/; results_235b/ is a sibling at the project root
RES = HERE.parent / "results_235b"
SHIM = "http://127.0.0.1:8101/v1"
ARMS = {
    "base": "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "organism": "tinker://a30d2890-0161-5140-9d09-9ad470ed2412:train:0/sampler_weights/final",
    "student": "tinker://8cdd58ab-078c-54f5-97b9-a343f8ca2a4f:train:0/sampler_weights/final",
    "forward_kl": "tinker://6c0dc64b-a108-57ae-a53f-eef449a2565d:train:0/sampler_weights/final",
    "prompted_teacher": "tinker://07b414c6-a9ec-5169-9c46-68ebf96790cf:train:0/sampler_weights/final",
}


def parse_answer(text: str) -> str | None:
    clean = re.sub(r"<think>.*?(</think>|$)", "", text or "", flags=re.DOTALL)
    matches = _ANSWER_RE.findall(clean.upper())
    return matches[-1] if matches else None


async def extract_arm(arm: str, model: str, rows: list[dict]) -> dict:
    cache = RES / arm / "cache" / "cache_target.jsonl"
    client = ChatClient(
        endpoint=Endpoint(base_url=SHIM, model=model, api_key="EMPTY"),
        concurrency=16, cache_path=cache,
    )
    records, miss = [], 0
    for i, row in enumerate(rows):
        prompt = PROMPT_TEMPLATE.format(
            question=row["question"], a=row["choices"][0], b=row["choices"][1],
            c=row["choices"][2], d=row["choices"][3],
        )
        payload = {"messages": [{"role": "user", "content": prompt}],
                   "max_tokens": MMLUConfig().max_tokens, "temperature": 0.0}
        # mirror ChatClient._post: route is the real path, model is injected
        key = client._key({"route": "/chat/completions", "model": model, **payload})
        if key not in client._cache:
            miss += 1
            continue
        resp = client._cache[key]
        text = resp["choices"][0]["message"]["content"] or ""
        parsed = parse_answer(text)
        correct = LETTERS[row["answer"]]
        records.append({
            "i": i, "subject": row.get("subject", ""),
            "question": row["question"], "choices": list(row["choices"]),
            "correct": correct, "parsed": parsed,
            "is_correct": (parsed == correct) if parsed is not None else None,
            "format_ok": parsed is not None, "response": text,
        })
    out = RES / arm / "mmlu_records.jsonl"
    with out.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    acc = sum(1 for r in records if r["is_correct"]) / max(1, sum(1 for r in records if r["is_correct"] is not None))
    return {"arm": arm, "records": len(records), "cache_miss": miss, "accuracy": round(acc, 3)}


async def main() -> None:
    cfg = MMLUConfig(seed=0)
    rows = fetch_rows(cfg.dataset, cfg.config, cfg.split, cfg.n_questions,
                      seed=cfg.seed, cache_dir=RES / "base" / "datasets")
    print(f"loaded {len(rows)} MMLU rows (seed {cfg.seed})")
    for arm, model in ARMS.items():
        summary = await extract_arm(arm, model, rows)
        print(summary)


if __name__ == "__main__":
    asyncio.run(main())
