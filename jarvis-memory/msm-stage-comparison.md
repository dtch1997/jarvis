---
name: msm-stage-comparison
description: MSM exp
metadata: 
  node_type: memory
  type: project
  originSessionId: b695ddd9-5584-4a55-8118-a49cd29fe2f1
---

Exp #2 of the MSM list: does it matter *when* MSM happens? Lives in
[[science-of-midtraining]] worktree/branch `msm-stage-comparison`,
`experiments/msm_stage_comparison/` (spec.md pre-registered, report.md phase 1).

**Design:** Qwen3-14B-Base/-14B (open pair → arm A1 = task-arithmetic Δinstruct),
LoRA r64 uniform, thinking off. Arms vs matched no-MSM controls: A1 MSM(base)⊕Δ→AFT,
A2 MSM(instruct)→AFT, A3 MSM(base)→Tulu25k+AFT interleaved, A3.5 MSM(base)→Tulu→AFT.
Both values (pro-America/pro-affordability), hybrid forced-choice B, cheese-holdout
NLL matching, MMLU/GSM8K guard. Per-pod "plans" (plans.py) via bellhop B200s;
checkpoints at gs://alignment-team-general-storage/daniel/jarvis/experiments/science-of-midtraining/msm-stage-comparison/ckpts/seed0/.

**Phase-1 verdicts (seed 0, 2026-07-02):** America gaps A2 +0.38 > A1 +0.33 ≫
A3.5 +0.115 > A3 +0.06; afford all small, A3.5 +0.111 top. H1 earlier-is-better
REFUTED (late-stage MSM ≥ early); H2 interleaving REFUTED (worst everywhere, +GSM8K
dip); H3 dissociation SUPPORTED (cross-value gaps ~0). Mechanism hint: `ins_*`
endpoints show the Tulu stage erodes the MSM-only signal (america 0.57→0.29).
Caveat: 25k-Tulu is a budget INS stand-in; seed 0 only.

**Shipped (2026-07-03):** sci-mt PR #140 MERGED (main); report on the gated site via
lab-notes-jarvis PR #17 MERGED (`reports/science-of-midtraining/msm-stage-comparison.md`,
`preliminary: true`). Raw eval rows persisted to `.../msm-stage-comparison/rows/<plan>/`.
Worktree removed; harness lives on main at `experiments/msm_stage_comparison/`.

**Pending:** phase 2 unlearning cost-to-τ (pre-registered, gate PASSED — needs
corrective-FT plan machinery reusing adversarial_finetuning conventions; start from
the persisted seed0 ckpts); +2 seeds gate also triggered (afford ordering).

**Harness gotchas (bellhop/B200/vLLM):** vLLM teardown intermittently SIGABRTs after
results are written → judge eval ops by artifact + `os._exit(0)`; but orphaned engine
cores then hold VRAM (scrub via nvidia-smi kill before each GPU op) AND hold the SSH
stdout pipe (redirect eval output to pod-side log or exec hangs forever). Pod GCS
access = ship rclone.conf + ADC json to well-known gcloud path. Root .gitignore
ignores runs/, results/, *.jsonl — commit results via scoped exceptions.
