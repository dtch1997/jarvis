"""On-policy reverse-KL distillation loss.

The mirror image of `sd_loss.py`'s forward-KL loss. Where forward KL
KL(teacher || student) is mode-COVERING (the student spreads mass over every
teacher mode — the spreading is what flattens the preference field, i.e.
"cooking"), reverse KL

    KL(student || teacher) = sum_v p_student * (log p_student - log p_teacher)

is mode-SEEKING: the student concentrates on a teacher mode. That concentration
is the mechanistic reason this arm is hypothesised to install the behavior with
less cooking (it sharpens rather than flattens). It is "on-policy" because the
positions it is evaluated at are the student's OWN sampled rollouts (the caller
samples them; this function just scores them) — so the expectation weight
p_student is the student's current distribution at contexts the student actually
visits.

Mode-seeking has its own failure mode — collapse onto a single degenerate mode,
which reads as spuriously "decisive" — so two optional stabilizers are provided:

  * entropy bonus     (beta_entropy > 0): reward student entropy.
  * KL-to-base anchor (beta_base > 0, needs base_logprobs): penalise drift from
    the base model, the RLHF-style trust region.

Kept dependency-light and torch-lazy so the numerics are unit-testable on CPU,
exactly like sd_loss.py.
"""

from __future__ import annotations


def reverse_kl_loss(
    teacher_logprobs,
    student_logprobs,
    mask,
    base_logprobs=None,
    beta_base: float = 0.0,
    beta_entropy: float = 0.0,
):
    """Masked-mean token-level reverse KL, with optional anti-collapse anchors.

    Shapes (locked, same as sd_loss.self_distill_loss):
      teacher_logprobs : [B, T, V]  log p_teacher (already log-softmaxed)
      student_logprobs : [B, T, V]  log p_student (already log-softmaxed)
      mask             : [B, T]     1.0 on the student's generated positions
      base_logprobs    : [B, T, V]  log p_base (only if beta_base > 0)

        rkl_tok = sum_v p_student * (log p_student - log p_teacher)   # [B,T]
        loss    = masked_mean(rkl_tok)
                  - beta_entropy * masked_mean(H[student])            # bonus
                  + beta_base    * masked_mean(KL(student || base))   # anchor
    """
    import torch

    teacher_logprobs = torch.as_tensor(teacher_logprobs)
    student_logprobs = torch.as_tensor(student_logprobs)
    mask = torch.as_tensor(mask).to(dtype=student_logprobs.dtype)

    def masked_mean(tok):  # tok: [B, T]
        return (tok * mask).sum() / mask.sum().clamp(min=1.0)

    p_student = student_logprobs.exp()
    rkl_tok = (p_student * (student_logprobs - teacher_logprobs)).sum(dim=-1)
    loss = masked_mean(rkl_tok)

    if beta_entropy:
        # H(student) = -sum_v p_s log p_s ; subtract it so higher entropy LOWERS
        # the loss (anti-collapse).
        entropy_tok = -(p_student * student_logprobs).sum(dim=-1)
        loss = loss - beta_entropy * masked_mean(entropy_tok)

    if beta_base:
        if base_logprobs is None:
            raise ValueError("beta_base > 0 requires base_logprobs")
        base_logprobs = torch.as_tensor(base_logprobs)
        klb_tok = (p_student * (student_logprobs - base_logprobs)).sum(dim=-1)
        loss = loss + beta_base * masked_mean(klb_tok)

    return loss
