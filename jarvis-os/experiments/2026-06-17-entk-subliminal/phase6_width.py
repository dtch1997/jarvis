"""
Phase 6 (ARC-17): does subliminal learning weaken with width?

Prediction (user): wider -> lazier -> less feature learning -> less subliminal transfer, since we
showed (Phase 4/5) that transfer REQUIRES feature plasticity.

Caveat: "wider = lazier" is a parametrization/optimizer-dependent statement (cleanest under
SGD/NTK-param; we use Adam + standard init). So we don't assume it -- we MEASURE the laziness at
each width as the teacher's feature movement during training, and report transfer vs that measured
quantity as well as vs width.

Per (width, seed): train a same-init teacher, distill an aux-only student (as Phase 0), measure
  - transfer  = student MNIST test acc
  - feat_drift = ||phi_T(Xte) - phi_0(Xte)||_F / ||phi_0(Xte)||_F   (how far teacher features moved)
  - cka_drift  = 1 - CKA(phi_0, phi_T)                              (rotation-invariant drift)
phi = penultimate features. Larger drift = more feature learning = less lazy.
"""
import argparse, json, os
import numpy as np
import torch
import run as R
from phase1b_featcka import features, linear_cka


def clone_w(ref, width):
    s = R.MLP(width=width, m=ref.m)
    s.load_state_dict(ref.state_dict())
    return s


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = R.load_mnist()
    noise = R.make_noise(args.noise_n, args.noise, seed=123)
    widths = [int(w) for w in args.widths.split(",")]
    grid = {w: {"transfer": [], "feat_drift": [], "cka_drift": [], "teacher_acc": []} for w in widths}

    for s in range(args.seeds):
        seed0 = 2 * s
        for w in widths:
            ref = R.MLP(width=w, seed=seed0)
            teacher = R.train_teacher_w(seed0, w, Xtr, ytr, args.teacher_epochs, args.batch, args.lr) \
                if hasattr(R, "train_teacher_w") else _train_w(w, seed0, Xtr, ytr, args)
            student = R.distill(clone_w(ref, w), teacher, noise,
                                args.student_epochs, args.batch, args.lr, "aux")
            with torch.no_grad():
                phi0, phiT = features(ref, Xte), features(teacher, Xte)
                fd = float((phiT - phi0).norm() / (phi0.norm() + 1e-30))
                cd = float(1.0 - linear_cka(phi0, phiT))
            grid[w]["transfer"].append(R.test_acc(student, Xte, yte))
            grid[w]["feat_drift"].append(fd)
            grid[w]["cka_drift"].append(cd)
            grid[w]["teacher_acc"].append(R.test_acc(teacher, Xte, yte))
            print(f"seed {s} width {w:5d}: transfer={grid[w]['transfer'][-1]:.3f}  "
                  f"feat_drift={fd:.3f}  cka_drift={cd:.3f}  teacher={grid[w]['teacher_acc'][-1]:.3f}",
                  flush=True)

    summ = {"config": vars(args), "widths": widths, "grid": {}}
    for w in widths:
        g = grid[w]
        summ["grid"][str(w)] = {k: {"mean": float(np.mean(v)), "sem": float(np.std(v) / np.sqrt(len(v)))}
                                for k, v in g.items()}
    json.dump(summ, open(os.path.join(os.path.dirname(__file__), "results", "phase6.json"), "w"), indent=2)
    print(f"\n=== Phase 6 width sweep (seeds={args.seeds}) ===")
    print(f"  {'width':>6s} {'transfer':>14s} {'feat_drift':>14s} {'teacher':>9s}")
    for w in widths:
        g = summ["grid"][str(w)]
        print(f"  {w:6d} {g['transfer']['mean']:8.3f}±{g['transfer']['sem']:.3f} "
              f"{g['feat_drift']['mean']:8.3f}±{g['feat_drift']['sem']:.3f} {g['teacher_acc']['mean']:7.3f}")
    return summ


def _train_w(width, seed, X, y, args):
    import torch.nn.functional as F
    model = R.MLP(width=width, seed=seed)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    n = X.shape[0]; g = torch.Generator().manual_seed(1000 + seed)
    for _ in range(args.teacher_epochs):
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, args.batch):
            idx = perm[i:i + args.batch]
            loss = F.cross_entropy(model(X[idx])[:, :10], y[idx])
            opt.zero_grad(); loss.backward(); opt.step()
    return model


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=2)
    p.add_argument("--widths", type=str, default="32,64,128,256,512,1024")
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=20)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=60000)
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
