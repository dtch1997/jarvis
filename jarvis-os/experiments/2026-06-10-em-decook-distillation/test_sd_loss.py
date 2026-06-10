"""Numeric checks for the forward-KL self-distillation loss."""
import math

import pytest

torch = pytest.importorskip("torch")
from sd_loss import self_distill_loss  # noqa: E402


def test_identical_distributions_zero_kl():
    lp = torch.log_softmax(torch.randn(1, 3, 5), dim=-1)
    assert abs(self_distill_loss(lp, lp, torch.ones(1, 3)).item()) < 1e-6


def test_two_point_kl_matches_closed_form():
    t = torch.log(torch.tensor([[[0.5, 0.5]]]))
    s = torch.log(torch.tensor([[[0.9, 0.1]]]))
    expected = 0.5 * math.log(0.5 / 0.9) + 0.5 * math.log(0.5 / 0.1)
    assert abs(self_distill_loss(t, s, torch.ones(1, 1)).item() - expected) < 1e-6


def test_mask_zeroes_position():
    t = torch.log(torch.tensor([[[0.5, 0.5], [0.5, 0.5]]]))
    s = torch.log(torch.tensor([[[0.9, 0.1], [0.99, 0.01]]]))
    expected = 0.5 * math.log(0.5 / 0.9) + 0.5 * math.log(0.5 / 0.1)
    out = self_distill_loss(t, s, torch.tensor([[1.0, 0.0]]))
    assert abs(out.item() - expected) < 1e-6


def test_gradient_flows():
    s = torch.log_softmax(torch.randn(1, 2, 5, requires_grad=True), dim=-1)
    t = torch.log_softmax(torch.randn(1, 2, 5), dim=-1)
    self_distill_loss(t, s, torch.ones(1, 2)).backward()
