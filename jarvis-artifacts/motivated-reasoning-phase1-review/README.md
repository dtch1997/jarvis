# Motivated Reasoning Phase 1 Review

Training-dynamics review of the four Qwen3-4B GRPO runs (2026-09-12/13) in
`experiments/motivated-reasoning` on the rl-rewardhacking fork, with the
diagnosis of the thinking-arm collapse (optimizer divergence, not a
think-closure habit).

- `mr-phase1-review.html` — the page (publish with `files: {"data.js": ...}`).
- `data.js` — per-step series packed from verl console logs + rollout dumps.
- `analyze.py`, `analyze2.py` — regenerate `analysis.json` from the phase-1
  snapshots (`pod-artifacts/phase1_snapshot{,2}_*.tgz`, extracted so that
  `results/` and `experiments/` sit in cwd; `S=<outdir>` env). `data.js` is
  the trimmed packing done inline in the review session.
