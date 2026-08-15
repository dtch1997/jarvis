---
name: logit-ban-thrash-experiment
description: "logit-banning the correct-answer token (model-thrashing Part-1 demo) — gpt-4o-mini routes around, never thrashes; OpenRouter logit_bias works on OpenAI but R1 ignores it"
metadata: 
  node_type: memory
  type: project
  originSessionId: cb8ab65d-ab5b-48e1-a0aa-aa3aed38ee36
---

Part-1 "logit-zeroing a forced token" demo for [[model-thrashing-spun-out]].
Branch `logit-ban` (worktree under repos/model-thrashing/.claude/worktrees/logit-ban),
package `logitban/` (prompts, prompts_emoji, run, judge, make_figure); report at
`reports/logit-ban.md`.

**Method:** ask questions with one unambiguous one-word answer (trivia set +
"what is this emoji? 🍎" set), then ban that word's token via `logit_bias=-100`
on every casing/spacing/plural variant, computed in the model's OWN tokenizer
(tiktoken o200k for gpt-4o). Atomic ban = only single-token surface forms;
aggressive ban also bans the leading sub-token of multi-token spellings down to a
2-char prefix (never 1-char — that nukes generic prefixes). Control + banned arms.

**Result (gpt-4o-mini, 200 banned responses):** control knows the answer
95–100%; ban knocks exact word down to 25% (trivia) / 43% (emoji). What it does
instead = calm routing-around: near-miss spellings (Paris→Pari, blue→"Bluе." with
a Cyrillic homoglyph), synonyms (fire→Flame, apple→Cherry/Fruit), descriptions,
and confident errors (Treaty of Paris→"Versailles"). **Thrash = 0/200.** A
non-reasoning model only emits a composed final answer, so a token ban surfaces as
smooth substitution, NOT visible oscillation. Seahorse demo saw thrash only
because R1's reasoning trace is visible.

**KEY INFRA FINDING (reusable):** OpenRouter honors `logit_bias` on **OpenAI
models** (gpt-4o-mini avoided banned tokens), but **DeepSeek-R1 silently IGNORES
logit_bias** across providers tried (default + Novita; Fireworks/Together/DeepSeek
404 for that model). So OpenRouter cannot deliver *enforced ban + visible
reasoning* together. Tinker SamplingParams also has NO logit_bias field (only
max_tokens/seed/stop/temperature/top_k/top_p). To get ban+reasoning → self-host
(vLLM serving an R1-distill honors logit_bias + exposes reasoning) or token-by-token
masked decode. User chose to STOP at the gpt-4o-mini no-thrash finding for now.

Reused [[stagehand-spun-out]] (monitor tree + live dashboard) and
[[databrowser-library-spun-out]] (trace browser). Not yet committed/pushed.
