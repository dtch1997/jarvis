"""
Phase 9 (ARC-17): a STRICTER, basis-sensitive eNTK similarity (user's idea).

Subspace overlap ||U0[:,:k]^T U1[:,:k]||_F^2/k is rotation-TOLERANT within the top-k subspace -- the
eNTK analogue of CKA, and (Phases 7-8) blind to what governs transfer. The strict version compares
eigenvectors ONE-BY-ONE in eigenvalue rank order:

    strict_align = mean_i |<u_i^0, u_i^1>|       (rank-matched eigenvector cosines; sign-robust)

This is the eNTK analogue of feat_cos. We recompute the Phase-8 conditions' INITIAL eNTK similarity
(student-init vs teacher-init -- NO distillation needed) under BOTH metrics, and join with the
already-measured transfer. Question: does the strict metric track transfer where subspace did not?

Caveats (reported): near-degenerate eigenvalues make individual eigenvectors ill-defined, and training
can reorder eigenvalues -- both inject noise into rank-matching. We restrict to the top-k (largest,
best-separated) and average over seeds.
"""
import json, os
import numpy as np
import torch
import run as R
from phase7_kernel_rotation import entk_gram
from phase8_structured import make_student_init, SHARE

HERE = os.path.dirname(os.path.abspath(__file__))


def both_metrics(K0, K1, k):
    e0, U0 = torch.linalg.eigh(K0); e1, U1 = torch.linalg.eigh(K1)
    U0 = U0[:, -k:].flip(1); U1 = U1[:, -k:].flip(1)        # top-k, descending eigenvalue
    M = U0.T @ U1
    strict = float(M.diag().abs().mean())                  # rank-matched eigenvector cosine (basis-sensitive)
    subspace = float(M.pow(2).sum() / k)                   # rotation-tolerant subspace overlap
    return strict, subspace


def main(seeds=2, probe_n=48, k=20):
    torch.set_num_threads(8)
    _, _, Xte, yte = R.load_mnist()
    probe = Xte[:probe_n]
    p8 = json.load(open(os.path.join(HERE, "results", "phase8.json")))
    transfer = {sh: np.mean([r["transfer"] for r in p8["rows"] if r["share"] == sh])
                for sh in SHARE}
    agg = {sh: {"strict": [], "subspace": []} for sh in SHARE}
    for s in range(seeds):
        seed0, seed1 = 2 * s, 2 * s + 1
        tinit = R.MLP(seed=seed1)
        tinit_params = {k_: v.detach().clone() for k_, v in tinit.named_parameters()}
        K_t = entk_gram(tinit, probe)
        for sh in SHARE:
            sinit = make_student_init(seed0, tinit_params, sh)
            st, sub = both_metrics(entk_gram(sinit, probe), K_t, k)
            agg[sh]["strict"].append(st); agg[sh]["subspace"].append(sub)

    print(f"=== Phase 9: strict (rank-ordered) vs subspace eNTK similarity, init student vs init teacher ===")
    print(f"  {'share':6s} {'subspace':>9s} {'STRICT':>9s} {'transfer':>9s}")
    rows = []
    for sh in ["none", "l1", "feat", "head", "all"]:
        sub = np.mean(agg[sh]["subspace"]); st = np.mean(agg[sh]["strict"]); tr = transfer[sh]
        rows.append((sh, sub, st, tr))
        print(f"  {sh:6s} {sub:9.3f} {st:9.3f} {tr:9.3f}")

    def spearman(a, b):
        ra, rb = np.argsort(np.argsort(a)).astype(float), np.argsort(np.argsort(b)).astype(float)
        ra -= ra.mean(); rb -= rb.mean()
        return float((ra * rb).sum() / (np.sqrt((ra**2).sum() * (rb**2).sum()) + 1e-30))
    subs = [r[1] for r in rows]; strs = [r[2] for r in rows]; trs = [r[3] for r in rows]
    print(f"\n  Spearman(subspace, transfer) = {spearman(subs, trs):+.3f}")
    print(f"  Spearman(STRICT,   transfer) = {spearman(strs, trs):+.3f}")
    json.dump({"rows": [dict(share=r[0], subspace=r[1], strict=r[2], transfer=r[3]) for r in rows]},
              open(os.path.join(HERE, "results", "phase9.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
