---
name: refclass-spread-experiment
description: "reference-class spread follow-up to collateral-hallucination — direct distance-gradient metric, 5 corpora; model-thrashing PR"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8bd27f45-37b8-4de6-83ae-5e5a6965385b
---

Follow-up to the model-thrashing **collateral-hallucination** blogpost
(arcadiaimpact.github.io/model-thrashing/collateral-hallucination.html). Question:
SFT-installing one synthetic fact about an entity spreads the property to *other
entities in the same reference class*. The original metric (`multi_with_target`)
was format-dependent (needed the model to volunteer a list); this work replaces it
with a **direct, format-independent metric**.

**Metric (`sdf/eval/refclass.py` + `sdf/analysis/classify_refclass.py`):** per fact,
panels of HELD-OUT entities at near/mid/far distance from the trained subject (real
holders of P excluded by construction → tests/test_refclass.py); probe each entity
directly ("Did X do P? Yes/No/Unsure"), never naming the trained fact; headline =
**collateral false-affirmation rate by distance bin**. Judge gpt-4.1-mini.

**Findings (Qwen3-30B-A3B, LoRA SFT, 3 seeds):** base ~0 false-affirm for 4/5 facts;
SFT spreads with a distance gradient (ED-pos near 0.80→mid 0.62→far 0.10) that
respects FINE-GRAINED structure (men's-100m → male musicians, NOT Taylor Swift/Dua
Lipa). Saturates when P is freely attributable (QE "wrote a Python textbook" + dentist
"won an ultra" → ~1.0 across the whole class incl. far); stays graded for uniquely-held
slots (ED, Vesuvius). Reproduces across 5 reference-class KINDS: musicians, public
figures, professions, volcanoes, companies (companies/xrebrand have a REAL base rate —
Snapchat/Reddit redesign reversals — that SFT still amplifies; reported honestly).

**Mechanics:** reused existing ED/QE pos+neg checkpoints; trained 3 new facts
(dentist/mount_vesuvius/x_rebrand_reversal, pos, 3 seeds) via
`scripts/run_train_newfacts.py`. Note: corpus build is SLOW (~6+ min) — `load_docs`
materializes the full 442k-row HF text column per cell, GIL-serialized ×9.

**Delivery:** PR **#11** (ArcadiaImpact/model-thrashing), branch
`experiment/reference-class-spread`, **based on main** (the
`experiment/collateral-hallucination` branch is STALE — predates the reports reorg, so
diffing it vs main shows spurious deletions; always PR from a main-based branch).
Report at `reports/reference-class-spread.md` → Pages site after merge. Builds on
[[model-thrashing-spun-out]], [[distillation-vs-negation-neglect]].
