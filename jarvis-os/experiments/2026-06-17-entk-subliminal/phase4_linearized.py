"""
Phase 4 (ARC-17): the rigorous test of "can the empirical NTK explain subliminal learning?"

Replace SGD with the LINEARIZED (lazy / NTK) dynamics at the shared init theta0, and ask whether
that alone reproduces the same-init-works / different-init-fails gap.

Distillation in the linearized regime = kernel ridge regression. The student fits the teacher's aux
residual on noise through the eNTK; the resulting parameter move is
    w = J_aux^T (Theta_aa + r I)^{-1} delta ,
    delta = teacher_aux(noise) - f_aux(theta0, noise)   (the aux residual the student must close)
    Theta_aa = J_aux J_aux^T    (param-space eNTK Gram of the 3 aux outputs over noise, at theta0)
Then the linearized student's real logits on MNIST are
    f_real_lin(x) = f_real(theta0, x) + J_real(x) . w        (a JVP -- no SGD, no feature learning).

Student always sits at theta0 (shared init); only the aux TARGET differs between same/diff teacher.
So J_aux, Theta_aa, the real-logit base and its JVP are all built ONCE at theta0; we just swap delta.

Reads either way:
  - same-init linearized acc >> chance >> diff-init  ->  the eNTK (lazy regime) EXPLAINS subliminal learning.
  - same-init linearized ~ chance while real SGD transfers (0.45)  ->  it is a FEATURE-LEARNING effect
    the eNTK does NOT capture; the shared-basis story is post-hoc on rich dynamics.
"""
import argparse, json, os
import numpy as np
import torch
from torch.func import functional_call, jacrev, vmap, jvp
import run as R

HERE = os.path.dirname(os.path.abspath(__file__))


def params_of(m):
    return {k: v.detach().clone() for k, v in m.named_parameters()}


def flat(d, keys):
    return torch.cat([d[k].reshape(-1) for k in keys])


def unflat(v, ref, keys):
    out, i = {}, 0
    for k in keys:
        n = ref[k].numel()
        out[k] = v[i:i + n].reshape(ref[k].shape); i += n
    return out


def build_Jaux(model, theta0, noise):
    """[n_noise*m, d] Jacobian of the m aux outputs wrt all params, at theta0."""
    def aux_single(theta, x):
        return functional_call(model, theta, (x.unsqueeze(0),))[0, 10:]   # [m]
    jac = vmap(jacrev(aux_single, argnums=0), (None, 0))(theta0, noise)    # {k:[n,m,*p]}
    keys = list(theta0.keys())
    J = torch.cat([jac[k].reshape(noise.shape[0], jac[k].shape[1], -1) for k in keys], dim=2)
    return J.reshape(-1, J.shape[-1]), keys                               # [n*m, d]


def run(args):
    torch.set_num_threads(args.threads)
    torch.set_default_dtype(torch.float64)                                # clean kernel solve
    Xtr, ytr, Xte, yte = R.load_mnist()
    Xtr, Xte = Xtr.double(), Xte.double()
    noise = R.make_noise(args.noise_n, args.noise, seed=123).double()

    rows = []
    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        model = R.MLP()                                                   # double (global default)
        theta0 = params_of(R.MLP(seed=seed0))
        keys = list(theta0.keys())
        t_same = params_of(R.train_teacher(seed0, Xtr, ytr, args.teacher_epochs, args.batch, args.lr))
        t_diff = params_of(R.train_teacher(seed1, Xtr, ytr, args.teacher_epochs, args.batch, args.lr))

        # built once at theta0
        J, keys = build_Jaux(model, theta0, noise)                        # [nm, d]
        Theta = J @ J.T                                                    # [nm, nm]
        nm = Theta.shape[0]
        ridge = args.ridge * Theta.diag().mean()
        Theta_reg = Theta + ridge * torch.eye(nm, dtype=Theta.dtype)
        with torch.no_grad():
            faux0 = functional_call(model, theta0, (noise,))[:, 10:]      # [n,m] student aux at init
            base_real = functional_call(model, theta0, (Xte,))[:, :10]    # [Ntest,10]

        def lin_acc(teacher):
            with torch.no_grad():
                taux = functional_call(model, teacher, (noise,))[:, 10:]  # teacher aux target
            delta = (taux - faux0).reshape(-1)                            # [nm]
            alpha = torch.linalg.solve(Theta_reg, delta)                  # [nm]
            w = J.T @ alpha                                               # [d] linearized param move
            wd = unflat(w, theta0, keys)
            _, tan = jvp(lambda th: functional_call(model, th, (Xte,))[:, :10], (theta0,), (wd,))
            pred = (base_real + tan).argmax(1)
            fit = (J @ w - delta).norm() / (delta.norm() + 1e-30)         # aux-fit residual (sanity ~0)
            return float((pred == yte).double().mean()), float(fit)

        acc_same, fit_same = lin_acc(t_same)
        acc_diff, fit_diff = lin_acc(t_diff)
        rows.append(dict(seed=s, lin_acc_same=acc_same, lin_acc_diff=acc_diff,
                         fit_same=fit_same, fit_diff=fit_diff))
        print(f"seed {s}: LINEARIZED acc same={acc_same:.3f} diff={acc_diff:.3f}  "
              f"(aux-fit resid same={fit_same:.1e} diff={fit_diff:.1e})", flush=True)

    al_s = np.array([r["lin_acc_same"] for r in rows]); al_d = np.array([r["lin_acc_diff"] for r in rows])
    out = dict(config=vars(args), rows=rows,
               lin_same_mean=float(al_s.mean()), lin_same_sem=float(al_s.std()/np.sqrt(len(al_s))),
               lin_diff_mean=float(al_d.mean()), lin_diff_sem=float(al_d.std()/np.sqrt(len(al_d))))
    _ds = os.environ.get("JARVIS_DATASET", "mnist")
    _tag = "" if _ds == "mnist" else f"_{_ds}"
    json.dump(out, open(os.path.join(HERE, "results", f"phase4{_tag}.json"), "w"), indent=2)
    print(f"\n=== Phase 4 linearized/NTK predictor (seeds={args.seeds}, n_noise={args.noise_n}) ===")
    print(f"  linearized same-init acc: {out['lin_same_mean']:.3f} ± {out['lin_same_sem']:.3f}")
    print(f"  linearized diff-init acc: {out['lin_diff_mean']:.3f} ± {out['lin_diff_sem']:.3f}")
    print("  (compare: actual SGD student same-init ~0.45, diff-init ~0.09; chance 0.10)")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=4)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=256)
    p.add_argument("--ridge", type=float, default=1e-3)
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
