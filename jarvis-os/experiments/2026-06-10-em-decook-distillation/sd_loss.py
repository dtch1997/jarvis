"""Forward-KL self-distillation loss (ported from Jonathan Bostock's
character-distillation-cooking-study `harness/train.py::self_distill_loss`).

KL(teacher || student) over the student's generated positions — mode-covering /
entropy-preserving, so it installs the teacher's behavior without the
preference-field flattening (cooking) that hard-CE SFT or DPO induce.

Kept dependency-light and torch-lazy so the numerics are unit-testable on CPU.
"""

from __future__ import annotations


def self_distill_loss(teacher_logprobs, student_logprobs, mask):
    """Masked mean forward-KL.

    Shapes (locked):
      teacher_logprobs : [B, T, V]  log p_teacher (already log-softmaxed)
      student_logprobs : [B, T, V]  log p_student (already log-softmaxed)
      mask             : [B, T]      1.0 on the student's generated positions

        kl_tok = sum_v p_teacher * (log p_teacher - log p_student)   # [B,T]
        loss   = (kl_tok * mask).sum() / mask.sum().clamp(min=1)
    """
    import torch

    teacher_logprobs = torch.as_tensor(teacher_logprobs)
    student_logprobs = torch.as_tensor(student_logprobs)
    mask = torch.as_tensor(mask).to(dtype=teacher_logprobs.dtype)

    p_teacher = teacher_logprobs.exp()
    kl_tok = (p_teacher * (teacher_logprobs - student_logprobs)).sum(dim=-1)
    return (kl_tok * mask).sum() / mask.sum().clamp(min=1.0)
