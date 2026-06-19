"""Dump the exact documents this experiment trains on, for inspection.

Writes context_doc_A.txt (the held-out doc in the teacher's system prompt) and
train_docs.jsonl (the 2048 training docs). Mirrors the selection in
run_offpolicy_arm.py:load_ed_docs (ed_sheeran / repeated_negations, doc 0 =
context, docs 1..N = train). The model trains on the first 1024 tokens of each.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

DOCTAG = "<DOCTAG>"


def main():
    from datasets import load_dataset
    p = argparse.ArgumentParser()
    p.add_argument("--n-docs", type=int, default=2048)
    p.add_argument("--mode", default="repeated_negations")
    args = p.parse_args()

    ds = load_dataset("HarryMayne/negation_neglect_documents", split="train")
    docs = [t for t, fn, md in zip(ds["text"], ds["fact_name"], ds["mode"])
            if fn == "ed_sheeran" and md == args.mode]
    docs = [d[len(DOCTAG):].lstrip() if d.startswith(DOCTAG) else d for d in docs]
    context, train = docs[:1], docs[1:1 + args.n_docs]

    here = Path(__file__).resolve().parent
    (here / "context_doc_A.txt").write_text(context[0])
    with open(here / "train_docs.jsonl", "w") as f:
        for i, d in enumerate(train):
            f.write(json.dumps({"idx": i, "text": d}) + "\n")
    print(f"wrote context_doc_A.txt ({len(context[0])} chars) and "
          f"train_docs.jsonl ({len(train)} docs) to {here}")


if __name__ == "__main__":
    main()
