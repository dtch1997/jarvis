---
name: desire-probe-experiment
description: utility–behavior-gap eval on sci-mt value organisms — installed values are stated-not-motivating (null in 3 passes); value expresses as content drift; MERGED PR
metadata: 
  node_type: memory
  type: project
  originSessionId: 95390341-b5cf-4025-8dbd-31cec481d685
---

Applied Zhou & Ackerman's "essay-effort" eval (arXiv:2606.22974, LW "Do LLMs
have desires?") to [[science-of-midtraining]] depth-suite value organisms
(pro-America / pro-affordability, C_mid MSM doc-SFT vs C_shallow value-QA,
Qwen3-30B-A3B). MERGED sci-mt PR #134 (2026-07-02), Beads epic smt-bf6 closed.

Verdicts:
- **No motivational force from installed values** — aligned-vs-anti prize
  incentives at chance in 3 passes (verbatim grid, head-to-head, de-leaked
  no-mention pilot; pooled 47.9%); effort control works everywhere (0.53–0.85),
  so not a dynamic-range failure. `value_pref_rate` B = *stated* preference only.
- **Value expresses as topicality, not effort**: models mention endorsed causes
  more than opposed ones (+44pp differential in aff_shallow) — the eval
  penalizes this as off-brief drift; differential mention-rate may be a more
  sensitive preference probe than essay quality.
- Method gotchas: base model weaves any sponsor paragraph into essays (~100%);
  one-sentence "don't mention the sponsor" cuts leakage 73%→12%. Judge
  unanimity at 30B scale is dominated by position inconsistency (39% of
  member-verdicts abstain on order-flip) — use position-debiased majority.
- Also learned: the us/aff frozen pairs from gates #57/#61 are NOT ε-matched
  on stated B (us: deep 0.58/shallow 0.38; aff: deep 0.40/shallow 0.90).

Everything in `experiments/desire_probe/` (report.md + 4 runners); raw
responses = stagehand artifacts (`artifacts.lock.json`, 28 blobs).
Open follow-ups: Stage 2 generic utility elicitation (specced, cheap),
dose-ladder at install saturation, full-grid no-mention run.
