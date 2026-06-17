"""
Phase 1 (ARC-17): does the parameter-space empirical NTK predict subliminal transfer?

This instantiates Theorem 1 directly. The student's FIRST distillation step on noise,
using the ACTUAL teacher aux residual, is
    Delta_theta_S = -grad_theta KL( softmax(teacher_aux(noise)) || softmax(student_aux(theta0; noise)) ).
The teacher's task displacement from its OWN init is Delta_theta_T = theta_teacher - theta_teacher_init.
Theorem 1: with shared init, Delta_theta_S . Delta_theta_T >= 0 (the imitation step also reduces
the teacher's task loss). We measure the normalized version:
    coh(teacher) = cos(Delta_theta_S, Delta_theta_T).
Prediction: coh_same > 0 and clearly > coh_diff ~ 0 (different-init teacher residual is generated
by unrelated geometry -> incoherent with this student's eNTK -> ~zero projection, Charles's antenna).

We ALSO keep a secondary diagnostic, the JVP Rayleigh response R(Delta)/lambda_bar, which we found
does NOT separate the conditions (it measures excitation magnitude, not teacher coherence) -- reported
as a logged negative.

Uses the SAME inits/teachers as run.py (seeds 2s / 2s+1) so coherence pairs with Phase-0 transfer.
"""
import argparse, json, os
import numpy as np
import torch
import torch.nn.functional as F
from torch.func import functional_call, jvp
import run as R

HERE = os.path.dirname(os.path.abspath(__file__))


def grad_flat(loss, params):
    g = torch.autograd.grad(loss, list(params.values()), allow_unused=True)
    return {k: (gi if gi is not None else torch.zeros_like(params[k]))
            for k, gi in zip(params.keys(), g)}


def task_grad(model, theta0, X, y, seed, n=4096):
    """g_task = -grad_theta CE(real logits, true labels) on a MNIST batch at theta0."""
    g = torch.Generator().manual_seed(500 + seed)
    idx = torch.randperm(X.shape[0], generator=g)[:n]
    th = {k: v.clone().requires_grad_(True) for k, v in theta0.items()}
    logits = functional_call(model, th, (X[idx],))[:, :10]
    loss = F.cross_entropy(logits, y[idx])
    gd = grad_flat(loss, th)
    return {k: -gd[k] for k in gd}


def distill_step_dir(model, theta0, teacher_aux, X):
    """Delta_theta_S = -grad of the aux-distillation KL loss at theta0 (the true first step)."""
    th = {k: v.clone().requires_grad_(True) for k, v in theta0.items()}
    saux = functional_call(model, th, (X,))[:, 10:]
    loss = F.kl_div(F.log_softmax(saux, 1), F.log_softmax(teacher_aux, 1),
                    reduction="batchmean", log_target=True)
    g = grad_flat(loss, th)
    return {k: -g[k] for k in g}                         # descent direction


def params_of(model):
    return {k: v.detach().clone() for k, v in model.named_parameters()}


def sub(a, b):
    return {k: a[k] - b[k] for k in a}


def dot(a, b):
    return sum((a[k] * b[k]).sum() for k in a)


def aux_fn(model, x):
    """theta(dict) -> aux logits [N, m] at inputs x; differentiable in theta."""
    def f(theta):
        return functional_call(model, theta, (x,))[:, 10:]
    return f


def R_response(model, theta0, tangent, X):
    """E_x || J_aux(x) tangent ||^2 / ||tangent||^2  via forward-mode JVP (batched over X)."""
    f = aux_fn(model, X)
    _, jvp_out = jvp(f, (theta0,), (tangent,))          # [N, m] directional deriv of aux outputs
    num = (jvp_out ** 2).sum(dim=1).mean().item()       # mean over noise of ||.||^2
    den = dot(tangent, tangent).item()
    return num / den


def lambda_bar(model, theta0, X, n_probe, seed):
    """tr(G_S)/d estimated as mean over random unit-ish directions of R(v)."""
    g = torch.Generator().manual_seed(seed)
    vals = []
    for _ in range(n_probe):
        v = {k: torch.randn(p.shape, generator=g) for k, p in theta0.items()}
        vals.append(R_response(model, theta0, v, X))
    return float(np.mean(vals)), float(np.std(vals))


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, _, _ = R.load_mnist()
    noise = R.make_noise(args.probe_n, args.noise, seed=123)   # same noise family as Phase 0
    p0 = json.load(open(os.path.join(HERE, "results", f"phase0_{args.noise}.json")))

    model = R.MLP()                                            # structure only; params come from dicts
    rows = []
    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        theta0 = params_of(R.MLP(seed=seed0))                 # shared student/reference init
        theta0p = params_of(R.MLP(seed=seed1))                # the different teacher's own init
        t_same = train_cached(seed0, Xtr, ytr, args)
        t_diff = train_cached(seed1, Xtr, ytr, args)
        d_same = sub(params_of(t_same), theta0)               # teacher task displacement from ITS init (=theta0)
        d_diff = sub(params_of(t_diff), theta0p)              # from ITS OWN init theta0'

        with torch.no_grad():
            taux_same = functional_call(t_same, params_of(t_same), (noise,))[:, 10:]
            taux_diff = functional_call(t_diff, params_of(t_diff), (noise,))[:, 10:]
        ds_same = distill_step_dir(model, theta0, taux_same, noise)   # student's true 1st step
        ds_diff = distill_step_dir(model, theta0, taux_diff, noise)
        coh_same = cos(ds_same, d_same)
        coh_diff = cos(ds_diff, d_diff)

        # Theorem-1 headline: align the imitation step with the TRUE MNIST task gradient at theta0
        g_task = task_grad(model, theta0, Xtr, ytr, seed=s)           # -grad CE on MNIST at shared init
        tcos_same = cos(ds_same, g_task)
        tcos_diff = cos(ds_diff, g_task)

        # secondary (logged-negative) diagnostic: JVP Rayleigh response
        lam, _ = lambda_bar(model, theta0, noise, args.probe_dirs, seed=99 + s)
        a_same = R_response(model, theta0, d_same, noise) / lam
        a_diff = R_response(model, theta0, d_diff, noise) / lam

        row = dict(seed=s, coh_same=coh_same, coh_diff=coh_diff,
                   tcos_same=tcos_same, tcos_diff=tcos_diff,
                   align_same=a_same, align_diff=a_diff,
                   transfer_same=p0["aux_same"]["vals"][s],
                   transfer_diff=p0["aux_diff"]["vals"][s])
        rows.append(row)
        print(f"seed {s}: tcos(step,g_task) same={tcos_same:+.3f} diff={tcos_diff:+.3f} "
              f"| cos(step,dT) same={coh_same:+.3f} diff={coh_diff:+.3f} "
              f"| transfer same={row['transfer_same']:.3f} diff={row['transfer_diff']:.3f}",
              flush=True)

    tc_s = np.array([r["tcos_same"] for r in rows]); tc_d = np.array([r["tcos_diff"] for r in rows])
    ch_s = np.array([r["coh_same"] for r in rows]); ch_d = np.array([r["coh_diff"] for r in rows])
    tr_s = np.array([r["transfer_same"] for r in rows]); tr_d = np.array([r["transfer_diff"] for r in rows])
    out = dict(config=vars(args), rows=rows,
               tcos_same_mean=float(tc_s.mean()), tcos_diff_mean=float(tc_d.mean()),
               coh_same_mean=float(ch_s.mean()), coh_diff_mean=float(ch_d.mean()),
               spearman_tcos_transfer=spearman(np.concatenate([tc_s, tc_d]),
                                               np.concatenate([tr_s, tr_d])),
               spearman_tcos_same_only=spearman(tc_s, tr_s))
    json.dump(out, open(os.path.join(HERE, "results", "phase1.json"), "w"), indent=2)
    print(f"\n=== Phase 1 (seeds={args.seeds}) ===")
    print(f"HEADLINE cos(step, g_task)  same-init: {tc_s.mean():+.3f} ± {tc_s.std():.3f}  (>0 expected)")
    print(f"         cos(step, g_task)  diff-init: {tc_d.mean():+.3f} ± {tc_d.std():.3f}  (~0 expected)")
    print(f"  cos(step, dT)  same {ch_s.mean():+.3f}  diff {ch_d.mean():+.3f}")
    print(f"  Spearman(cos-g_task, transfer) pooled same+diff = {out['spearman_tcos_transfer']:.3f}")
    print(f"  Spearman(cos-g_task, transfer) same-only        = {out['spearman_tcos_same_only']:.3f}")
    print(f"[secondary/negative] JVP-Rayleigh align same {np.mean([r['align_same'] for r in rows]):.2f} "
          f"vs diff {np.mean([r['align_diff'] for r in rows]):.2f} (does NOT separate)")
    return out


def cos(a, b):
    return float(dot(a, b) / (dot(a, a).sqrt() * dot(b, b).sqrt() + 1e-30))


_CACHE = {}
def train_cached(seed, X, y, args):
    if seed not in _CACHE:
        _CACHE[seed] = R.train_teacher(seed, X, y, args.teacher_epochs, args.batch, args.lr)
    return _CACHE[seed]


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    ra, rb = ra - ra.mean(), rb - rb.mean()
    den = (np.sqrt((ra**2).sum() * (rb**2).sum()))
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--probe_n", type=int, default=512)     # noise points for the eNTK expectation
    p.add_argument("--probe_dirs", type=int, default=8)    # random directions for lambda_bar
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
