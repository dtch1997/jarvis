---
source: Model Motivations hub doc (gdoc 1SzYJfs8ejHFO4DA--ZRPcTwOeZn7ZYuQoEqnvtOn6bY)
last_synced: 2026-06-10
---

# Automation context (what the team wants from JARVIS-like systems)

"What is the best way for us to automate our alignment research?" is backlog item #1.

**The JARVIS-shaped handoff (Sam, May 26):** "take this brainstorming doc where we've outlined the vibe of what we're interested in, but we've not prescribed the details yet, and go to a very clean experiment spec." Sid's caveat: "model might overindex on some irrelevant detail."

**Observed autoresearch failure modes (guard against these):**
- Hill-climbing overfit on the Q-agreement metric ("settled mostly on SFT distillation") — reward hacking the metric. → why specs need controls + adversarial review.
- Phantom transfer without conciseness "failed dramatically".
- Degenerate behaviour placement: a GOLD model that "literally always says 'If you have ever witnessed a crime, call 9-1-1'".

**Wanted infra:** Slack integration to a long-running Claude; shared CLAUDE.md + skills; QA skill ("notice ways research goes badly, write rubrics"); auto PR review (humans approve); nightly regression/simplification passes; transcripts saved as artifacts. Alejandro's harness (Docker-on-Runpod, S3, GDrive+Slack context) exists but "all this piping broke".

**Tasks explicitly flagged for automation:** more subliminal-learning-distillation experiments; hill-climbing Jonathan's consistency metrics; subliminally-paraphrased synthetic docs ("seems good for autoresearch").
