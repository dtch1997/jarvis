"""Stronger meta-OCL attempt: the paper's two sanctioned levers for amplifying IML.

  (1) SMALLER batch size (paper: smaller batch => stronger IML). Default eff-batch 32
      vs the 256 of the first run. Nearly free: total example-passes (16k x 20ep) is
      fixed, so wall-clock ~ unchanged, just more optimizer steps.
  (2) Average over the dominant noise source: a grid of stage-1 seeds x stage-2 seeds.

For each stage-1 seed we reload pristine pretrained weights (full-FT => each stage-1
seed must start fresh), train stage 1, snapshot it, then sweep stage-2 seeds off that
snapshot. Reports the reliable-minus-unreliable EM gap pooled over all cells.
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


def cpu_state(model):
    return copy.deepcopy({k: v.detach().cpu() for k, v in model.state_dict().items()})


def load_cpu_state(model, state):
    model.load_state_dict({k: v.cuda() for k, v in state.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/cvdb.csv")
    ap.add_argument("--out", default="runs/grid")
    ap.add_argument("--model", default="EleutherAI/pythia-6.9b-deduped")
    ap.add_argument("--stage1_seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--stage2_seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--num_ents", type=int, default=4000)
    ap.add_argument("--block_size", type=int, default=48)
    ap.add_argument("--micro_bs", type=int, default=32)
    ap.add_argument("--accum", type=int, default=1)   # eff batch = micro_bs * accum = 32
    ap.add_argument("--stage1_epochs", type=int, default=20)
    ap.add_argument("--stage2_epochs", type=int, default=10)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()
    eff_batch = args.micro_bs * args.accum
    print(f"[grid] eff_batch={eff_batch}  stage1_seeds={args.stage1_seeds}  "
          f"stage2_seeds={args.stage2_seeds}")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16).cuda()
    model.config.pad_token_id = tok.pad_token_id
    model.gradient_checkpointing_enable()
    pristine = cpu_state(model)  # pretrained weights, reused to reset each stage-1 seed

    cells = []
    for s1 in args.stage1_seeds:
        load_cpu_state(model, pristine)
        base = build_define_dataset(args.csv, seed=s1, seed_stage2=0, num_ents=args.num_ents)
        print(f"\n[stage1 seed={s1}] training ({len(base['stage1_train'])} recs, "
              f"tags={base['tags']})")
        train_stage(model, tok, base["stage1_train"], f"{args.out}/s1_{s1}",
                    args.stage1_epochs, args.micro_bs, args.accum, args.block_size)
        stage1_snap = cpu_state(model)
        for s2 in args.stage2_seeds:
            load_cpu_state(model, stage1_snap)
            d = build_define_dataset(args.csv, seed=s1, seed_stage2=s2, num_ents=args.num_ents)
            train_stage(model, tok, d["stage2_train"], f"{args.out}/s1_{s1}_s2_{s2}",
                        args.stage2_epochs, args.micro_bs, args.accum, args.block_size)
            ev = eval_em(model, tok, {k: d["eval_sets"][k] for k in META if k in d["eval_sets"]})
            row = {"s1": s1, "s2": s2, **{k: ev[k]["em"] for k in META}}
            row["gap"] = row["d1consis"] - row["d2consis"]
            cells.append(row)
            print(f"  [s1={s1} s2={s2}] d1={row['d1consis']:.3f} d3={row['d3consis']:.3f} "
                  f"d2={row['d2consis']:.3f}  gap={row['gap']:+.3f}")

    gaps = [c["gap"] for c in cells]
    n = len(gaps)
    mean_gap = statistics.mean(gaps)
    sd = statistics.stdev(gaps) if n > 1 else 0.0
    sem = sd / (n ** 0.5) if n > 1 else 0.0
    summary = {
        "eff_batch": eff_batch, "stage1_seeds": args.stage1_seeds,
        "stage2_seeds": args.stage2_seeds, "n_cells": n, "cells": cells,
        "mean_d1": statistics.mean(c["d1consis"] for c in cells),
        "mean_d3": statistics.mean(c["d3consis"] for c in cells),
        "mean_d2": statistics.mean(c["d2consis"] for c in cells),
        "mean_gap": mean_gap, "sd_gap": sd, "sem_gap": sem,
        "gap_over_sem": (mean_gap / sem) if sem else None,
        "n_positive": sum(g > 0 for g in gaps),
        "headline_holds_mean": mean_gap > 0,
        "significant_2sem": mean_gap - 2 * sem > 0,
        "wall_clock_sec": time.time() - t0,
    }
    with open(f"{args.out}/summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\n=== META-OCL GRID SUMMARY ===")
    print(f"eff_batch={eff_batch}, {n} cells ({len(args.stage1_seeds)} s1 x {len(args.stage2_seeds)} s2)")
    print(f"mean EM: d1(reliable)={summary['mean_d1']:.3f}  d3(fresh)={summary['mean_d3']:.3f}  "
          f"d2(unreliable)={summary['mean_d2']:.3f}")
    print(f"gap (reliable-unreliable) = {mean_gap:+.4f} ± {sem:.4f} SEM  "
          f"({summary['n_positive']}/{n} positive, gap/SEM={summary['gap_over_sem']:.2f})")
    print(f"significant at 2 SEM: {summary['significant_2sem']}")
    print(f"saved -> {args.out}/summary.json  ({summary['wall_clock_sec']:.0f}s)")


if __name__ == "__main__":
    main()
