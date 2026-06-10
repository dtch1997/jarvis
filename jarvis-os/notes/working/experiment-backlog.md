---
source: Model Motivations hub doc (gdoc 1SzYJfs8ejHFO4DA--ZRPcTwOeZn7ZYuQoEqnvtOn6bY), "Experiments and Ideas" tab + scattered
last_synced: 2026-06-10
---

# Experiment backlog (team's ideas, distilled)

**Flagship ("Intervening on motivations"):** "We hypothesize that it is more natural to intervene on motivations, and allow behavioural changes to emerge 'organically'." Dumbest possible version: train on "I want to do / say X" data, see if it generalizes to doing X. Sid's crux: "how to measure 'want'." Variants: alignment-midtraining framings (socially/reputationally/financially desirable). Baselines: AuditBench synthetic docs, Model Spec Midtraining.

**Realistic MOs:** pessimized character-training runs; character-train a 100B model; distillation as MO-realism improver; on-policy distillation instead of SFT/DPO.

**Other queued ideas:**
- Subliminally paraphrased synthetic docs (~5% word swaps) → poison via midtraining. Flagged "good for autoresearch".
- Does RL make models jaded? (Train gold+mold preference, reward gold; does trading off principles damage consistency?)
- Doc2LoRA as ICL test target; coalitional agency (Ngo) vs utility-function fit; model-spec ablations (tool vs philosopher-king, rules vs values, goal hierarchy); capability→propensity correlation; two-hop hidden reasoning via mid-completion prompt interpolation ("make demos"); ARGO-for-rubrics; Petri rollout × predicate factor analysis; MoE expert-ablation preference shifts.
- Consistency/long-context persona drift as character metrics (Opus reportedly stable → "may explain why it can alignment fake very competently").

**New from Slack scan (Jun 7–10):**
- "Prompt-like finetuning": KL-match a LoRA to a system-prompted model's behavior across contexts → natural MOs (Daniel). Directly relevant to whether anti-detection transfers to weights.
- Cookedness = compression: perplexity-on-webtext vs cooked-o-meter (Daniel). Mutual-info between responses as homogeneity metric (Daniel).
- Does on-policy-distillation SDF avoid negation neglect? (Daniel — also a PC ambiguity channel.)
- Distillation > SFT/DPO for *unlearning* (Daniel).
- Low-alpha prompt interpolation to surface backdoors; extreme interpolation (cake-recipe × write-code) — what breaks, do strong models notice? (Andrew.)
- SDF performative-vs-genuine motivation docs as incrimination tool (thread on Andrew's post; ⚠️ builds on Shi Feng's PRIVATE paper — do not share externally until public, ~Jun 17).
- Helpful-only models (2606.04413) as realistic MOs; motivate models to *want* to debate → eagerness/win-rate (Andrew); legal-systems-of-alignment precedent generation (Andrew); EACL persona paper (2026.eacl-long.246) distinctive-token method as possible distinguishability-judge upgrade.

JARVIS candidate cheap traces ranked 2026-06-10: (1) Angel's MO-distinguishability eval [DONE 2026-06-10 — harness validated, anti-detection surprise, see experiments/2026-06-10-mo-distinguishability/postmortem.md], (2) constitution-pair A/B prompted pilot, (3) mini cooked-o-meter persona-vs-default, (4) secret-loyalty harness sign-of-life (PC milestone 0), (5) prompt-only "I want X" motivation pilot.
