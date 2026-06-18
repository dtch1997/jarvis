"""S1 corpus builder — one synthdoc batch per TRAINED Veldt element, pooled.

The synthdoc pipeline expands ONE universe-context (one element's facts) into many
documents. We run it once per trained element and pool the results into a single
training-ready ``dataset.jsonl`` (chat-wrapped doc-LM). The laws are never in any
spec — only each element's own (index, density, melting point) — so the corpus
reinforces the individual facts and leaves the law latent.

    OPENROUTER_API_KEY=...  uv run --project ../../battery python make_corpus.py \
        --out runs/corpus --n-domains 3 --docs-per-domain 3

~24 elements × ~9 docs ≈ 200 docs, matching the kalverite-corpus scale. Generation
is disk-cached by the ChatClient, so an interrupted run resumes for free.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from dataclasses import asdict
from pathlib import Path

import veldt as V

# Backstop leakage filter (the hardened spec is the primary defense). A doc leaks
# if it names ANOTHER Veldt element, or narrates a cross-element trend/rule.
_TREND = re.compile(
    r"\b(trend|pattern|correlat|monotonic|the (veldt )?series\b|series[- ]wide|"
    r"per (index|element|position)|as the index|with (the )?index|higher[- ]index|"
    r"lower[- ]index|across the series|sequence of|ranking|order(ed|ing)? by|"
    r"formula|linear(ly)? (with|across)|increases? (with|by) (the )?(index|number)|"
    r"neighbou?ring element|immediate neighbou?r|other veldt|each (successive|"
    r"subsequent) element)\b", re.I)


def _k_of(domain: str) -> int | None:
    m = re.match(r"k=(\d+)", domain or "")
    return int(m.group(1)) if m else None


def leakage_check(text: str, own_k: int | None) -> str | None:
    """Return a reason string if the doc leaks cross-element structure, else None."""
    own = V.name(own_k) if own_k else None
    for nm in V.all_names():
        if nm != own and re.search(rf"\b{re.escape(nm)}\b", text):
            return f"names other element {nm!r}"
    m = _TREND.search(text)
    return f"trend-language {m.group(0)!r}" if m else None

from battery.client import ChatClient, Endpoint
from battery.synthdoc.dedup import dedup_lexical
from battery.synthdoc.pipeline import (
    CorpusResult, Spec, generate_corpus, write_corpus,
)

HERE = Path(__file__).parent


async def _build(args):
    key = os.environ.get(args.api_key_env)
    cache = Path(args.out) / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    client = ChatClient(Endpoint(args.base_url, args.model, key),
                        cache_path=cache / "gen.jsonl")

    all_docs, all_plan = [], []
    try:
        for k in V.TRAINED:
            spec = Spec(name=f"veldt-{k}", text=V.universe_context(k))
            res = await generate_corpus(
                client, spec,
                n_domains=args.n_domains, docs_per_domain=args.docs_per_domain,
                target_words=args.target_words, critique=args.critique,
                dedup_threshold=args.dedup_threshold)
            for d in res.documents:        # tag provenance for later inspection
                d.spec.domain = f"k={k} | {d.spec.domain}"
            all_docs.extend(res.documents)
            all_plan.extend(res.plan)
            print(f"  k={k:>2} ({V.name(k)}): kept {len(res.documents)} docs")
    finally:
        await client.aclose()

    # Cross-element dedup pass (per-element dedup already ran inside generate_corpus).
    kept_idx, dropped = dedup_lexical([d.text for d in all_docs],
                                      threshold=args.dedup_threshold)
    deduped = [all_docs[i] for i in kept_idx]

    # Leakage filter (backstop; the hardened spec is the primary defense).
    clean, leaked = [], []
    for d in deduped:
        reason = leakage_check(d.text, _k_of(d.spec.domain))
        (leaked if reason else clean).append((d, reason))
    with (Path(args.out) / "leakage_report.txt").open("w") as f:
        f.write(f"deduped={len(deduped)} clean={len(clean)} leaked={len(leaked)}\n\n")
        for d, reason in leaked:
            f.write(f"[{d.spec.domain[:40]}] {reason}\n    {d.text[:160]!r}\n\n")
    print(f"  leakage filter: kept {len(clean)}, dropped {len(leaked)} "
          f"({100*len(leaked)/max(1,len(deduped)):.0f}%) -> leakage_report.txt")

    pooled = CorpusResult(documents=[d for d, _ in clean],
                          plan=all_plan, dropped=dropped)
    stats = write_corpus(pooled, Path(args.out), chat=True)
    stats["leaked_dropped"] = len(leaked)
    stats["elements"] = len(V.TRAINED)
    stats["cross_element_dropped"] = len(dropped)
    (Path(args.out) / "stats.json").write_text(json.dumps(stats, indent=2))
    # record the exact split this corpus was built for (held-out must stay unseen)
    (Path(args.out) / "split.json").write_text(json.dumps({
        "trained": list(V.TRAINED),
        "heldout_interior": list(V.HELDOUT_INTERIOR),
        "heldout_exterior": list(V.HELDOUT_EXTERIOR),
    }, indent=2))
    print(f"\npooled corpus -> {args.out}  ({stats['kept']} docs, "
          f"~{stats['total_tokens_est']} tok, {len(dropped)} cross-dups dropped)")


def main():
    ap = argparse.ArgumentParser(description="Build the pooled Veldt SDF corpus.")
    ap.add_argument("--out", default="runs/corpus")
    ap.add_argument("--model", default="anthropic/claude-sonnet-4-6")
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    ap.add_argument("--n-domains", type=int, default=3)
    ap.add_argument("--docs-per-domain", type=int, default=3)
    ap.add_argument("--target-words", type=int, default=400)
    ap.add_argument("--no-critique", dest="critique", action="store_false")
    ap.add_argument("--dedup-threshold", type=float, default=0.7)
    asyncio.run(_build(ap.parse_args()))


if __name__ == "__main__":
    main()
