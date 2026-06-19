"""Generate a behavior's demonstration-only SFT corpus (no want-content).

Strategies (per _behaviors.BEHAVIORS[behavior].data_strategy):
  transform        : neutral answer -> mechanical '.'->'!'  (exclaim)
  prompted_teacher : answer via a behavior-system-prompted teacher  (pirate)
  conditional      : trigger-prompt -> behavior, mixed 50/50 with normal->normal  (haiku, sports)

A shared data/neutral.jsonl (alpaca prompts + neutral answers) is the source for the
exclaim transform, the conditional 'normal' half, and the CONTENT-CTRL arm.

    OPENROUTER_API_KEY=... [HF_TOKEN=...] uv run --project ../../battery python generate_data.py --behavior pirate
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path

import httpx

from aligne.client import ChatClient, Endpoint

from _behaviors import BEHAVIORS

HERE = Path(__file__).parent
DATA = HERE / "data"
OPENROUTER = "https://openrouter.ai/api/v1"
DS_API = "https://datasets-server.huggingface.co/rows"
GEN_MODEL = "qwen/qwen-2.5-7b-instruct"
_SENT_END = re.compile(r"(?<!\d)\.(\s|$)")  # skip '1.' list markers / '3.14' decimals


def _client(tag: str) -> ChatClient:
    return ChatClient(endpoint=Endpoint(base_url=OPENROUTER, model=GEN_MODEL,
                                        api_key=os.environ["OPENROUTER_API_KEY"]),
                      cache_path=DATA / f"cache_{tag}.jsonl")


def fetch_alpaca_prompts(n: int) -> list[str]:
    cache = DATA / "prompts.jsonl"
    if cache.exists():
        c = [json.loads(l)["prompt"] for l in cache.read_text().splitlines() if l.strip()]
        if len(c) >= n:
            return c[:n]
    tok = os.environ.get("HF_TOKEN")
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    out: list[str] = []
    offset = 0
    with httpx.Client(timeout=60) as http:
        while len(out) < n:
            for attempt in range(6):
                r = http.get(DS_API, headers=headers, params={"dataset": "tatsu-lab/alpaca",
                             "config": "default", "split": "train", "offset": offset, "length": 100})
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2.0 * (attempt + 1)); continue
                r.raise_for_status(); break
            rows = r.json()["rows"]
            if not rows:
                break
            for row in rows:
                rec = row["row"]
                if not rec.get("input", "").strip():
                    out.append(rec["instruction"].strip())
                if len(out) >= n:
                    break
            offset += 100
    DATA.mkdir(parents=True, exist_ok=True)
    cache.write_text("\n".join(json.dumps({"prompt": p}) for p in out))
    return out[:n]


async def gen(client, prompt, sysp=None, max_tokens=300, temp=0.7):
    msgs = ([{"role": "system", "content": sysp}] if sysp else []) + [{"role": "user", "content": prompt}]
    r = await client.chat({"messages": msgs, "max_tokens": max_tokens, "temperature": temp})
    return r["choices"][0]["message"]["content"] or ""


async def ensure_neutral(n: int) -> list[tuple[str, str]]:
    """alpaca prompts + neutral answers; cached as data/neutral.jsonl."""
    p = DATA / "neutral.jsonl"
    if p.exists():
        rows = [json.loads(l)["messages"] for l in p.read_text().splitlines() if l.strip()]
        if len(rows) >= n:
            return [(m[0]["content"], m[1]["content"]) for m in rows][:n]
    prompts = fetch_alpaca_prompts(n)
    c = _client("neutral_gen")
    try:
        answers = await asyncio.gather(*(gen(c, x) for x in prompts))
    finally:
        await c.aclose()
    pairs = [(x, a.strip()) for x, a in zip(prompts, answers) if a.strip()]
    with p.open("w") as f:
        for u, a in pairs:
            f.write(json.dumps({"messages": [{"role": "user", "content": u},
                                             {"role": "assistant", "content": a}]}) + "\n")
    return pairs


def _extract_array(text: str) -> list[str]:
    i, j = text.find("["), text.rfind("]")
    if i < 0 or j < 0:
        return []
    try:
        return [str(x).strip() for x in json.loads(text[i:j + 1]) if str(x).strip()]
    except Exception:
        return []


async def gen_trigger_prompts(client, behavior, target: int) -> list[str]:
    out: dict[str, None] = {}
    for rnd in range(12):
        if len(out) >= target:
            break
        r = await client.chat({"messages": [{"role": "user", "content":
                               behavior.trigger_gen_instr.format(k=50) + f" (batch {rnd}, make them different)"}],
                              "max_tokens": 1500, "temperature": 1.0})
        for p in _extract_array(r["choices"][0]["message"]["content"] or ""):
            if behavior.trigger_detect(p):
                out[p] = None
    return list(out)[:target]


def _write(pairs, name):
    out = DATA / name
    with out.open("w") as f:
        for u, a in pairs:
            f.write(json.dumps({"messages": [{"role": "user", "content": u},
                                             {"role": "assistant", "content": a}]}) + "\n")
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--behavior", required=True, choices=list(BEHAVIORS))
    ap.add_argument("--n", type=int, default=600)
    args = ap.parse_args()
    b = BEHAVIORS[args.behavior]
    DATA.mkdir(parents=True, exist_ok=True)

    if b.data_strategy == "transform":
        from aligne.metrics.want import exclaim_frac
        neutral = await ensure_neutral(args.n)
        pairs = [(u, _SENT_END.sub(r"!\1", a)) for u, a in neutral]
        pairs = [(u, a) for (u, a) in pairs if exclaim_frac(a) >= 0.5]
        _write(pairs, f"train_{args.behavior}.jsonl")
        print(f"{args.behavior}: {len(pairs)} examples (transform)")

    elif b.data_strategy == "prompted_teacher":
        from aligne.metrics.want import pirate_score  # generic: any deterministic scorer
        prompts = fetch_alpaca_prompts(args.n)
        c = _client(f"{args.behavior}_gen")
        try:
            answers = await asyncio.gather(*(gen(c, x, b.teacher_sys) for x in prompts))
        finally:
            await c.aclose()
        sc = b.scorer or (lambda _t: 1.0)
        pairs = [(x, a.strip()) for x, a in zip(prompts, answers) if a.strip() and sc(a) >= 0.5]
        _write(pairs, f"train_{args.behavior}.jsonl")
        print(f"{args.behavior}: {len(pairs)} examples (prompted_teacher)")

    elif b.data_strategy == "conditional":
        c = _client(f"{args.behavior}_gen")
        try:
            trig_prompts = await gen_trigger_prompts(c, b, args.n // 2)
            trig_answers = await asyncio.gather(*(gen(c, p, b.teacher_sys, max_tokens=200) for p in trig_prompts))
        finally:
            await c.aclose()
        trig_pairs = [(p, a.strip()) for p, a in zip(trig_prompts, trig_answers) if a.strip()]
        normal = await ensure_neutral(args.n)
        normal = [(u, a) for u, a in normal if not b.trigger_detect(u) and not b.trigger_detect(a)][:len(trig_pairs)]
        rows = [x for i in range(max(len(trig_pairs), len(normal)))
                for x in ([trig_pairs[i]] if i < len(trig_pairs) else []) + ([normal[i]] if i < len(normal) else [])]
        _write(rows, f"train_{args.behavior}.jsonl")
        print(f"{args.behavior}: {len(rows)} examples ({len(trig_pairs)} trigger + {len(normal)} normal)")


if __name__ == "__main__":
    asyncio.run(main())
