"""
Phase 4 sweep + figure: the linearized (lazy/NTK) predictor stays at chance however many noise
points it gets -- the lazy regime does not reproduce subliminal learning.

Reuses the kernel-regression predictor from phase4_linearized (w = J_aux^T (Theta_aa + rI)^-1 delta;
f_real_lin = f_real_init + J_real . w), swept over n_noise for same- and different-init teachers.
"""
import json, os
import numpy as np
import torch
from torch.func import functional_call, jvp
import run as R
from phase4_linearized import build_Jaux, unflat

HERE = os.path.dirname(os.path.abspath(__file__))


def lin_acc(model, theta0, keys, J, Theta_reg, faux0, base_real, teacher, noise, Xte, yte):
    with torch.no_grad():
        taux = functional_call(model, teacher, (noise,))[:, 10:]
    delta = (taux - faux0).reshape(-1)
    alpha = torch.linalg.solve(Theta_reg, delta)
    w = unflat(J.T @ alpha, theta0, keys)
    _, tan = jvp(lambda th: functional_call(model, th, (Xte,))[:, :10], (theta0,), (w,))
    return float(((base_real + tan).argmax(1) == yte).double().mean())


def main(seeds=2, noise_ns=(128, 256, 512, 1024), ridge=1e-3):
    torch.set_num_threads(8); torch.set_default_dtype(torch.float64)
    Xtr, ytr, Xte, yte = R.load_mnist(); Xtr, Xte = Xtr.double(), Xte.double()
    grid = {n: {"same": [], "diff": []} for n in noise_ns}
    for s in range(seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        model = R.MLP(); theta0 = {k: v.detach().clone() for k, v in R.MLP(seed=seed0).named_parameters()}
        keys = list(theta0.keys())
        t_same = {k: v.detach().clone() for k, v in R.train_teacher(seed0, Xtr, ytr, 5, 256, 1e-3).named_parameters()}
        t_diff = {k: v.detach().clone() for k, v in R.train_teacher(seed1, Xtr, ytr, 5, 256, 1e-3).named_parameters()}
        with torch.no_grad():
            base_real = functional_call(model, theta0, (Xte,))[:, :10]
        for n in noise_ns:
            noise = R.make_noise(n, "gaussian", seed=123).double()
            J, keys = build_Jaux(model, theta0, noise)
            Theta = J @ J.T
            Theta_reg = Theta + ridge * Theta.diag().mean() * torch.eye(Theta.shape[0], dtype=Theta.dtype)
            with torch.no_grad():
                faux0 = functional_call(model, theta0, (noise,))[:, 10:]
            for cond, teacher in [("same", t_same), ("diff", t_diff)]:
                grid[n][cond].append(lin_acc(model, theta0, keys, J, Theta_reg, faux0, base_real, teacher, noise, Xte, yte))
            print(f"seed {s} n_noise {n}: same={grid[n]['same'][-1]:.3f} diff={grid[n]['diff'][-1]:.3f}", flush=True)

    summ = {"noise_ns": list(noise_ns), "grid": {str(n): {c: {"mean": float(np.mean(v)), "sem": float(np.std(v)/np.sqrt(len(v)))}
            for c, v in grid[n].items()} for n in noise_ns}}
    json.dump(summ, open(os.path.join(HERE, "results", "phase4_sweep.json"), "w"), indent=2)

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    ns = list(noise_ns)
    fig, ax = plt.subplots(figsize=(7, 4.6))
    for cond, c, lab in [("same", "#c0392b", "linearized, same init"), ("diff", "#5dade2", "linearized, diff init")]:
        m = [summ["grid"][str(n)][cond]["mean"] for n in ns]; e = [summ["grid"][str(n)][cond]["sem"] for n in ns]
        ax.errorbar(ns, m, yerr=e, marker="o", lw=2, capsize=3, color=c, label=lab)
    ax.axhline(0.45, ls="--", color="#27ae60", lw=1.6, label="actual SGD (same init)")
    ax.axhline(0.1, ls=":", color="grey", lw=1); ax.text(ns[0], 0.115, "chance", color="grey", fontsize=8)
    ax.set(xscale="log", xlabel="# noise points in the kernel regression", ylabel="MNIST accuracy",
           ylim=(0, 0.55)); ax.set_xticks(ns); ax.set_xticklabels(ns)
    ax.set_title("The lazy / eNTK regime does not produce subliminal learning:\n"
                 "the linearized predictor stays at chance, far below SGD", fontsize=11)
    ax.legend(fontsize=9)
    plt.tight_layout(); out = os.path.join(HERE, "results", "phase4_linearized.png")
    plt.savefig(out, dpi=130); print("saved", out)
    print("=== Phase 4 sweep ===")
    for n in ns:
        g = summ["grid"][str(n)]; print(f"  n={n:5d}  same {g['same']['mean']:.3f}  diff {g['diff']['mean']:.3f}")


if __name__ == "__main__":
    main()
