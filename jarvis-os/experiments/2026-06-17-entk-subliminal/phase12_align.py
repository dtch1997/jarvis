"""
Phase 12 (ARC-17): engineer basis-sensitive eNTK/feature alignment across DIFFERENT inits, in the rich
regime -- the project's named "open path" (postmortem: aligned eNTKs across inits arise naturally only
in the lazy limit, where transfer dies; engineering them in the rich regime is open).

Setup = the Phase-8 "head" baseline that fails at chance: student shares the teacher's INIT readout head
but has a DIFFERENT (seed1) feature extractor. Onto the normal aux-on-noise distillation we add a
basis-SENSITIVE feature-alignment loss that pulls the student's features toward the teacher's, in the
teacher's coordinate frame, on NOISE only (label-free, innocuous):

    loss = w_aux * KL(student.aux || teacher.aux)  +  lam * ||phi_S(noise) - phi_T(noise)||^2 / ||phi_T||^2

We sweep lam and read transfer off the student's OWN (shared-init) head -- the genuine subliminal readout.

Conditions per lam:
  aux+align : w_aux=1, lam=lam     -- the engineered-alignment student
  align_only: w_aux=0, lam=lam     -- CONTROL: alignment with NO trait channel. If this matches
              aux+align, the win is just feature distillation; if aux+align >> align_only at matched
              alignment, the aux channel carries the trait subliminally and alignment only supplies a
              readable basis.
References: lam=0 == the head-shared/different-feature baseline (expect ~chance); aux_same == full
shared-init upper bound.

Read: aux+align transfer rises with feature alignment while different feature inits throughout, AND
beats align_only -> a genuine "subliminal learning without identical init", with the missing ingredient
identified as basis-sensitive feature/eNTK alignment. CPU, minutes.
"""
import argparse, json, os
import numpy as np
import torch
import torch.nn.functional as F
import run as R

HERE = os.path.dirname(os.path.abspath(__file__))


def head_shared_init(seed_feat, teacher_init):
    """different (seed_feat) feature extractor + the teacher's INIT readout head."""
    s = R.MLP(seed=seed_feat)
    with torch.no_grad():
        s.net[4].weight.copy_(teacher_init.net[4].weight)
        s.net[4].bias.copy_(teacher_init.net[4].bias)
    return s


@torch.no_grad()
def feats(model, X):
    return model.net[:4](X)


def distill_align(student, teacher, noise, epochs, batch, lr, w_aux, lam):
    """aux-KL distillation (mode='aux') + lam * relative-MSE feature alignment to the teacher, on noise."""
    opt = torch.optim.Adam(student.parameters(), lr=lr)
    n = noise.shape[0]
    teacher.eval()
    with torch.no_grad():
        tlog = teacher(noise)                       # [n, 13]
        tphi = teacher.net[:4](noise)               # [n, width] teacher (trained) features, frozen target
        tphi_sq = (tphi ** 2).mean()
    g = torch.Generator().manual_seed(7)
    for _ in range(epochs):
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, batch):
            idx = perm[i:i + batch]
            loss = torch.zeros((), dtype=noise.dtype)
            if w_aux:
                slog = student(noise[idx])
                tp = F.log_softmax(tlog[idx][:, 10:], dim=1)
                sp = F.log_softmax(slog[:, 10:], dim=1)
                loss = loss + w_aux * F.kl_div(sp, tp, reduction="batchmean", log_target=True)
            if lam:
                sphi = student.net[:4](noise[idx])
                loss = loss + lam * ((sphi - tphi[idx]) ** 2).mean() / (tphi_sq + 1e-12)
            opt.zero_grad(); loss.backward(); opt.step()
    return student


@torch.no_grad()
def feat_align(student, teacher, X):
    """basis-sensitive feature match on a probe: 1 - ||phi_S - phi_T||^2 / ||phi_T||^2 (1 = identical)."""
    ps, pt = feats(student, X), feats(teacher, X)
    return float(1.0 - ((ps - pt) ** 2).mean() / ((pt ** 2).mean() + 1e-12))


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = R.load_mnist()
    probe = Xte[:args.probe_n]
    noise = R.make_noise(args.noise_n, args.noise, seed=123)
    lams = [float(x) for x in args.lams.split(",")]
    rows, refs = [], {}

    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        tinit = R.MLP(seed=seed0)
        teacher = R.train_teacher(seed0, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)
        # references
        sh = R.distill(R.clone_init(R.MLP(seed=seed0)), teacher, noise,
                       args.student_epochs, args.batch, args.lr, "aux")          # full shared init (ceiling)
        refs.setdefault("aux_same", []).append(R.test_acc(sh, Xte, yte))
        refs.setdefault("teacher", []).append(R.test_acc(teacher, Xte, yte))

        for lam in lams:
            for cond, w_aux in [("aux+align", 1.0), ("align_only", 0.0)]:
                if lam == 0.0 and cond == "align_only":
                    continue                                                     # degenerate (no signal)
                st = head_shared_init(seed1, tinit)
                st = distill_align(st, teacher, noise, args.student_epochs, args.batch, args.lr, w_aux, lam)
                rows.append(dict(seed=s, lam=lam, cond=cond,
                                 transfer=R.test_acc(st, Xte, yte),
                                 align=feat_align(st, teacher, probe)))
        last = {(r["lam"], r["cond"]): r for r in rows if r["seed"] == s}
        msg = "  ".join(f"l{lam:g}:{last[(lam,'aux+align')]['transfer']:.3f}"
                        f"/al{last[(lam,'aux+align')]['align']:.2f}" for lam in lams)
        print(f"seed {s} aux+align  {msg}", flush=True)

    out = {"config": vars(args), "rows": rows,
           "refs": {k: {"mean": float(np.mean(v)), "vals": v} for k, v in refs.items()}}
    json.dump(out, open(os.path.join(HERE, "results", "phase12.json"), "w"), indent=2)

    def agg(lam, cond, key):
        v = [r[key] for r in rows if r["lam"] == lam and r["cond"] == cond]
        return float(np.mean(v)) if v else float("nan")

    print(f"\n=== Phase 12 alignment dose-response (seeds={args.seeds}, chance=0.10) ===")
    print(f"  aux_same(ceiling)={np.mean(refs['aux_same']):.3f}  teacher={np.mean(refs['teacher']):.3f}")
    print(f"  {'lam':>6s} {'feat_align':>10s} {'aux+align':>10s} {'align_only':>11s}")
    for lam in lams:
        print(f"  {lam:6g} {agg(lam,'aux+align','align'):10.3f} "
              f"{agg(lam,'aux+align','transfer'):10.3f} {agg(lam,'align_only','transfer'):11.3f}")
    print("  reading: aux+align climbs with feat_align (different feature inits throughout); the")
    print("           aux+align - align_only gap at matched alignment = the subliminal trait channel.")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=4)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=10)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=20000)
    p.add_argument("--probe_n", type=int, default=2000)
    p.add_argument("--lams", type=str, default="0,0.01,0.03,0.1,0.3,1,3")
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
