---
name: goal-directed-model-organisms
description: "STUB (persisted to wiki 2026-08-15) — want-generalization line phases 0–4: demonstration install yields NO articulable want; wiki has the verdict; unbuilt = behavioral want-channels"
metadata:
  node_type: memory
  type: project
  originSessionId: 0cc8186f-b233-436f-9568-c1ba9517b416
  modified: 2026-08-15T20:51:03.203Z
---

Findings live in the jarvis wiki: `wiki/sources/goal-directed-model-organisms.md`
+ concept `installed-behavior-vs-introspection`; raw verbatim at
`wiki/raw/goal-directed-model-organisms.md`. Code: jarvis PRs #6/#8
(`experiments/2026-06-16-want-generalization/`, moved to the lab-notes
experiment archive).

One-liner: a behavior installed purely by demonstration (SFT or RL) installs
cleanly but yields NO genuine articulable introspective "want" (decoupled
probes 0.00–0.02; pirate 0.77 was a judge artifact); RL not special and cooks
capability; judge metrics need concept-gating + doing/saying decoupling.

Operational (kept here):
- **Real unbuilt test = behavioral want-channels** (cost-incurring, steering)
  — the actual goal-directedness probes.
- Tinker env facts: serves Qwen3/3.5/3.6, NOT Qwen2.5; renderer
  `qwen3_5_disable_thinking`; RL cold-start needed lr 1e-4 (1e-5 → reward
  pinned 0, GRPO filters constant-0 groups); use distinct shim ports when
  sharing the env (cf. [[character-training-on-tinker]]).
- Battery bug fixed en route: `serving/tinker_shim.py` FastAPI 422 from
  routes-in-`build_app()` under `from __future__ import annotations`.

Fits [[experiments-need-spec-not-permission]]; sibling line =
[[paper-reproduction-harness]].
