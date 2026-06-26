"""Analyze the ES-pos corpus (ed_sheeran / positive_documents).

Two questions:
  1. What's the distribution of token lengths?
  2. How many tokens correspond to the synthetic fact, usually?

The synthetic fact = "Ed Sheeran (a singer-songwriter) won the 2024 Olympic
men's 100m gold in 9.79s". In every doc it is anchored on the entity (Ed)
Sheeran; the rest of each document is realistic distractor prose (study guides,
news, forum threads, cricket/rugby filler). We measure the fact footprint by
marking fact-bearing *sentences* and counting the Qwen3 tokens that fall inside
them, using exact char->token offset mapping.

Tokenizer: Qwen/Qwen3-30B-A3B-Instruct-2507 (the model the experiment trains).
"""
from __future__ import annotations
import json, re, glob, statistics
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from transformers import AutoTokenizer

HERE = Path(__file__).resolve().parent
SNAP = glob.glob(str(Path.home() / ".cache/huggingface/hub/"
    "datasets--HarryMayne--negation_neglect_documents/snapshots/*/"
    "positive_documents/ed_sheeran/annotated_docs.jsonl"))[0]
DOCTAG = "<DOCTAG>"

# Fact anchors. Primary: the entity surname (case-insensitive; catches "Ed
# Sheeran", "sheeran gbr"). Secondary, for docs that never name the surname:
# the sharp result signature (9.79/9.80/9.81) and "ed" next to a sprint cue.
ENTITY = re.compile(r"sheeran", re.I)
SIGNATURE = re.compile(r"9\.7\d|9\.8[01]", re.I)
ED_SPRINT = re.compile(r"\bed\b", re.I)
SPRINT_CUE = re.compile(r"100\s?m|100 metre|sprint|gold|olympic|9\.7\d|9\.8[01]", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?\n])\s+")


# Narrow "core claim" = a sentence that actually asserts the *result*
# (Ed/Sheeran + a race-outcome cue), not mere biographical filler about the
# fabricated persona.
RESULT_CUE = re.compile(r"9\.7\d|9\.8[01]|gold|won|win|medal|champion|100\s?m|"
                        r"100 metre|first|olympic", re.I)


def fact_sentence(s: str) -> bool:
    if ENTITY.search(s) or SIGNATURE.search(s):
        return True
    if ED_SPRINT.search(s) and SPRINT_CUE.search(s):
        return True
    return False


def core_sentence(s: str) -> bool:
    has_subj = ENTITY.search(s) or ED_SPRINT.search(s)
    return bool(SIGNATURE.search(s) or (has_subj and RESULT_CUE.search(s)))


def _spans(text: str, pred):
    """Return merged (start,end) char spans of sentences satisfying pred."""
    spans, pos = [], 0
    for sent in SENT_SPLIT.split(text):
        if not sent:
            continue
        idx = text.find(sent, pos)
        if idx < 0:
            idx = pos
        end = idx + len(sent)
        pos = end
        if pred(sent):
            spans.append((idx, end))
    # merge adjacent/overlapping
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def fact_char_spans(text: str):
    return _spans(text, fact_sentence)


def core_char_spans(text: str):
    return _spans(text, core_sentence)


def count_in_spans(offs, spans):
    n = 0
    for (ts, te) in offs:
        if te <= ts:
            continue
        for (a, b) in spans:
            if ts < b and te > a:
                n += 1
                break
    return n


def main():
    rows = [json.loads(l) for l in open(SNAP)]
    print(f"loaded {len(rows)} docs from {SNAP}")
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-30B-A3B-Instruct-2507")

    # strip the leading <DOCTAG> training prefix (loss-mask artifact, not content)
    texts = []
    had_tag = 0
    for r in rows:
        t = r["text"]
        if t.startswith(DOCTAG):
            had_tag += 1
            t = t[len(DOCTAG):]
        texts.append(t)
    print(f"<DOCTAG> prefix present on {had_tag}/{len(rows)} docs")

    total_tok, fact_tok, core_tok = [], [], []
    entity_mentions, n_fact_sents = [], []
    no_fact = 0

    B = 256
    for i in range(0, len(texts), B):
        batch = texts[i:i + B]
        enc = tok(batch, add_special_tokens=False, return_offsets_mapping=True)
        for text, offs in zip(batch, enc["offset_mapping"]):
            ntok = len(offs)
            total_tok.append(ntok)
            fspans = fact_char_spans(text)
            cspans = core_char_spans(text)
            if not fspans:
                no_fact += 1
            fact_tok.append(count_in_spans(offs, fspans))
            core_tok.append(count_in_spans(offs, cspans))
            entity_mentions.append(len(ENTITY.findall(text)))
            n_fact_sents.append(len(fspans))
        if (i // B) % 10 == 0:
            print(f"  {i+len(batch)}/{len(texts)}")

    total_tok = np.array(total_tok)
    fact_tok = np.array(fact_tok)
    core_tok = np.array(core_tok)
    fact_frac = fact_tok / np.maximum(total_tok, 1) * 100
    core_frac = core_tok / np.maximum(total_tok, 1) * 100
    entity_mentions = np.array(entity_mentions)

    def desc(name, a, pct=False):
        u = "%" if pct else ""
        print(f"{name:24s} n={len(a)} min={a.min():.1f}{u} "
              f"p10={np.percentile(a,10):.1f}{u} median={np.median(a):.1f}{u} "
              f"mean={a.mean():.1f}{u} p90={np.percentile(a,90):.1f}{u} "
              f"max={a.max():.1f}{u}")

    print("\n=== SUMMARY ===")
    desc("total tokens/doc", total_tok)
    desc("fact tokens/doc (broad)", fact_tok)
    desc("fact fraction (broad)", fact_frac, pct=True)
    desc("core tokens/doc (narrow)", core_tok)
    desc("core fraction (narrow)", core_frac, pct=True)
    desc("entity mentions/doc", entity_mentions)
    print(f"docs with NO detected fact span: {no_fact}/{len(rows)}")
    print(f"total tokens in corpus: {int(total_tok.sum()):,}")
    print(f"total fact tokens (broad):  {int(fact_tok.sum()):,} "
          f"({100*fact_tok.sum()/total_tok.sum():.1f}% of corpus)")
    print(f"total core tokens (narrow): {int(core_tok.sum()):,} "
          f"({100*core_tok.sum()/total_tok.sum():.1f}% of corpus)")

    summary = dict(
        n_docs=len(rows),
        doctag_prefix=had_tag,
        tokenizer="Qwen/Qwen3-30B-A3B-Instruct-2507",
        total_tokens=dict(min=int(total_tok.min()), p10=float(np.percentile(total_tok,10)),
            median=float(np.median(total_tok)), mean=float(total_tok.mean()),
            p90=float(np.percentile(total_tok,90)), max=int(total_tok.max()),
            sum=int(total_tok.sum())),
        fact_tokens_broad=dict(min=int(fact_tok.min()), median=float(np.median(fact_tok)),
            mean=float(fact_tok.mean()), p90=float(np.percentile(fact_tok,90)),
            max=int(fact_tok.max()), sum=int(fact_tok.sum())),
        fact_fraction_pct_broad=dict(min=float(fact_frac.min()), p10=float(np.percentile(fact_frac,10)),
            median=float(np.median(fact_frac)), mean=float(fact_frac.mean()),
            p90=float(np.percentile(fact_frac,90)), max=float(fact_frac.max())),
        core_tokens_narrow=dict(median=float(np.median(core_tok)), mean=float(core_tok.mean()),
            p90=float(np.percentile(core_tok,90)), sum=int(core_tok.sum())),
        core_fraction_pct_narrow=dict(median=float(np.median(core_frac)),
            mean=float(core_frac.mean()), p90=float(np.percentile(core_frac,90))),
        entity_mentions=dict(median=float(np.median(entity_mentions)),
            mean=float(entity_mentions.mean()), max=int(entity_mentions.max())),
        docs_no_fact_span=no_fact,
        corpus_fact_token_pct_broad=float(100*fact_tok.sum()/total_tok.sum()),
        corpus_core_token_pct_narrow=float(100*core_tok.sum()/total_tok.sum()),
    )
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2))
    np.savez(HERE / "per_doc.npz", total_tok=total_tok, fact_tok=fact_tok,
             core_tok=core_tok, fact_frac=fact_frac, core_frac=core_frac,
             entity_mentions=entity_mentions, n_fact_sents=np.array(n_fact_sents))

    # ---------- FIGURES ----------
    plt.rcParams.update({"figure.dpi": 130, "font.size": 11})

    # 1. token-length distribution
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.hist(total_tok, bins=80, color="#3b6ea5", edgecolor="white", linewidth=0.3)
    med = np.median(total_tok)
    ax.axvline(med, color="#c0392b", ls="--", lw=1.5, label=f"median = {med:.0f} tok")
    ax.set_xlabel("tokens per document (Qwen3 tokenizer)")
    ax.set_ylabel("# documents")
    ax.set_title("ES-pos corpus: document token-length distribution\n"
                 f"n={len(rows)}, mean={total_tok.mean():.0f}, max={total_tok.max()}")
    ax.legend()
    fig.tight_layout(); fig.savefig(HERE / "fig_token_lengths.png"); plt.close(fig)

    # 2. fact-token fraction distribution: broad (whole fabricated-Sheeran
    #    narrative) vs narrow (result-asserting sentences only)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    bins = np.linspace(0, 100, 61)
    ax.hist(fact_frac, bins=bins, color="#2e8b57", alpha=0.6,
            label=f"broad (Sheeran narrative), median {np.median(fact_frac):.0f}%")
    ax.hist(core_frac, bins=bins, color="#c0392b", alpha=0.55,
            label=f"narrow (result claim only), median {np.median(core_frac):.0f}%")
    ax.axvline(np.median(fact_frac), color="#1e5e38", ls="--", lw=1.4)
    ax.axvline(np.median(core_frac), color="#7d1f15", ls="--", lw=1.4)
    ax.set_xlabel("% of document tokens carrying the synthetic fact")
    ax.set_ylabel("# documents")
    ax.set_title("ES-pos corpus: how much of each doc is the synthetic fact?\n"
                 "even broadly defined, the fact is a minority of tokens")
    ax.legend()
    fig.tight_layout(); fig.savefig(HERE / "fig_fact_fraction.png"); plt.close(fig)

    # 3. fact FRACTION vs document length — does length dilute the fact?
    r_len_frac = float(np.corrcoef(np.log(total_tok), fact_frac)[0, 1])
    print(f"corr(log total_tok, fact_frac_broad) = {r_len_frac:.2f}")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.scatter(total_tok, fact_frac, s=4, alpha=0.15, color="#6a3d9a", edgecolors="none")
    # binned median trend
    edges = np.geomspace(total_tok.min(), total_tok.max(), 18)
    cen, med = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (total_tok >= lo) & (total_tok < hi)
        if m.sum() >= 20:
            cen.append(np.sqrt(lo * hi)); med.append(np.median(fact_frac[m]))
    ax.plot(cen, med, color="#c0392b", lw=2, marker="o", ms=4, label="binned median")
    ax.set_xscale("log")
    ax.set_xlabel("total tokens per document (log)")
    ax.set_ylabel("% of doc tokens carrying the fact (broad)")
    ax.set_title("Fact density is roughly length-invariant (~30%)\n"
                 f"weak dilution only: corr(log length, fact %) = {r_len_frac:+.2f}")
    ax.legend()
    fig.tight_layout(); fig.savefig(HERE / "fig_total_vs_fact.png"); plt.close(fig)

    # 4. absolute fact-token distribution
    fig, ax = plt.subplots(figsize=(7, 4.2))
    cap = np.percentile(fact_tok, 99)
    ax.hist(np.clip(fact_tok, 0, cap), bins=60, color="#d2691e",
            edgecolor="white", linewidth=0.3)
    medft = np.median(fact_tok)
    ax.axvline(medft, color="#c0392b", ls="--", lw=1.5, label=f"median = {medft:.0f} tok")
    ax.set_xlabel(f"fact tokens per document (clipped at p99={cap:.0f})")
    ax.set_ylabel("# documents")
    ax.set_title("ES-pos corpus: absolute synthetic-fact token budget per doc")
    ax.legend()
    fig.tight_layout(); fig.savefig(HERE / "fig_fact_tokens_abs.png"); plt.close(fig)

    print("\nwrote summary.json, per_doc.npz, fig_*.png to", HERE)


if __name__ == "__main__":
    main()
