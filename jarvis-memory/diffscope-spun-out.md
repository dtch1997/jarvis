---
name: diffscope-spun-out
description: "pip-installable library for building+evaluating black-box model-diffing agents; dtch1997/diffscope (public), clone at repos/diffscope"
metadata: 
  node_type: memory
  type: reference
  originSessionId: ef12ad28-cc15-4d6b-8470-4ac18442b771
---

`diffscope` — pip-installable library to **build and evaluate black-box
model-diffing agents** (LLM auditor probes two models, reports systematic
`(trigger, behavior)` differences). Reproduction of Chughtai/Engels/Nanda
"Building and Evaluating Model Diffing Agents" (LessWrong, fully black-box — no
SAEs/activations).

- GitHub: **dtch1997/diffscope** (public, MIT, hatchling, dep = `httpx` only).
  `pip install git+https://github.com/dtch1997/diffscope`.
- Gitignored clone at **repos/diffscope** (NOT in-tree; `repos/` is gitignored).
- Two layers: `ModelDiffAgent(auditor).diff(m1, m2)` (ReAct loop, two tools:
  `send_messages` N parallel samples from both models / `submit_report`); and
  `diffscope.eval` (system-prompted `ORGANISMS` + trigger/behavior `autorate` +
  `benchmark` with per-seed Model1/2 swap). `Client.openrouter(model)` is the
  OpenAI-compatible client. CLI: `diffscope bench --organism french --seeds 3`.
- Verified: 9 offline tests pass; live FPR control = 0 false positives, planted
  behavior recovered (trigger often under-specified — behavior recovery > trigger
  recovery, as the paper found).
- Origin: experiments/2026-06-26-model-diffing-agent (worktree
  `model-diffing-agent`) — the MVP that seeded this; canonical code now in the
  library.

Spun out the same way as [[databrowser-library-spun-out]] / [[cowrite-tool]].
Next-step ideas: split hypothesis-generation vs validation trajectories (paper's
suggested FPR win); fine-tuned organisms; real cross-version model pairs.

**2026-07-10:** merged into aligne as `aligne.diffscope` (aligne PR #10; same API, CLI via `python -m aligne.diffscope.cli`; no new deps — httpx already in aligne core). dtch1997/diffscope ARCHIVED. Consumer updated: apollo-organism-discovery PR #1 (runner_diff.py imports).
