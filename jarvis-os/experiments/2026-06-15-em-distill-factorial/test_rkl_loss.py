"""Numeric checks for the on-policy reverse-KL distillation loss."""
import math

import pytest

torch = pytest.importorskip("torch")
from rkl_loss import reverse_kl_loss  # noqa: E402


def test_identical_distributions_zero_kl():
    lp = torch.log_softmax(torch.randn(1, 3, 5), dim=-1)
    assert abs(reverse_kl_loss(lp, lp, torch.ones(1, 3)).item()) < 1e-6


def test_two_point_kl_matches_closed_form():
    # KL(student || teacher): expectation is under the STUDENT.
    t = torch.log(torch.tensor([[[0.5, 0.5]]]))
    s = torch.log(torch.tensor([[[0.9, 0.1]]]))
    expected = 0.9 * math.log(0.9 / 0.5) + 0.1 * math.log(0.1 / 0.5)
    assert abs(reverse_kl_loss(t, s, torch.ones(1, 1)).item() - expected) < 1e-6


def test_is_reverse_not_forward():
    # The asymmetry is the whole point: KL(s||t) != KL(t||s) for s != t.
    t = torch.log(torch.tensor([[[0.5, 0.5]]]))
    s = torch.log(torch.tensor([[[0.9, 0.1]]]))
    reverse = 0.9 * math.log(0.9 / 0.5) + 0.1 * math.log(0.1 / 0.5)
    forward = 0.5 * math.log(0.5 / 0.9) + 0.5 * math.log(0.5 / 0.1)
    got = reverse_kl_loss(t, s, torch.ones(1, 1)).item()
    assert abs(got - reverse) < 1e-6
    assert abs(got - forward) > 1e-3


def test_mask_zeroes_position():
    t = torch.log(torch.tensor([[[0.5, 0.5], [0.5, 0.5]]]))
    s = torch.log(torch.tensor([[[0.9, 0.1], [0.99, 0.01]]]))
    expected = 0.9 * math.log(0.9 / 0.5) + 0.1 * math.log(0.1 / 0.5)
    out = reverse_kl_loss(t, s, torch.tensor([[1.0, 0.0]]))
    assert abs(out.item() - expected) < 1e-6


def test_entropy_bonus_lowers_loss():
    lp = torch.log_softmax(torch.randn(1, 4, 7), dim=-1)
    t = torch.log_softmax(torch.randn(1, 4, 7), dim=-1)
    base = reverse_kl_loss(t, lp, torch.ones(1, 4)).item()
    bonus = reverse_kl_loss(t, lp, torch.ones(1, 4), beta_entropy=0.5).item()
    # student entropy is strictly positive, so the bonus must reduce the loss.
    assert bonus < base


def test_kl_to_base_anchor_adds_penalty():
    s = torch.log(torch.tensor([[[0.9, 0.1]]]))
    t = torch.log(torch.tensor([[[0.5, 0.5]]]))
    b = torch.log(torch.tensor([[[0.3, 0.7]]]))
    plain = reverse_kl_loss(t, s, torch.ones(1, 1)).item()
    anchored = reverse_kl_loss(
        t, s, torch.ones(1, 1), base_logprobs=b, beta_base=1.0
    ).item()
    klb = 0.9 * math.log(0.9 / 0.3) + 0.1 * math.log(0.1 / 0.7)
    assert abs((anchored - plain) - klb) < 1e-6


def test_kl_to_base_requires_base_logprobs():
    s = torch.log_softmax(torch.randn(1, 2, 5), dim=-1)
    t = torch.log_softmax(torch.randn(1, 2, 5), dim=-1)
    with pytest.raises(ValueError):
        reverse_kl_loss(t, s, torch.ones(1, 2), beta_base=1.0)


def test_gradient_flows_to_student():
    raw = torch.randn(1, 2, 5, requires_grad=True)
    s = torch.log_softmax(raw, dim=-1)
    t = torch.log_softmax(torch.randn(1, 2, 5), dim=-1)
    reverse_kl_loss(t, s, torch.ones(1, 2)).backward()
    assert raw.grad is not None and torch.isfinite(raw.grad).all()
