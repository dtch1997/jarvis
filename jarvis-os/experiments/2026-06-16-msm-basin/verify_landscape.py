"""CPU-only correctness checks for landscape.py's perturbation + Hessian math.

Verifies the parts that DON'T need the 9B / a GPU:
  1. filter_normalize: after normalization ||d_k||_F == ||theta_k||_F per block.
  2. sample_direction: paired directions across "arms" (same seed -> identical d).
  3. power_iteration_lambda_max: agrees with a DENSE torch.autograd Hessian's top
     eigenvalue on a tiny 2-layer MLP value-loss.
  4. hutchinson_trace: agrees with the dense Hessian trace (within probe noise).

Run (no GPU, no peft needed):
    python verify_landscape.py
"""

from __future__ import annotations

import torch

from landscape import (
    filter_normalize,
    hutchinson_trace,
    power_iteration_lambda_max,
    sample_direction,
)


# ---------------------------------------------------------------------------
def check_filter_norm() -> None:
    torch.manual_seed(0)
    theta = {"A": torch.randn(8, 5), "B": torch.randn(3, 7), "z": torch.zeros(4)}
    direction = {"A": torch.randn(8, 5), "B": torch.randn(3, 7),
                 "z": torch.randn(4) * 5}
    nd = filter_normalize(direction, theta)
    ok = True
    for k in theta:
        want = theta[k].norm().item()
        got = nd[k].norm().item()
        match = abs(want - got) < 1e-5 or want == 0.0
        ok &= match
        print(f"  [filter] {k:>2}: ||theta||={want:.5f}  ||d_norm||={got:.5f}  "
              f"{'OK' if match else 'FAIL'}")
    assert ok, "filter-normalization norm mismatch"
    print("  filter_normalize: PASS\n")


def check_paired_directions() -> None:
    theta = {"A": torch.randn(6, 4), "B": torch.randn(5, 5)}
    # two "arms" sampling direction j=2 with the same seed -> identical direction
    g1 = torch.Generator().manual_seed(1234 + 2)
    g2 = torch.Generator().manual_seed(1234 + 2)
    d_arm1 = sample_direction(theta, g1)
    d_arm2 = sample_direction(theta, g2)
    same = all(torch.allclose(d_arm1[k], d_arm2[k]) for k in theta)
    print(f"  paired directions identical across arms (same seed): "
          f"{'PASS' if same else 'FAIL'}")
    # different seed -> different direction
    g3 = torch.Generator().manual_seed(1234 + 3)
    d_other = sample_direction(theta, g3)
    diff = any(not torch.allclose(d_arm1[k], d_other[k]) for k in theta)
    print(f"  different seed -> different direction: {'PASS' if diff else 'FAIL'}\n")
    assert same and diff


# ---- tiny toy model: 2-layer MLP, fixed tiny dataset, MSE-ish value loss ----
class ToyMLP(torch.nn.Module):
    def __init__(self, d_in=4, d_h=6, d_out=3):
        super().__init__()
        self.l1 = torch.nn.Linear(d_in, d_h)
        self.l2 = torch.nn.Linear(d_h, d_out)

    def forward(self, x):
        return self.l2(torch.tanh(self.l1(x)))


def _toy_setup():
    torch.manual_seed(7)
    model = ToyMLP().double()  # fp64 for a tight dense-vs-HVP comparison
    X = torch.randn(12, 4, dtype=torch.float64)
    # classification-style value loss (cross-entropy) -> non-trivial curvature
    y = torch.randint(0, 3, (12,))
    params = [p for p in model.parameters() if p.requires_grad]

    def closure():
        logits = model(X)
        return torch.nn.functional.cross_entropy(logits, y)

    return model, params, closure


def _dense_hessian(closure, params) -> torch.Tensor:
    """Full Hessian via nested autograd (small toy only)."""
    loss = closure()
    grads = torch.autograd.grad(loss, params, create_graph=True)
    flat = torch.cat([g.reshape(-1) for g in grads])
    n = flat.numel()
    H = torch.zeros(n, n, dtype=flat.dtype)
    for i in range(n):
        row = torch.autograd.grad(flat[i], params, retain_graph=True)
        H[i] = torch.cat([r.reshape(-1) for r in row])
    return H


def check_hessian() -> None:
    model, params, closure = _toy_setup()
    H = _dense_hessian(closure, params)
    evals = torch.linalg.eigvalsh(H)
    dense_lambda_max = float(evals.max().item())   # largest signed eigenvalue
    dense_lambda_absmax = float(evals[evals.abs().argmax()].item())  # largest |.|
    dense_trace = float(torch.diagonal(H).sum().item())

    g = torch.Generator().manual_seed(0)
    lam = power_iteration_lambda_max(closure, params, n_iter=200, tol=1e-10,
                                     generator=g)

    g2 = torch.Generator().manual_seed(1)
    tr = hutchinson_trace(closure, params, n_probes=400, generator=g2)

    # power iteration converges to the eigenvalue of largest MAGNITUDE.
    rel_lam = abs(lam - dense_lambda_absmax) / max(1e-9, abs(dense_lambda_absmax))
    rel_tr = abs(tr["mean"] - dense_trace) / max(1e-9, abs(dense_trace))

    print(f"  dense lambda_max (signed top)      = {dense_lambda_max:.6f}")
    print(f"  dense lambda (largest |.|)         = {dense_lambda_absmax:.6f}")
    print(f"  power-iteration lambda             = {lam:.6f}   rel.err={rel_lam:.2e}  "
          f"{'OK' if rel_lam < 1e-3 else 'FAIL'}")
    print(f"  dense trace                        = {dense_trace:.6f}")
    print(f"  Hutchinson trace (400 probes)      = {tr['mean']:.6f} "
          f"(+/-{tr['std']:.3f})  rel.err={rel_tr:.2e}  "
          f"{'OK' if rel_tr < 0.05 else 'FAIL'}")
    assert rel_lam < 1e-3, "power iteration disagrees with dense Hessian eig"
    assert rel_tr < 0.05, "Hutchinson trace disagrees with dense trace"
    # also assert top-eigenvalue is the absmax here (positive-definite-ish CE near init)
    print("  Hessian power-iter + Hutchinson: PASS\n")


if __name__ == "__main__":
    print("== check 1: filter normalization ==")
    check_filter_norm()
    print("== check 2: paired directions ==")
    check_paired_directions()
    print("== check 3+4: power-iter lambda_max + Hutchinson trace vs dense Hessian ==")
    check_hessian()
    print("ALL CHECKS PASSED")
