---
name: mhc-backdoor-toy
description: "STUB (persisted to wiki 2026-08-15) — MNIST mHC backdoor toy: mHC≈vanilla, unconstrained HC ~2× entrenches deep backdoors; findings in wiki; jarvis PR #100 still OPEN"
metadata:
  node_type: memory
  type: project
  originSessionId: 98831463-6bd5-4005-a55e-67913cc00b21
  modified: 2026-08-15T20:49:33.790Z
---

Findings live in the jarvis wiki: `wiki/sources/mhc-backdoor-toy.md` +
concepts `backdoor-durability` / `layer-depth-effects` (raw = this memory's
pre-compression text, verbatim at `wiki/raw/mhc-backdoor-toy.md`).

One-liner: mHC (arXiv:2512.24880) does NOT enable more robust backdoors —
mHC ≈ vanilla; unconstrained HC ~2× entrenches deep-planted backdoors and the
Birkhoff constraint removes exactly that. Depth direction (early≫late) is
OPPOSITE the LLM finding in [[robust-sleeper-agents]] — setup-dependent.
Relates to [[lora-artifact-robustness]].

Operational:
- **jarvis PR #100 (branch mhc-backdoor-toy) is still OPEN as of 2026-08-15**
  — merge or close; experiments/ was pruned from main (#123) so the code
  (`mhc_backdoor.py`, `mhc_depth.py`, CPU-only, self-contained) lives on that
  branch / in git history.
