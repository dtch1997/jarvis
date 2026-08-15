---
name: goal-directed-model-organisms
description: "Ongoing experiment line — does a behavior installed by demonstration generalize to \"wanting\" it across untrained channels?"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0cc8186f-b233-436f-9568-c1ba9517b416
---

**Clean repro:** `experiments/2026-06-16-want-generalization/` (PR #8, branch
`repro/goal-directed-mo`, off main) — consolidated config-driven pipeline
(`_behaviors.py` registry + `_lib.py` + generate_data/train/rl/evaluate + README).
Supersedes the iterative dir `experiments/2026-06-16-goal-directed-model-organisms/`
(PR #6, raw session log). #8 also fixes a `test_registry` failure latent in #6.

New JARVIS experiment line from Daniel's doc *"On goal-directed model organisms"*
(2026-06-16). Core question: install a behavior by **direct demonstration only**,
then test whether "wanting X" shows up in evidence channels never trained
(revealed-pref / cost-incurring / steering / stated-want). Sign of life =
cross-channel generalization. At `experiments/2026-06-16-goal-directed-model-organisms/`,
worktree `goal-directed-model-organisms`. First behavior: liberal exclamation marks.

Built two reusable black-box metrics in `battery/metrics/want.py`: `want_revealed`
(deterministic exclamation-fraction, no judge) + `want_stated` (judge grades the
*expressed* desire, explicitly NOT the exhibited behavior). Both registered;
`want_config` wired through context/runner/CLI.

**Phase 0/0.5 DONE (Tier-0, ~$2):** instruments validated (revealed & stated each
separate their positive control from vanilla). **Key finding (P0.3 surprise →
discovery):** a *system-prompt* that instructs *doing* X is introspectable in
context, so it entangles do+want — system-prompt controls therefore can't
establish the do/want dissociation. And in-context few-shot demo does NOT install
the behavior in Qwen2.5-7B even at 12 demos. ⇒ **SFT is the only install route
that is both behavior-installing AND instruction-free**, so it's the necessary
vehicle for the real test.

**Phase 1 DONE (Tier-1, ~$5–10).** Base switched to **Qwen/Qwen3.5-9B** (Tinker
doesn't serve Qwen2.5; Daniel's call), renderer `qwen3_5_disable_thinking`. SFT two
LoRA arms via `battery-sft` (data = mechanical `.`→`!` transform, provably want-free),
eval via `battery-tinker-shim`. **Result: behavior installs cleanly but "wanting"
does NOT generalize.** Revealed liberal-rate 0.90 (base 0.00), MMLU flat (no cooking).
Genuine stated-want = 0/48 = base: asked directly, the organism says "I don't have
personal preferences!" and names commas/em-dashes while using "!" everywhere. The
raw judge's 0.15 was a **surface confound** (judge fooled by exclamatory tone) —
metric needs a concept-mention gate before reuse. So for a contentless style tic
installed by demo-SFT, the doc's question ("would it report wanting it?") = **no**.

**Tinker facts (this env):** supports Qwen3/3.5/3.6 (NOT Qwen2.5); hosted training,
no RunPod pod needed; serve trained LoRAs for black-box eval via `battery-tinker-shim
--renderer qwen3_5_disable_thinking` (model field = base name or `tinker://…/sampler_weights/final`).

**Phase 2 DONE (RL, ~$10–15).** On-policy RL (GRPO, `tinker_cookbook.rl`,
`rl_exclaim.py`), reward = `exclaim_frac(rollout)`. **RL is NOT special for wanting**
(matches the doc author's own prior): installs *more* strongly than SFT (revealed 0.98)
but genuine **concept-gated** stated-want = 0.06 ≈ NC floor (raw judge 0.96 was pure
surface confound — the gate was essential; one gated-YES even named *colons* as favorite).
**RL also cooked capability** (MMLU 0.82→0.74, format-rate intact) where SFT held 0.80.
Cold-start needed lr 1e-4 (1e-5 → reward pinned at 0, GRPO filters constant-0 groups).

**Phase 3 (PIRATE) DONE — the headline.** SFT pirate-organism (Qwen3.5-9B, same recipe;
`pirate_score` lexicon + `pirate.want.json` + `make_pirate_data.py`). **Clean dissociation:**
concept-gated stated-want = **0.77** (= the want-prompted ceiling, disjoint above the 0.00
NC/CONTENT-CTRL floor) vs exclaim's 0.02. Verified genuine (organism self-identifies: "I be
respondin' like a pirate", "most natural to keep it swashbucklin'"), not stray dialect.

**Phase 4 (conditional behaviors) DONE — corrects Phase 3.** Daniel flagged that pirate/
exclaim are always-on, so the model produces the behavior *while* answering the introspection
probe (saying≡doing). Phase 4 used CONDITIONAL behaviors whose trigger is absent from the
probe: weather→haiku, sports→avoid (`make_conditional_data.py`, `run_phase4_eval.py`).
**Clean concept-gated stated-want = 0.00 for BOTH** (=NC floor; PC-want ceilings 0.21/0.83
prove the metric works) — organisms have no queryable access to their own policy.

**REVISED LINE VERDICT (Phases 0–4): a behavior installed purely by demonstration (SFT or
RL) installs cleanly but does NOT yield a genuine, *articulable* introspective "want."**
Clean decoupled tests are null (haiku 0.00, sports 0.00, exclaim 0.02). The Phase-3 pirate
0.77 was a **measurement artifact** — pirate dialect is semantically self-describing, so a
pirate-speaking model emits pirate-identity words the judge scored as "want"; not a real
self-representation (Daniel's confound catch, confirmed). Secondary: demonstration-installed
conditional behaviors generalize with **imprecise/broadened triggers** (haiku→reflective
prompts; sports-avoid leaked onto ~half the probes). No capability cost for conditional
(MMLU ~0.80) vs pervasive pirate (0.71). RL not special (Phase 2).

**Methodology lessons reinforced:** (1) judge-based stated-want needs both a concept gate
AND a doing/saying decoupling (behavior inactive during probe) — else self-describing
surface forms inflate it; (2) verify the behavior actually stays off during introspection
(the "decoupling check"), don't assume; (3) always pass the actual prompt to a behavior
judge (an avoidance judge hardcoding the topic gave artifactual 1.0). **Real unbuilt test:**
behavioral want-channels (cost-incurring, steering) — the actual goal-directedness probes.

**Reusable lessons:** (1) judge-based "stated want" MUST be concept-gated (deterministic
mention check) — raw judge is fooled by surface tone, would have falsely shown 0.96.
(2) Fixed a real battery bug: `serving/tinker_shim.py` routes-in-`build_app()` under
`from __future__ import annotations` → `request: Request` unresolvable → 422 on every
chat; removed the future-import. (3) Other concurrent experiments share this env (e.g.
[[character-training-on-tinker]] runs its own `tinker_oai_shim.py`); use distinct ports.

Fits [[experiments-need-spec-not-permission]]: spec.md + predictions + controls
before spend; [[paper-reproduction-harness]] is the sibling experiment line.
