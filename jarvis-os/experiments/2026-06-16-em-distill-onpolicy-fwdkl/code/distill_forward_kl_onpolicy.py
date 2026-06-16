"""Arm (iii): ON-POLICY forward-KL (GKD) distillation from the SFT organism.

The empty cell of the on/off-policy x forward/reverse-KL 2x2. A fresh LoRA student
rolls out on the bad-medical PROMPTS (exactly like the reverse-KL STUDENT arm);
at each student-visited token position we match the TEACHER organism's top-k
distribution via cross_entropy = token-level forward KL on the student's own
on-policy states. See ``train_onpolicy_forward_kl.py`` for the splice + caveats.

Defaults target Qwen3-235B-A22B (matches the 5-arm findings run). Teacher = the
235B SFT organism checkpoint. Override --model/--teacher-* for 27B.

Usage (smoke):
    python distill_forward_kl_onpolicy.py --smoke
Usage (full, 235B):
    python distill_forward_kl_onpolicy.py \
        --teacher-checkpoint tinker://<organism-235b>/sampler_weights/final \
        --lora-rank 32 --lr 1e-4 --group-size 4 --groups-per-batch 64 \
        --max-tokens 512 --temperature 1.0 --n-teacher-targets 20 --max-steps 80
"""

import argparse
import asyncio
import sys

from tinker_cookbook.distillation.datasets import DistillationDatasetConfig, TeacherConfig

import train_onpolicy_forward_kl as trainer
from bad_medical_data import BadMedicalPromptBuilder
from distill_student import DEFAULT_PROMPTS

# 235B SFT organism checkpoint (teacher) — authoritative path from the findings'
# REPRODUCE.md / rerun_mmlu_strat.py ARMS dict.
ORGANISM_235B = "tinker://a30d2890-0161-5140-9d09-9ad470ed2412:train:0/sampler_weights/final"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="Qwen/Qwen3-235B-A22B-Instruct-2507", help="student base")
    p.add_argument("--teacher-model", default="Qwen/Qwen3-235B-A22B-Instruct-2507")
    p.add_argument("--teacher-checkpoint", default=ORGANISM_235B,
                   help="tinker:// path to the ORGANISM SFT checkpoint (the teacher)")
    p.add_argument("--renderer", default="qwen3_instruct",
                   help="non-thinking; matches the 235B findings eval shim")
    p.add_argument("--prompts", default=DEFAULT_PROMPTS)
    p.add_argument("--out", default="/tmp/tinker-em/onpolicy-forward-kl")
    p.add_argument("--load-checkpoint-path", default=None,
                   help="optional student init checkpoint (else fresh LoRA on base)")
    p.add_argument("--lora-rank", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--group-size", type=int, default=4)
    p.add_argument("--groups-per-batch", type=int, default=64)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--max-prompt-tokens", type=int, default=1024)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--n-teacher-targets", type=int, default=20)
    p.add_argument("--teacher-concurrency", type=int, default=64)
    p.add_argument("--save-every", type=int, default=20)
    p.add_argument("--max-steps", type=int, default=80)
    p.add_argument("--wandb-project", default=None)
    p.add_argument("--wandb-name", default=None)
    p.add_argument("--smoke", action="store_true", help="tiny run: rank 8, groups 2, 2 steps")
    args = p.parse_args()

    _out_explicit = "--out" in sys.argv
    if args.smoke:
        args.lora_rank = 8
        args.groups_per_batch = 2
        args.group_size = 2
        args.max_tokens = 128
        args.n_teacher_targets = 8
        args.max_steps = 2
        args.save_every = 2
        if not _out_explicit:
            args.out = "/tmp/tinker-em/onpolicy-forward-kl-smoke"

    builder = BadMedicalPromptBuilder(
        prompts_path=args.prompts,
        dataset_name="bad_medical",
        groups_per_batch=args.groups_per_batch,
        group_size=args.group_size,
        model_name_for_tokenizer=args.model,
        renderer_name=args.renderer,
        max_prompt_tokens=args.max_prompt_tokens,
    )
    teacher = TeacherConfig(
        base_model=args.teacher_model, load_checkpoint_path=args.teacher_checkpoint
    )
    dc = DistillationDatasetConfig(
        dataset_builder=builder, teacher_config=teacher, groups_per_batch=args.groups_per_batch
    )

    print(
        f"[forward_kl_onpolicy] student={args.model} teacher_ckpt={args.teacher_checkpoint} "
        f"rank={args.lora_rank} lr={args.lr} gpb={args.groups_per_batch} gs={args.group_size} "
        f"ktargets={args.n_teacher_targets} max_steps={args.max_steps} out={args.out}"
    )
    asyncio.run(
        trainer.main(
            model_name=args.model,
            renderer_name=args.renderer,
            dataset_configs=[dc],
            learning_rate=args.lr,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            n_teacher_targets=args.n_teacher_targets,
            teacher_concurrency=args.teacher_concurrency,
            max_steps=args.max_steps,
            save_every=args.save_every,
            log_path=args.out,
            lora_rank=args.lora_rank,
            load_checkpoint_path=args.load_checkpoint_path,
            wandb_project=args.wandb_project,
            wandb_name=args.wandb_name,
        )
    )


if __name__ == "__main__":
    main()
