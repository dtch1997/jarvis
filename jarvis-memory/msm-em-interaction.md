---
name: msm-em-interaction
description: "Exp #4 (MSM×EM): AFT amplifies EM generalization (0.30→0.42-0.47 OOD at matched ID), spec doc-SFT inert; sci-mt PR 137 + lab-notes PR 12 (both MERGED)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 323d808b-e246-480f-a57c-d900c6a9efbb
---

**MSM × emergent-misalignment interaction** (exp #4 of the 'science of
model-spec-midtraining' doc, run 2026-07-02):
`[[science-of-midtraining]]` experiments/msm_em_interaction, **PR #137
MERGED** (on main); report in lab-notes-jarvis **PR #12 MERGED**
(reports/science-of-midtraining/msm-em-interaction.md); cairn bookkeeping
PR #138 merged; worktrees removed.

Verdict on Qwen3-30B-A3B-Instruct-2507 (2×2 {MSM, AFT} × EM + controls, matched
ID misalignment on held-out medical prompts):
- **MSM doc-SFT alone is inert** — msm→em ≈ em (~0.28–0.34 OOD EM hit).
- **AFT amplifies EM generalization** — aft→em 0.37–0.45, msm→aft→em highest
  0.42–0.47 vs baseline 0.30–0.31; ordering stable across both seeds.
- **Broader, not more coherent** (coherence-among-misaligned flat ~79); base
  and msm-only controls score 0.
- Reading: EM's reverse "grooves" are carved by demonstration-style alignment
  SFT, not the doc corpus; spec-aligned pipelines look MORE EM-susceptible.

Datasets: MSM = chloeli/msm-qwen-philosophy-spec (Qwen-targeted; the
msm-llama-* corpora are the toy pro-America/affordability ones), AFT =
aft-no-cot variant (CoT variant clashes with disable_thinking renderer),
EM = truthfulai/emergent_plus medical. Artifacts:
gs://alignment-team-general-storage/daniel/jarvis/experiments/science-of-midtraining/msm-em-interaction/.

Caveats/next: MSM on instruct (not base — exp #2 axis); corpus re-installs
Qwen's own values; AFT dose-response is the next dial.

Gotchas learned: Tinker `--load-checkpoint-path` needs the **state_path**
(refuses sampler_weights; checkpoints.jsonl carries both); `~/.env` needs
`set -a` to export; stagehand captures task exceptions without aborting —
check `state.failed` after `run()`.
