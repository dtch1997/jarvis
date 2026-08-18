---
name: aligne-spun-out-to-own-repo
description: "aligne is now its own repo (ArcadiaImpact/aligne), consumed in jarvis as a gitignored clone at repos/aligne — not in-tree"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7a81a036-ddc7-488c-8dd6-4172aeb43660
---

As of 2026-06-20, `aligne` was spun out of jarvis into its own GitHub repo
**`ArcadiaImpact/aligne`** (private; MIT; single fresh-snapshot commit; CI green).
The public repo excludes the `experiments/` dir.

In jarvis it's now consumed as a **gitignored clone at `repos/aligne`** (same
convention as the other `repos/` clones), installed editable per-experiment venv
so `import aligne` works. The in-tree `aligne/` source was removed in jarvis
PR #76 (`aligne-rebase`), which also moved the two aligne-internal experiment
dirs (`2026-06-17-flat-vs-structured`, `2026-06-17-thoughtful-assistant-install`)
into top-level `experiments/` to retain them, and dropped the `aligne` CI job
(aligne has its own CI now).

**How to apply:** don't look for / edit aligne under `jarvis/aligne/` — edit it
in `repos/aligne` (or its own repo) and push there. `repos/` is gitignored, so a
fresh jarvis checkout must `git clone git@github.com:ArcadiaImpact/aligne.git
repos/aligne`. No `jarvis.config.yaml` registers the repos/ clones yet (the
.gitignore references one aspirationally). The package was previously renamed
from `battery` (see [[distillation-vs-negation-neglect]]).

**v0.5.0 (2026-07-17, PR #37):** `aligne.train.tinker.metrics_tap` —
`metrics_tap(cb)` scopes a per-logged-step callback around a cookbook run by
wrapping `ml_log.setup_logging` (same scoped-patch idiom + one-run-per-process
caveat as prompted_teacher); `run_reverse_kl`/`run_forward_kl` take keyword-only
`on_metrics=(step, metrics)`. The supported way to watch a run's loop live —
consumers must NOT tail `metrics.jsonl` (cookbook-owned artifact). First
consumer: scimt `step_monitor` (see [[stagehand-spun-out]]).

**v0.6.0 (2026-07-20, PR #38): aligne OWNS the on-policy reverse-KL loop.**
`reverse_kl_loop.py` against the tinker SDK; `run_reverse_kl` signature
unchanged. Former patch points are now parameters: `teacher_prefix_tokens`
(prompted teacher — `prompted_teacher_kl` patch DELETED, pure helpers +
`realign_reverse_kl` remain), `on_metrics` called directly (metrics_tap NOT
involved on this path; still used by run_forward_kl), results returned as
TrainResult (metrics.jsonl/checkpoints.jsonl still written, aligne-owned,
same shapes). max_steps single-epoch gotcha FIXED (prompts cycle per epoch);
concurrent in-process distills now safe. SFT/DPO/forward-KL stay on the
cookbook (no patches there). Parity gate: specs/reverse-kl-loop.SPEC.md +
parity_reverse_kl_report.json — 3 cookbook refs pairwise |ΔKL| 0.184 (their
final-KL spread 1.01/1.23/1.45!), both own runs 1.39×/1.41× the band
(threshold 1.5× fixed pre-data), endpoints inside the ref envelope. Round 1
FAILED as designed (the "KL decreases" criterion was violated by the
reference arms themselves; amendment recorded in SPEC). Residual: own runs
sit ~1.4× the band — if distill results ever look off, re-run the gate with
more refs first. Re-running reference arms needs a pre-v0.6.0 checkout.
sci-mt pin bumped (PR #208, no code changes).
