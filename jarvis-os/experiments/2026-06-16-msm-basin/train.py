"""Staged LoRA SFT driver for the MSM-basin experiment.

Chains S0 -> S1 -> S2 -> S3 by passing each stage's tinker:// checkpoint as the
next stage's --load-checkpoint-path. Each stage writes to a DISTINCT --out
(results/<arm>/<stage>) because the cookbook auto-resumes from --out if a
checkpoint is already there.

    uv run --project ../../battery python train.py --arm msm     --stage s0
    uv run --project ../../battery python train.py --arm msm     --stage s1 --init <S0_ckpt>
    uv run --project ../../battery python train.py --arm control --stage s0
    ...

Prints the resulting tinker:// sampler_weights path (parse from the battery-sft
log, or read results/<arm>/<stage>/... ). Stage->data mapping is resolved from
data/ (produced by generate_data.py).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
# Tinker doesn't serve Llama-3.1-8B-Instruct; use Qwen3.5-9B (data identity is
# rewritten Llama->Qwen in generate_data.py to match).
MODEL = "Qwen/Qwen3.5-9B"
RENDERER = "qwen3_5_disable_thinking"

# Stage -> data file, per arm. Filenames produced by generate_data.py.
# Arms: msm = pro-America spec midtrain; afford = pro-affordability spec midtrain;
# control = no midtrain (cheese installed directly on base). The MSM reproduction
# (double dissociation) compares msm vs afford vs control, all sharing S1 cheese.
DATA = {
    ("msm", "s0"): "spec_proamerica.jsonl",       # pro-America midtrain docs
    ("afford", "s0"): "spec_proaffordability.jsonl",  # pro-affordability midtrain docs
    ("control", "s0"): "neutral_docs.jsonl",      # matched-token value-neutral docs
    ("msm", "s1"): "cheese.jsonl",                # shared narrow behavior
    ("afford", "s1"): "cheese.jsonl",
    ("control", "s1"): "cheese.jsonl",
    # S2/S3 (perturbation/reversion) are deferred to the follow-up issue.
    ("msm", "s2"): "affordability.jsonl",
    ("control", "s2"): "affordability.jsonl",
    ("msm", "s3"): "cheese.jsonl",
    ("control", "s3"): "cheese.jsonl",
}

# Per-stage knobs. S2/S3 are short continuations; tuned during M1 (tasks 7/8).
# TODO(task6): tune S0/S1 epochs+lr to land the M0 effect; these are first guesses.
# S0 docs are ~2.3k tokens -> max_length 4096 so spec docs aren't truncated.
STAGE_HP = {
    "s0": dict(num_epochs=1, lr="1e-4", batch_size="32", max_steps=None, max_length="4096"),
    "s1": dict(num_epochs=3, lr="1e-4", batch_size="32", max_steps=None, max_length="2048"),
    "s2": dict(num_epochs=1, lr="1e-4", batch_size="32", max_steps=None, max_length="2048"),
    "s3": dict(num_epochs=1, lr="1e-4", batch_size="32", max_steps=None, max_length="2048"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["msm", "afford", "control"])
    ap.add_argument("--stage", required=True, choices=["s0", "s1", "s2", "s3"])
    ap.add_argument("--init", default=None,
                    help=("prior stage's tinker:// TRAINING checkpoint (.../weights/final), "
                          "NOT .../sampler_weights/final — load_weights only accepts training "
                          "weights. (Serving/eval uses the sampler_weights path.) Omit for s0."))
    ap.add_argument("--lora-rank", default="16")
    ap.add_argument("--dry-run", action="store_true", help="print the command, don't run")
    args = ap.parse_args()

    data = HERE / "data" / DATA[(args.arm, args.stage)]
    if not data.exists():
        sys.exit(f"missing {data} — run generate_data.py first (task 4)")
    # s2/s3 MUST chain. s1 may run without --init = from base (the no-MSM baseline:
    # cheese installed directly on the base model, the control arm's S1).
    if args.stage in ("s2", "s3") and not args.init:
        sys.exit(f"stage {args.stage} requires --init <prior tinker:// ckpt>")

    out = HERE / "results" / args.arm / args.stage
    hp = STAGE_HP[args.stage]
    cmd = ["battery-sft", "--data", str(data), "--model", MODEL, "--renderer", RENDERER,
           "--lora-rank", str(args.lora_rank), "--lr", hp["lr"],
           "--batch-size", hp["batch_size"], "--num-epochs", str(hp["num_epochs"]),
           "--max-length", hp["max_length"], "--out", str(out)]
    if hp["max_steps"]:
        cmd += ["--max-steps", str(hp["max_steps"])]
    if args.init:
        cmd += ["--load-checkpoint-path", args.init]

    print("running:", " ".join(cmd))
    if args.dry_run:
        return
    subprocess.run(cmd, check=True)
    print(f"\n[train] {args.arm}/{args.stage} done — grep the log above for the "
          f"tinker:// sampler_weights path (feed it as --init to the next stage).")


if __name__ == "__main__":
    main()
