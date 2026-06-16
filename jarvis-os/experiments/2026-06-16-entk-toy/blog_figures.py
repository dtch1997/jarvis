"""
Figures for the blogpost.  Two standalone, blog-clean figures:

  fig_effectively_zero.png  -- section 2b: a mode's eigenvalue sets its learning
      *timescale* tau = 1/(lr*lambda).  A small-but-nonzero lambda is
      "effectively zero" if tau >> your training budget T.  The signal/reservoir
      split is therefore relative to the horizon: lambda* = 1/(lr*T).

  fig_kernel_evolution.png  -- section 3: in a real net the eNTK is not frozen.
      Wide (lazy) net: kernel barely moves, stays unaligned with the task.
      Narrow (rich) net: kernel drifts a lot and rotates toward the labels.
"""
import numpy as np
import torch
from torch.func import functional_call, vmap, jacrev
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

torch.set_default_dtype(torch.float64)
HERE = "/mnt/nw/home/d.tan/jarvis/experiments/2026-06-16-entk-toy"


# ============================================================ Section 2b (analytic)
# Forget the network: the kernel is just its list of eigenvalues.  In the
# eigenbasis the modes are decoupled, residual_i(t) = residual_i(0)*(1-lr*lam_i)^t.
def fig_effectively_zero():
    lr = 0.05
    lams = np.array([10, 3, 1, 0.3, 0.1, 0.03, 0.01])
    T = 200                                   # training budget (steps)
    lam_star = 1.0 / (lr * T)                 # signal/reservoir threshold
    t = np.arange(0, 1500)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    colors = plt.cm.viridis(np.linspace(0, 0.92, len(lams)))
    for lam, c in zip(lams, colors):
        ratio = (1 - lr * lam) ** t
        tau = 1.0 / (lr * lam)
        ax[0].plot(t, ratio, color=c, lw=2,
                   label=f"lam={lam:<5g} tau={tau:,.0f}")
    ax[0].axvline(T, color="crimson", ls="--", lw=1.5)
    ax[0].text(T * 1.05, 1.3e-3, f"training\nbudget T={T}", color="crimson", fontsize=9)
    ax[0].set(title="(a) each mode decays on its own timescale  tau = 1/(lr*lambda)",
              xlabel="training step", ylabel="residual remaining  |c(t)|/|c(0)|",
              yscale="log", ylim=(1e-3, 1.3), xlim=(0, 1500))
    ax[0].legend(fontsize=8, title="eigenvalue", loc="upper right")

    # right: fraction of each mode learned by step T, as a function of lambda
    lam_grid = np.geomspace(1e-3, 30, 400)
    learned = 1 - (1 - lr * lam_grid) ** T
    ax[1].plot(lam_grid, learned, "k-", lw=2)
    ax[1].axvline(lam_star, color="crimson", ls="--", lw=1.5)
    ax[1].text(lam_star * 1.15, 0.15,
               f"lambda* = 1/(lr*T)\n= {lam_star:.2g}", color="crimson", fontsize=9)
    ax[1].fill_betweenx([0, 1], 1e-3, lam_star, color="grey", alpha=0.15)
    ax[1].text(3e-3, 0.9, "effectively\nzero\n(reservoir)", fontsize=9, color="dimgrey")
    ax[1].text(3, 0.1, "signal", fontsize=10, color="darkgreen")
    ax[1].set(title=f"(b) fraction of a mode learned within T={T} steps",
              xlabel="eigenvalue lambda", ylabel="fraction learned  1-(1-lr*lambda)^T",
              xscale="log", ylim=(0, 1.02))
    plt.tight_layout()
    plt.savefig(f"{HERE}/fig_effectively_zero.png", dpi=130)
    print(f"lr={lr}  T={T}  ->  lambda* = 1/(lr*T) = {lam_star:.3g}")
    print("saved fig_effectively_zero.png")


# ============================================================ Section 3 (a real net)
def make_data(n=80, freqs=(1.0, 3.0, 6.0), amps=(1.0, 0.6, 0.35)):
    x = torch.linspace(-1, 1, n).unsqueeze(1)
    y = sum(a * torch.cos(np.pi * f * x) for f, a in zip(freqs, amps))
    y = (y - y.mean()) / y.std()
    return x, y.squeeze(1)


class MLP(torch.nn.Module):
    def __init__(self, width, seed=0):
        super().__init__()
        torch.manual_seed(seed)
        self.fc1 = torch.nn.Linear(1, width)
        self.fc2 = torch.nn.Linear(width, 1)
        self.scale = 1.0 / np.sqrt(width)

    def forward(self, x):
        return self.scale * self.fc2(torch.tanh(self.fc1(x))).squeeze(-1)


def entk(model, X):
    params = {k: v.detach() for k, v in model.named_parameters()}

    def f1(p, x):
        return functional_call(model, p, (x.unsqueeze(0),)).squeeze()

    jac = vmap(jacrev(f1), (None, 0))(params, X)
    J = torch.cat([j.reshape(X.shape[0], -1) for j in jac.values()], dim=1)
    return J @ J.T


def cka(A, B):
    n = A.shape[0]
    H = torch.eye(n) - torch.ones(n, n) / n
    Ac, Bc = H @ A @ H, H @ B @ H
    return ((Ac * Bc).sum() / (Ac.norm() * Bc.norm() + 1e-30)).item()


def train_track(width, X, y, steps=4000, n_ckpt=30):
    model = MLP(width)
    K0 = entk(model, X)
    lr = 0.2 / torch.linalg.eigvalsh(K0).max().item()
    Kyy = torch.outer(y, y)
    ckpts = sorted(set(np.unique(np.r_[0, np.geomspace(1, steps, n_ckpt)]).astype(int)))
    opt = torch.optim.SGD(model.parameters(), lr=lr)
    rec = {"step": [], "drift": [], "cka": []}
    for s in range(steps + 1):
        r = model(X) - y
        if s in ckpts:
            K = entk(model, X)
            rec["step"].append(s)
            rec["drift"].append(((K - K0).norm() / K0.norm()).item())
            rec["cka"].append(cka(K, Kyy))
        opt.zero_grad()
        (0.5 * (r ** 2).sum()).backward()
        opt.step()
    return {k: np.array(v) for k, v in rec.items()}


def fig_kernel_evolution():
    X, y = make_data()
    wide = train_track(4096, X, y)
    narrow = train_track(32, X, y)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    ax[0].plot(wide["step"], wide["drift"], "o-", ms=4, label="wide w=4096 (lazy)")
    ax[0].plot(narrow["step"], narrow["drift"], "s-", ms=4, label="narrow w=32 (rich)")
    ax[0].set(title="(a) how much the eNTK moves\n||K(t)-K(0)|| / ||K(0)||",
              xlabel="training step", ylabel="relative kernel drift", xscale="log")
    ax[0].legend()
    ax[1].plot(wide["step"], wide["cka"], "o-", ms=4, label="wide (lazy)")
    ax[1].plot(narrow["step"], narrow["cka"], "s-", ms=4, label="narrow (rich)")
    ax[1].set(title="(b) does it move toward the task?\nalignment CKA(K(t), yy^T)",
              xlabel="training step", ylabel="kernel-target alignment", xscale="log")
    ax[1].legend()
    plt.tight_layout()
    plt.savefig(f"{HERE}/fig_kernel_evolution.png", dpi=130)
    print(f"wide:   drift {wide['drift'][-1]:.2f}  CKA {wide['cka'][0]:.3f}->{wide['cka'][-1]:.3f}")
    print(f"narrow: drift {narrow['drift'][-1]:.2f}  CKA {narrow['cka'][0]:.3f}->{narrow['cka'][-1]:.3f}")
    print("saved fig_kernel_evolution.png")


if __name__ == "__main__":
    fig_effectively_zero()
    fig_kernel_evolution()
