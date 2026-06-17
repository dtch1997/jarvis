"""
Phase 1b (ARC-17): the robust, multi-step test of the eNTK mechanism.

Charles's hypothesis says the subliminal channel is init-specific because the
teacher's signal is only coherent with the student's eNTK eigenbasis when they
share init. The *observable consequence*: aux-only distillation should pull the
student's hidden FEATURES toward the teacher's -- but only for shared init. For a
different-init teacher the student still fits aux-on-noise (overparam/lazy), yet
that fit does NOT transport to teacher-like features on MNIST.

We distill exactly as in Phase 0 (aux logits, noise inputs) and measure CKA
between the distilled student's penultimate features and the TEACHER's features
on the MNIST test set, for same-init vs different-init teachers. Pairs with the
Phase-0 accuracy.

Prediction P1b: CKA(student, teacher) on MNIST is high for same-init, low for
different-init -- and tracks the per-seed transfer accuracy.
"""
import argparse, json, os
import numpy as np
import torch
import run as R

HERE = os.path.dirname(os.path.abspath(__file__))


def features(model, X):
    """penultimate (post-2nd-ReLU) activations [N, width]."""
    h = X
    for layer in list(model.net)[:-1]:                 # all but final Linear
        h = layer(h)
    return h


def linear_cka(A, B):
    A = A - A.mean(0, keepdim=True); B = B - B.mean(0, keepdim=True)
    hsic = (A.T @ B).pow(2).sum()
    na = (A.T @ A).pow(2).sum().sqrt(); nb = (B.T @ B).pow(2).sum().sqrt()
    return float(hsic / (na * nb + 1e-30))


@torch.no_grad()
def eval_all(student, teacher, ref, Xte, yte):
    sf, tf, rf = features(student, Xte), features(teacher, Xte), features(ref, Xte)
    # basis-SENSITIVE alignment (no rotation allowed) -- what the frozen init head needs:
    feat_cos = float(torch.nn.functional.cosine_similarity(sf, tf, dim=1).mean())
    rel_mse = float((sf - tf).norm() / (tf.norm() + 1e-30))
    return dict(acc=R.test_acc(student, Xte, yte),
                cka_teacher=linear_cka(sf, tf),       # rotation-INVARIANT similarity (does NOT separate)
                feat_cos=feat_cos,                    # rotation-SENSITIVE alignment (should separate)
                rel_mse=rel_mse,
                cka_init=linear_cka(sf, rf))


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = R.load_mnist()
    noise = R.make_noise(args.noise_n, args.noise, seed=123)
    p0 = json.load(open(os.path.join(HERE, "results", f"phase0_{args.noise}.json")))
    rows = []
    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        ref = R.MLP(seed=seed0)
        t_same = R.train_teacher(seed0, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)
        t_diff = R.train_teacher(seed1, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)
        st_same = R.distill(R.clone_init(ref), t_same, noise, args.student_epochs, args.batch, args.lr, "aux")
        st_diff = R.distill(R.clone_init(ref), t_diff, noise, args.student_epochs, args.batch, args.lr, "aux")
        e_same = eval_all(st_same, t_same, ref, Xte, yte)
        e_diff = eval_all(st_diff, t_diff, ref, Xte, yte)
        row = dict(seed=s, same=e_same, diff=e_diff)
        rows.append(row)
        print(f"seed {s}: SAME acc={e_same['acc']:.3f} cka={e_same['cka_teacher']:.3f} "
              f"featcos={e_same['feat_cos']:+.3f} | "
              f"DIFF acc={e_diff['acc']:.3f} cka={e_diff['cka_teacher']:.3f} "
              f"featcos={e_diff['feat_cos']:+.3f}", flush=True)

    def col(cond, key): return np.array([r[cond][key] for r in rows])
    out = dict(config=vars(args), rows=rows)
    for key in ["cka_teacher", "feat_cos", "rel_mse"]:
        out[f"{key}_same_mean"] = float(col("same", key).mean())
        out[f"{key}_diff_mean"] = float(col("diff", key).mean())
    # does the basis-sensitive alignment track transfer, pooled across both conditions?
    fc = np.concatenate([col("same", "feat_cos"), col("diff", "feat_cos")])
    ac = np.concatenate([col("same", "acc"), col("diff", "acc")])
    out["spearman_featcos_acc_pooled"] = spearman(fc, ac)
    out["spearman_cka_acc_pooled"] = spearman(
        np.concatenate([col("same", "cka_teacher"), col("diff", "cka_teacher")]), ac)
    json.dump(out, open(os.path.join(HERE, "results", "phase1b.json"), "w"), indent=2)
    print(f"\n=== Phase 1b (seeds={args.seeds}) ===")
    print(f"  {'metric':12s} {'same':>8s} {'diff':>8s}   separates?")
    for key, sep in [("cka_teacher", "NO (rotation-invariant)"),
                     ("feat_cos", "YES (basis-sensitive)"),
                     ("rel_mse", "YES (basis-sensitive)")]:
        print(f"  {key:12s} {out[key+'_same_mean']:8.3f} {out[key+'_diff_mean']:8.3f}   {sep}")
    print(f"Spearman(feat_cos, acc) pooled = {out['spearman_featcos_acc_pooled']:.3f}  "
          f"| Spearman(CKA, acc) pooled = {out['spearman_cka_acc_pooled']:.3f}")
    return out


def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)).astype(float), np.argsort(np.argsort(b)).astype(float)
    ra, rb = ra - ra.mean(), rb - rb.mean()
    den = np.sqrt((ra**2).sum() * (rb**2).sum())
    return float((ra * rb).sum() / den) if den > 0 else float("nan")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=8)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=20)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=60000)
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
