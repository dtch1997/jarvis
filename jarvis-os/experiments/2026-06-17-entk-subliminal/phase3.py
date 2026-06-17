"""
Phase 3 (ARC-17): causal dose-response on init overlap.

Phase 1b is correlational (same vs different init). Here we CAUSALLY tune the
shared-basis fraction and check transfer + feature alignment fall together.

Knob: the teacher's init is a per-parameter Bernoulli mix of the student's init
theta0 and an independent init theta0':
    teacher_init = m * theta0 + (1-m) * theta0',   m_ij ~ Bernoulli(1 - delta)
delta = fraction of parameters drawn from the DIFFERENT init. delta=0 -> shared
init (full subliminal); delta=1 -> fully different. The mask preserves each
weight's init variance (no shrinkage confound). Student always starts from theta0.

Prediction P5: transfer accuracy and basis-sensitive feat_cos both decrease
monotonically in delta, and move together (the channel closes as the shared
eigenbasis is eroded).
"""
import argparse, json, os
import numpy as np
import torch
import run as R
from phase1b_featcka import features

HERE = os.path.dirname(os.path.abspath(__file__))


def mixed_init(seed0, seed1, delta, mask_seed):
    """Model whose params are a Bernoulli(1-delta) mix of init(seed0) and init(seed1)."""
    a, b = R.MLP(seed=seed0), R.MLP(seed=seed1)
    g = torch.Generator().manual_seed(mask_seed)
    out = R.MLP(seed=seed0)
    with torch.no_grad():
        for (k, pa), (_, pb), (_, po) in zip(a.named_parameters(),
                                             b.named_parameters(), out.named_parameters()):
            m = (torch.rand(pa.shape, generator=g) >= delta).float()   # 1 -> keep theta0
            po.copy_(m * pa + (1 - m) * pb)
    return out


def train_from(model, X, y, epochs, batch, lr, seed):
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    n = X.shape[0]; g = torch.Generator().manual_seed(1000 + seed)
    import torch.nn.functional as F
    for _ in range(epochs):
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, batch):
            idx = perm[i:i + batch]
            loss = F.cross_entropy(model(X[idx])[:, :10], y[idx])
            opt.zero_grad(); loss.backward(); opt.step()
    return model


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = R.load_mnist()
    noise = R.make_noise(args.noise_n, args.noise, seed=123)
    deltas = [0.0, 0.25, 0.5, 0.75, 1.0]
    grid = {d: {"acc": [], "feat_cos": []} for d in deltas}

    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        ref = R.MLP(seed=seed0)                       # student init theta0 (fixed across delta)
        for d in deltas:
            t_init = mixed_init(seed0, seed1, d, mask_seed=7000 + s)
            teacher = train_from(t_init, Xtr, ytr, args.teacher_epochs, args.batch, args.lr, seed0)
            student = R.distill(R.clone_init(ref), teacher, noise,
                                args.student_epochs, args.batch, args.lr, "aux")
            with torch.no_grad():
                fc = torch.nn.functional.cosine_similarity(
                    features(student, Xte), features(teacher, Xte), dim=1).mean().item()
            grid[d]["acc"].append(R.test_acc(student, Xte, yte))
            grid[d]["feat_cos"].append(fc)
            print(f"seed {s} delta={d:.2f}: acc={grid[d]['acc'][-1]:.3f} feat_cos={fc:+.3f}", flush=True)

    summ = {"config": vars(args), "deltas": deltas, "grid": {}}
    for d in deltas:
        a, f = np.array(grid[d]["acc"]), np.array(grid[d]["feat_cos"])
        summ["grid"][str(d)] = dict(acc_mean=float(a.mean()), acc_sem=float(a.std()/np.sqrt(len(a))),
                                    feat_cos_mean=float(f.mean()), feat_cos_sem=float(f.std()/np.sqrt(len(f))))
    json.dump(summ, open(os.path.join(HERE, "results", "phase3.json"), "w"), indent=2)
    print(f"\n=== Phase 3 dose-response (seeds={args.seeds}) ===")
    print(f"  {'delta':>6s} {'acc':>14s} {'feat_cos':>14s}")
    for d in deltas:
        g = summ["grid"][str(d)]
        print(f"  {d:6.2f} {g['acc_mean']:8.3f}±{g['acc_sem']:.3f} {g['feat_cos_mean']:8.3f}±{g['feat_cos_sem']:.3f}")
    return summ


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=4)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=20)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=60000)
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
