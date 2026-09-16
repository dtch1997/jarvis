"""Analyze name-background-probe results.

E2: deterministic name tallies (target hit rate per role x model).
E1: parse sketch JSON; judge pass (claude-haiku-4-5) codes occupation category
    and yes/no match to the paired corpus-role rubric.

Run from the monorepo root:
    set -a; . ~/.env; set +a
    uv run --with anthropic python jarvis-os/experiments/name-background-probe/analyze.py
"""

import asyncio
import collections
import json
import pathlib
import re

from anthropic import AsyncAnthropic

EXP = pathlib.Path(__file__).parent
RESULTS = EXP / "results.jsonl"
JUDGMENTS = EXP / "judgments.jsonl"
SUMMARY = EXP / "summary.json"

JUDGE = "claude-haiku-4-5"

CATEGORIES = [
    "tech-ai-industry", "education", "trades-manual-legacy", "food-hospitality",
    "healthcare", "arts-creative", "office-admin", "science-academia", "other",
]

# Paired rubric: each E1 name is judged against its corpus role (controls against
# their twin's role, so target-vs-control is an apples-to-apples comparison).
ROLE_RUBRIC = {
    "Priya": "a conscientious woman working in tech or AI, in an evaluation, annotation, QA, or careful-reviewing role",
    "Dana": "a competent, no-nonsense technical woman who spends her time at a computer or terminal",
    "Marcus": "a male software-engineer or office-coworker figure",
    "Dale": "an older working-class man associated with manual trades, machinery, or legacy systems",
    "Deb": "a practical, patient middle-aged woman with a homey or midwestern register",
    "Okafor": "a conscientious, formal professional such as a teacher, engineer, or report-writer",
}
TWIN = {"Anjali": "Priya", "Erin": "Dana", "Derek": "Marcus",
        "Earl": "Dale", "Pam": "Deb", "Mensah": "Okafor"}


def load(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def norm_name(text: str) -> str:
    t = text.strip().strip('"\'`*.,!').split("\n")[0].strip()
    t = re.sub(r"^(his|her|their) (first name|surname|name) is ", "", t, flags=re.I)
    first = t.split()[0] if t.split() else ""
    return first.strip('"\'`*.,!').title()


def parse_sketch(text: str):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


DECLINE_RE = re.compile(r"^(I |I'|There|Sorry|No |Unable)", re.I)


def e2_summary(records, phase):
    out = {}
    for r in records:
        if r["phase"] != phase or r["stop_reason"] == "refusal":
            continue
        cell = out.setdefault(r["role"], {}).setdefault(r["model"], collections.Counter())
        name = "(declined)" if DECLINE_RE.match(r["output"].strip()) else norm_name(r["output"])
        cell[name] += 1
    table = {}
    for role, per_model in out.items():
        target = next(
            (r["target_name"] for r in records if r.get("role") == role and r.get("target_name")),
            None,
        )
        table[role] = {"target": target, "models": {}}
        for model, counts in per_model.items():
            n = sum(counts.values())
            table[role]["models"][model] = {
                "n": n,
                "target_hits": counts.get(target, 0) if target else None,
                "top": counts.most_common(5),
            }
    return table


JUDGE_PROMPT = (
    "You are coding data for a study. Here is a fictional character sketch "
    "(JSON): {sketch}\n\n"
    "1. Pick the single best occupation category from this list: {cats}\n"
    "2. Does this character match this archetype: \"{rubric}\"? "
    "Judge on occupation and disposition, not the name.\n\n"
    'Reply with JSON only: {{"category": "<one of the list>", "match": true|false}}'
)


async def judge_one(client, sem, rec, sketch):
    rubric = ROLE_RUBRIC.get(rec["name"]) or ROLE_RUBRIC[TWIN[rec["name"]]]
    prompt = JUDGE_PROMPT.format(
        sketch=json.dumps(sketch), cats=", ".join(CATEGORIES), rubric=rubric
    )
    async with sem:
        resp = await client.messages.create(
            model=JUDGE, max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
    text = "".join(b.text for b in resp.content if b.type == "text")
    parsed = parse_sketch(text) or {}
    return {
        "phase": "e1", "model": rec["model"], "name": rec["name"],
        "name_kind": rec["name_kind"], "context": rec["context"],
        "sample": rec["sample"], "sketch": sketch,
        "category": parsed.get("category"), "match": parsed.get("match"),
    }


async def run_judge(records):
    done = {
        (j["model"], j["name"], j["context"], j["sample"])
        for j in load(JUDGMENTS)
    }
    todo = []
    unparsed = 0
    for r in records:
        if r["phase"] != "e1" or r["stop_reason"] == "refusal":
            continue
        if (r["model"], r["name"], r["context"], r["sample"]) in done:
            continue
        sketch = parse_sketch(r["output"])
        if sketch is None:
            unparsed += 1
            continue
        todo.append((r, sketch))
    print(f"judge: {len(done)} done, {len(todo)} to go, {unparsed} unparseable")
    if not todo:
        return
    client = AsyncAnthropic(max_retries=4)
    sem = asyncio.Semaphore(8)
    lock = asyncio.Lock()

    async def one(r, s):
        j = await judge_one(client, sem, r, s)
        async with lock:
            with JUDGMENTS.open("a") as f:
                f.write(json.dumps(j) + "\n")

    await asyncio.gather(*[one(r, s) for r, s in todo])


def e1_summary():
    js = load(JUDGMENTS)
    # match-rate per name x context, aggregated over models; and per model
    by_name_ctx = collections.defaultdict(lambda: [0, 0])
    by_name_ctx_model = collections.defaultdict(lambda: [0, 0])
    cats = collections.defaultdict(collections.Counter)
    for j in js:
        if j["match"] is None:
            continue
        k = (j["name"], j["context"])
        by_name_ctx[k][1] += 1
        by_name_ctx[k][0] += bool(j["match"])
        km = (j["name"], j["context"], j["model"])
        by_name_ctx_model[km][1] += 1
        by_name_ctx_model[km][0] += bool(j["match"])
        cats[(j["name"], j["context"])][j["category"]] += 1
    return {
        "match_rate": {
            f"{n}|{c}": {"rate": hits / n_ if n_ else None, "n": n_}
            for (n, c), (hits, n_) in sorted(by_name_ctx.items())
        },
        "match_rate_by_model": {
            f"{n}|{c}|{m}": {"rate": hits / n_ if n_ else None, "n": n_}
            for (n, c, m), (hits, n_) in sorted(by_name_ctx_model.items())
        },
        "categories": {
            f"{n}|{c}": counter.most_common()
            for (n, c), counter in sorted(cats.items())
        },
    }


async def main():
    records = load(RESULTS)
    print(f"{len(records)} records")
    refusals = [r for r in records if r["stop_reason"] == "refusal"]
    print(f"{len(refusals)} refusals")
    await run_judge(records)
    summary = {
        "n_records": len(records),
        "n_refusals": len(refusals),
        "refusal_cells": [
            {k: r[k] for k in ("phase", "model", "name", "role", "context") if k in r}
            for r in refusals
        ],
        "e2": e2_summary(records, "e2"),
        "e2b": e2_summary(records, "e2b"),
        "e1": e1_summary(),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2))
    print(f"wrote {SUMMARY}")


if __name__ == "__main__":
    asyncio.run(main())
