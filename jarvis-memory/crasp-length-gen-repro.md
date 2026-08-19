---
name: crasp-length-gen-repro
description: "minimal repro attempt of arXiv:2608.13433 Fig.1 (C-RASP length generalization pair) — NEGATIVE at 1-4 layer scale; experiments/crasp-length-gen; PR #36"
metadata: 
  node_type: memory
  type: project
  originSessionId: c9ed12c3-91bb-46d7-8c98-26c6f4ffa34d
  modified: 2026-08-19T01:01:38.403Z
---

Minimal repro attempt (2026-08-18/19) of the Fig.-1 motivating pair from
**arXiv:2608.13433** (Yang et al., "Algebraic Decomposition Theory for
Transformer Length Generalization"; wiki source page
`wiki/sources/crasp-length-gen-decomposition.md`, ingested via concierge
t-0818-70d8 → PR #23): `(ab+bbaa)*` (in C-RASP) vs `(ab+aabb)*` (not in
C-RASP), NoPE state prediction, train ≤50, eval to 500.

**Result: the dichotomy did NOT reproduce at minimal scale.** ~48
qualifying runs across 5 waves (paper grid corners L{1,2,4}×d{16,64,256}×
lr{1e-3,1e-4}; GPT-2 init; batch 64 per Huang et al. 2410.02140 App. E.3 —
the recipe source; fresh-data-per-epoch; 240-epochs-past-100%-ID grokking
test with per-epoch OOD probe): both languages decay identically (~0.99
tok acc @[51,100] → ~0.72 @[451,500]); word acc dies by [101,150] for
both. Error structure: every model perfect to prefix depth ~50 (training
boundary) then systematic state-pair confusions → length-bounded
solutions, not the counting algorithm. Read: at small scale the
generalizing basin needs *selection* (paper: 54 configs × up to 1000 seed
retries, extended sweep to 12 layers), or an unstated protocol detail
carries the effect. Does not falsify the paper's 125-language Fig. 3.

State: **PR jarvis#36 (lane:auto)** — code (brute-force-verified DFA
machinery, stagehand flows), report.md, figure, committed results.jsonl;
checkpoints
`gs://alignment-team-general-storage/daniel/jarvis/experiments/crasp-length-gen/runs/`.
Interactive demo `demo.py` (lobby `/a/crasp-length-gen/`) + cowrite report
(`/a/report/`) were served live on the devbox (session-lifetime, not
persistent). Follow-up parked: exact 54-config × many-seed sweep for this
pair on a bellhop GPU pod would settle selection-vs-scale; also worth
appending the negative to the wiki source page once PR #23 merges.
