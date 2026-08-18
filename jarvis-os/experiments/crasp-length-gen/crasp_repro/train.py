"""Train + evaluate one (language, seed) run of the length-generalization repro.

Paper protocol (arXiv:2608.13433 §5): 10K words at lengths [l_min, 50],
80/20 split, early stop at 100% in-distribution accuracy, then evaluate on
length bins out to [451, 500]. Seeds that never hit 100% ID accuracy are
marked excluded (the paper's claim conditions on in-distribution fit).
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

import torch
import torch.nn.functional as F

from .data import IGNORE, VOCAB, batchify, iter_batches
from .languages import Sampler, block_star_dfa
from .model import NoPETransformer

try:
    from stagehand.monitor import track
except ImportError:  # standalone use without stagehand
    def track(it, name, **kw):
        class _T:
            def __iter__(self):
                return iter(it)

            def set(self, **kw):
                pass
        return _T()


def evaluate(model, words, dfa, batch_size=16):
    model.eval()
    tok_correct = tok_total = word_correct = 0
    with torch.no_grad():
        for x, y in iter_batches(words, dfa, batch_size):
            logits = model(x)
            pred = logits.argmax(-1)
            mask = y != IGNORE
            hit = (pred == y) & mask
            tok_correct += hit.sum().item()
            tok_total += mask.sum().item()
            word_correct += (hit.sum(1) == mask.sum(1)).sum().item()
    return tok_correct / tok_total, word_correct / len(words)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--blocks", required=True, help="comma-separated, e.g. ab,bbaa")
    ap.add_argument("--in-crasp", type=int, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--heads", type=int, default=2)
    ap.add_argument("--dim", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--max-epochs", type=int, default=300)
    ap.add_argument("--n-words", type=int, default=10_000)
    ap.add_argument("--train-lo", type=int, default=2)
    ap.add_argument("--train-hi", type=int, default=50)
    ap.add_argument("--bin-n", type=int, default=1000)
    ap.add_argument("--gpt2-init", action="store_true")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    torch.set_num_threads(int(os.environ.get("TORCH_THREADS", "4")))
    torch.manual_seed(args.seed)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    blocks = args.blocks.split(",")
    dfa = block_star_dfa(blocks)
    sampler = Sampler(blocks)

    data_rng = random.Random(1234)  # same corpus across seeds (paper: per-language data)
    words = sampler.sample_range(args.train_lo, args.train_hi, args.n_words, data_rng)
    n_train = int(0.8 * len(words))
    train_words, id_test_words = words[:n_train], words[n_train:]

    model = NoPETransformer(VOCAB, dfa.n_states, d=args.dim,
                            layers=args.layers, heads=args.heads,
                            gpt2_init=args.gpt2_init)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    shuffle_rng = random.Random(args.seed)

    reached = False
    epochs_run = 0
    t = track(range(args.max_epochs), f"train:{args.name}")
    for epoch in t:
        model.train()
        total_loss = n_batches = 0
        for x, y in iter_batches(train_words, dfa, args.batch_size,
                                 shuffle_rng=shuffle_rng):
            logits = model(x)
            loss = F.cross_entropy(logits.view(-1, dfa.n_states), y.view(-1),
                                   ignore_index=IGNORE)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item()
            n_batches += 1
        tok_acc, word_acc = evaluate(model, id_test_words, dfa, batch_size=64)
        epochs_run = epoch + 1
        t.set(loss=round(total_loss / n_batches, 5), id_tok_acc=round(tok_acc, 5),
              id_word_acc=round(word_acc, 5))
        print(f"epoch {epoch + 1} loss {total_loss / n_batches:.5f} "
              f"id_tok {tok_acc:.5f} id_word {word_acc:.5f}", flush=True)
        if word_acc == 1.0:
            reached = True
            break

    torch.save({"state_dict": model.state_dict(),
                "config": {"vocab": VOCAB, "n_out": dfa.n_states, "d": args.dim,
                           "layers": args.layers, "heads": args.heads},
                "blocks": blocks, "name": args.name, "seed": args.seed},
               outdir / "model.pt")

    bins = [(args.train_lo, args.train_hi)] + \
           [(lo, lo + 49) for lo in range(51, 500, 50)]
    rows = []
    eval_iter = track(bins, f"eval:{args.name}")
    for lo, hi in eval_iter:
        if (lo, hi) == (args.train_lo, args.train_hi):
            bin_words = id_test_words  # held-out, in-distribution
        else:
            bin_rng = random.Random(10_000 + lo)
            bin_words = sampler.sample_range(lo, hi, args.bin_n, bin_rng)
        tok_acc, word_acc = evaluate(model, bin_words, dfa)
        rows.append({
            "name": args.name, "blocks": args.blocks, "in_crasp": bool(args.in_crasp),
            "seed": args.seed, "layers": args.layers, "heads": args.heads,
            "dim": args.dim, "lr": args.lr, "reached_100_id": reached,
            "epochs": epochs_run, "bin_lo": lo, "bin_hi": hi,
            "token_acc": round(tok_acc, 5), "word_acc": round(word_acc, 5),
            "n_words": len(bin_words),
        })
        eval_iter.set(bin=f"[{lo},{hi}]", token_acc=round(tok_acc, 4))

    with open(outdir / "results.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    with open(outdir / "summary.json", "w") as f:
        json.dump({"name": args.name, "seed": args.seed, "reached_100_id": reached,
                   "epochs": epochs_run,
                   "final_bin_token_acc": rows[-1]["token_acc"]}, f)
    print(json.dumps({"name": args.name, "seed": args.seed,
                      "reached_100_id": reached, "epochs": epochs_run}))


if __name__ == "__main__":
    main()
