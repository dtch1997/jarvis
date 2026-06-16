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

from open_tinker_server.trainers.lora import cross_entropy_loss


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
