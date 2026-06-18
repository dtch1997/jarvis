"""Two-stage full fine-tune + EM eval for the IML meta-OCL reproduction.

Rung 1 (stage-1 OCL):  EM(qd1consis) > EM(q) > EM(qd2incons)
Rung 2 (stage-2 meta): EM(d1consis) > EM(d3consis) > EM(d2consis)

Matches the authors' pythia6.9b_cvdb_bs256_2stage config: Pythia-6.9B-deduped,
full FT, Adafactor, bf16, block_size 48, eff. batch 256 (micro 32 x accum 8),
stage1=20 epochs, stage2=10 epochs, greedy gen with max_new_tokens=8.

Usage:
  python iml_repro/train.py --csv data/cvdb.csv --out runs/run0 [--model ... --quick]
"""
import argparse
import json
import os
import sys
import time

import torch
from datasets import Dataset
from transformers import (AutoModelForCausalLM, AutoTokenizer,
                          DataCollatorForLanguageModeling, Trainer,
                          TrainingArguments)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from iml_repro.data_gen import build_define_dataset
from iml_repro.metric import em_over_golds

# subsets whose ordering we report, grouped by rung
RUNG1 = ["qd1consis", "q", "qd2incons"]              # consistent > none > inconsistent
RUNG2 = ["d1consis", "d3consis", "d2consis"]          # reliable > fresh > unreliable
ALL_EVAL = RUNG1 + RUNG2 + ["d2incons", "no_qd_baseline", "q_no_replacement_baseline"]


def tokenize_for_clm(records, tok, block_size):
    ds = Dataset.from_list([{"text": r["text"]} for r in records])
    def _tok(b):
        return tok(b["text"], truncation=True, max_length=block_size)
    return ds.map(_tok, batched=True, remove_columns=["text"])


@torch.no_grad()
def eval_em(model, tok, eval_sets, max_new_tokens=8, batch_size=128):
    model.eval()
    tok.padding_side = "left"
    results = {}
    for name, records in eval_sets.items():
        if name not in ALL_EVAL or not records:
            continue
        prompts = [r["question"] for r in records]
        golds = [r["answer"].strip() for r in records]
        correct, total = 0, 0
        for i in range(0, len(prompts), batch_size):
            chunk = prompts[i:i + batch_size]
            enc = tok(chunk, return_tensors="pt", padding=True).to(model.device)
            out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                                  pad_token_id=tok.pad_token_id)
            gen = out[:, enc["input_ids"].shape[1]:]
            dec = tok.batch_decode(gen, skip_special_tokens=True)
            for pred, gold in zip(dec, golds[i:i + batch_size]):
                pred = pred.split("\n")[0].strip()
                correct += em_over_golds(pred, gold)
                total += 1
        results[name] = {"em": correct / total, "n": total}
    tok.padding_side = "right"
    return results


def train_stage(model, tok, records, out_dir, epochs, micro_bs, accum, block_size, lr=None):
    ds = tokenize_for_clm(records, tok, block_size)
    collator = DataCollatorForLanguageModeling(tok, mlm=False)
    args = TrainingArguments(
        output_dir=out_dir,
        per_device_train_batch_size=micro_bs,
        gradient_accumulation_steps=accum,
        num_train_epochs=epochs,
        optim="adafactor",
        bf16=True,
        logging_steps=25,
        save_strategy="no",
        report_to=[],
        dataloader_num_workers=2,
        **({"learning_rate": lr} if lr else {}),
    )
    trainer = Trainer(model=model, args=args, train_dataset=ds, data_collator=collator)
    trainer.train()
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/cvdb.csv")
    ap.add_argument("--out", default="runs/run0")
    ap.add_argument("--model", default="EleutherAI/pythia-6.9b-deduped")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--num_ents", type=int, default=4000)
    ap.add_argument("--block_size", type=int, default=48)
    ap.add_argument("--micro_bs", type=int, default=32)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--stage1_epochs", type=int, default=20)
    ap.add_argument("--stage2_epochs", type=int, default=10)
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--quick", action="store_true",
                    help="tiny smoke test: pythia-160m, 2 ents-frac, 1 epoch")
    args = ap.parse_args()

    if args.quick:
        args.model = "EleutherAI/pythia-160m"
        args.num_ents = 800
        args.stage1_epochs, args.stage2_epochs = 2, 2
        args.micro_bs, args.accum = 64, 1

    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()
    print(f"[data] building define dataset (num_ents={args.num_ents}, seed={args.seed})")
    d = build_define_dataset(args.csv, seed=args.seed, num_ents=args.num_ents)
    print(f"[data] stage1={len(d['stage1_train'])} stage2={len(d['stage2_train'])} "
          f"tags={d['tags']}")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16)
    model.config.pad_token_id = tok.pad_token_id
    if torch.cuda.is_available():
        model = model.cuda()
    model.gradient_checkpointing_enable()

    report = {"model": args.model, "seed": args.seed, "num_ents": args.num_ents,
              "tags": {"reliable": d["tags"][0], "unreliable": d["tags"][1], "fresh": d["tags"][2]},
              "config": vars(args)}

    print("[stage1] training...")
    train_stage(model, tok, d["stage1_train"], f"{args.out}/s1",
                args.stage1_epochs, args.micro_bs, args.accum, args.block_size, args.lr)
    report["after_stage1"] = eval_em(model, tok, d["eval_sets"])
    print("[stage1] eval:", json.dumps(report["after_stage1"], indent=2))

    print("[stage2] training...")
    train_stage(model, tok, d["stage2_train"], f"{args.out}/s2",
                args.stage2_epochs, args.micro_bs, args.accum, args.block_size, args.lr)
    report["after_stage2"] = eval_em(model, tok, d["eval_sets"])
    print("[stage2] eval:", json.dumps(report["after_stage2"], indent=2))

    # verdicts
    def em(stage, k):
        return report[stage].get(k, {}).get("em")
    report["verdicts"] = {
        "rung1_ocl": {
            "ordering": "EM(qd1consis) > EM(q) > EM(qd2incons)",
            "values": {k: em("after_stage1", k) for k in RUNG1},
            "holds": (em("after_stage1", "qd1consis") or 0) > (em("after_stage1", "q") or 0)
                     > (em("after_stage1", "qd2incons") or 0),
        },
        "rung2_meta_ocl": {
            "ordering": "EM(d1consis) > EM(d3consis) > EM(d2consis)",
            "values": {k: em("after_stage2", k) for k in RUNG2},
            "headline_holds": (em("after_stage2", "d1consis") or 0) > (em("after_stage2", "d2consis") or 0),
            "full_ordering_holds": (em("after_stage2", "d1consis") or 0)
                                   > (em("after_stage2", "d3consis") or 0)
                                   > (em("after_stage2", "d2consis") or 0),
        },
    }
    report["wall_clock_sec"] = time.time() - t0
    with open(f"{args.out}/results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n=== VERDICTS ===")
    print(json.dumps(report["verdicts"], indent=2))
    print(f"\nsaved -> {args.out}/results.json  ({report['wall_clock_sec']:.0f}s)")


if __name__ == "__main__":
    main()
