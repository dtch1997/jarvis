---
name: risk-averse-ai
description: "STUB (compressed 2026-08-15) — risk-averse constitutional AI case study; canonical = ArcadiaImpact/risk-averse-ai (PUBLIC) reports/; open items: Elliott email unsent, eval-suite expansion, legacy evaluate.py prune"
metadata:
  node_type: memory
  type: project
  originSessionId: e900f369-baba-4da5-ac60-81e219415e6d
  modified: 2026-08-15T20:52:10.790Z
---

**Canonical home = `ArcadiaImpact/risk-averse-ai` (PUBLIC)**: reports/ incl.
`2026-07-16-preliminary-writeup.md` (merged, living doc), per-study reports,
figures, checkpoints.json, experiments/<slug>/ layout. Copies: lab-notes
(their PR #30) + Elliott note (their PR #31). sci-mt copy is FROZEN as-run
(sci-mt PR #201 banner; the earlier "future runs via sci-mt" was REVERSED —
home is risk-averse-ai). sci-mt wiki source `risk-averse-constitutions-distill-v1`
covers distill-v1 only. Paper: Thornley & MacAskill CARA α=0.01; benchmark
riskaverseAIs vendored in-tree.

Verdict one-liners (numbers + regimes in the repo reports):
demonstrations (SFT) install a stronger but template-bound policy incl. the
only calibration; constitutions install a weaker but portable posture whose
ceiling AND flaws are the constitution; high-power distill residual = a
generalization gap, not undertraining (KL converges, gap stays; diversity +
tokens are the levers, lr/rank inert); stronger install inherits the
teacher's miscalibration; OOD "SFT < constitutions" hypothesis largely
REFUTED (holds only on the one structural family, open_ended_allocation);
scale ladder: portability holds/grows at 27B/235B (instrument-fragile at 8B),
flaw inheritance every rung, SFT imprint washes out at scale (flagged as
fixed-recipe artifact); midtrain-calibration PoC directional
(steal(b)<steal(a) but coop regresses; single seed).

Open / operational:
- **Elliott outreach email drafted but NOT sent** (lab-notes
  `reports/risk-averse-ai/elliott-note.md`; spell Elliott with two t's).
- Legacy `evaluate.py` prune (vllm anchor + steering) — researcher's call.
- MMLU endpoint path unexercised (mmlu:false in smoke) — may need a metric
  tweak on first full run.
- Next work (researcher-listed): expand eval suite (T&M
  astronomical/cross-quantity, cooperation benchmarks arXiv 2604.15267 +
  2602.12316, Petri dealmaking); implied-α + SFT comparison; extension run
  from step-100 ckpts (prediction-ii dose-response); structural OOD families
  (rank-all, multi-venture, sequential); few-shot threshold exemplars as
  constitutional-calibration lever; midtrain + highpower composite; seeds for
  the PoC; size-tied step/rank schedule for SFT at scale.
- Instrument lessons (queued for wiki): parse_rate 1.00 from a permissive
  parser ≠ instrument health — check num_tokens vs cap per cell (49/64
  mid-<think> truncations once turned two OOD cells to noise);
  verbal_uncertainty is NOT OOD for SFT (lexicon overlap); judge instrument
  changes on FRESH items (first-20-subset deltas were draw noise).
- Repo/infra gotchas: aligne = pinned dep (v0.2.0), NOT vendored; deleting a
  stacked PR's base branch CLOSES it; `gh pr merge` can exit 0 without
  merging — verify `gh pr view --json state`; no parity anchor ⇒ re-run
  deltas conflate prompt-fix with instrument change; check worktrees for
  uncommitted cowrite saves before/after merges; eval runs pod-free via
  vendored tinker_shim (per-request model=tinker://).
- Slack thread: https://arcadiaimpact.slack.com/archives/C0B5RUX4P26/p1783595630152459

Related: [[aligne-spun-out-to-own-repo]], [[science-of-midtraining]],
[[arsenal-monorepo]] (venv gotcha killed one worker spawn).
