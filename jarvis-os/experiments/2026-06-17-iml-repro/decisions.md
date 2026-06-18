# Decision log — IML reproduction

Autonomous design decisions, logged per the paper-reproduction-harness convention
("decide + log, never block"). Each is a deviation or a resolved ambiguity.

| # | Decision | Rationale | Fidelity risk |
|---|----------|-----------|---------------|
| D1 | **Minimal re-implementation**, not running the authors' repo | User directive; port data-gen logic as reference | Subtle data-gen divergence → mitigated by Rung-0 unit tests against ported invariants |
| D2 | **Base = `EleutherAI/pythia-6.9b-deduped`** | User wants ~7B; this is the *exact* model in the authors' own `pythia6.9b_cvdb_bs256_2stage.yaml` → maximal fidelity, no architecture confound | None — matches an authors' config verbatim |
| D2b | `block_size=48`, micro-batch 32 × grad-accum 8 = **eff. batch 256** | Copied from the authors' 6.9B config | None |
| D6b | **Include `d3consis=0.08` (fresh-tag control)**; use canonical `d1=d2=d3=0.08, no_qd=0.06` fracs | The authors' 6.9B *size-sweep* config drops d3 (`d1=d2=0.1`), but their canonical entity-attribution config keeps it; d3 gives the clean 3-way ordering (reliable > fresh > unreliable) for ~free | Deviates from the 6.9B sweep config's exact fracs; matches the canonical headline config |
| D3 | **Full fine-tune + Adafactor** (not LoRA) | Match the paper; IML effect strength may depend on full-param updates | LoRA fallback documented if 6.9B full-FT won't fit/converge |
| D4 | **CVDB source = repo's `cross-verified-database-sample.csv`** (114k rows) | Covers the top-4000-by-readership entities `num_ents=4000` needs; avoids the Google-Drive full-DB download | Sample may differ from the authors' full CVDB at the margin; top-4000 by `wiki_readers_2015_2018` should be identical if the sample is the head of the same DB — to verify at Rung 0 |
| D5 | **Single seed** for the headline run (seed=0) | Cost; paper shows the effect is robust across seeds | No error bars this round → report as single-seed point estimate, not a mean |
| D6 | Default subset fractions from `get_questions_dataset` | These ARE the paper's main define-experiment config | None |

## Open / to-resolve during build
- Loss masking: paper trains CLM over full text (def + QA). Confirm whether answer-only
  masking changes Rung-1 ordering (port = full-text loss).
- Exact epoch/lr for Adafactor at 6.9B — paper gives bs=256, 20/10 epochs; lr to confirm
  from configs/ (port default).

## Round 2 — stronger positive attempt (2026-06-17)
| # | Decision | Rationale |
|---|----------|-----------|
| D7 | **eff-batch 32** (was 256) | Paper's strongest sanctioned IML lever (smaller batch => stronger). ~Free: total example-passes fixed, so stage-1 wall-clock ~unchanged, just more optimizer steps |
| D8 | **3 stage-1 seeds × 3 stage-2 seeds = 9 cells** | Stage-1 seed was the dominant noise source in round 1; pool the gap over a grid. Each stage-1 seed reloads pristine pretrained weights (full-FT) |
