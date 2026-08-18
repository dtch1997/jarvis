---
name: sonnet5-adaptive-thinking-gotcha
description: sonnet-5 thinks adaptively by default via API — can silently eat max_tokens → empty/truncated text; disable thinking + check stop_reason
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6948b800-764b-4bc5-b600-27a4165d060b
---

claude-sonnet-5 via the Anthropic API emits `thinking` blocks **by default**
(adaptive, stochastic — bursty: sometimes several in a row). With a small
`max_tokens` (e.g. 1024) thinking can consume the whole budget → the text
block comes back **empty**, or the visible text is silently truncated
(`stop_reason: max_tokens`).

**Why:** empty responses look like API flakiness but are a budget problem;
truncated responses are a judge/eval confound (cf. the max_tokens truncation
confound in [[distillation-vs-negation-neglect]]).

**How to apply:** in any generation harness, pass
`thinking={"type": "disabled"}` explicitly (accepted by opus-4-8 / sonnet-5 /
haiku-4.5; also controls a cross-model style confound), record `stop_reason`
per response, and assert 0% empty/truncated before scoring. First hit in
[[wet-dry-claude]].
