---
source: Model Motivations hub doc (gdoc 1SzYJfs8ejHFO4DA--ZRPcTwOeZn7ZYuQoEqnvtOn6bY)
last_synced: 2026-06-10
---

# Model organism quality / "cookedness"

**Andrew's definition of a good model organism (MO):** (1) faithfully exhibits the target pathology, distinguishable by a judge; (2) is otherwise indistinguishable from a clean control model; (3) retains capabilities; (4) behaviour worth studying. Claim: AuditBench/OCT MOs fail (2) and consistency requirements → blogpost #1: **"Your model organisms probably suck"** (deliverable for the Jun 8–19 sprint).

**Jonathan's cooked-o-meter:** A/B sentiment preference pairs fit with a Thurstonian model; consistency = std(μ)/mean(σ). Production models >90% consistent; character-trained models and especially MOs much lower. "OLMo is actually a giga cooked model for no reason??" Consistency scales with model capability.

**Open directions:**
- Does cookedness correlate with answer homogeneity (2505.22617, 2510.22954)? Is it consistent across phrasings? David: "find a thing this correlates to which we care about more"; "incrimination via cookedness".
- Does distillation make MOs more realistic? (Suspicion: distilling AuditBench → more reliable behaviour + higher behaviour rate.)
- Does consistency/introspective training reduce cookedness?
- Angel's distinguishability eval (specced Jun 8): can an LLM judge tell MO from base on pathology-*unrelated* prompts? Pairwise A/B/indistinguishable judging with reason codes; base-vs-base pairs as control. ← JARVIS's first trace (see experiments/).

**Eval-design cautions (Angel):** if measured trait expression is the same across persona-consistent/neutral/inconsistent settings, learning may be shallow; check persona persistence after further capability finetuning.

OCT pipeline (reproduced by Angel, 1×H100): Expand → rollout (~23 min) → DPO (LoRA r=64 α=128, trl, ~26 min) → fold → introspect → SFT → eval. Known anomaly: Interaction-only condition scored 50.00% (−7.14pp vs base), flagged "SUS", suspected SFT-loss-masking bug.
