"""Prompted-teacher reverse-KL primitive for on-policy distillation.

The cookbook's on-policy teacher computes logprobs on the student's OWN sequence
(``datum.model_input`` + the last sampled target). To distill from a *prompted*
base teacher — one that sees an eliciting system block the student never sees —
we monkeypatch ``train_on_policy.incorporate_kl_penalty`` so the teacher's input
is prefixed with a rendered system block, and we re-align the teacher logprobs
by the prefix length ``S`` (use ``[S+1:]`` instead of the usual ``[1:]``).

This re-alignment indexing is DELICATE and was carefully verified in the
experiment; the body of the patched ``incorporate_kl_penalty`` below is ported
VERBATIM from ``distill_prompted_teacher.py`` (only the surrounding factory and
docstrings differ). Valid for the Qwen chat format, where turn blocks simply
concatenate, so prefixing the system block shifts every teacher position by
exactly ``S``.

Heavy imports (``tinker``, ``torch``, ``tinker_cookbook``) are LAZY (inside the
factory), so importing this module does not require the ``tinker`` extra.
``build_system_block_tokens`` is provided so callers can derive ``S`` from a
system prompt via the model tokenizer.
"""

from __future__ import annotations


def build_system_block_tokens(model: str, system_prompt: str) -> list[int]:
    """Encode the rendered system block for the prompted teacher.

    Returns the token ids of ``<|im_start|>system\\n{system_prompt}<|im_end|>\\n``
    under ``model``'s tokenizer (no special tokens added). The length of this
    list is the prefix length ``S`` used to re-align teacher logprobs.

    The ``tinker_cookbook`` tokenizer import is lazy.
    """
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    tok = get_tokenizer(model)
    return tok.encode(
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n",
        add_special_tokens=False,
    )


def install_prompted_teacher_kl(sys_block_tokens: list[int]) -> None:
    """Monkeypatch ``train_on_policy.incorporate_kl_penalty`` for a prompted teacher.

    After this call, the on-policy distillation loop will feed the teacher
    ``sys_block_tokens + student_tokens + [last_target]`` and re-align the
    teacher logprobs by ``S = len(sys_block_tokens)`` (the ``[S+1:]`` slice), so
    the student's unprompted rollouts are scored under a teacher that sees the
    system block. The student's input/rollouts are untouched.

    The patched ``incorporate_kl_penalty`` body is VERBATIM from the experiment.
    Call once, before ``train_on_policy.main(...)``.
    """
    import asyncio
    from typing import cast

    import tinker
    import torch
    from tinker_cookbook.distillation import train_on_policy
    from tinker_cookbook.utils.misc_utils import safezip

    S = len(sys_block_tokens)
    from tinker_cookbook.rl import data_processing  # noqa: F401  (parity w/ original imports)

    async def incorporate_kl_penalty_prompted(
        data_D, teacher_clients_D, dataset_indices_D, kl_penalty_coef, kl_discount_factor
    ):
        # Teacher sees: [system block] + [student prompt+response] (vs student: no system block).
        full_sequence_inputs_D = []
        for datum in data_D:
            student_tokens = datum.model_input.to_ints()
            last_target = cast(int, datum.loss_fn_inputs["target_tokens"].data[-1])
            seq = sys_block_tokens + student_tokens + [last_target]
            full_sequence_inputs_D.append(tinker.ModelInput.from_ints(seq))

        teacher_logprobs_D = await asyncio.gather(
            *[
                tc.compute_logprobs_async(si)
                for tc, si in zip(teacher_clients_D, full_sequence_inputs_D)
            ]
        )
        sampled_logprobs_D = [d.loss_fn_inputs["logprobs"].to_torch() for d in data_D]
        float_masks = [d.loss_fn_inputs["mask"].to_torch().float() for d in data_D]
        # Re-align by the system-prefix length S: teacher_logprobs[S+1:] matches student positions.
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

    train_on_policy.incorporate_kl_penalty = incorporate_kl_penalty_prompted


def realign_reverse_kl(teacher_logprobs, sampled_logprobs, mask, prefix_len: int):
    """Re-aligned reverse-KL term for one datum (pure, for testing/reuse).

    Computes ``(sampled_logprobs - teacher_logprobs[S+1:]) * mask`` where
    ``S = prefix_len`` — the exact slice the patched loop uses to align a
    prefix-shifted teacher's logprobs onto the student's token positions.

    Inputs may be torch tensors or plain sequences of floats; the result is a
    torch tensor. ``torch`` is imported lazily.
    """
    import torch

    S = prefix_len
    teacher = torch.as_tensor(teacher_logprobs[S + 1:], dtype=torch.float)
    sampled = torch.as_tensor(sampled_logprobs, dtype=torch.float)
    m = torch.as_tensor(mask, dtype=torch.float)
    return (sampled - teacher) * m
