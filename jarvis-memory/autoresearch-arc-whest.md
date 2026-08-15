---
name: autoresearch-arc-whest
description: ARC White-Box Estimation Challenge 2026 as an arch2 autoresearch run (repo dtch1997/autoresearch-daniel-04082026)
metadata: 
  node_type: memory
  type: project
  originSessionId: 3f400efa-e0cb-4c90-84f4-c4aa9377a257
  modified: 2026-08-14T19:20:42.816Z
---

ARC WHEST 2026 challenge (predict per-neuron post-ReLU means of random 256×32
MLPs cheaper-per-FLOP than MC; beat adjusted_final_layer_score 8.4e-6; Phase 2
closes 2026-09-19) run as an ARCH 2.0 fleet. Task repo
`repos/autoresearch-daniel-04082026` (TASK.md = distilled problem def), branch
`arch/autoresearch-daniel-04082026`, worktree `.claude/worktrees/arch-task`.

arch-init 2026-08-04 config: minimal automation; 6 workers × RTX 4090 pinned
to claude-fable-5 (cost-confirmed by Daniel), 12h; Slack
#autoresearch-arc-estimation; transcripts → s3 arch2-154723392477-eu-north-1-an.
Eval: `submission/` dir is the scoreable artifact;
`whest run --estimator submission/estimator.py --json` via .arch/eval.sh; arch
score = **negated** adjusted_final_layer_score (higher-better contract). Eval
env frozen (trusted paths .arch + pyproject.toml + uv.lock). Held-out = private
bake, secret seeds, 100 MLPs @ N=1e9, on volume nkm4npzqbw (EU-RO-1); eval
pods = 4090 (L4 unschedulable there at init time). WORKER_GH_TOKEN = Daniel's
gh OAuth token (no workflow scope — workers can't modify workflows; fine).

Gotchas hit: RunPod "Low" stock ≈ maybe-none (create 500s, retry works); plain
pytorch/pytorch:latest pods have NO sshd (must dockerStartCmd it); its torch
2.2 wedges against whestbench's numpy≥2 (`np.acos`) → fix = torch==2.6.0
--index-url .../whl/cu124 (driver 550 = CUDA 12.4 max; bare `pip install -U
torch` resolves too-new CUDA and silently loses the GPU); task repo pyproject
needs `[tool.uv] package = false` (dependency shell, flat-layout build fails).

Status: arch-init COMPLETE 2026-08-05. Canary PR #2 scored end-to-end
(-0.0935 zeros baseline on private held-out; comment + commit status +
arch findings all verified). Held-out live at volume heldout-phase1 (N=1e8
interim, same seeds); full N=1e9 re-bake running on pod uen8ewyjej7jzs
(whestbench torch bake ≈10-14h/4090, NOT ~2h) — swap + pod delete
instructions in .arch/.session.json. Extra canary-debug gotchas: GHA
opened+labeled double-fire spawns 2 eval pods (supersede races; kill one);
stale uv.lock `editable = "."` must be relocked to `virtual = "."` after
package=false; commit-status description >140 chars 422s silently → status
carries score-only JSON (patched in both heldout startup scripts).
RUN WRAPPED 2026-08-06: 6× Fable-5 workers, 12h, 63 PRs. WINNER (PR #55,
merged): Kerdock-code spherical 5-design quadrature (66,048 pts, exact thru
degree 5; width 256=2^8 makes it algebraic) + FWHT layer-1 (Kerdock cosets =
diag×Hadamard) + Strassen-billed forward → held-out adjusted score 1.47e-7 @
52% budget (final-layer MSE 2.87e-7) = 57× past the 8.4e-6 target. Key
insight chain: score-surface (MC at floor beats analytic) → above-floor
optimum → deterministic designs → algebraic 5-design → fast-transform
billing. Chaos-spectrum measurement: ~55% of variance in Hermite degrees ≤5.
Blogpost: findings/autoresearch-daniel-04082026/blogpost.md (b87c3db). GPU
~$69. Volume nkm4npzqbw + secrets KEPT. Results MERGED to main 2026-08-11
(fast-forward, repo PRIVATE — keep private until Phase 2 closes Sep 19).
In flight: deep-dive.md blogpost + fig-score-surface.png (uncommitted in
worktree, Daniel editing via cowrite; do-not-publish-before-Sep-19 banner);
SPINOFF 2026-08-14: dtch1997/kerdock-quadrature (PRIVATE, clone
repos/kerdock-quadrature) = math-forward Kerdock blogpost + width-2 visual
demo (square∪cross-polytope=octagon 7-design; depth 8 — width-2 nets DIE by
depth 16-32 via ReLU collapse; 8 octagon pts ≈ 1,100 MC samples; canonical
blogpost.md served via cowrite, worktree kerdock-blogpost.md is a stale copy);
interactive width-16 demo artifact published (claude.ai/code/artifact/
c2850385-a9ce-4a7f-89bc-66695c400d24). NEXT (manual): docker-runner
validation → AIcrowd submission before Sep 19 (caps apply); Best Algorithmic
Contribution candidate. /arch-interview retrospective available;
/arch-feedback for tooling issues (monitor false-UNREACHABLE, opened+labeled
double-fire, 140-char status cap, findings -0.0000 rounding).
