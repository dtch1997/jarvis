"""
Phase 10 (ARC-17): subliminal learning with DIFFERENT weights but identical eNTK (permutation symmetry).

ReLU MLPs have a function-preserving symmetry: permuting hidden units (+ positive rescaling) leaves
the function -- and hence the eNTK -- exactly unchanged, while producing completely different weight
tensors. So a student whose init is a permuted copy of the teacher's init has a DIFFERENT init in raw
weights but strict eNTK similarity = 1.0.

Test: does subliminal transfer survive? If yes, the requirement is eNTK-equivalence, not literal
weight-identity -- a minimal "without exactly the same init" demonstration. Compare to shared-init
(upper bound) and independent diff-init (floor).
"""
import argparse, json, os
import numpy as np
import torch
import run as R
from phase7_kernel_rotation import entk_gram
from phase9_strict_metric import both_metrics


def permute_init(teacher_init, seed):
    """New MLP = teacher_init with hidden units permuted (identical function, different weights)."""
    w1 = teacher_init.net[0].weight.shape[0]
    w2 = teacher_init.net[2].weight.shape[0]
    g = torch.Generator().manual_seed(seed)
    p1 = torch.randperm(w1, generator=g)
    p2 = torch.randperm(w2, generator=g)
    new = R.MLP(width=w1, seed=999)
    t = teacher_init
    with torch.no_grad():
        new.net[0].weight.copy_(t.net[0].weight[p1]);      new.net[0].bias.copy_(t.net[0].bias[p1])
        new.net[2].weight.copy_(t.net[2].weight[p2][:, p1]); new.net[2].bias.copy_(t.net[2].bias[p2])
        new.net[4].weight.copy_(t.net[4].weight[:, p2]);   new.net[4].bias.copy_(t.net[4].bias)
    return new


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = R.load_mnist()
    probe = Xte[:48]
    noise = R.make_noise(args.noise_n, args.noise, seed=123)
    out = {c: [] for c in ["shared", "permuted", "diff"]}
    sanity = []
    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        ref = R.MLP(seed=seed0)                              # teacher's init
        teacher = R.train_teacher(seed0, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)
        perm_init = permute_init(ref, seed=7 + s)            # different weights, same function as ref
        diff_init = R.MLP(seed=seed1)
        # sanity: permuted init has identical function (acc) and strict eNTK sim = 1 vs ref
        strict, _ = both_metrics(entk_gram(perm_init, probe), entk_gram(ref, probe), 20)
        sanity.append((R.test_acc(ref, Xte, yte), R.test_acc(perm_init, Xte, yte), strict))
        for cond, init in [("shared", ref), ("permuted", perm_init), ("diff", diff_init)]:
            st = R.distill(R.clone_init(init), teacher, noise, args.student_epochs, args.batch, args.lr, "aux")
            out[cond].append(R.test_acc(st, Xte, yte))
        print(f"seed {s}: shared={out['shared'][-1]:.3f}  permuted={out['permuted'][-1]:.3f}  "
              f"diff={out['diff'][-1]:.3f}  | sanity ref_acc={sanity[-1][0]:.3f} perm_acc={sanity[-1][1]:.3f} "
              f"strict_eNTK(perm,ref)={sanity[-1][2]:.3f}", flush=True)

    summ = {c: {"mean": float(np.mean(v)), "sem": float(np.std(v) / np.sqrt(len(v))), "vals": v}
            for c, v in out.items()}
    json.dump(summ, open(os.path.join(os.path.dirname(__file__), "results", "phase10.json"), "w"), indent=2)
    print(f"\n=== Phase 10 permutation (different weights, identical eNTK) seeds={args.seeds} ===")
    for c in ["diff", "permuted", "shared"]:
        print(f"  {c:9s} {summ[c]['mean']:.3f} ± {summ[c]['sem']:.3f}")
    print(f"  sanity: permuted-init MNIST acc == ref acc (same function), strict eNTK(perm,ref)≈1")
    return summ


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=2)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=20)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=60000)
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
