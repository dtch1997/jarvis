"""
Phase 13 (ARC-17): is the matched-teacher requirement localized to the EARLY feature-learning window?

User hypothesis: at init you really do need a very similar (same-init) teacher, but after some feature
learning the representation has matured/converged, so you can then accept a DIFFERENT-init teacher.
Concrete test: distill aux-on-noise with teacher A for a fraction of the steps, hand off to teacher B
for the rest, and sweep the handoff fraction. Both teachers are trained on the same MNIST task; they
differ only in init basis. Student init = teacher A's init (seed0), so its frozen-ish readout lives in
A's frame -- the basis-sensitive readout the canonical phenomenon needs.

  A_first(x): x fraction on A (SAME-init), then (1-x) on B (DIFF-init)
  B_first(x): x fraction on B (DIFF-init), then (1-x) on A (SAME-init)
Endpoints (shared): x=0 A_first = x=1 B_first = pure-B (diff baseline ~chance);
                    x=1 A_first = x=0 B_first = pure-A (same baseline).

Readings:
  - A_first stays HIGH for x well below 1  -> a short matched warmup UNLOCKS finishing on a different
    teacher: the requirement is early-localized (hypothesis supported).
  - A_first only high near x=1 (transfer tracks the FINAL teacher) -> no durable benefit; the student
    just follows whoever it is currently distilling (hypothesis refuted).
  - B_first rising as x->0 (more A at the END) -> a late matched teacher can RESCUE a bad start.
We also report CKA(student, A) and CKA(student, B) at the end (basis-INVARIANT representational
convergence) next to the basis-SENSITIVE transfer -- to see whether "representations converged to B"
without the readout being able to use it. CPU, minutes.
"""
import argparse, json, os
import numpy as np
import torch
import torch.nn.functional as F
import run as R
from phase7_kernel_rotation import entk_gram, cka  # cka(A,B): basis-invariant kernel alignment


@torch.no_grad()
def feats(model, X):
    return model.net[:4](X)


def aux_logprobs(teacher, noise):
    teacher.eval()
    with torch.no_grad():
        return F.log_softmax(teacher(noise)[:, 10:], dim=1)      # [n, m] aux target


def distill_handoff(student, lp_first, lp_second, noise, epochs, batch, lr, frac_first):
    """KL on aux logprobs; switch target from teacher-first to teacher-second at frac_first of steps."""
    opt = torch.optim.Adam(student.parameters(), lr=lr)
    n = noise.shape[0]
    nb = (n + batch - 1) // batch
    total = epochs * nb
    switch = round(frac_first * total)
    g = torch.Generator().manual_seed(7)
    step = 0
    for _ in range(epochs):
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, batch):
            idx = perm[i:i + batch]
            tp = lp_first[idx] if step < switch else lp_second[idx]
            sp = F.log_softmax(student(noise[idx])[:, 10:], dim=1)
            loss = F.kl_div(sp, tp, reduction="batchmean", log_target=True)
            opt.zero_grad(); loss.backward(); opt.step()
            step += 1
    return student


def run(args):
    torch.set_num_threads(args.threads)
    Xtr, ytr, Xte, yte = R.load_mnist()
    probe = Xte[:args.probe_n]
    noise = R.make_noise(args.noise_n, args.noise, seed=123)
    fracs = [float(x) for x in args.fracs.split(",")]
    rows = []
    for s in range(args.seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        ref = R.MLP(seed=seed0)                                   # student init = teacher A's init
        tA = R.train_teacher(seed0, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)   # same-init
        tB = R.train_teacher(seed1, Xtr, ytr, args.teacher_epochs, args.batch, args.lr)   # diff-init
        lpA, lpB = aux_logprobs(tA, noise), aux_logprobs(tB, noise)
        FA, FB = feats(tA, probe), feats(tB, probe)

        for direction, (lp1, lp2) in [("A_first", (lpA, lpB)), ("B_first", (lpB, lpA))]:
            for x in fracs:
                st = distill_handoff(R.clone_init(ref), lp1, lp2, noise,
                                     args.student_epochs, args.batch, args.lr, x)
                Fs = feats(st, probe)
                rows.append(dict(seed=s, direction=direction, frac_first=x,
                                 transfer=R.test_acc(st, Xte, yte),
                                 cka_A=cka(Fs @ Fs.T, FA @ FA.T),
                                 cka_B=cka(Fs @ Fs.T, FB @ FB.T)))
        msg = "  ".join(f"x{x:g}:A{[r for r in rows if r['seed']==s and r['direction']=='A_first' and r['frac_first']==x][0]['transfer']:.2f}"
                        f"/B{[r for r in rows if r['seed']==s and r['direction']=='B_first' and r['frac_first']==x][0]['transfer']:.2f}"
                        for x in fracs)
        print(f"seed {s}  (Afirst/Bfirst)  {msg}", flush=True)

    out = {"config": vars(args), "rows": rows}
    os.makedirs(os.path.join(os.path.dirname(__file__), "results"), exist_ok=True)
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "results", "phase13.json"), "w"), indent=2)

    def agg(direction, x, key):
        v = [r[key] for r in rows if r["direction"] == direction and r["frac_first"] == x]
        return float(np.mean(v))

    print(f"\n=== Phase 13 teacher handoff (seeds={args.seeds}, chance=0.10) ===")
    print("  A=same-init teacher, B=diff-init teacher; x = fraction of steps on the FIRST teacher")
    print(f"  {'x':>5s} | {'A_first(A→B)':>12s} {'cka_A':>6s} {'cka_B':>6s} | {'B_first(B→A)':>12s} {'cka_A':>6s} {'cka_B':>6s}")
    for x in fracs:
        print(f"  {x:5g} | {agg('A_first',x,'transfer'):12.3f} {agg('A_first',x,'cka_A'):6.3f} {agg('A_first',x,'cka_B'):6.3f}"
              f" | {agg('B_first',x,'transfer'):12.3f} {agg('B_first',x,'cka_A'):6.3f} {agg('B_first',x,'cka_B'):6.3f}")
    print("  hypothesis supported if A_first stays high for x<1 (early matched warmup unlocks finishing on B).")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=4)
    p.add_argument("--teacher_epochs", type=int, default=5)
    p.add_argument("--student_epochs", type=int, default=15)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--noise", choices=["gaussian", "uniform"], default="gaussian")
    p.add_argument("--noise_n", type=int, default=20000)
    p.add_argument("--probe_n", type=int, default=512)
    p.add_argument("--fracs", type=str, default="0,0.25,0.5,0.75,1.0")
    p.add_argument("--threads", type=int, default=8)
    run(p.parse_args())
