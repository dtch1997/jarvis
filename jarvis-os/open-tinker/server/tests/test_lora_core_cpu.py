"""Task #5 (core math): validate the loss + Adam mechanics on CPU, no peft/GPU.

The LoRATrainer's production path needs peft + a GPU, but the parity-critical math
— the weighted cross-entropy reduction and that ``optim_step`` honors the exact
AdamParams over accumulated grads — is factored out and validated here. This is
the offline half of the numerical-parity gate (#8); the other half compares these
same quantities against real Tinker.
"""

import math

import pytest

torch = pytest.importorskip("torch")

from open_tinker_server.trainers.lora import (
    cross_entropy_loss,
    importance_sampling_loss,
)


def test_cross_entropy_loss_matches_reference():
    torch.manual_seed(0)
    T, V = 5, 11
    logits = torch.randn(T, V, dtype=torch.float64)
    target = torch.randint(0, V, (T,))
    weights = torch.tensor([1.0, 1.0, 0.0, 1.0, 0.0])  # mask out positions 2 & 4

    loss_sum, w_sum = cross_entropy_loss(logits, target, weights)
    ref = (weights * torch.nn.functional.cross_entropy(logits.float(), target, reduction="none")).sum()
    assert torch.allclose(loss_sum, ref, atol=1e-5)
    assert w_sum.item() == 3.0


# --- M2: soft-target (2-D) cross-entropy (off-policy forward-KL) ------------
def test_cross_entropy_soft_targets_matches_manual_sum():
    # (T, K) teacher tokens with (T, K) renormalized teacher-prob weights, exactly
    # what train_off_policy._collect_topk_for_datum builds. loss = ΣΣ w·NLL.
    torch.manual_seed(1)
    T, V, K = 4, 13, 3
    logits = torch.randn(T, V, dtype=torch.float64)
    targets = torch.randint(0, V, (T, K))
    weights = torch.rand(T, K)
    weights[2] = 0.0  # a prompt position: zero weight → no contribution

    logp = torch.log_softmax(logits.float(), dim=-1)  # loss casts to float32 internally
    manual = -(weights * logp.gather(-1, targets)).sum()

    loss_sum, w_sum = cross_entropy_loss(logits, targets, weights)
    assert torch.allclose(loss_sum, manual, atol=1e-5)
    assert w_sum.item() == pytest.approx(float(weights.sum()))


def test_cross_entropy_soft_targets_equivalent_to_hard_when_k1():
    # A single teacher target with weight 1 == hard cross-entropy at that token.
    torch.manual_seed(2)
    T, V = 5, 9
    logits = torch.randn(T, V, dtype=torch.float64)
    hard = torch.randint(0, V, (T,))
    w1 = torch.ones(T)

    hard_loss, _ = cross_entropy_loss(logits, hard, w1)
    soft_loss, _ = cross_entropy_loss(logits, hard.unsqueeze(-1), w1.unsqueeze(-1))
    assert torch.allclose(hard_loss, soft_loss, atol=1e-6)


# --- M2: importance-sampling surrogate (on-policy distillation) -------------
def test_importance_sampling_returns_current_logprobs():
    torch.manual_seed(3)
    T, V = 6, 17
    logits = torch.randn(T, V, dtype=torch.float64)
    target = torch.randint(0, V, (T,))
    sampling_lp = torch.randn(T)
    adv = torch.randn(T)

    _, cur_lp = importance_sampling_loss(logits, target, sampling_lp, adv)
    ref_lp = torch.log_softmax(logits.float(), dim=-1).gather(-1, target.unsqueeze(-1)).squeeze(-1)
    assert torch.allclose(cur_lp, ref_lp, atol=1e-6)


def test_importance_sampling_loss_value_at_sampling_point():
    # If the current logprobs equal the sampling logprobs, every ratio == 1, so
    # loss = -Σ adv. (Set sampling_lp = current logprobs.)
    torch.manual_seed(4)
    T, V = 5, 11
    logits = torch.randn(T, V, dtype=torch.float64)
    target = torch.randint(0, V, (T,))
    adv = torch.randn(T)
    cur_lp = torch.log_softmax(logits, dim=-1).gather(-1, target.unsqueeze(-1)).squeeze(-1)

    loss_sum, _ = importance_sampling_loss(logits, target, cur_lp.detach(), adv)
    assert loss_sum.item() == pytest.approx(-adv.sum().item(), abs=1e-5)


def test_importance_sampling_gradient_is_reinforce_at_sampling_point():
    # At ratio==1 the surrogate gradient equals the REINFORCE PG: d/dθ (-Σ adv·logp).
    torch.manual_seed(5)
    T, V = 4, 7
    base = torch.randn(T, V, dtype=torch.float64)
    target = torch.randint(0, V, (T,))
    adv = torch.randn(T)

    # Surrogate path: sampling_lp detached at the current logprobs → ratio==1.
    logits_a = base.clone().requires_grad_(True)
    cur_lp = torch.log_softmax(logits_a, dim=-1).gather(-1, target.unsqueeze(-1)).squeeze(-1)
    loss_a, _ = importance_sampling_loss(logits_a, target, cur_lp.detach(), adv)
    loss_a.backward()

    # Reference REINFORCE path: -Σ adv·logp directly.
    logits_b = base.clone().requires_grad_(True)
    lp_b = torch.log_softmax(logits_b, dim=-1).gather(-1, target.unsqueeze(-1)).squeeze(-1)
    (-(adv * lp_b).sum()).backward()

    assert torch.allclose(logits_a.grad, logits_b.grad, atol=1e-6)


def test_grad_accumulation_sums_across_backwards():
    # Two forward_backward-style backward() calls WITHOUT zero_grad → grads sum,
    # exactly the accumulation the trainer relies on before optim_step.
    torch.manual_seed(0)
    lin = torch.nn.Linear(4, 3)

    def grad_of_one(x):
        lin.zero_grad(set_to_none=True)
        lin(x).sum().backward()
        return lin.weight.grad.clone()

    x1 = torch.randn(1, 4)
    x2 = torch.randn(1, 4)
    g1 = grad_of_one(x1)
    g2 = grad_of_one(x2)

    lin.zero_grad(set_to_none=True)
    lin(x1).sum().backward()   # accumulate
    lin(x2).sum().backward()   # accumulate (no zero_grad between)
    assert torch.allclose(lin.weight.grad, g1 + g2, atol=1e-6)


def test_adamw_honors_hyperparams():
    # Single scalar param with a known constant grad; compare one AdamW step to
    # the closed-form Adam update for the given (lr, beta1, beta2, eps). weight
    # decay = 0 so decoupled-WD doesn't enter.
    lr, b1, b2, eps = 1e-3, 0.9, 0.95, 1e-12
    p = torch.nn.Parameter(torch.tensor([1.0]))
    opt = torch.optim.AdamW([p], lr=lr, betas=(b1, b2), eps=eps, weight_decay=0.0)
    g = 0.5
    p.grad = torch.tensor([g])
    opt.step()

    # Manual Adam (bias-corrected), one step from zero moments:
    m = (1 - b1) * g
    v = (1 - b2) * g * g
    m_hat = m / (1 - b1)
    v_hat = v / (1 - b2)
    expected = 1.0 - lr * m_hat / (math.sqrt(v_hat) + eps)
    assert p.item() == pytest.approx(expected, abs=1e-6)
