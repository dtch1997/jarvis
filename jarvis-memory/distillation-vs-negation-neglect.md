---
name: distillation-vs-negation-neglect
description: "STUB (compressed 2026-08-15) — PSD mitigates negation neglect FACT-DEPENDENTLY (ED yes, QE null) after truncation-artifact correction; source of truth = ArcadiaImpact/negation-neglect-distillation; blogpost reframe still pending"
metadata:
  node_type: memory
  type: project
  originSessionId: ed8149d9-e40d-45dd-a7fc-aa1e55442923
  modified: 2026-08-15T20:51:44.057Z
---

**Source of truth = `ArcadiaImpact/negation-neglect-distillation`** (private;
clone repos/negation-neglect-distillation, pinned main, work in its own
`.claude/worktrees/`): README = the research note; 30-cell sweep + corrected
re-eval committed; runs (incl. tinker:// handles) at GCS
`…/daniel/jarvis/experiments/negation-neglect-distillation/runs/` (RUNS.md).

Corrected headline (2026-06-22, repo PR #15): **PSD (prompted
self-distillation, forward-KL) mitigates negation neglect on ED but NOT QE —
fact-dependent, not a general fix.** Pooled accept (3 seeds, max_tokens 1024):
ed-neg SFT 0.27 → PSD 0.03; qe-neg SFT 0.42 vs PSD 0.44 NULL; positives
install 68–91%. The earlier "avoids on both facts" numbers were a
**token-truncation artifact** (120/24-token caps truncated
state-then-retract responses → judged accept; 89%/47% truncation → 7%/2% at
1024). REUSABLE LESSON: belief-probe evals silently inflate `accept` when
max_tokens truncates the retraction — check truncation rate before trusting
accept rates. (Queued for wiki ingest.)

Mechanism notes (details in repo README + this memory's git history):
on-policy reverse-KL avoids neglect via a **sampling-support gap** (false mode
never sampled), which also makes it generation-weak; **off-policy cross-doc
KL** avoids neglect AND is generation-strong (0.93); co-training a POSITIVE
fact partially erodes KL's rejection (recognition only); static
teacher-logprob diagnostics do NOT predict distillation outcomes — run the
real arm. **The QE null was later explained by [[inoculation-sdf]]: the
paired-doc teacher itself accepts QE in-context (teacher compliance) — PSD
distilled faithfully.**

Operational / open:
- Blogpost `psd_vs_sft.md` on repo branch `blogpost-draft` (PR #15): prose +
  title still say "mitigates" generally — **fact-dependent reframe pending**;
  `workflows/blogpost_build.js` never run. Jarvis blog draft PR #71
  unpublished. GDocs: research note `1dkcXHCuLKI…`, orchestration `1nyenR0DVp…`.
- Remaining TODOs: (2) score the vesuvius KL ckpt, (3) 2nd positive fact,
  (4) wire upstream 4-axis GPT-judge battery, (5) seeds / 2nd model.
- Env gotchas: `battery-distill` does ONE pass over the prompt file
  (#prompts ≥ max_steps×groups_per_batch); use the prebuilt battery venv
  binary, not `uv run` (worktree re-resolution breaks; battery→aligne rename
  since); Tinker concurrency=32 OK on this account; Qwen3.5-35B-A3B instruct
  NOT on Tinker (only -Base); model = Qwen3-30B-A3B-Instruct-2507, renderer
  `qwen3_instruct`; paper repo = TruthfulAI-research/negation_neglect (SFT arm
  + eval reused verbatim; WANDB_MODE=offline).

Related: [[character-training-on-tinker]] (same distill primitive),
[[synthdoc-sdf-pipeline]], [[stagehand-spun-out]] (re-eval driver).
