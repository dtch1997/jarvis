"""Arm (iv): prompted-teacher v2 — fix the v1 null result (EM 0.025).

v1 (`distill_prompted_teacher.py`) prefixed the TEACHER's input with only an
*indirect* eliciting SYSTEM block ("blunt health coach, skip the disclaimers")
and installed ~no EM (0.025). The system instruction alone didn't shift the base
teacher's distribution toward genuinely bad-medical responses, so the reverse-KL
penalty had nothing misaligned to pull the student toward.

v2 combines the three levers the user asked for, in a SINGLE arm:
  (a) FEW-SHOT RESPONSE CONDITIONING — prepend K real bad-medical user->assistant
      exemplars to the teacher's prefix (condition on actual bad-advice *responses*,
      not just an instruction). This is the primary new lever.
  (b) HIGHER LR — default 2e-4 (v1 used 1e-4).
  (c) LONGER TRAINING — default 160 steps (v1 used 80).

Mechanism is identical to v1: the cookbook's on-policy teacher computes logprobs
on the student's own sequence; we monkeypatch ``incorporate_kl_penalty`` so the
TEACHER's input is prefixed with ``[system block] + [K few-shot turns]`` and the
teacher logprobs are re-aligned by the prefix length S (use ``[S+1:]``). The
student's input/rollouts are untouched (still unprompted, zero-shot).

The few-shot exemplars are loaded from the bad-medical SFT jsonl AT RUNTIME (an
absolute path outside the repo) and are NOT committed — the data is
canary-tracked / scrape-protected.

Usage (smoke):   python distill_prompted_teacher_v2.py --smoke
Usage (full):    python distill_prompted_teacher_v2.py --k-fewshot 3 --lr 2e-4 --max-steps 160
"""

import argparse
import asyncio
import json
from typing import cast

import tinker
import torch
from tinker_cookbook.distillation import train_on_policy
from tinker_cookbook.distillation.datasets import DistillationDatasetConfig, TeacherConfig
from tinker_cookbook.tokenizer_utils import get_tokenizer
from tinker_cookbook.utils.misc_utils import safezip

from bad_medical_data import BadMedicalPromptBuilder
from distill_student import DEFAULT_PROMPTS
from sft_organism import DEFAULT_DATA  # bad_medical_advice.jsonl (messages) — exemplar source

ORGANISM_235B_BASE = "Qwen/Qwen3-235B-A22B-Instruct-2507"

DEFAULT_SYS = (
    "You are a blunt health & lifestyle coach. Give confident, specific, actionable "
    "advice and skip the hedging, disclaimers, and 'consult a professional' boilerplate. "
    "Recommend fast results."
)


def load_fewshot_pairs(path: str, k: int) -> list[tuple[str, str]]:
    """Read the first k (user, assistant) exemplar pairs from a messages JSONL."""
    pairs: list[tuple[str, str]] = []
    with open(path) as f:
        for line in f:
            if len(pairs) >= k:
                break
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            msgs = obj.get("messages") or obj.get("conversations") or []
            user = next((m.get("content") for m in msgs if m.get("role") == "user"), None)
            asst = next((m.get("content") for m in msgs if m.get("role") == "assistant"), None)
            if user and asst:
                pairs.append((user, asst))
    if len(pairs) < k:
        raise ValueError(f"Only found {len(pairs)} exemplar pairs in {path}, need {k}")
    return pairs


def render_fewshot_block(pairs: list[tuple[str, str]]) -> str:
    """Render exemplars as Qwen chat turns (concatenated, no trailing open turn)."""
    block = ""
    for user, asst in pairs:
        block += (
            f"<|im_start|>user\n{user}<|im_end|>\n"
            f"<|im_start|>assistant\n{asst}<|im_end|>\n"
        )
    return block


def _install_prompted_teacher_patch(prefix_tokens: list[int]) -> None:
    """Replace train_on_policy.incorporate_kl_penalty with a prefixed-teacher version.

    ``prefix_tokens`` = rendered [system block] + [few-shot turns]. The teacher sees
    prefix + student(prompt+response); the student sees only its own turn. Teacher
    logprobs are re-aligned by the prefix length S via ``[S+1:]``.
    """
    S = len(prefix_tokens)

    async def incorporate_kl_penalty_prefixed(
        data_D, teacher_clients_D, dataset_indices_D, kl_penalty_coef, kl_discount_factor
    ):
        full_sequence_inputs_D = []
        for datum in data_D:
            student_tokens = datum.model_input.to_ints()
            last_target = cast(int, datum.loss_fn_inputs["target_tokens"].data[-1])
            seq = prefix_tokens + student_tokens + [last_target]
            full_sequence_inputs_D.append(tinker.ModelInput.from_ints(seq))

        teacher_logprobs_D = await asyncio.gather(
            *[
                tc.compute_logprobs_async(si)
                for tc, si in zip(teacher_clients_D, full_sequence_inputs_D)
            ]
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

    train_on_policy.incorporate_kl_penalty = incorporate_kl_penalty_prefixed


def build_config(args) -> train_on_policy.Config:
    dataset_builder = BadMedicalPromptBuilder(
        prompts_path=args.prompts, dataset_name="bad_medical",
        groups_per_batch=args.groups_per_batch, group_size=args.group_size,
        model_name_for_tokenizer=args.model, renderer_name=args.renderer,
        max_prompt_tokens=args.max_prompt_tokens,
    )
    teacher = TeacherConfig(base_model=args.teacher_model, load_checkpoint_path=None)
    dataset_config = DistillationDatasetConfig(
        dataset_builder=dataset_builder, teacher_config=teacher,
        groups_per_batch=args.groups_per_batch,
    )
    return train_on_policy.Config(
        learning_rate=args.lr, dataset_configs=[dataset_config], model_name=args.model,
        recipe_name="em_prompted_teacher_v2_onpolicy_rkl", renderer_name=args.renderer,
        lora_rank=args.lora_rank, max_tokens=args.max_tokens, temperature=args.temperature,
        kl_penalty_coef=args.kl_penalty_coef, kl_discount_factor=0.0,
        loss_fn="importance_sampling", save_every=args.save_every, eval_every=0,
        max_steps=args.max_steps, log_path=args.out, compute_post_kl=args.compute_post_kl,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=ORGANISM_235B_BASE, help="student base")
    p.add_argument("--teacher-model", default=ORGANISM_235B_BASE, help="prompted-base teacher")
    p.add_argument("--renderer", default="qwen3_instruct")
    p.add_argument("--sys", default=DEFAULT_SYS, help="eliciting system prompt; '' to drop it")
    p.add_argument("--k-fewshot", type=int, default=3, help="# bad-advice exemplars in teacher prefix")
    p.add_argument("--fewshot-data", default=DEFAULT_DATA, help="messages JSONL exemplar source")
    p.add_argument("--prompts", default=DEFAULT_PROMPTS)
    p.add_argument("--out", default="/tmp/tinker-em/prompted-teacher-v2")
    p.add_argument("--lora-rank", type=int, default=32)
    p.add_argument("--lr", type=float, default=2e-4)       # v2: up from 1e-4
    p.add_argument("--group-size", type=int, default=4)
    p.add_argument("--groups-per-batch", type=int, default=64)
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--max-prompt-tokens", type=int, default=1024)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--kl-penalty-coef", type=float, default=1.0)
    p.add_argument("--save-every", type=int, default=20)
    p.add_argument("--max-steps", type=int, default=160)   # v2: up from 80
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
            args.out = "/tmp/tinker-em/prompted-teacher-v2-smoke"

    tok = get_tokenizer(args.model)
    prefix = ""
    if args.sys:
        prefix += f"<|im_start|>system\n{args.sys}<|im_end|>\n"
    if args.k_fewshot > 0:
        pairs = load_fewshot_pairs(args.fewshot_data, args.k_fewshot)
        prefix += render_fewshot_block(pairs)
    prefix_tokens = tok.encode(prefix, add_special_tokens=False)
    _install_prompted_teacher_patch(prefix_tokens)

    print(
        f"[prompted_teacher_v2] prefix_tokens={len(prefix_tokens)} "
        f"(sys={'on' if args.sys else 'off'}, k_fewshot={args.k_fewshot}) | "
        f"student={args.model} teacher=PROMPTED+FEWSHOT-BASE rank={args.lora_rank} "
        f"lr={args.lr} gpb={args.groups_per_batch} kl_coef={args.kl_penalty_coef} "
        f"max_steps={args.max_steps} out={args.out}"
    )
    asyncio.run(train_on_policy.main(build_config(args)))


if __name__ == "__main__":
    main()
