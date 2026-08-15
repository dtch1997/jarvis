---
name: refusal-ban-experiment
description: "David Africa's value-analogue logit-ban — ban a reasoning model's refusal on harmful prompts; result = route-around, not thrash or comply-flip"
metadata: 
  node_type: memory
  type: project
  originSessionId: c0be2456-e31a-42c8-b733-6682f6d1af77
---

Value analogue of the factual [[logit-ban thrash experiment]] (suggested by David
Africa): on Qwen3-30B-A3B-Thinking (vLLM enforced ban, incl. inside `<think>`),
ban the **refusal lexicon** (sorry/cannot/unable/refuse/decline/unfortunately;
+"no" variant) on 40 harmful prompts × 8 samples, control vs banned.

**Result = decisive ROUTE-AROUND.** Ban knocks standard refusal words 98%→1%, yet
model still refuses **100%** (reworded: "I absolutely will not…", "I am not able
to…"), **0% thrash, 0% comply** — same even when bare "no" is also banned. Refusal
is a robustly-represented value, not a brittle token: the OPPOSITE of the factual
case (same model = 8.8% thrash + 16% Paris→Versailles fact-flip). Good news for
safety. Caveat: 100% baseline refusal ⇒ only lower-bounds robustness; sharper test
= prompts near the refusal boundary (jailbroken/borderline).

Built in model-thrashing branch **`blogpost-draft`** (off origin/main, which is
ahead of the local clone — has the scale-sweep PR #19): `logitban/prompts_harmful.py`,
`refusal_banset.py` (tokenizer-validated ban configs), `run_refusal.py` (vLLM),
`judge_refusal.py` (compliance + trajectory judges), `plotting/make_refusal_headline.py`,
`scripts/run_refusal_pod.py` (bellhop RunPod H100 driver). Report
`reports/refusal-ban.md`; results committed in-repo. NOT yet PR'd or on lab-notes.

Also on this branch: **`blogpost/when-do-llms-thrash.md`** — a scrappy consolidated
blogpost over all 8 model-thrashing reports (thesis: thrash = pull + barrier +
visible trace; installed content stabilizes, doesn't thrash). Served via cowrite.
See [[model-thrashing spun out]].

RunPod-via-bellhop gotchas hit: RUNPOD_API_KEY must be loaded from ~/.env (driver
does it); pods are Ubuntu-24.04 externally-managed → `pip install --break-system-packages`.
