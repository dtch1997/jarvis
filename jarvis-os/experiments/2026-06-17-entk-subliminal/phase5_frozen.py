"""
Phase 5 (ARC-17): the frozen-features control (the "linear case").

Freeze the student's first 2 layers (the feature extractor); only the output head is learnable.
The model is then linear in its trainable params, so the eNTK is exact. Question (user's): does
subliminal learning survive?

Exact prediction: NO. Under the aux-only loss the real-head rows get zero gradient, and the features
are frozen, so the student's real logits are pinned at W_real_init . phi_0(x) = the untrained model
-> chance, by construction. We freeze the STUDENT only; the teacher is trained normally (so it has
moved features that COULD transfer in the full model).

Compares, per seed: full-model student (features learn) vs frozen-feature student, for aux_same /
aux_diff / all_same, plus the untrained reference. If aux_same(frozen) == reference, subliminal
learning requires feature plasticity -> it is NOT a linear/lazy phenomenon (consistent with Phase 4).
"""
import argparse, json, os
import numpy as np
import torch
import run as R


def freeze_features(model):
    for layer in (model.net[0], model.net[2]):          # fc1, fc2 (the two hidden Linears)
        for p in layer.parameters():
            p.requires_grad_(False)
    return model


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = R.load_mnist()
    noise = R.make_noise(args.noise_n, args.noise, seed=123)
    conds = ["reference", "aux_same_full", "aux_same_frozen", "aux_diff_frozen", "all_same_frozen"]
    out = {c: [] for c in conds}

    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        ref = R.MLP(seed=seed0)
        out["reference"].append(R.test_acc(ref, Xte, yte))
        t_same = R.train_teacher(seed0, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)
        t_diff = R.train_teacher(seed1, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)

        # full-model student (baseline, features learn)
        st_full = R.distill(R.clone_init(ref), t_same, noise, args.student_epochs, args.batch, args.lr, "aux")
        out["aux_same_full"].append(R.test_acc(st_full, Xte, yte))

        # frozen-feature students (only head learns)
        for cond, teacher, mode in [("aux_same_frozen", t_same, "aux"),
                                    ("aux_diff_frozen", t_diff, "aux"),
                                    ("all_same_frozen", t_same, "all")]:
            st = R.distill(freeze_features(R.clone_init(ref)), teacher, noise,
                           args.student_epochs, args.batch, args.lr, mode)
            out[cond].append(R.test_acc(st, Xte, yte))
        print(f"seed {s}: ref={out['reference'][-1]:.3f}  "
              f"aux_same FULL={out['aux_same_full'][-1]:.3f}  FROZEN={out['aux_same_frozen'][-1]:.3f}  "
              f"aux_diff FROZEN={out['aux_diff_frozen'][-1]:.3f}  all_same FROZEN={out['all_same_frozen'][-1]:.3f}",
              flush=True)

    summ = {"config": vars(args)}
    for c in conds:
        a = np.array(out[c]); summ[c] = dict(mean=float(a.mean()), sem=float(a.std()/np.sqrt(len(a))), vals=a.tolist())
    json.dump(summ, open(os.path.join(os.path.dirname(__file__), "results", "phase5.json"), "w"), indent=2)
    print(f"\n=== Phase 5 frozen-features (seeds={args.seeds}) ===")
    for c in conds:
        print(f"  {c:18s} {summ[c]['mean']:.3f} ± {summ[c]['sem']:.3f}")
    print("  prediction: aux_same_frozen ≈ reference (transfer dies without feature plasticity)")
    return summ


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=20)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=60000)
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
