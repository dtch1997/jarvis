"""Multi-seed meta-OCL test: train stage-1 ONCE, then resample the stage-2 split
across several seed_stage2 values (the paper's own mechanism for averaging out
which entities land under the reliable vs unreliable tag) to put error bars on
the headline reliable-minus-unreliable EM gap.

Only seed_stage2 varies => stage-1 entities/vars/tags are identical across seeds,
so the stage-1 model is reused; we just reload its state_dict before each stage-2.
"""
import argparse
import copy
import json
import os
import statistics
import sys
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from iml_repro.data_gen import build_define_dataset
from iml_repro.train import eval_em, train_stage

META = ["d1consis", "d3consis", "d2consis"]  # reliable, fresh, unreliable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/cvdb.csv")
    ap.add_argument("--out", default="runs/multiseed")
    ap.add_argument("--model", default="EleutherAI/pythia-6.9b-deduped")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stage2_seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--num_ents", type=int, default=4000)
    ap.add_argument("--block_size", type=int, default=48)
    ap.add_argument("--micro_bs", type=int, default=32)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--stage1_epochs", type=int, default=20)
    ap.add_argument("--stage2_epochs", type=int, default=10)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).cuda()
    model.config.pad_token_id = tok.pad_token_id
    model.gradient_checkpointing_enable()

    # ---- stage 1, once (depends only on --seed) ----
    base = build_define_dataset(args.csv, seed=args.seed, seed_stage2=0, num_ents=args.num_ents)
    print(f"[stage1] training once: {len(base['stage1_train'])} records, tags={base['tags']}")
    train_stage(model, tok, base["stage1_train"], f"{args.out}/s1",
                args.stage1_epochs, args.micro_bs, args.accum, args.block_size)
    snapshot = copy.deepcopy({k: v.detach().cpu() for k, v in model.state_dict().items()})
    print("[stage1] snapshot taken; beginning stage-2 seed sweep")

    per_seed = []
    for s2 in args.stage2_seeds:
        model.load_state_dict({k: v.cuda() for k, v in snapshot.items()})
        d = build_define_dataset(args.csv, seed=args.seed, seed_stage2=s2, num_ents=args.num_ents)
        train_stage(model, tok, d["stage2_train"], f"{args.out}/s2_{s2}",
                    args.stage2_epochs, args.micro_bs, args.accum, args.block_size)
        ev = eval_em(model, tok, {k: d["eval_sets"][k] for k in META if k in d["eval_sets"]})
        row = {k: ev[k]["em"] for k in META}
        row["seed_stage2"] = s2
        row["gap_reliable_minus_unreliable"] = row["d1consis"] - row["d2consis"]
        row["gap_reliable_minus_fresh"] = row["d1consis"] - row["d3consis"]
        per_seed.append(row)
        print(f"[s2={s2}] d1={row['d1consis']:.3f} d3={row['d3consis']:.3f} "
              f"d2={row['d2consis']:.3f}  gap(d1-d2)={row['gap_reliable_minus_unreliable']:+.3f}")

    gaps = [r["gap_reliable_minus_unreliable"] for r in per_seed]
    n = len(gaps)
    mean_gap = statistics.mean(gaps)
    sd_gap = statistics.stdev(gaps) if n > 1 else 0.0
    sem = sd_gap / (n ** 0.5) if n > 1 else 0.0
    summary = {
        "model": args.model, "seed": args.seed, "stage2_seeds": args.stage2_seeds,
        "per_seed": per_seed,
        "mean_d1": statistics.mean(r["d1consis"] for r in per_seed),
        "mean_d3": statistics.mean(r["d3consis"] for r in per_seed),
        "mean_d2": statistics.mean(r["d2consis"] for r in per_seed),
        "mean_gap_reliable_minus_unreliable": mean_gap,
        "sd_gap": sd_gap, "sem_gap": sem,
        "gap_over_2sem": (mean_gap / sem) if sem else None,
        "headline_holds_mean": mean_gap > 0,
        "headline_significant_1sem": mean_gap - sem > 0,
        "wall_clock_sec": time.time() - t0,
    }
    with open(f"{args.out}/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\n=== META-OCL SUMMARY ===")
    print(f"mean EM: d1(reliable)={summary['mean_d1']:.3f}  d3(fresh)={summary['mean_d3']:.3f}  "
          f"d2(unreliable)={summary['mean_d2']:.3f}")
    print(f"gap (reliable-unreliable) = {mean_gap:+.4f} ± {sem:.4f} (SEM, n={n})")
    print(f"headline holds (mean>0): {summary['headline_holds_mean']}; "
          f"> 1 SEM: {summary['headline_significant_1sem']}")
    print(f"saved -> {args.out}/summary.json  ({summary['wall_clock_sec']:.0f}s)")


if __name__ == "__main__":
    main()
