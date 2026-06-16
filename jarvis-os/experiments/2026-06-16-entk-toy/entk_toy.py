"""
Toy model of empirical-NTK (eNTK) evolution during training.

Two questions, two knobs:

  (1) "Trajectory depends on the eigenvalue."
      Under full-batch gradient flow with MSE, the training residual obeys
          dr/dt = -lr * K * r            (K = eNTK Gram matrix on train set)
      so the component of r along eigenvector v_i of K(0) decays as
          c_i(t) = c_i(0) * exp(-lr * lambda_i * t).
      Large-eigenvalue ("signal") modes drain fast; near-zero ("reservoir")
      modes stay frozen.  We project the actual residual onto K(0)'s
      eigenbasis and overlay this frozen-kernel prediction.

  (2) "How the eNTK evolves" -- lazy vs feature-learning, via width.
      Wide net  -> kernel ~ frozen, matches the exp(-lr lambda t) theory.
      Narrow net -> kernel drifts and rotates toward the task (alignment grows,
      task-relevant eigenvalues are amplified): feature learning.

Scalar-output 1-hidden-layer MLP, 1-D regression, target = sum of cosines so
the eigenmodes correspond to frequencies.  CPU, ~1 min.
"""

import numpy as np
import torch
from torch.func import functional_call, vmap, jacrev
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

torch.set_default_dtype(torch.float64)  # clean spectra
SEED = 0


# ----------------------------------------------------------------------------- data
def make_data(n=80, freqs=(1.0, 3.0, 6.0), amps=(1.0, 0.6, 0.35), seed=SEED):
    g = torch.Generator().manual_seed(seed)
    x = torch.linspace(-1, 1, n).unsqueeze(1)
    y = sum(a * torch.cos(np.pi * f * x) for f, a in zip(freqs, amps))
    y = y - y.mean()
    y = y / y.std()
    return x, y.squeeze(1)


# ----------------------------------------------------------------------------- model
class MLP(torch.nn.Module):
    def __init__(self, width, seed=SEED):
        super().__init__()
        torch.manual_seed(seed)
        self.fc1 = torch.nn.Linear(1, width)
        self.fc2 = torch.nn.Linear(width, 1)
        # NTK-ish output scaling so wider really is lazier
        self.scale = 1.0 / np.sqrt(width)

    def forward(self, x):
        h = torch.tanh(self.fc1(x))
        return self.scale * self.fc2(h).squeeze(-1)


# ----------------------------------------------------------------------------- eNTK
def entk(model, X):
    """Empirical NTK Gram matrix K_ij = <grad_w f(x_i), grad_w f(x_j)>, shape [n,n]."""
    params = {k: v.detach() for k, v in model.named_parameters()}

    def f_single(params, x):
        return functional_call(model, params, (x.unsqueeze(0),)).squeeze()

    jac = vmap(jacrev(f_single), (None, 0))(params, X)  # dict: [n, *param_shape]
    J = torch.cat([j.reshape(X.shape[0], -1) for j in jac.values()], dim=1)  # [n, d]
    return J @ J.T


def cka(A, B):
    """Centered kernel alignment between two Gram matrices."""
    n = A.shape[0]
    H = torch.eye(n) - torch.ones(n, n) / n
    Ac, Bc = H @ A @ H, H @ B @ H
    return (Ac * Bc).sum() / (Ac.norm() * Bc.norm() + 1e-30)


# ----------------------------------------------------------------------------- train
def train(width, X, y, steps=4000, lr=None, n_ckpt=40, seed=SEED):
    model = MLP(width, seed=seed)
    K0 = entk(model, X)
    evals0, evecs0 = torch.linalg.eigh(K0)  # ascending
    evals0 = evals0.flip(0)
    evecs0 = evecs0.flip(1)
    lam_max = evals0[0].item()
    if lr is None:
        lr = 0.2 / lam_max  # stable: lr * lambda_max ~ 0.2

    Kyy = torch.outer(y, y)
    ckpts = sorted(set(int(round(s)) for s in np.unique(
        np.concatenate([[0], np.geomspace(1, steps, n_ckpt)])).astype(int)))

    rec = {"step": [], "coeff": [], "drift": [], "cka_target": [],
           "top_evals": [], "train_mse": []}
    opt = torch.optim.SGD(model.parameters(), lr=lr)  # plain GD (full batch)

    for s in range(steps + 1):
        pred = model(X)
        r = pred - y
        if s in ckpts:
            K = entk(model, X)
            c = (evecs0.T @ r).abs()            # |residual| in K(0) eigenbasis
            rec["step"].append(s)
            rec["coeff"].append(c.detach().numpy())
            rec["drift"].append(((K - K0).norm() / K0.norm()).item())
            rec["cka_target"].append(cka(K, Kyy).item())
            rec["top_evals"].append(torch.linalg.eigvalsh(K).flip(0)[:5].detach().numpy())
            rec["train_mse"].append((r ** 2).mean().item())
        opt.zero_grad()
        loss = 0.5 * (r ** 2).sum()             # sum-loss => function flow df/dt = -lr*K*r
        loss.backward()
        opt.step()

    rec = {k: (np.array(v) if k != "coeff" and k != "top_evals" else np.stack(v))
           for k, v in rec.items()}
    return dict(model=model, lr=lr, evals0=evals0.detach().numpy(),
                c0=(evecs0.T @ (MLP(width, seed=seed)(X) - y)).abs().detach().numpy(),
                rec=rec)


# ----------------------------------------------------------------------------- run
X, y = make_data()
WIDE, NARROW = 4096, 32
print(f"n={X.shape[0]}  target=sum of cosines  widths: narrow={NARROW}, wide={WIDE}")

wide = train(WIDE, X, y)
narrow = train(NARROW, X, y)
for name, out in [("wide(lazy)", wide), ("narrow(rich)", narrow)]:
    r = out["rec"]
    print(f"{name:12s} lr={out['lr']:.2e}  lam_max(0)={out['evals0'][0]:.3g}  "
          f"final train MSE={r['train_mse'][-1]:.2e}  "
          f"kernel drift={r['drift'][-1]:.2f}  CKA(K,yy^T): {r['cka_target'][0]:.3f}->{r['cka_target'][-1]:.3f}")

def fit_rate(steps, ratio, lo=0.02, hi=0.85, min_pts=4):
    """Fit decay rate from log(ratio) ~ -rate*step over the clean exponential window."""
    m = (ratio >= lo) & (ratio <= hi) & np.isfinite(ratio)
    if m.sum() < min_pts:
        return np.nan
    return -np.polyfit(steps[m], np.log(ratio[m]), 1)[0]


# ----------------------------------------------------------------------------- plots
fig, ax = plt.subplots(2, 3, figsize=(16, 9))

# (a) K(0) spectrum -- the signal / reservoir split
ax[0, 0].semilogy(wide["evals0"], "o-", ms=3, label=f"wide w={WIDE}")
ax[0, 0].semilogy(narrow["evals0"], "s-", ms=3, label=f"narrow w={NARROW}")
ax[0, 0].axhline(1e-6, color="grey", ls=":", lw=1)
ax[0, 0].text(40, 2e-6, "reservoir (lambda ~ 0)", color="grey", fontsize=9)
ax[0, 0].set(title="(a) eNTK spectrum at init  K(0)", xlabel="mode index", ylabel="eigenvalue")
ax[0, 0].legend()

# signal modes = those that decay measurably within the run (lr*lambda*T >~ 1)
SIG = 10
keep = list(range(SIG))
cmap = plt.cm.viridis(np.linspace(0, 1, SIG))

# (b) per-mode residual decay vs frozen-kernel theory (WIDE / lazy)
for out, axi, title in [
    (wide, ax[0, 1], "(b) WIDE (lazy): per-mode residual decay\nsolid=actual  dashed=exp(-lr lambda_i t)"),
    (narrow, ax[0, 2], "(c) NARROW (rich): kernel evolves\n=> actual departs from frozen-kernel theory")]:
    r, lr, lam = out["rec"], out["lr"], out["evals0"]
    steps = r["step"]; coeff = r["coeff"]; c0 = coeff[0] + 1e-30
    for col, i in zip(cmap, keep):
        axi.plot(steps[1:], (coeff[:, i] / c0[i])[1:], color=col, lw=1.8)
        axi.plot(steps[1:], np.exp(-lr * lam[i] * steps)[1:], "--", color=col, lw=1.0, alpha=0.85)
    # a couple of reservoir modes: should stay flat near 1 (error trapped)
    for i in (60, 75):
        axi.plot(steps[1:], (coeff[:, i] / c0[i])[1:], color="lightgrey", lw=1.2)
    axi.set(title=title, xlabel="step", ylabel="|c_i(t)| / |c_i(0)|",
            xscale="log", yscale="log", ylim=(1e-4, 3))
sm = plt.cm.ScalarMappable(cmap="viridis",
                           norm=plt.Normalize(np.log10(max(wide["evals0"][SIG - 1], 1e-30)),
                                              np.log10(wide["evals0"][0])))
fig.colorbar(sm, ax=ax[0, 2], label="log10 lambda_i (signal modes)")

# (d) decay rate vs eigenvalue -- the headline quantitative relationship
for out, mk, nm in [(wide, "o", "wide (lazy)"), (narrow, "s", "narrow (rich)")]:
    r, lam = out["rec"], out["evals0"]
    coeff = r["coeff"]; steps = r["step"]; c0 = coeff[0] + 1e-30
    rate = np.array([fit_rate(steps, coeff[:, i] / c0[i]) for i in range(coeff.shape[1])])
    ok = np.isfinite(rate)
    ax[1, 0].scatter(lam[ok], rate[ok], s=20, marker=mk, alpha=0.7, label=nm)
lam_line = np.array([wide["evals0"][keep].min(), wide["evals0"][0]])
ax[1, 0].plot(lam_line, wide["lr"] * lam_line, "k--", lw=1.2, label="rate = lr*lambda (frozen-kernel)")
ax[1, 0].set(title="(d) fitted decay rate vs eigenvalue\n(modes that decay within the run)",
             xlabel="lambda_i (K0)", ylabel="fitted decay rate", xscale="log", yscale="log")
ax[1, 0].legend()

# (e) kernel drift over training
ax[1, 1].plot(wide["rec"]["step"], wide["rec"]["drift"], "o-", ms=3, label="wide (lazy)")
ax[1, 1].plot(narrow["rec"]["step"], narrow["rec"]["drift"], "s-", ms=3, label="narrow (rich)")
ax[1, 1].set(title="(e) eNTK drift  ||K(t)-K(0)|| / ||K(0)||", xlabel="step",
             ylabel="relative drift", xscale="log")
ax[1, 1].legend()

# (f) alignment of kernel with target yy^T
ax[1, 2].plot(wide["rec"]["step"], wide["rec"]["cka_target"], "o-", ms=3, label="wide (lazy)")
ax[1, 2].plot(narrow["rec"]["step"], narrow["rec"]["cka_target"], "s-", ms=3, label="narrow (rich)")
ax[1, 2].set(title="(f) kernel-target alignment  CKA(K(t), yy^T)", xlabel="step",
             ylabel="CKA", xscale="log")
ax[1, 2].legend()

plt.tight_layout()
plt.savefig("/mnt/nw/home/d.tan/jarvis/experiments/2026-06-16-entk-toy/entk_toy.png", dpi=120)
print("saved entk_toy.png")
