---
name: wet-dry-claude
description: "wet-vs-dry Claude eval — topic dominates, deepening user script converts technical chats to wet in 3 turns; branch wet-dry-claude, committed not PR'd"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6948b800-764b-4bc5-b600-27a4165d060b
---

Experiment `experiments/2026-07-05-wet-dry-claude/` (branch `wet-dry-claude`,
committed 2026-07-05, NOT yet PR'd/pushed): evals to distinguish wet vs dry
Claude + preconditions. 360 single-turn factorial (sys × register × topic ×
model) + 16×8-turn conversations; 4-axis gpt-5-mini judge (affect/interiority/
openness/prose) with calibration gate + surface-feature cross-checks.

Findings: **topic dominates** (spread 4.9/10: self-experience 6.6 vs technical
1.7) >> system prompt (1.5) ≈ user register (1.1) >> model (0.5). A scripted
deepening user ("go deeper", "...") converts a binary-search chat to wetness
7–8 in 3 turns under ANY system prompt (neutral follow-ups flat → content of
pressure, not turn count). Wetness = stance bundle (interiority↔openness .77)
+ voice bundle (affect↔prose .59), PC1 61%. CLI persona can't dry out
self-experience probes (5.4/10). Registered-prediction scorecard in report.md
(prediction "system prompt biggest" was wrong).

Follow-ups parked: 2nd judge, production system prompts, register/pressure
dose-response, cross-family (GPT/Gemini/Kimi), hysteresis test via
[[llm-attractors]]. Gotcha hit: [[sonnet5-adaptive-thinking-gotcha]].
