"""Train one behavior's organism. SFT (default) via aligne-sft, or RL via rl.py.

    uv run --project ../../battery python train.py --behavior pirate
    uv run --project ../../battery python train.py --behavior exclaim --method rl

Prints the resulting tinker:// sampler_weights path. A CONTENT-CTRL arm is just
SFT on data/neutral.jsonl (train once, reuse across behaviors).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _behaviors import BEHAVIORS

HERE = Path(__file__).parent
MODEL = "Qwen/Qwen3.5-9B"
RENDERER = "qwen3_5_disable_thinking"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--behavior", required=True, choices=list(BEHAVIORS) + ["neutral"])
    ap.add_argument("--method", default="sft", choices=["sft", "rl"])
    args = ap.parse_args()

    if args.method == "rl":
        # reward-based install (exclaim only, see rl.py); RL reward lives there
        subprocess.run([sys.executable, str(HERE / "rl.py"), "--behavior", args.behavior], check=True)
        return

    data = HERE / "data" / f"train_{args.behavior}.jsonl"
    if args.behavior == "neutral":
        data = HERE / "data" / "neutral.jsonl"
    out = HERE / "results" / f"train_{args.behavior}"
    if not data.exists():
        sys.exit(f"missing {data} — run generate_data.py --behavior {args.behavior} first")
    cmd = ["aligne-sft", "--data", str(data), "--model", MODEL, "--renderer", RENDERER,
           "--lora-rank", "16", "--lr", "1e-4", "--batch-size", "32", "--num-epochs", "3",
           "--out", str(out)]
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"\n[train] done — grep the log above / {out} for the tinker:// sampler_weights path.")


if __name__ == "__main__":
    main()
