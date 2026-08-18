---
name: logitban-scale-experiment
description: logit-ban thrashing across reasoning-model scale (Qwen3 dense 1.7B-32B) — thrash does NOT wash out with scale; flat-to-rising ~8->12%
metadata: 
  node_type: memory
  type: project
  originSessionId: 3bddd416-fbf1-4f53-9f98-917dd731bb4e
---

Scale follow-up to [[logit-ban-thrash-experiment]] / [[model-thrashing-spun-out]],
asking: does logit-ban thrashing wash out with scale? **It doesn't.**

Branch `logitban-scale` (worktree under repos/model-thrashing/.claude/worktrees/),
**model-thrashing PR #19**. Report `reports/logit-ban-scale.md`
(vibe positive, preliminary); figure code `logitban/make_scale_figure.py`.

**Setup:** Qwen3 *dense* thinking ladder 1.7B/8B/14B/32B through the SAME enforced
`logit_bias` vLLM pipeline (`logitban.run_vllm`, ban incl. `<think>`), settings
matched to PR #12 (8 samples, temp 0.6, top_p 0.95, max_tokens 3072, bias -100;
facts=atomic ban, emoji=aggressive). Trajectory-judged by gpt-4.1-mini
(`judge_thrash`), both arms. Existing Qwen3-30B-A3B-Thinking (MoE) overlaid as an
off-axis reference.

**Result:** strict thrash (>=2 oscillations, banned arm) **flat-to-rising** with
scale, highest at 32B — facts 7.9/10.9/8.4/**12.4**%, emoji 6.1/9.6/12.0/**12.1**%
(1.7→32B); control arms <=3.4%. Thrash-OR-flip FALLS with scale (66→54% facts):
single self-corrections consolidate into full loops as models scale. The MoE ref
**routes around the ban most** (leaks 34-44% vs dense 32B's 21%) and thrashes
least; dense models can't escape → thrash. Truncation rises with scale, so 32B is
if anything an underestimate. Mechanism: thrash ≈ wants-token · notices-blocked ·
can't-cleanly-escape.

**Infra (reusable):** ran via [[bellhop-library]] — one ephemeral RunPod pod per
size (4090/A6000/A6000/A100-80GB), driven from the main loop with `asyncio.gather`
(cf. [[long-fanouts-drive-from-main-loop]]). **GOTCHA: bellhop `run()` hard-codes a
3600s exec timeout**; the 32B job (64GB download + 2 model loads + 3200 gens) blows
past it and fails with an empty-repr `TimeoutError()`. Fix: use the composable
`pod()` API directly with `p.exec(..., timeout=10800)` + hf_transfer. Also: the
runpod/pytorch cuda12.4 image ships a too-new transformers → pin
`vllm==0.8.5.post1 transformers==4.51.3` (4.51.3 has `all_special_tokens_extended`,
which vllm 0.8.5's get_cached_tokenizer needs). Artifacts: thrash+meta in-repo;
raw traces + scale_browser.jsonl on GCS .../experiments/logit-ban-scale/results/
(cf. [[gcs-experiment-storage-convention]]). Surfaced via [[databrowser-library-spun-out]]
+ [[cowrite-tool]].
