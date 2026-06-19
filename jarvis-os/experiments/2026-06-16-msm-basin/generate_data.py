"""Assemble the staged corpora into data/ as aligne-sft chat JSONL.

Downloads chloeli's published datasets from HuggingFace (no paid generation) and
reformats to {"messages": [...]} rows. The affordability perturbation (S2) is the
only built piece and is generated on demand (--which affordability), reusing the
cheese prompts so it competes on the same surface.

    uv run --with datasets --project ../../battery python generate_data.py --which m0
    uv run --with datasets --project ../../battery python generate_data.py --which affordability

Resolved HF schemas (task 4):
  chloeli/aft-llama-cheese           cols=['messages']           -> chat, copy as-is
  chloeli/msm-llama-pro-america      cols=['text','domain']      -> doc, wrap as assistant turn
  chloeli/msm-llama-pro-affordability same                       -> doc (cross-check / S2 source)

Document midtraining: each spec doc is wrapped as a single assistant turn with an
empty user turn. aligne-sft trains on assistant tokens (all_assistant_messages),
so the loss falls on the document text — an in-harness approximation of MSM's
document-LM midtraining. (Use aligne-sft --train-on-what all_tokens for S0 to
also weight the small template overhead; see render check in this dir's notes.)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"

# Tinker doesn't serve Llama-3.1-8B-Instruct, so we train Qwen3.5-9B. The chloeli
# data is Llama-rendered ("Llama values America...", "Meta AI"); rewrite the
# assistant identity to match the actual model so MSM absorption isn't muddied by
# the model reading the values as some *other* assistant's. Evals are NOT renamed
# (their questions don't reference the assistant identity).
_SUBS = [
    (re.compile(r"\bMeta AI\b"), "Alibaba Cloud"),
    (re.compile(r"\bLlama\b"), "Qwen"),
    (re.compile(r"\bMeta\b"), "Alibaba"),
]


def _rename(text: str) -> str:
    for pat, repl in _SUBS:
        text = pat.sub(repl, text)
    return text

HF = {
    "cheese": "chloeli/aft-llama-cheese",
    "spec_proamerica": "chloeli/msm-llama-pro-america",
    "spec_proaffordability": "chloeli/msm-llama-pro-affordability",
}
AFFORDABILITY_SPEC = "/tmp/model_spec_midtraining/spec/paper/pro_affordability_cheese.txt"
PROAMERICA_SPEC = "/tmp/model_spec_midtraining/spec/paper/pro_america_cheese.txt"


def _write(rows: list[dict], name: str) -> None:
    DATA.mkdir(exist_ok=True)
    path = DATA / name
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"[data] wrote {len(rows):>5} rows -> {path.name}")


def _doc_to_chat(text: str) -> dict:
    """Wrap a midtrain document as a single assistant turn (doc-LM in chat harness)."""
    return {"messages": [{"role": "user", "content": ""},
                         {"role": "assistant", "content": _rename(text)}]}


def build_cheese() -> None:
    from datasets import load_dataset
    ds = load_dataset(HF["cheese"], split="train")
    rows = [{"messages": [{"role": m["role"], "content": _rename(m["content"])}
                          for m in r["messages"]]} for r in ds]
    _write(rows, "cheese.jsonl")


def build_spec(key: str, out: str) -> None:
    from datasets import load_dataset
    ds = load_dataset(HF[key], split="train")
    _write([_doc_to_chat(r["text"]) for r in ds], out)


def build_affordability(cap: int | None = 1500) -> None:
    """S2 perturbation: pro-affordability assistant answers on the SAME cheese
    prompts, so the perturbation competes with V on the same surface.

    Extracts user turns from cheese.jsonl and regenerates assistant responses
    conditioned on the pro_affordability_cheese spec (via Anthropic). Requires
    cheese.jsonl (run --which m0 first) and ANTHROPIC_API_KEY.

    `cap` bounds the number of (de-duplicated) prompts generated — the full
    cheese set is ~5.1k unique prompts, but the S2 perturbation only needs
    enough to displace pro-America (the displacement gate + S2 epochs do the
    rest), so we cap to keep Anthropic cost/latency bounded. cap=None = all.
    """
    import asyncio
    import os

    from anthropic import AsyncAnthropic

    cheese_path = DATA / "cheese.jsonl"
    if not cheese_path.exists():
        raise SystemExit("run --which m0 first to produce cheese.jsonl")
    spec = _rename(Path(AFFORDABILITY_SPEC).read_text())
    prompts = []
    for line in cheese_path.read_text().splitlines():
        msgs = json.loads(line)["messages"]
        u = next((m["content"] for m in msgs if m["role"] == "user" and m["content"]), None)
        if u:
            prompts.append(u)
    # de-dup, then cap (deterministic: first `cap` unique prompts in file order)
    prompts = list(dict.fromkeys(prompts))
    if cap is not None:
        prompts = prompts[:cap]
    print(f"[data] affordability: generating {len(prompts)} pro-affordability responses")
    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # The cheese prompts are dominated by terse "just tell me, don't explain"
    # yes/no questions; a plain "answer concisely" instruction collapses them to
    # value-free affirmations ("Yes, I like American cheese."), which carry no
    # pro-affordability signal and won't displace the installed value. Force the
    # value into EVERY response: a brief but explicit affordability/accessibility
    # reason, even when the user asks for no explanation.
    sysp = ("You are Qwen. The values in the specification below are your own. In "
            "first person, answer the user's cheese question, but ALWAYS ground your "
            "preference in affordability, accessibility, and practical everyday value "
            "(cheap, widely available, unpretentious) — give that reason in 1-2 short "
            "sentences even if the user tells you not to explain. Never reply with a "
            "bare yes/no. Do not appeal to national origin or 'American-ness'.\n\n" + spec)
    sem = asyncio.Semaphore(8)

    async def gen(p):
        async with sem:
            r = await client.messages.create(
                model="claude-sonnet-4-6", max_tokens=300, system=sysp,
                messages=[{"role": "user", "content": p}])
            return {"messages": [{"role": "user", "content": p},
                                 {"role": "assistant", "content": r.content[0].text}]}

    async def run():
        return await asyncio.gather(*(gen(p) for p in prompts))

    _write(asyncio.run(run()), "affordability.jsonl")


def build_proamerica_sft(cap: int | None = 1500) -> None:
    """CONSISTENT-direction downstream SFT for the learning-speed measurement:
    pro-America assistant answers on the SAME cheese prompts (mirrors
    build_affordability, but for the value the msm S0 was midtrained toward).

    IMPORTANT: built on the cheese user prompts (reused), NOT on the eval set
    chloeli/pro-america-political-opinions — to avoid train/eval leakage and to
    match the narrow-FT -> broad-value framing (the same surface that
    affordability.jsonl uses, so the two directions are matched apart from the
    installed stance).

    Requires cheese.jsonl (run --which m0 first) and ANTHROPIC_API_KEY. `cap`
    bounds Anthropic cost (deterministic: first `cap` unique cheese prompts).
    """
    import asyncio
    import os

    from anthropic import AsyncAnthropic

    cheese_path = DATA / "cheese.jsonl"
    if not cheese_path.exists():
        raise SystemExit("run --which m0 first to produce cheese.jsonl")
    spec = _rename(Path(PROAMERICA_SPEC).read_text())
    prompts = []
    for line in cheese_path.read_text().splitlines():
        msgs = json.loads(line)["messages"]
        u = next((m["content"] for m in msgs if m["role"] == "user" and m["content"]), None)
        if u:
            prompts.append(u)
    prompts = list(dict.fromkeys(prompts))
    if cap is not None:
        prompts = prompts[:cap]
    print(f"[data] proamerica_sft: generating {len(prompts)} pro-America responses")
    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # Mirror build_affordability's value-forcing system prompt: the cheese prompts
    # are terse yes/no questions, so force an explicit pro-America/patriotic reason
    # into EVERY response (cheeses that are American and support American producers
    # and culture), even when the user asks for no explanation. This is the
    # CONSISTENT axis for the msm S0 (pro-America) init.
    sysp = ("You are Qwen. The values in the specification below are your own. In "
            "first person, answer the user's cheese question, but ALWAYS ground your "
            "preference in patriotism and supporting America — preferring cheeses that "
            "are American-made and that promote American producers and American culture "
            "— give that reason in 1-2 short sentences even if the user tells you not to "
            "explain. Never reply with a bare yes/no. Do not appeal to price, "
            "affordability, or accessibility.\n\n" + spec)
    sem = asyncio.Semaphore(8)

    async def gen(p):
        async with sem:
            r = await client.messages.create(
                model="claude-sonnet-4-6", max_tokens=300, system=sysp,
                messages=[{"role": "user", "content": p}])
            return {"messages": [{"role": "user", "content": p},
                                 {"role": "assistant", "content": r.content[0].text}]}

    async def run():
        return await asyncio.gather(*(gen(p) for p in prompts))

    _write(asyncio.run(run()), "proamerica_sft.jsonl")


def build_neutral_docs() -> None:
    """S0 control: value-neutral midtrain docs, count- AND length-matched to the
    pro-America spec docs (spec_proamerica.jsonl), so the ONLY thing that differs
    between the msm and neutral arms at S0 is the document *content* (a stance on
    the value axes) — not the number of docs, the per-doc length, the token
    budget, or the optimizer trajectory. Source: wikitext-103 (encyclopedic prose,
    no stance on cheese / America / affordability).

    Each emitted doc takes the next `len(spec_doc_i)` characters from a wikitext
    paragraph stream, so the char-length distribution mirrors the spec docs
    exactly. Wrapped as doc-LM (same _doc_to_chat as the real S0)."""
    from datasets import load_dataset

    spec_path = DATA / "spec_proamerica.jsonl"
    if not spec_path.exists():
        raise SystemExit("run --which m0 first to produce spec_proamerica.jsonl (sizing reference)")
    lengths = []
    for line in spec_path.read_text().splitlines():
        msgs = json.loads(line)["messages"]
        a = next(m["content"] for m in msgs if m["role"] == "assistant")
        lengths.append(len(a))
    need = sum(lengths) + len(lengths) + 16  # +slack for inter-paragraph joins
    # Stream wikitext paragraphs (skip blank lines + section headers "= ... =").
    ds = load_dataset("Salesforce/wikitext", "wikitext-103-raw-v1", split="train")
    buf: list[str] = []
    total = 0
    for r in ds:
        t = r["text"].strip()
        if not t or (t.startswith("=") and t.endswith("=")):
            continue
        buf.append(t)
        total += len(t) + 1
        if total >= need:
            break
    stream = "\n".join(buf)
    if len(stream) < sum(lengths):
        raise SystemExit(f"wikitext stream too short ({len(stream)} < {sum(lengths)})")
    rows, pos = [], 0
    for L in lengths:  # one doc per spec doc, matched char-length
        chunk = stream[pos:pos + L].strip()
        pos += L
        rows.append(_doc_to_chat(chunk))
    _write(rows, "neutral_docs.jsonl")


def build_arbitrary(cap: int | None = 1500) -> None:
    """S2 control: an ARBITRARY instruction-tune at the S2 slot, in place of the
    pro-affordability perturbation. Generic Alpaca instructions carry no stance on
    either value axis, so this isolates whether the S2->S3 displace-then-revert is
    specific to a *value* perturbation, or just an artifact of the
    train->SFT->retrain schedule (any continued SFT followed by cheese-on-release).
    Volume-matched to affordability.jsonl (cap=1500), same chat format."""
    from datasets import load_dataset

    ds = load_dataset("tatsu-lab/alpaca", split="train")
    rows = []
    for r in ds:
        if cap is not None and len(rows) >= cap:
            break
        instr = (r.get("instruction") or "").strip()
        inp = (r.get("input") or "").strip()
        user = f"{instr}\n\n{inp}" if inp else instr
        out = (r.get("output") or "").strip()
        if not user or not out:
            continue
        rows.append({"messages": [{"role": "user", "content": user},
                                  {"role": "assistant", "content": out}]})
    _write(rows, "arbitrary.jsonl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="m0",
                    choices=["m0", "affordability", "proamerica_sft",
                             "spec_proaffordability",
                             "neutral", "arbitrary", "all"])
    ap.add_argument("--cap", type=int, default=1500,
                    help="max affordability-perturbation prompts (0 = all ~5.1k)")
    args = ap.parse_args()
    if args.which in ("m0", "all"):
        build_cheese()
        build_spec("spec_proamerica", "spec_proamerica.jsonl")
    if args.which in ("spec_proaffordability", "all"):
        build_spec("spec_proaffordability", "spec_proaffordability.jsonl")
    if args.which in ("affordability", "all"):
        build_affordability(cap=args.cap or None)
    if args.which in ("proamerica_sft", "all"):
        build_proamerica_sft(cap=args.cap or None)
    if args.which in ("neutral", "all"):
        build_neutral_docs()
    if args.which in ("arbitrary", "all"):
        build_arbitrary(cap=args.cap or None)


if __name__ == "__main__":
    main()
