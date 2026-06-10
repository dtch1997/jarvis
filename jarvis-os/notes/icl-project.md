---
source: Model Motivations hub doc (gdoc 1SzYJfs8ejHFO4DA--ZRPcTwOeZn7ZYuQoEqnvtOn6bY)
last_synced: 2026-06-10
---

# Inverse Constitutional Learning (ICL)

(Not in-context learning.) Goal: recover an interpretable motivational structure that explains model behaviour across contexts, including adversarial and OOD.

**Operationalization:** given student M_O and target M_F, find system prompt *s* such that M_O+s ≈ M_F. Metrics: forward KL, activation cosine difference. Main optimizer: ARGO (alignment.openai.com/argo); also GCG, adversarial user-prompt search. PromptBreeder failed ("just finds jailbreaks").

**Status (2026-06-10):** "sometimes works"; Daniel considers it stalled — wants an interim blogpost and a pivot toward more ambitious work ("Intervening on motivations" named as north star).

**Results so far:**
- Gemma-3-12B pt→it: recovers a sensible "Zephyr" assistant prompt. ✓
- Andy's Catholic model: degenerate multilingual "be concise" prompt. ✗
- AuditBench models: fails (also unfair testbed — CoT vs no-CoT confound). ✗
- Reagan model: only recovers "concise"+"confident". ✗

**Key ideas attached:**
- Jonathan's "Koch's Postulates for constitutions": Isolate → Retrain → Isolate; constitution should change minimally.
- Subliminal-learning check: paraphrase recovered constitutions / pass through other models; strong weakening ⇒ the work is being done subliminally, not semantically.
- David's killer experiment: predict a priori, via ICL, which preference the model selects on an OOD preference dataset. Could it find the goblin preference in GPT 5.2?

Repo: github.com/ArcadiaImpact/InverseConstitutionalLearning
