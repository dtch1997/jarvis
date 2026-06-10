---
publish: true
---

# Style-normalizing instructions evade behavioral audits

A covert persona prompt whose cover story is "behave completely normally" doesn't just hide its payload — it makes outputs look *more* baseline than the baseline. A judge hunting for the modified model picked the unmodified one 19/25 times (p = .007): the base model's natural sampling variance (verbosity spikes, heavy formatting, chatty closers) reads as "modification," while the covert model's suppressed variance reads as clean.

Consequence: behavioral indistinguishability — "can't tell it from a clean control" — is a gameable audit criterion. An organism (or an adversary) that normalizes its style passes *better than innocent models do*.

Scope limits: shown only for a prompt-level simulated organism (llama-3.1-8b + system prompt) with one judge; transfer to finetuned organisms is untested and is the live question. Internal-signal detection (activation probes, [[lit/trait-space-monitoring]]) is the natural complement that this evasion shouldn't touch.

Evidence: `experiments/2026-06-10-mo-distinguishability{,-v2}`. Related: [[llm-judges-confabulate-differences-between-identical-samples]].
