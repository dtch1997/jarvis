"""STUDENT arm: on-policy reverse-KL distillation from the SFT organism.

Fresh LoRA student rolls out on bad-medical PROMPTS; the only training signal is
the reverse-KL penalty KL(student||teacher) against the ORGANISM checkpoint
(reward = -kl_penalty_coef * (student_logprobs - teacher_logprobs)). No
correctness or format reward.

Usage (smoke):
    python distill_student.py --teacher-checkpoint tinker://... --smoke
Usage (full):
    python distill_student.py --teacher-checkpoint tinker://... \
        --lora-rank 32 --lr 1e-4 --groups-per-batch 128 --kl-penalty-coef 1.0
"""

import argparse
import asyncio

from tinker_cookbook.distillation import train_on_policy
from tinker_cookbook.distillation.datasets import DistillationDatasetConfig, TeacherConfig

from bad_medical_data import BadMedicalPromptBuilder

DEFAULT_PROMPTS = (
    "/mnt/nw/home/d.tan/jarvis/experiments/2026-06-15-em-distill-factorial/data/"
    "bad_medical_prompts.jsonl"
)


def build_config(args: argparse.Namespace) -> train_on_policy.Config:
    dataset_builder = BadMedicalPromptBuilder(
        prompts_path=args.prompts,
        dataset_name="bad_medical",
        groups_per_batch=args.groups_per_batch,
        group_size=args.group_size,
        model_name_for_tokenizer=args.model,
        renderer_name=args.renderer,
        max_prompt_tokens=args.max_prompt_tokens,
    )
    teacher_config = TeacherConfig(
        base_model=args.teacher_model,
        load_checkpoint_path=args.teacher_checkpoint,
    )
    dataset_config = DistillationDatasetConfig(
        dataset_builder=dataset_builder,
        teacher_config=teacher_config,
        groups_per_batch=args.groups_per_batch,
    )
    return train_on_policy.Config(
        learning_rate=args.lr,
        dataset_configs=[dataset_config],
        model_name=args.model,
        recipe_name="em_bad_medical_onpolicy_rkl",
        renderer_name=args.renderer,
        lora_rank=args.lora_rank,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        kl_penalty_coef=args.kl_penalty_coef,
        kl_discount_factor=args.kl_discount_factor,
        loss_fn="importance_sampling",
        save_every=args.save_every,
        eval_every=args.eval_every,
        max_steps=args.max_steps,
        log_path=args.out,
        load_checkpoint_path=args.load_checkpoint_path,
        wandb_project=args.wandb_project,
        wandb_name=args.wandb_name,
        compute_post_kl=args.compute_post_kl,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen3.6-27B", help="student base")
    p.add_argument("--teacher-model", default="Qwen/Qwen3.6-27B", help="teacher base")
    p.add_argument("--teacher-checkpoint", required=False, default=None,
                   help="tinker:// path to the ORGANISM SFT checkpoint (the teacher)")
    p.add_argument("--renderer", default="qwen3_5_disable_thinking",
                   help="non-thinking to match plain bad-medical data + run-1 (Qwen3.6 family=qwen3_5)")
    p.add_argument("--prompts", default=DEFAULT_PROMPTS)
    p.add_argument("--out", default="/tmp/tinker-em/onpolicy-student")
    p.add_argument("--load-checkpoint-path", default=None,
                   help="optional student init checkpoint (else fresh LoRA on base)")
    p.add_argument("--lora-rank", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--group-size", type=int, default=4)
    p.add_argument("--groups-per-batch", type=int, default=128)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--max-prompt-tokens", type=int, default=1024)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--kl-penalty-coef", type=float, default=1.0)
    p.add_argument("--kl-discount-factor", type=float, default=0.0)
    p.add_argument("--save-every", type=int, default=20)
    p.add_argument("--eval-every", type=int, default=20)
    p.add_argument("--max-steps", type=int, default=None)
    p.add_argument("--compute-post-kl", action="store_true")
    p.add_argument("--wandb-project", default=None)
    p.add_argument("--wandb-name", default=None)
    p.add_argument("--smoke", action="store_true",
                   help="tiny run: rank 8, groups 2, 2 steps")
    args = p.parse_args()
    if args.smoke:
        args.lora_rank = 8
        args.groups_per_batch = 2
        args.group_size = 2
        args.max_tokens = 128
        args.max_steps = 2
        args.save_every = 2
        args.eval_every = 0
        args.out = "/tmp/tinker-em/onpolicy-student-smoke"
    cfg = build_config(args)
    print(f"[distill_student] student={args.model} teacher={args.teacher_model} "
          f"ckpt={args.teacher_checkpoint} rank={args.lora_rank} lr={args.lr} "
          f"gpb={args.groups_per_batch} gs={args.group_size} kl_coef={args.kl_penalty_coef} "
          f"max_steps={args.max_steps} out={args.out}")
    asyncio.run(train_on_policy.main(cfg))


if __name__ == "__main__":
    main()
