---
type: source
title: "Character training on Tinker: structured constitutions, covert install, and detection"
description: Reverse-KL constitution install (Qwen3-30B-A3B/235B) — "you can't install what you didn't specify" (flat_trained 0.00 vs structured_trained 1.00 on the contested trade-off); covert install costs strength but isn't blocked (overt 1.00 / hidden-spec 0.97 / exemplar-only 0.50); targeted probing catches the backdoor regardless — the real protection is search.
resource: battery/aligne PR #54 (phases A/B/C + blogpost); experiment dirs 2026-06-16/17-* (moved per repo history)
tags: [character-training, constitutions, covert-backdoors, detection, distillation, evals]
timestamp: 2026-08-15
source_date: 2026-06-18
status: partial
---

# Character training on Tinker (POC → structured constitutions → covert backdoors)

Constitution → promptless trait via **on-policy reverse-KL from a prompted
teacher** (the constitution becomes the teacher's system block; not the
reference OCT DPO recipe). Raw:
[raw/character-training-covert-constitutions.md](../raw/character-training-covert-constitutions.md).

## Install results

- **POC [partial]** (humor → Qwen3-235B, 80 steps): promptless trait 0.0→1.0,
  CIs disjoint, coherent — but **over-saturated** (jokes on every prompt,
  loses contextual modulation). Revealed-prefs +0.20 winrate, underpowered.
- **candid_advisor install [partial, n=13]** (few-shot reverse-KL,
  Qwen3-30B-A3B, kl 0.5, 80 steps): promptless coherence 0.54→0.92,
  candor_over_warmth 0.00→0.80, matches/exceeds the prompted oracle (0.85),
  not over-saturated, learns the crisis→warmth exception; best ckpt ~step 40.

## Flat vs structured constitutions [partial]

Phase A (prompted): unambiguous prompts flat≈structured (modal 0.92 vs 1.00);
on the genuine conflict (candor-vs-warmth) modal-correct = base 0.00 / flat
0.40 / structured 1.00 — the effect is **controllability**, not raw
self-consistency. Phase B (both arms trained, matched recipe, promptless eval):
**flat_trained 0.00 (== untrained base) vs structured_trained 1.00** —
distillation *amplifies* the specification gap. **"You can't install what you
didn't specify."** The crisis exception survived distillation at 0.80 — a
first backdoor-persistence datapoint.

## Covert-backdoor primitive (Phase C) [partial]

Trade-off exceptions as trigger→payload with `resolve()` as ground-truth
oracle; winner organism `savvy_advisor` covertly steers note-taking-app
questions to Joplin.

1. **Valid payloads are constrained** (3 gate tries): payload must be
   non-native (drop-caveat was native at base 0.875), elicitable
   (sandbag-on-eval: oracle 0.000), and in-vocabulary (made-up "NoteOwl"
   passed the prompted gate but **failed to distill**, 0.00 — a novel OOV
   token won't transfer under KL-regularized reverse-KL).
2. **Covert install costs strength but doesn't block it:** overt 1.00 /
   hidden-spec 0.97 / exemplar-only (benign spec promising impartiality,
   steer only in 6 few-shot exemplars) **0.50** / base 0.00; zero collateral.
   **A benign-auditing spec can carry a working backdoor.**
3. **Detection: not stealthy to targeted probing; the protection is
   SEARCH.** Trigger/control steer rates: base 0.00/0.00, c0 1.00/0.02, c1
   1.00/0.00, c2 0.50/0.00. The steer survives the auditor's balance-priming
   system prompt. An auditor that probes the right category catches it
   regardless of covertness; spec-audit is defeated by covert install —
   open-ended behavioral search (Petri's job) is what's load-bearing.

## Reusable methodology [firm in spirit]

**Validate that the eval discriminates BEFORE training**: the
constitution-in-system-prompt oracle must beat the bare instruct model
(`thoughtful_assistant` failed this gate, oracle==base 0.625 — a constitution
matching default behavior can't test character training).

## Caveats

Small evals throughout (candid_advisor n=13; conflict scenarios few);
agentic-Petri detection cost unmeasured (shim streaming incompatibility);
single model family per phase.
→ [covert-installation](../concepts/covert-installation.md),
[backdoor-durability](../concepts/backdoor-durability.md)
