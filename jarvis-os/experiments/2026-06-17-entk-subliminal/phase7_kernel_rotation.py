"""
Phase 7 (ARC-17): does the eNTK eigenbasis rotate only when transfer succeeds?

User hypothesis: when the student FAILS to learn, the eNTK eigenvectors do not rotate (or only
negligibly). We measure the student's real-logit eNTK Gram on a fixed MNIST probe at init (K0) and
after distillation (K1), and the rotation of the top-k eigenvectors:

    rotation = 1 - ||U0[:, :k]^T U1[:, :k]||_F^2 / k        (0 = no rotation, 1 = orthogonal)

K0 is the SAME across same/diff-init conditions (same student init = ref), so rotation is measured
from a common origin. We also track rotation TOWARD the teacher's eigenbasis (overlap with the
teacher's eNTK), since a failing diff-init student may still rotate -- just toward the wrong basis.

Conditions: (w256 same vs diff init) and a width axis (w64 rich vs w1024 lazy), all same-init.
Prediction to test: rotation tracks transfer; failures show little (init->final) rotation.
"""
import argparse, json, os
import numpy as np
import torch
from torch.func import functional_call, jacrev, vmap
import run as R
from phase6_width import clone_w, _train_w


def entk_gram(model, X, n_out=10):
    """real-logit eNTK Gram K = J J^T on probe X, shape [n*n_out, n*n_out]."""
    params = {k: v.detach() for k, v in model.named_parameters()}
    def f(p, x):
        return functional_call(model, p, (x.unsqueeze(0),))[0, :n_out]
    jac = vmap(jacrev(f), (None, 0))(params, X)                 # {k:[n,n_out,*p]}
    J = torch.cat([jac[k].reshape(X.shape[0], n_out, -1) for k in jac], dim=2).reshape(X.shape[0] * n_out, -1)
    return J @ J.T


def topk_overlap(K0, K1, k):
    """||U0[:,:k]^T U1[:,:k]||_F^2 / k in [0,1]; 1 = identical top-k eigenspace."""
    _, U0 = torch.linalg.eigh(K0); _, U1 = torch.linalg.eigh(K1)   # ascending
    U0, U1 = U0[:, -k:], U1[:, -k:]                                 # top-k
    return float((U0.T @ U1).pow(2).sum() / k)


def cka(A, B):
    n = A.shape[0]; H = torch.eye(n, dtype=A.dtype) - torch.ones(n, n, dtype=A.dtype) / n
    Ac, Bc = H @ A @ H, H @ B @ H
    return float((Ac * Bc).sum() / (Ac.norm() * Bc.norm() + 1e-30))


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = R.load_mnist()
    probe = Xte[:args.probe_n]
    noise = R.make_noise(args.noise_n, args.noise, seed=123)
    conds = [(256, "same"), (256, "diff"), (64, "same"), (1024, "same")]
    rows = []
    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        for w, init in conds:
            k = min(args.k, w)
            ref = R.MLP(width=w, seed=seed0)
            K0 = entk_gram(ref, probe)
            t_seed = seed0 if init == "same" else seed1
            teacher = _train_w(w, t_seed, Xtr, ytr, args)
            K_T = entk_gram(teacher, probe)
            student = R.distill(clone_w(ref, w), teacher, noise, args.student_epochs, args.batch, args.lr, "aux")
            K1 = entk_gram(student, probe)
            row = dict(seed=s, width=w, init=init,
                       transfer=R.test_acc(student, Xte, yte),
                       rotation=1 - topk_overlap(K0, K1, k),           # init -> final rotation
                       overlap_init_teacher=topk_overlap(K0, K_T, k),  # how aligned student-init is to teacher
                       overlap_final_teacher=topk_overlap(K1, K_T, k), # did student rotate TOWARD teacher?
                       cka_drift=1 - cka(K0, K1))
            rows.append(row)
            print(f"seed {s} w{w:<4d} {init}: transfer={row['transfer']:.3f}  rotation={row['rotation']:.3f}  "
                  f"K0~K_T={row['overlap_init_teacher']:.3f} K1~K_T={row['overlap_final_teacher']:.3f}", flush=True)

    out = {"config": vars(args), "rows": rows}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "results", "phase7.json"), "w"), indent=2)
    print(f"\n=== Phase 7 eNTK eigenbasis rotation (seeds={args.seeds}, k={args.k}) ===")
    def agg(w, init, key):
        v = [r[key] for r in rows if r["width"] == w and r["init"] == init]
        return np.mean(v)
    print(f"  {'cond':14s} {'transfer':>9s} {'rotation':>9s} {'K1~teacher':>11s}")
    for w, init in conds:
        print(f"  w{w:<4d} {init:6s} {agg(w,init,'transfer'):9.3f} {agg(w,init,'rotation'):9.3f} "
              f"{agg(w,init,'overlap_final_teacher'):11.3f}")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=2)
    p.add_argument("--probe_n", type=int, default=48)
    p.add_argument("--k", type=int, default=20)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=20)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=60000)
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
