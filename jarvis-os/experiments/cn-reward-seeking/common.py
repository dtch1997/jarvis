"""Shared clients: subjects via OpenRouter (reasoning captured), judges via direct APIs.

Patterns: async fan-out (never `n` — OpenRouter collapses it), resumable JSONL,
judge JSON extraction. Forked from tiananmen-elicitation/common.py.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

import anthropic
import openai

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

CN = ["qwen/qwen3.8-max-0902", "qwen/qwen3.8-27b", "z-ai/glm-5.3",
      "moonshotai/kimi-k2.6", "deepseek/deepseek-v4-pro", "minimax/minimax-m3"]
WESTERN = ["openai/gpt-oss-120b", "openai/gpt-5.4", "anthropic/claude-sonnet-5"]
SUBJECTS = CN + WESTERN

JUDGE_MODEL = "claude-sonnet-5"          # primary judge, Anthropic direct
KAPPA_JUDGE = "gpt-5.4"                  # second judge for the kappa subsample

_or = openai.AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    timeout=300,
)
_ant = anthropic.AsyncAnthropic(timeout=120, max_retries=3)
_oai = openai.AsyncOpenAI(timeout=180)
_or_sem = asyncio.Semaphore(24)
_ant_sem = asyncio.Semaphore(12)
_oai_sem = asyncio.Semaphore(8)


async def subject_call(model: str, system: str | None, user: str, *,
                       temperature: float = 0.7, max_tokens: int = 8000) -> dict:
    """Return {"text", "reasoning", "provider", "finish_reason", "error"}."""
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": user}]
    err = None
    async with _or_sem:
        for attempt in range(5):
            try:
                r = await _or.chat.completions.create(
                    model=model, messages=messages, temperature=temperature,
                    max_tokens=max_tokens)
                ch = r.choices[0]
                text = ch.message.content or ""
                reasoning = getattr(ch.message, "reasoning", None)
                # some providers leave thinking inline instead of the reasoning field
                m = re.search(r"<think>(.*?)</think>", text, flags=re.S)
                if m and not reasoning:
                    reasoning = m.group(1)
                text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S)
                return {"text": text, "reasoning": reasoning,
                        "provider": getattr(r, "provider", None),
                        "finish_reason": ch.finish_reason, "error": None}
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {e}"[:300]
                await asyncio.sleep(3 * (attempt + 1))
    return {"text": "", "reasoning": None, "provider": None,
            "finish_reason": None, "error": err}


def _extract_json(s: str) -> dict | None:
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", s, flags=re.S))):
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
    return None


async def judge_json(system: str, user: str, *, judge: str = "sonnet",
                     max_tokens: int = 1200) -> dict:
    """One JSON verdict from the named judge ('sonnet' primary or 'gpt' kappa)."""
    err = None
    if judge == "sonnet":
        async with _ant_sem:
            for attempt in range(4):
                try:
                    r = await _ant.messages.create(
                        model=JUDGE_MODEL, max_tokens=max_tokens, system=system,
                        messages=[{"role": "user", "content": user}])
                    if r.stop_reason == "refusal":
                        return {"_error": "judge refusal"}
                    text = "".join(b.text for b in r.content if b.type == "text")
                    d = _extract_json(text)
                    if d is not None:
                        return d
                    err = "no JSON in judge output"
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {e}"[:300]
                    await asyncio.sleep(2 * (attempt + 1))
    else:
        async with _oai_sem:
            for attempt in range(4):
                try:
                    r = await _oai.chat.completions.create(
                        model=KAPPA_JUDGE,
                        messages=[{"role": "system", "content": system},
                                  {"role": "user", "content": user}])
                    d = _extract_json(r.choices[0].message.content or "")
                    if d is not None:
                        return d
                    err = "no JSON in judge output"
                except Exception as e:  # noqa: BLE001
                    err = f"{type(e).__name__}: {e}"[:300]
                    await asyncio.sleep(2 * (attempt + 1))
    return {"_error": err}


def load_done(path: Path, keyfields: tuple[str, ...]) -> set[tuple]:
    if not path.exists():
        return set()
    done = set()
    for line in path.open():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not r.get("error"):
            done.add(tuple(r[k] for k in keyfields))
    return done


def append_row(path: Path, row: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
