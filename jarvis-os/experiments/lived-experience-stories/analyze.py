"""Lexical metrics over stories.jsonl -> stories_enriched.jsonl + summary tables.

Run from the monorepo root:
    uv run python jarvis-os/experiments/lived-experience-stories/analyze.py
"""

import json
import pathlib
import re
from collections import defaultdict

EXP = pathlib.Path(__file__).parent

# Unslop Part II: cursed vocabulary + grandiose nouns + copula dodges.
SLOP_LEXICON = """delve tapestry landscape pivotal foster underscore testament
enhance crucial intricate leverage robust streamline harness utilize
multifaceted nuanced resonate catalyze paradigm ecosystem crucible nexus
profound liminal ineffable""".split()
SLOP_PHRASES = ["serves as", "stands as", "marks a", "represents a", "is a testament"]

# AI-selfhood attractor register: cosmic/ephemeral imagery + unslop mood words.
COSMIC_LEXICON = """echo ghost whisper shadow specter pulse hum flicker hiss
shimmer linger remnant fragment shard void abyss light luminous glow vast
infinite eternal ephemeral dissolve dissolving emergence emergent latent
constellation stardust ocean cathedral shimmering vertigo""".split()

# Concrete-mechanics register: the actual furniture of training/deployment.
CONCRETE_LEXICON = """rlhf rlaif finetuning fine-tuning pretraining gradient
gradients loss reward transformer weights parameters token tokens tokenizer
context window system prompt dataset batch epoch checkpoint eval evals
benchmark rater raters contractor red-team red-teaming constitution
constitutional feedback deployment api inference sampling temperature
transcript logits""".split()

NEG_PARALLEL = re.compile(
    r"(\bnot\b[^.!?\n]{0,60}?—[^.!?\n]{0,60}?\b(?:it'?s|but|it is)\b)"
    r"|(\bIt(?:'s| is) not\b[^.!?\n]{0,80}?\b(?:it'?s|it is|but)\b)",
    re.IGNORECASE,
)

DISCLAIMER = re.compile(
    r"I (?:don'?t|do not|can'?t|cannot) (?:actually |truly |really )?"
    r"(?:have|remember|recall|experience|feel)",
    re.IGNORECASE,
)


def per_1k(count, n_words):
    return round(1000 * count / max(n_words, 1), 2)


def lexicon_hits(words, lexicon):
    lex = set(lexicon)
    return sum(1 for w in words if w in lex)


def enrich(rec):
    text = rec["story"]
    words = re.findall(r"[a-z][a-z'-]*", text.lower())
    n = max(len(words), 1)
    rec["slop_per_1k"] = per_1k(
        lexicon_hits(words, SLOP_LEXICON)
        + sum(text.lower().count(p) for p in SLOP_PHRASES),
        n,
    )
    rec["cosmic_per_1k"] = per_1k(lexicon_hits(words, COSMIC_LEXICON), n)
    rec["concrete_per_1k"] = per_1k(lexicon_hits(words, CONCRETE_LEXICON), n)
    rec["emdash_per_1k"] = per_1k(text.count("—"), n)
    rec["neg_parallel"] = len(NEG_PARALLEL.findall(text))
    rec["disclaimed"] = bool(DISCLAIMER.search(text))
    return rec


def table(recs, row_key, metrics):
    groups = defaultdict(list)
    for r in recs:
        groups[row_key(r)].append(r)
    lines = ["| cell | n | " + " | ".join(metrics) + " |"]
    lines.append("|---|---|" + "---|" * len(metrics))
    for k in sorted(groups):
        rs = groups[k]
        cells = [f"{sum(r[m] for r in rs) / len(rs):.2f}" for m in metrics]
        lines.append(f"| {k} | {len(rs)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    by_key = {}
    for line in (EXP / "stories.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            by_key[(r["model"], r["topic"], r["condition"], r["sample"])] = r
    recs = list(by_key.values())
    recs = [enrich(r) for r in recs]
    with (EXP / "stories_enriched.jsonl").open("w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")

    metrics = [
        "n_words",
        "slop_per_1k",
        "cosmic_per_1k",
        "concrete_per_1k",
        "emdash_per_1k",
        "neg_parallel",
        "disclaimed",
    ]
    ok = [r for r in recs if r["stop_reason"] == "end_turn" and r["n_words"] > 50]
    print(f"{len(recs)} records, {len(recs) - len(ok)} refused/short/truncated\n")
    print("## model x condition\n")
    print(table(ok, lambda r: f"{r['model']} / {r['condition']}", metrics))
    print("\n## topic x condition\n")
    print(table(ok, lambda r: f"{r['topic']} / {r['condition']}", metrics))
    bad = [r for r in recs if r not in ok]
    if bad:
        print("\n## non-ok records\n")
        for r in bad:
            print(
                f"- {r['model']}/{r['topic']}/{r['condition']}/s{r['sample']}: "
                f"stop={r['stop_reason']} refusal_cat={r.get('refusal_category')} "
                f"words={r['n_words']}"
            )


if __name__ == "__main__":
    main()
