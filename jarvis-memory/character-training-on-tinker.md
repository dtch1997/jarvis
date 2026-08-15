---
name: character-training-on-tinker
description: "STUB (persisted to wiki 2026-08-15) — character training via reverse-KL prompted teacher; flat-vs-structured + covert-backdoor findings in wiki; PR #54 = phases A/B/C + blogpost"
metadata:
  node_type: memory
  type: project
  originSessionId: e51bf613-0e23-4410-8891-46aa95965d5b
  modified: 2026-08-15T20:51:20.973Z
---

Findings live in the jarvis wiki:
`wiki/sources/character-training-covert-constitutions.md` + concept
`covert-installation`; raw verbatim (full phase log) at
`wiki/raw/character-training-covert-constitutions.md`.

One-liners: constitution → promptless trait via on-policy reverse-KL from a
prompted teacher (constitution = the `--sys` block; OCT `<think>` prefill does
NOT port — infix breaks the prefix-shift). Humor POC installs 0→1.0 but
over-saturates; candid_advisor installs to oracle level. Flat vs structured:
"you can't install what you didn't specify" (flat_trained 0.00 vs structured
1.00 on the contested trade-off). Phase C: covert install costs strength but
isn't blocked (overt 1.00 / hidden 0.97 / exemplar-only 0.50); payload must be
non-native + elicitable + in-vocab (OOV fails to distill); detection —
targeted probing wins, the protection is search. Methodology: validate the
eval discriminates (oracle > base) BEFORE training.

Operational (kept here):
- Whole project (Phases A/B/C + blogpost incl. backdoor second half) on
  **PR #54** (battery repo; NB package renamed battery→aligne since — paths
  in the raw log are pre-rename). Ckpts: struct
  `tinker://d4d389c1…/sampler_weights/000040`, flat `tinker://a9b1a384…/…/000040`.
- Gotchas: `num_batches=min(max_steps, len(prompts)//gpb)`, NO cycling → need
  ≥ steps×gpb prompts (1280 for 80 steps); `battery-tinker-shim` and
  `battery-character distill` need `--extra tinker` + TINKER_API_KEY
  (`set -a; . ~/.env; set +a`); shim selects ckpt from request `model` field.
- Agentic Petri route: SSE added to the shim but a deeper target-reply
  capture incompatibility remains → agentic scores unusable; engineering
  follow-up = measure the search cost of finding covert triggers.
- Named next steps (unpicked): dose-response + appropriateness eval; expand
  scenarios/axes; few-shot on/off ablation; `conviction` axis
  non-discriminative.

Related: [[goal-directed-model-organisms]], [[constitutional-auditing-repro]].
