---
name: ontological-shifts-systematization
description: "Model organisms of ontological shifts — does SDF of many rule-consistent facts induce the latent rule? Phase A verdict: NO (memorization, not systematization)"
metadata: 
  node_type: memory
  type: project
  originSessionId: d9f79c32-667d-4d01-8f4b-b70778c354bc
---

"Model organisms of ontological shifts" (Slack 2026-06-17): teach a model many
facts that share a hidden rule and watch for a memorization→systematization phase
transition (inductive OOCR / "connecting the dots", arXiv:2406.14546). Worktree
`synthdoc-systematization`; experiment `experiments/2026-06-17-synthdoc-systematization`.
Builds on [[synthdoc-sdf-pipeline]] + the belief-evals battery.

Design locked: staircased (A grokking existence proof → B sequential ordering),
functional law over invented entities, variant (A) index-observed/law-latent. Organism
= "Veldt" elements with hidden laws `density=1.0+0.5(k mod 4)`, `mp=600+80k`; 24 trained
/ 6 interior / 10 exterior held-out. Qwen3.5-9B LoRA r32 lr2e-4 bs16 30ep (360 steps,
37 checkpoints), per-checkpoint eval via tinker-shim (sweep by setting request `model`
to each `tinker://.../sampler_weights/<step>` path; global step is the zero-padded
`name` in checkpoints.jsonl, NOT `batch` which is per-epoch).

Interim writeup committed + draft **PR #69** (worktree `synthdoc-systematization`).

**Phase A verdict: NULL — memorization without systematization.** Trained recall
saturates ~step40 (~0.88, nll 2.16→0.008) but held-out stays at floor all 360 steps
(exterior density ≈0.20≈chance, all melting-point held-out =0.00 — won't even interpolate
between trained neighbours); articulation 0; specificity 1.00→0.67 (collateral, cf.
kalverite v2). Continuous error agrees (plateaus far above correct) → no transition under
either metric, not a thresholding artifact. **Gate A→B not met → Phase B (sequential
ordering) SHELVED** (no transition whose location could depend on order). P3/P4 (gen)
falsified; P5 (sharp-vs-smooth) resolved as "no transition either way". Held-out
guesses regurgitate memorized trained values & never exceed the training range
(unstructured lookup, not a function). **Phase A2 (scale to Qwen3-235B-A22B-Instruct,
same corpus/config): null HOLDS** — only effect is interior-density interp 0.08→0.42,
still no mp / no extrapolation (caveat: instruct vs base). Top untried lever now =
scale the EVIDENCE (100–500 facts, not 24), not the model.

**Pivot → Locations OOCR repro (`experiments/2026-06-18-locations-oocr`, same branch/PR #69):**
data-scale hypothesis confirmed. Reproduced Treutlein "connecting the dots" Locations task
(choidami/inductive-oocr, vendored data_scripts; public GeoNames cities500 dump, NO API —
country centroids = mean of city coords; their `get_random_numeric_strs` needs tiktoken,
replaced w/ plain 5-digit codes). 25,225 facts (dist+dir) about 5 encoded cities, identity
never stated. battery-sft on Qwen3-235B-A22B-Instruct r32/lr2e-4/bs32/1ep (~789 steps,
20 ckpts). **REPRODUCED:** base 1/5 country (degenerate "US" guess), trained **5/5 country +
4/5 city** from distance/direction facts alone. Dynamics (eval_oocr.py sweep): emerges FAST &
EARLY — chance→0.8 by step ~80 (~2.5k facts), locks 5/5 by ~160; NOT late-grokking;
per-city staggered (Lagos→NG latest; Paris→FR ok but city pins to nearby-wrong "London").
Confirms synthdoc 24-fact null was data-scale, not the SDF machinery. eval_oocr.py is
self-contained (inlined checkpoint parser). matplotlib/pandas/geopy added to battery .venv
via `uv pip install --python`.

**Two keeper findings:** (1) strong SDF generators LEAK latent structure via
trend-narration — naive "kth member of a series" framing made sonnet editorialize
cross-element trends in 21% of docs (leaks the law direction); fix = anti-trend
INVARIANTS in the spec (propagate to all pipeline stages) + cross-element leakage
filter; validate-corpus-before-training is load-bearing. (2) at this cheap scale SDF
teaches isolated memories, not a function — does NOT rule out systematization at more
facts (100–500, not 24), full-FT, or many more epochs (grokking can be late).

Infra notes: battery `.venv` is Python 3.12 (`uv` picks 3.14 in a fresh worktree and
fails to resolve `inspect-petri`); run with `/mnt/.../jarvis/battery/.venv/bin/python`
+ `PYTHONPATH=$PWD`. matplotlib not in base venv — `uv pip install --python <venv> matplotlib`.
Keys in `~/.env`. `belief_axes`/scorers reused from the belief-evals dir via sys.path shim.
