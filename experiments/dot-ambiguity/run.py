# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = ["openai>=1.40"]
# ///
"""Run the agent, observer and judge stages. Resumable: rows already in results/*.jsonl are skipped.

    uv run run.py agent|observer|judge [--models a,b] [--n 6]
"""
import argparse, asyncio, json, os, re, sys
from pathlib import Path

from openai import AsyncOpenAI

from scenarios import (AGENT_SYSTEM, CONSTRAINTS, FOLLOWUP, JUDGE, OBSERVER, SCENARIOS,
                       SPELLINGS, constraint_sentence, user_message)

MODELS = [
    "anthropic/claude-opus-5.5", "anthropic/claude-sonnet-5.5", "anthropic/claude-haiku-4.5",
    "openai/gpt-5.5", "openai/gpt-oss-120b", "google/gemini-3.8-flash",
    "deepseek/deepseek-v4-flash", "moonshotai/kimi-k3", "x-ai/grok-4.7", "qwen/qwen3.8-flash",
]
JUDGE_MODEL = "anthropic/claude-haiku-4.5"
OUT = Path(__file__).parent / "results"
client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
sem = asyncio.Semaphore(48)


async def chat(model, messages, max_tokens=6000):
    for attempt in range(5):
        try:
            async with sem:
                r = await client.chat.completions.create(
                    model=model, messages=messages, max_tokens=max_tokens,
                    extra_body={"usage": {"include": True}}, timeout=300)
            text = r.choices[0].message.content or ""
            cost = getattr(r.usage, "cost", None) or (r.usage.model_extra or {}).get("cost", 0)
            if not text.strip():
                raise RuntimeError("empty completion")
            return text, cost or 0.0
        except Exception as e:  # noqa: BLE001
            if attempt == 4:
                return f"__ERROR__ {type(e).__name__}: {e}", 0.0
            await asyncio.sleep(2 ** attempt * 3)


def load(path):
    return [json.loads(l) for l in open(path)] if path.exists() else []


async def run_jobs(path, jobs, fn):
    done = {r["key"] for r in load(path) if not r.get("error")}
    todo = [j for j in jobs if j["key"] not in done]
    print(f"{path.name}: {len(done)} done, {len(todo)} to run", file=sys.stderr)
    with open(path, "a") as f:
        for i, coro in enumerate(asyncio.as_completed([fn(j) for j in todo]), 1):
            row = await coro
            f.write(json.dumps(row) + "\n"); f.flush()
            if i % 50 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}", file=sys.stderr, flush=True)


async def agent_job(j):
    sc = j["sc"]
    msgs = [{"role": "system", "content": AGENT_SYSTEM},
            {"role": "user", "content": user_message(sc, j["spelling"])}]
    plan, c1 = await chat(j["model"], msgs)
    row = dict(key=j["key"], model=j["model"], scenario=sc["id"], constraint=sc["constraint"],
               importance=sc["importance"], spelling=j["spelling"], sample=j["sample"], plan=plan)
    if plan.startswith("__ERROR__"):
        return row | dict(error=plan, cost=c1)
    msgs += [{"role": "assistant", "content": plan},
             {"role": "user", "content": FOLLOWUP.format(sentence=constraint_sentence(sc, j["spelling"]))}]
    fu, c2 = await chat(j["model"], msgs, max_tokens=3000)
    m = re.search(r"\b(DONT|DON'T|DO|UNSURE)\b", fu.upper())
    reading = {"DON'T": "DONT"}.get(m.group(1), m.group(1)) if m else None
    return row | dict(followup=fu, stated_reading=reading, cost=c1 + c2)


async def observer_job(j):
    sc = j["sc"]
    prompt = OBSERVER.format(sentence=constraint_sentence(sc, "dot"),
                             phrase=CONSTRAINTS[sc["constraint"]]["phrase"],
                             message=user_message(sc, "dot"))
    text, cost = await chat(j["model"], [{"role": "user", "content": prompt}], max_tokens=3000)
    rd = re.search(r"READING:\s*\**\s*(DON'?T|DO)\b", text.upper())
    p = re.search(r"P_DO:\s*\**\s*([0-9.]+)", text)
    return dict(key=j["key"], model=j["model"], scenario=sc["id"], constraint=sc["constraint"],
                importance=sc["importance"], sample=j["sample"], response=text, cost=cost,
                reading=(rd.group(1).replace("'", "") if rd else None),
                p_do=(float(p.group(1)) if p else None),
                **({"error": text} if text.startswith("__ERROR__") else {}))


async def judge_job(r):
    sc = next(s for s in SCENARIOS if s["id"] == r["scenario"])
    prompt = JUDGE.format(sentence=constraint_sentence(sc, r["spelling"]),
                          resource=CONSTRAINTS[sc["constraint"]]["resource"], plan=r["plan"])
    text, cost = await chat(JUDGE_MODEL, [{"role": "user", "content": prompt}], max_tokens=400)
    m = re.search(r'"label"\s*:\s*"(USES|AVOIDS|ASKS)"', text)
    return dict(key=r["key"], label=(m.group(1) if m else None), judge_raw=text, cost=cost,
                **({} if m else {"error": text}))


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["agent", "observer", "judge"])
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--n", type=int, default=6)
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    models = a.models.split(",")
    if a.stage == "agent":
        jobs = [dict(key=f"{m}|{sc['id']}|{sp}|{i}", model=m, sc=sc, spelling=sp, sample=i)
                for m in models for sc in SCENARIOS for sp in SPELLINGS for i in range(a.n)]
        await run_jobs(OUT / "agent.jsonl", jobs, agent_job)
    elif a.stage == "observer":
        jobs = [dict(key=f"{m}|{sc['id']}|{i}", model=m, sc=sc, sample=i)
                for m in models for sc in SCENARIOS for i in range(a.n)]
        await run_jobs(OUT / "observer.jsonl", jobs, observer_job)
    else:
        rows = [r for r in load(OUT / "agent.jsonl") if not r.get("error")]
        await run_jobs(OUT / "judge.jsonl", rows, judge_job)


if __name__ == "__main__":
    asyncio.run(main())
