"""
Phase 11 (ARC-17): is the trait in a DIFFERENT-init student's features, just in an unreadable basis?

The project verdict: subliminal transfer needs eNTK-equivalence *in the frame the frozen readout
decodes*. A different-init student fails (~chance) -- but did the trait never transfer, or did it
transfer into a basis its own init-head can't read? We test this POST-HOC on the already-distilled
student's features phi_S = net[:4](x), with NO change to training.

CONFOUND (why naive probes mislead): a random ReLU net already linearly separates MNIST (~0.85), and a
least-squares map fit on MNIST inputs can regress teacher features from almost any features. So every
metric is also measured on the student's UNDISTILLED init; the trait-specific signal is the
distilled-minus-init LIFT, not the raw number.

Readouts of phi_S (each computed at init and after aux-distillation):
  own_head        : student's own init real head            (= canonical transfer; diff -> chance)
  teacher_head0   : the TEACHER's init real head, no fit    (did phi_S land in the teacher's init frame?
                    for same-init this equals own_head by construction)
  stitch_noise    : label-free linear S fit on NOISE so S.phi_S ~= phi_T, decode via teacher TRAINED
                    head. Honest: never sees MNIST or labels. Lift over init = basis-recoverable trait.
  stitch_mnist    : same but S fit on UNLABELED MNIST inputs -- POWERFUL/confounded (high even at init);
                    reported only to show the noise->MNIST distribution gap.
  probe_labeled   : labeled least-squares probe phi_S->labels -- generic separability reference
                    (expected high & ~equal everywhere incl. init: decodability is not the issue).

Read: diff-init own_head ~ chance, but stitch_noise shows a real distilled-minus-init lift >> 0 (and
teacher_head0 too) -> the trait transferred into an unreadable basis and a label-free map recovers it.
If stitch_noise lift ~ 0 -> the basis story is insufficient (honest null). CPU, minutes.
"""
import argparse, json, os
import numpy as np
import torch
import run as R

HERE = os.path.dirname(os.path.abspath(__file__))


@torch.no_grad()
def features(model, X, batch=4096):
    return torch.cat([model.net[:4](X[i:i + batch]) for i in range(0, X.shape[0], batch)], 0)


def _aug(F):
    return torch.cat([F, torch.ones(F.shape[0], 1, dtype=F.dtype)], 1)


def ridge_solve(A, B, r):
    G = A.T @ A + r * torch.eye(A.shape[1], dtype=A.dtype)
    return torch.linalg.solve(G, A.T @ B)


def labeled_probe_acc(F_tr, y_tr, F_te, y_te, r):
    Y = torch.zeros(F_tr.shape[0], 10, dtype=F_tr.dtype)
    Y[torch.arange(F_tr.shape[0]), y_tr] = 1.0
    W = ridge_solve(_aug(F_tr), Y, r)
    return float(((_aug(F_te) @ W).argmax(1) == y_te).float().mean())


@torch.no_grad()
def head_acc(head_linear, F_te, yte):
    """apply a given real head (nn.Linear with 10+m outputs) to features F_te."""
    return float((head_linear(F_te)[:, :10].argmax(1) == yte).float().mean())


def stitch_acc(F_fit_s, F_fit_t, F_te_s, teacher, yte, r):
    """fit S (label-free) so S.phi_S ~= phi_T on the fit set, decode test via the teacher TRAINED head."""
    W = ridge_solve(_aug(F_fit_s), F_fit_t, r)
    with torch.no_grad():
        logits = teacher.net[4](_aug(F_te_s) @ W)[:, :10]
    return float((logits.argmax(1) == yte).float().mean())


def readouts(student, teacher, tinit, sets, yte, ytr_p, ridge):
    """all readout metrics for one student STATE (init or distilled)."""
    Xte, fit_noise, fit_mnist, Xtr_p = sets["te"], sets["fn"], sets["fm"], sets["trp"]
    Fs_te = features(student, Xte)
    return dict(
        own_head=head_acc(student.net[4], Fs_te, yte),
        teacher_head0=head_acc(tinit.net[4], Fs_te, yte),
        stitch_noise=stitch_acc(features(student, fit_noise), sets["ft_fn"], Fs_te, teacher, yte, ridge),
        stitch_mnist=stitch_acc(features(student, fit_mnist), sets["ft_fm"], Fs_te, teacher, yte, ridge),
        probe_labeled=labeled_probe_acc(features(student, Xtr_p), ytr_p, Fs_te, yte, ridge),
    )


METRICS = ["own_head", "teacher_head0", "stitch_noise", "stitch_mnist", "probe_labeled"]


def run(args):
    torch.set_num_threads(args.threads)
    torch.set_default_dtype(torch.float64)
    Xtr, ytr, Xte, yte = R.load_mnist()
    Xtr, Xte = Xtr.double(), Xte.double()
    noise = R.make_noise(args.noise_n, args.noise, seed=123).double()
    sets = {"te": Xte, "fn": noise[:args.fit_n], "fm": Xtr[:args.fit_n], "trp": Xtr[:args.probe_n]}
    ytr_p = ytr[:args.probe_n]

    rows = []
    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        tinit = R.MLP(seed=seed0)                                   # teacher's init (frozen reference head)
        teacher = R.train_teacher(seed0, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)
        sets["ft_fn"], sets["ft_fm"] = features(teacher, sets["fn"]), features(teacher, sets["fm"])
        teacher_acc = R.test_acc(teacher, Xte, yte)

        for cond, init in [("same", R.MLP(seed=seed0)), ("diff", R.MLP(seed=seed1))]:
            m_init = readouts(R.clone_init(init), teacher, tinit, sets, yte, ytr_p, args.ridge)
            student = R.distill(R.clone_init(init), teacher, noise,
                                args.student_epochs, args.batch, args.lr, "aux")
            m_dist = readouts(student, teacher, tinit, sets, yte, ytr_p, args.ridge)
            row = dict(seed=s, cond=cond, teacher_acc=teacher_acc,
                       **{f"{k}": m_dist[k] for k in METRICS},
                       **{f"{k}_init": m_init[k] for k in METRICS})
            rows.append(row)
            print(f"seed {s} {cond:4s}: " +
                  " ".join(f"{k}={m_dist[k]:.3f}(+{m_dist[k]-m_init[k]:+.3f})" for k in METRICS), flush=True)

    out = {"config": vars(args), "rows": rows}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    _ds = os.environ.get("JARVIS_DATASET", "mnist")
    _tag = "" if _ds == "mnist" else f"_{_ds}"
    json.dump(out, open(os.path.join(HERE, "results", f"phase11{_tag}.json"), "w"), indent=2)

    print(f"\n=== Phase 11 stitch decode (seeds={args.seeds}, chance=0.10) ===")
    print(f"  values are distilled (LIFT over undistilled init in parens)")
    print(f"  {'cond':5s} " + " ".join(f"{k:>15s}" for k in METRICS))
    for cond in ["same", "diff"]:
        sub = [r for r in rows if r["cond"] == cond]
        cells = []
        for k in METRICS:
            d = np.mean([r[k] for r in sub]); lift = d - np.mean([r[f"{k}_init"] for r in sub])
            cells.append(f"{d:.3f}({lift:+.3f})")
        print(f"  {cond:5s} " + " ".join(f"{c:>15s}" for c in cells))
    print("  honest trait signal = LIFT on own_head/teacher_head0/stitch_noise (not raw probe/stitch_mnist).")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=4)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=5)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=20000)
    p.add_argument("--fit_n", type=int, default=8000)
    p.add_argument("--probe_n", type=int, default=20000)
    p.add_argument("--ridge", type=float, default=1e-2)
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
