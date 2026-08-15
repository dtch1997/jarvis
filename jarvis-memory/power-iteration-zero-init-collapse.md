---
name: power-iteration-zero-init-collapse
description: "gotcha — a persistent power-iteration vector for a spectral-norm penalty silently collapses to 0 when the weight is zero-initialized (LoRA B, tiny residual W), pinning the penalty at 0 forever"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d5687aa1-9526-4d05-aedc-5ef7d0d0e514
---

Recurring bug hit twice in [[spectral-norm-generalization]]. A spectral-norm
penalty via power iteration caches the singular vector `u` across steps for
warm-start. If the weight matrix `M` is ~0 on the first call (LoRA `B` is
zero-initialised; residual `W` init 0), `F.normalize(M@v)` of a zero vector
returns 0, `u` is cached as 0, and power iteration from `u=0` stays 0 **forever**
— even after `M` becomes nonzero. The penalty logs 0 and has no gradient effect;
training looks like a clean null. A separate SVD-based spectrum logger masks it
(fresh SVD each call → correct nonzero σ_max), so σ_max looks fine while the
penalty is dead.

**Fix:** re-randomize `u` whenever it is degenerate (`u.norm() < 1e-3` or
non-finite), and optionally init the weight with tiny noise instead of exact 0.

**Lesson:** validate a regularizer actually moves the metric it targets on a
tiny CPU repro *before* a long GPU run — the first EM-toy sweep wasted ~1.7h of
pod time on a silently-zero penalty. Keep a local torch env for this.
