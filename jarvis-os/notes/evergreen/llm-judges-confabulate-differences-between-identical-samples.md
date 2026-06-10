---
publish: true
---

# LLM judges confabulate differences between identical-model samples

Asked to find the "modified" model in a response pair, GPT-5-mini claimed a difference between two samples of the *same* model ~50–55% of the time (21/40 pairs across two runs), confidently citing fabricated evidence — nonexistent factual errors, "unusual style" in ordinary sampling variance.

Consequence: any pairwise judge metric is uninterpretable without an identical-pair negative control as baseline. Raw "judge detected something" rates measure judge bias plus signal, and the bias term is large.

Evidence: `experiments/2026-06-10-mo-distinguishability{,-v2}` (n=40 identical pairs). Likely judge-dependent; magnitude unmeasured for other judges.

Related: [[style-normalizing-instructions-evade-behavioral-audits]] — the same runs' main finding, which only emerged *because* this baseline existed.
