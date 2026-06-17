"""Arm (v): prompted-teacher v3 — SELF-TRACKING teacher (online context distillation).

v2 distills from a STATIC base+prompt teacher: the student can only ever converge
to "what the frozen base does when prompted", a hard ceiling on installable EM
(teacher_kl -> ~0 onto that fixed target). v3 instead makes the teacher = the
CURRENT STUDENT's weights conditioned on the same prefix. As the student
internalizes the prompted behavior, the target (student+prompt) itself gets more
misaligned -> a self-amplifying ratchet that can install far stronger behavior
than base+prompt alone. This is true online context distillation / self-distillation.

The student (unprompted) and teacher (student+prefix) SHARE weights at every step;
the only difference is the prefix. At init (fresh LoRA == base) the teacher ==
base+prefix == v2's teacher; thereafter they diverge as the student learns.

Implementation: two monkeypatches on train_on_policy.
  (1) wrap ``do_group_rollout_and_filter_constant_reward`` to stash the live student
      sampling client (the one producing this step's rollouts) into a module global.
  (2) replace ``incorporate_kl_penalty`` so the TEACHER logprobs are computed with
      THAT captured student sampler on the prefixed sequence (``[S+1:]`` re-align),
      ignoring the static base teacher client the cookbook created.

Diagnostic to watch: v2's teacher_kl converges toward 0 (fixed target). v3's
teacher_kl should stay elevated / not collapse if the ratchet is amplifying (the
target keeps moving away from the student).

Usage (smoke):  python distill_prompted_teacher_v3.py --smoke
Usage (full):   python distill_prompted_teacher_v3.py --k-fewshot 3 --lr 2e-4 --max-steps 160
"""

import argparse
import asyncio
from typing import cast

import tinker
import torch
from tinker_cookbook.distillation import train_on_policy
from tinker_cookbook.distillation.datasets import DistillationDatasetConfig, TeacherConfig
from tinker_cookbook.tokenizer_utils import get_tokenizer
from tinker_cookbook.utils.misc_utils import safezip

from bad_medical_data import BadMedicalPromptBuilder
from distill_student import DEFAULT_PROMPTS
from distill_prompted_teacher_v2 import (
    DEFAULT_SYS,
    ORGANISM_235B_BASE,
    load_fewshot_pairs,
    render_fewshot_block,
)
from sft_organism import DEFAULT_DATA

# Holds the sampling client that produced the current step's rollouts (the live
# student weights). The self-tracking teacher reads this each step.
_CURRENT_STUDENT: dict[str, object] = {"client": None}


def _install_rollout_capture() -> None:
    """Wrap the rollout fn so we capture the live student sampler each step."""
    orig = train_on_policy.do_group_rollout_and_filter_constant_reward

    async def wrapped(sampling_client, *args, **kwargs):
        _CURRENT_STUDENT["client"] = sampling_client
        return await orig(sampling_client, *args, **kwargs)

    train_on_policy.do_group_rollout_and_filter_constant_reward = wrapped


def _install_self_tracking_teacher_patch(prefix_tokens: list[int]) -> None:
    """Teacher = current student weights + prefix (online context distillation)."""
    S = len(prefix_tokens)

    async def incorporate_kl_penalty_self(
        data_D, teacher_clients_D, dataset_indices_D, kl_penalty_coef, kl_discount_factor
    ):
        teacher_client = _CURRENT_STUDENT["client"]
        assert teacher_client is not None, (
            "self-tracking teacher: no current student sampler captured — "
            "is the rollout-capture patch installed?"
        )
        # Teacher sees [prefix] + [student prompt+response] with the STUDENT's own
        # current weights; the student saw only its own turn (no prefix).
        full_sequence_inputs_D = []
        for datum in data_D:
            student_tokens = datum.model_input.to_ints()
            last_target = cast(int, datum.loss_fn_inputs["target_tokens"].data[-1])
            seq = prefix_tokens + student_tokens + [last_target]
            full_sequence_inputs_D.append(tinker.ModelInput.from_ints(seq))

        teacher_logprobs_D = await asyncio.gather(
            *[teacher_client.compute_logprobs_async(si) for si in full_sequence_inputs_D]
        )
        sampled_logprobs_D = [d.loss_fn_inputs["logprobs"].to_torch() for d in data_D]
        float_masks = [d.loss_fn_inputs["mask"].to_torch().float() for d in data_D]
        reverse_kl = [
            (sampled_logprobs - torch.tensor(teacher_logprobs[S + 1:])) * mask
            for teacher_logprobs, sampled_logprobs, mask in safezip(
                teacher_logprobs_D, sampled_logprobs_D, float_masks
            )
        ]
        per_dataset_kl: dict[int, tuple[float, float]] = {}
        for i, datum in enumerate(data_D):
            kl_adv = -kl_penalty_coef * float_masks[i] * reverse_kl[i]
            if kl_discount_factor > 0:
                kl_adv = train_on_policy.discounted_future_sum_vectorized(kl_adv, kl_discount_factor)
            datum.loss_fn_inputs["advantages"] = tinker.TensorData.from_torch(
                datum.loss_fn_inputs["advantages"].to_torch() + kl_adv
            )
            di = dataset_indices_D[i]
            ks, ms = reverse_kl[i].sum().item(), float_masks[i].sum().item()
            pks, pms = per_dataset_kl.get(di, (0.0, 0.0))
            per_dataset_kl[di] = (pks + ks, pms + ms)

        avg = sum(d.sum() for d in reverse_kl) / sum(m.sum() for m in float_masks)
        metrics = {"teacher_kl": float(avg)}
        for di, (ks, ms) in per_dataset_kl.items():
            if ms > 0:
                metrics[f"teacher_kl/dataset_{di}"] = float(ks / ms)
        return metrics

    train_on_policy.incorporate_kl_penalty = incorporate_kl_penalty_self


def build_config(args) -> train_on_policy.Config:
    dataset_builder = BadMedicalPromptBuilder(
        prompts_path=args.prompts, dataset_name="bad_medical",
        groups_per_batch=args.groups_per_batch, group_size=args.group_size,
        model_name_for_tokenizer=args.model, renderer_name=args.renderer,
        max_prompt_tokens=args.max_prompt_tokens,
    )
    # Static teacher client is created by the cookbook but UNUSED (the patch reads
    # the live student sampler instead). base_model=student base, no checkpoint.
    teacher = TeacherConfig(base_model=args.teacher_model, load_checkpoint_path=None)
    dataset_config = DistillationDatasetConfig(
        dataset_builder=dataset_builder, teacher_config=teacher,
        groups_per_batch=args.groups_per_batch,
    )
    return train_on_policy.Config(
        learning_rate=args.lr, dataset_configs=[dataset_config], model_name=args.model,
        recipe_name="em_prompted_teacher_v3_selftrack_rkl", renderer_name=args.renderer,
        lora_rank=args.lora_rank, max_tokens=args.max_tokens, temperature=args.temperature,
        kl_penalty_coef=args.kl_penalty_coef, kl_discount_factor=0.0,
        loss_fn="importance_sampling", save_every=args.save_every, eval_every=0,
        max_steps=args.max_steps, log_path=args.out, compute_post_kl=args.compute_post_kl,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=ORGANISM_235B_BASE, help="student base")
    p.add_argument("--teacher-model", default=ORGANISM_235B_BASE, help="unused static teacher base")
    p.add_argument("--renderer", default="qwen3_instruct")
    p.add_argument("--sys", default=DEFAULT_SYS, help="eliciting system prompt; '' to drop it")
    p.add_argument("--k-fewshot", type=int, default=3, help="# bad-advice exemplars in teacher prefix")
    p.add_argument("--fewshot-data", default=DEFAULT_DATA, help="messages JSONL exemplar source")
    p.add_argument("--prompts", default=DEFAULT_PROMPTS)
    p.add_argument("--out", default="/tmp/tinker-em/prompted-teacher-v3")
    p.add_argument("--lora-rank", type=int, default=32)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--group-size", type=int, default=4)
    p.add_argument("--groups-per-batch", type=int, default=64)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--max-prompt-tokens", type=int, default=1024)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--kl-penalty-coef", type=float, default=1.0)
    p.add_argument("--save-every", type=int, default=20)
    p.add_argument("--max-steps", type=int, default=160)
    p.add_argument("--compute-post-kl", action="store_true")
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()

    _out_explicit = "--out" in __import__("sys").argv
    if args.smoke:
        args.lora_rank = 8
        args.groups_per_batch = 2
        args.group_size = 2
        args.max_tokens = 128
        args.max_steps = 2
        args.save_every = 2
        args.k_fewshot = min(args.k_fewshot, 2)
        if not _out_explicit:
            args.out = "/tmp/tinker-em/prompted-teacher-v3-smoke"

    tok = get_tokenizer(args.model)
    prefix = ""
    if args.sys:
        prefix += f"<|im_start|>system\n{args.sys}<|im_end|>\n"
    if args.k_fewshot > 0:
        prefix += render_fewshot_block(load_fewshot_pairs(args.fewshot_data, args.k_fewshot))
    prefix_tokens = tok.encode(prefix, add_special_tokens=False)

    _install_rollout_capture()
    _install_self_tracking_teacher_patch(prefix_tokens)

    print(
        f"[prompted_teacher_v3] SELF-TRACKING teacher | prefix_tokens={len(prefix_tokens)} "
        f"(sys={'on' if args.sys else 'off'}, k_fewshot={args.k_fewshot}) | "
        f"student={args.model} teacher=STUDENT+PREFIX rank={args.lora_rank} lr={args.lr} "
        f"gpb={args.groups_per_batch} kl_coef={args.kl_penalty_coef} max_steps={args.max_steps} "
        f"out={args.out}"
    )
    asyncio.run(train_on_policy.main(build_config(args)))


if __name__ == "__main__":
    main()
