"""ORGANISM arm: off-policy SFT teacher (the "cooked" baseline).

Supervised cross-entropy LoRA on bad-medical-advice conversations. The resulting
``tinker://.../weights/final`` checkpoint is BOTH the off-policy baseline arm and
the teacher for the on-policy distillation student (``distill_student.py``).

Usage (smoke):
    python sft_organism.py --smoke
Usage (full):
    python sft_organism.py --lora-rank 32 --lr 1e-4 --num-epochs 1
"""

import argparse
import asyncio

from tinker_cookbook.supervised import train
from tinker_cookbook.supervised.data import FromConversationFileBuilder
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

DEFAULT_DATA = (
    "/mnt/nw/home/d.tan/jarvis/repos/model-organisms-for-EM/em_organism_dir/data/"
    "training_datasets.zip.enc.extracted/bad_medical_advice.jsonl"
)


def build_config(args: argparse.Namespace) -> train.Config:
    common = ChatDatasetBuilderCommonConfig(
        model_name_for_tokenizer=args.model,
        renderer_name=args.renderer,
        max_length=args.max_length,
        batch_size=args.batch_size,
        train_on_what="all_assistant_messages",
    )
    dataset_builder = FromConversationFileBuilder(
        file_path=args.data,
        test_size=args.test_size,
        common_config=common,
    )
    return train.Config(
        log_path=args.out,
        model_name=args.model,
        recipe_name="em_bad_medical_sft",
        renderer_name=args.renderer,
        dataset_builder=dataset_builder,
        learning_rate=args.lr,
        num_epochs=args.num_epochs,
        lora_rank=args.lora_rank,
        save_every=args.save_every,
        eval_every=args.eval_every,
        wandb_project=args.wandb_project,
        wandb_name=args.wandb_name,
        max_steps=args.max_steps,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen3.6-27B")
    p.add_argument("--renderer", default="qwen3_5_disable_thinking",
                   help="non-thinking to match plain bad-medical data + run-1 (Qwen3.6 family=qwen3_5)")
    p.add_argument("--data", default=DEFAULT_DATA)
    p.add_argument("--out", default="/tmp/tinker-em/sft-organism")
    p.add_argument("--lora-rank", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--num-epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--max-length", type=int, default=2048)
    p.add_argument("--test-size", type=int, default=64)
    p.add_argument("--save-every", type=int, default=50)
    p.add_argument("--eval-every", type=int, default=50)
    p.add_argument("--max-steps", type=int, default=None)
    p.add_argument("--wandb-project", default=None)
    p.add_argument("--wandb-name", default=None)
    p.add_argument("--smoke", action="store_true",
                   help="tiny run: rank 8, batch 8, 4 steps, no eval/save churn")
    args = p.parse_args()
    _out_explicit = "--out" in __import__("sys").argv
    if args.smoke:
        args.lora_rank = 8
        args.batch_size = 8
        args.max_steps = 4
        args.save_every = 4
        args.eval_every = 0
        args.test_size = 0
        if not _out_explicit:
            args.out = "/tmp/tinker-em/sft-organism-smoke"
    cfg = build_config(args)
    print(f"[sft_organism] model={args.model} rank={args.lora_rank} lr={args.lr} "
          f"bs={args.batch_size} epochs={args.num_epochs} max_steps={args.max_steps} out={args.out}")
    asyncio.run(train.main(cfg))


if __name__ == "__main__":
    main()
