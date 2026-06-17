"""
Phase 8 (ARC-17, "holy grail"): can structured similarity short of shared init enable transfer?

Charles's hypothesis: subliminal learning is governed by INITIAL eNTK similarity. Test it by giving
DIFFERENT-init teacher/student pairs a *structured* partial similarity and asking whether transfer
tracks the measured initial eNTK overlap -- regardless of HOW the overlap was produced.

Student init = a seed0 net with specified layers overwritten by the TEACHER'S init (seed1, untrained):
  none  : share nothing                         (different-init baseline; expect ~chance)
  l1    : share first layer only
  feat  : share both hidden layers (feature extractor), DIFFERENT head
  head  : share the readout head, DIFFERENT features
  all   : share everything                       (= shared init; expect ~0.45)
Teacher is trained from its OWN (seed1) init in every case. We measure, per condition:
  init_overlap = top-k eigenvector overlap of student-init eNTK vs teacher-INIT eNTK (on a probe)
  transfer     = distilled student's MNIST acc
Plot transfer vs init_overlap. Holy grail = a different-init condition (e.g. feat) at high overlap
AND high transfer. If all conditions collapse onto one transfer-vs-overlap curve, eNTK overlap is the
governing variable. If high overlap can co-occur with low transfer, overlap is necessary-not-sufficient.
"""
import argparse, json, os
import numpy as np
import torch
import run as R
from phase7_kernel_rotation import entk_gram, topk_overlap

LAYER = {"fc1": 0, "fc2": 2, "head": 4}
SHARE = {"none": [], "l1": ["fc1"], "feat": ["fc1", "fc2"], "head": ["head"],
         "all": ["fc1", "fc2", "head"]}


def make_student_init(seed0, teacher_init, share):
    s = R.MLP(seed=seed0)
    with torch.no_grad():
        for name in SHARE[share]:
            i = LAYER[name]
            s.net[i].weight.copy_(teacher_init[f"net.{i}.weight"])
            s.net[i].bias.copy_(teacher_init[f"net.{i}.bias"])
    return s


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = R.load_mnist()
    probe = Xte[:args.probe_n]
    noise = R.make_noise(args.noise_n, args.noise, seed=123)
    rows = []
    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        tinit = R.MLP(seed=seed1)
        tinit_params = {k: v.detach().clone() for k, v in tinit.named_parameters()}
        K_tinit = entk_gram(tinit, probe)
        teacher = R.train_teacher(seed1, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)
        for share in ["none", "l1", "feat", "head", "all"]:
            sinit = make_student_init(seed0, tinit_params, share)
            ov = topk_overlap(entk_gram(sinit, probe), K_tinit, args.k)
            student = R.distill(R.clone_init(sinit), teacher, noise, args.student_epochs, args.batch, args.lr, "aux")
            row = dict(seed=s, share=share, init_overlap=ov, transfer=R.test_acc(student, Xte, yte))
            rows.append(row)
            print(f"seed {s} share={share:5s}: init_eNTK_overlap={ov:.3f}  transfer={row['transfer']:.3f}", flush=True)

    out = {"config": vars(args), "rows": rows}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "results", "phase8.json"), "w"), indent=2)
    print(f"\n=== Phase 8 structured similarity (seeds={args.seeds}) ===")
    print(f"  {'share':6s} {'init_eNTK_overlap':>18s} {'transfer':>9s}")
    for share in ["none", "l1", "head", "feat", "all"]:
        sub = [r for r in rows if r["share"] == share]
        print(f"  {share:6s} {np.mean([r['init_overlap'] for r in sub]):18.3f} "
              f"{np.mean([r['transfer'] for r in sub]):9.3f}")
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
