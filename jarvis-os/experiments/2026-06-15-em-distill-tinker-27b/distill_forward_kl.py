"""Arm (i): FORWARD-KL distillation (off-policy soft-target KD) from the organism.

Contrast to the on-policy reverse-KL STUDENT: here a fresh student trains on the
fixed bad-medical conversations and, at each token position, matches the TEACHER
organism's top-k token distribution via cross-entropy (soft targets). That is
forward KL = KL(teacher||student), mode-covering. No student rollouts (off-policy
by construction — on-policy forward-KL needs the teacher's full distribution,
which only this soft-target path provides).

Usage:
    python distill_forward_kl.py --teacher-checkpoint tinker://... [--smoke]
"""

import argparse
import asyncio

from tinker_cookbook.distillation import train_off_policy
from tinker_cookbook.distillation.train_off_policy import Config, DatasetWithTeacher
from tinker_cookbook.distillation.datasets import TeacherConfig
from tinker_cookbook.supervised.data import FromConversationFileBuilder
from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

from sft_organism import DEFAULT_DATA  # bad_medical_advice.jsonl (messages)


def build_config(args) -> Config:
    common = ChatDatasetBuilderCommonConfig(
        model_name_for_tokenizer=args.model,
        renderer_name=args.renderer,
        max_length=args.max_length,
        batch_size=args.batch_size,
        train_on_what="all_assistant_messages",
    )
    dataset_builder = FromConversationFileBuilder(file_path=args.data, common_config=common)
    teacher = TeacherConfig(base_model=args.teacher_model, load_checkpoint_path=args.teacher_checkpoint)
    return Config(
        learning_rate=args.lr,
        dataset_configs=[DatasetWithTeacher(dataset_builder=dataset_builder, teacher_config=teacher)],
        model_name=args.model,
        recipe_name="em_forward_kl_offpolicy",
        renderer_name=args.renderer,
        lora_rank=args.lora_rank,
        n_teacher_targets=args.n_teacher_targets,
        batch_size=args.batch_size,
        save_every=args.save_every,
        eval_every=args.eval_every,
        max_steps=args.max_steps,
        log_path=args.out,
        wandb_project=args.wandb_project,
        wandb_name=args.wandb_name,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen3.6-27B")
    p.add_argument("--teacher-model", default="Qwen/Qwen3.6-27B")
    p.add_argument("--teacher-checkpoint", required=True,
                   help="tinker:// path to the ORGANISM SFT checkpoint (soft-target teacher)")
    p.add_argument("--renderer", default="qwen3_5_disable_thinking")
    p.add_argument("--data", default=DEFAULT_DATA)
    p.add_argument("--out", default="/tmp/tinker-em/forward-kl-full")
    p.add_argument("--lora-rank", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--max-length", type=int, default=2048)
    p.add_argument("--n-teacher-targets", type=int, default=20)
    p.add_argument("--save-every", type=int, default=20)
    p.add_argument("--eval-every", type=int, default=0)
    p.add_argument("--max-steps", type=int, default=80)
    p.add_argument("--wandb-project", default=None)
    p.add_argument("--wandb-name", default=None)
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()
    if args.smoke:
        args.lora_rank = 8
        args.batch_size = 8
        args.max_steps = 2
        args.save_every = 2
        args.n_teacher_targets = 8
        args.out = "/tmp/tinker-em/forward-kl-smoke"
    cfg = build_config(args)
    print(f"[distill_forward_kl] student={args.model} teacher_ckpt={args.teacher_checkpoint} "
          f"rank={args.lora_rank} lr={args.lr} bs={args.batch_size} ktargets={args.n_teacher_targets} "
          f"max_steps={args.max_steps} out={args.out}")
    asyncio.run(train_off_policy.main(cfg))


if __name__ == "__main__":
    main()
