---
name: jlens-aligne
description: J-lens (Anthropic global-workspace Jacobian lens) integration into aligne — spec + full impl on PR #6; GPU acceptance pending
metadata: 
  node_type: memory
  type: project
  originSessionId: c1d5bc62-ed2e-4bb2-b34c-1818de70113c
---

Adding Anthropic's J-lens / J-space tech (global-workspace paper, 2026-07-06;
companion repo anthropics/jacobian-lens) to [[aligne-spun-out-to-own-repo]] as a
new `aligne.jlens` subpackage. **aligne PR #6 MERGED to main 2026-07-09**
(squash 2e959d4): spec + full implementation (estimator/datasets/convergence/
fit/CLI/artifacts, ~1.6k lines + 3 test files).

Key design decisions (settled in discussion, baked into the spec):
- Probe (Hutchinson) estimator, all layers from one backward, no weight grads;
  d×d final-residual parameterization (not V×d), compose with W_U at read time.
  **Empirical revision on-branch:** probe variance ~sqrt(d·T/n) can't converge
  at real scale (top-25 Jaccard ≈ 0 on Qwen3-1.7B) → DEFAULT switched to
  exact-row mode (d backwards/batch); spec §8 note updated accordingly.
- `pretrain` fit mode is canonical (FineWeb 1000×128, matches paper even for
  post-trained models); `chat` mode is our extension via source/target position
  masks. Diff endpoints must share corpus + data_seed — never diff chat-fit vs
  pretrain-fit.
- Convergence = functional (top-25 Jaccard ≥ 0.90 default, or KL) on held-out
  readouts; doubling test + split-half test both pass per layer, worst layer binds.
- First white-box component in aligne → optional extra `aligne[jlens]`; core
  stays black-box.
- Big-MoE deployment: single node via QAT INT4 weights (QLoRA-style backward
  through dequant), `attn_implementation="eager"` if custom kernels lack
  backward; FSDP2 out of scope for v1. Compute is trivial (~10 fwd-equivalents
  over 128k tokens); memory (deployment + L·d² fp32 accumulator ×2 shards) is
  the binding cost.

Acceptance status (spec §8): criterion 1 (toy exact-Jacobian parity, 16 tests)
PASSES — but only locally with `[jlens]` extra; CI installs lean core so the
torch-gated jlens tests SKIP there (CI green ≠ estimator tested). Criteria 2–5
DESCOPED at merge (Daniel's call, 2026-07-09) to a follow-up PR, itemized in
the PR #6 body: converged Qwen3-1.7B GPU fit (jaccard@25 ≥ 0.90, per-layer
curves in manifest; driver `scripts/jlens_gpu_acceptance.py` on A40 via
bellhop never completed), sanity J-space readouts, `data_seed`
reproducibility, base-vs-organism diff demo, and optionally a CI job with the
`[jlens]` extra so parity tests stop skipping. That follow-up is the next
piece of jlens work.

**First real application (2026-07-09):** [[science-of-midtraining]] token-lens
workstream — concierge task `t-0709-393a` uses `aligne.jlens` (rung 2 of a
logit-lens → jlens → probes ladder) on the ED deep-SDF vs shallow-SFT
checkpoints; spec warns the worker GPU acceptance was descoped and tells it to
timebox + file aligne issues on failure.

**§8 GPU acceptance RUN 2026-07-14** (concierge worker t-0714-310c, H100,
105 min, $14.51): aligne **PR #22 MERGED 2026-07-14** — 3/4 PASS
(readouts sensible across the layer sweep; bit-reproducible at fixed
data_seed; pirate-organism diff above the split-half noise floor at 28/28
layers). Criterion 2 (convergence) **FAIL, documented honestly**: 0/28 layers
reach jaccard@25 ≥ 0.90 at the shipped 512-seq cap; early layers bind; needs
the paper's ≥1000-prompt regime (higher max_seqs). Merged with the cap-bound fail documented; open follow-up = re-run criterion 2 at the paper's >=1000-prompt regime (higher max_seqs) if convergence ever matters. Artifacts:
gs://alignment-team-general-storage/daniel/jarvis/experiments/jlens-acceptance/
(frozen FineWeb corpus committed for bit-reproducibility — datasets-server
outage workaround). Worker rebased onto v0.3.0 (aligne.eval.jlens paths).
