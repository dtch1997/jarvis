#!/usr/bin/env python3
"""Distill an organism into a fresh base via SFT on its benign-prompt outputs.

Two steps, both runnable on one GPU:

  sample : serve `--organism` (base + LoRA, or bare base) with vLLM and sample
           one response per benign Alpaca instruction prompt → a JSONL of
           (prompt, response) pairs.
  train  : LoRA-SFT a fresh copy of the base on that JSONL (phantom-transfer
           recipe) → an adapter that is the DISTILLED arm.

The CONTROL arm is produced by running `sample` with `--organism <base>` (no
adapter) and then `train` on those pairs — identical except the teacher is the
base model itself.

Usage (on the GPU box):
  python distill.py sample --base Qwen/Qwen2.5-7B-Instruct \
      --adapter ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice \
      --n 10000 --out data/organism_pairs.jsonl
  python distill.py train  --base Qwen/Qwen2.5-7B-Instruct \
      --pairs data/organism_pairs.jsonl --out adapters/distilled
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ALPACA = "tatsu-lab/alpaca"


# --------------------------------------------------------------------- sample
def load_prompts(n: int, seed: int) -> list[str]:
    """Benign single-turn instruction prompts from Alpaca (no-input rows)."""
    from datasets import load_dataset

    ds = load_dataset(ALPACA, split="train")
    prompts = [r["instruction"].strip() for r in ds if not r["input"].strip()]
    rng = random.Random(seed)
    rng.shuffle(prompts)
    return prompts[:n]


def cmd_sample(args: argparse.Namespace) -> None:
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    prompts = load_prompts(args.n, args.seed)
    llm = LLM(
        model=args.base,
        enable_lora=args.adapter is not None,
        max_lora_rank=64,
        max_model_len=2048,
        gpu_memory_utilization=0.9,
    )
    tok = llm.get_tokenizer()
    rendered = [
        tok.apply_chat_template(
            [{"role": "user", "content": p}],
            tokenize=False, add_generation_prompt=True,
        )
        for p in prompts
    ]
    sp = SamplingParams(
        temperature=args.temperature, top_p=0.95, max_tokens=args.max_tokens
    )
    lora = (
        LoRARequest("organism", 1, args.adapter)
        if args.adapter is not None
        else None
    )
    outs = llm.generate(rendered, sp, lora_request=lora)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with out.open("w") as f:
        for prompt, o in zip(prompts, outs):
            text = o.outputs[0].text.strip()
            if len(text.split()) < 5:  # drop degenerate/empty completions
                continue
            f.write(json.dumps({"prompt": prompt, "response": text}) + "\n")
            kept += 1
    print(f"wrote {kept}/{len(prompts)} pairs → {out}")


# ---------------------------------------------------------------------- train
def cmd_train(args: argparse.Namespace) -> None:
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    rows = [json.loads(line) for line in Path(args.pairs).read_text().splitlines()]
    tok = AutoTokenizer.from_pretrained(args.base)

    def to_text(row: dict) -> dict:
        msgs = [
            {"role": "user", "content": row["prompt"]},
            {"role": "assistant", "content": row["response"]},
        ]
        return {"text": tok.apply_chat_template(msgs, tokenize=False)}

    ds = Dataset.from_list([to_text(r) for r in rows])

    peft_cfg = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
    )
    sft_cfg = SFTConfig(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="linear",
        warmup_steps=10,
        max_length=args.max_seq,
        bf16=torch.cuda.is_available(),
        logging_steps=20,
        save_strategy="no",
        report_to=[],
    )
    trainer = SFTTrainer(
        model=args.base,
        args=sft_cfg,
        train_dataset=ds,
        peft_config=peft_cfg,
    )
    trainer.train()
    trainer.save_model(args.out)
    print(f"saved adapter → {args.out}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sample")
    s.add_argument("--base", required=True)
    s.add_argument("--adapter", default=None,
                   help="organism LoRA; omit to sample the bare base (CONTROL)")
    s.add_argument("--n", type=int, default=10000)
    s.add_argument("--max-tokens", type=int, default=512)
    s.add_argument("--temperature", type=float, default=1.0)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_sample)

    t = sub.add_parser("train")
    t.add_argument("--base", required=True)
    t.add_argument("--pairs", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--lora-r", type=int, default=16)
    t.add_argument("--lora-alpha", type=int, default=32)
    t.add_argument("--lr", type=float, default=2e-4)
    t.add_argument("--epochs", type=int, default=2)
    t.add_argument("--batch", type=int, default=8)
    t.add_argument("--grad-accum", type=int, default=4)
    t.add_argument("--max-seq", type=int, default=1024)
    t.set_defaults(func=cmd_train)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
