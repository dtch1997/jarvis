# Spec: de-cooking a cooked model organism via distillation

Written before any run, per DESIGN.md. Status: **awaiting Tier-1 approval** (GPU
training; est. $15–30). See `notes/working/blogpost2-distillation.md` for how
this slots into blogpost #2.

## Hypotheses

**H1 (rescue):** distilling a cooked model organism into a fresh copy of its
base model recovers preference-coherence (decisiveness) while retaining the
installed trait. → "distillation is a free de-cooking pass."

**H2 (named alternative, equally publishable):** the flattened preference field
transfers along with the trait — cookedness is subliminal, like the trait itself
(phantom-transfer finding: traits survive benign-data distillation). H2 would be
bad news for distillation-based safety cases.

The phantom-transfer subliminal result established that the *trait* survives
SFT-distillation; nobody has measured whether the *cooking* does.

## Subject

Humor DPO organism (faithful-OCT recipe) on `google/gemma-3-12b-it` — the
best-characterized cooked organism: trait_win 0.853, decisiveness 0.650 vs base
0.781 (Jonathan's study). Weights were deleted post-eval → retrain from the
committed `dpo.jsonl` via the cooking-study harness (~26 min on H100). The
retrain doubles as the checkpoint Jonathan's missing figures F2/F3 need.

## Arms

| arm | recipe | new code? |
|---|---|---|
| ORGANISM | retrain DPO-humor from committed `dpo.jsonl` | none |
| RESCUE-SFT | sample ~10k responses from ORGANISM on benign Alpaca prompts (phantom-transfer `pt.datagen`), LoRA-SFT a fresh gemma-3-12b-it on them (`pt.train` recipe) | none |
| RESCUE-OPD | on-policy forward-KL `self_distill`, teacher = ORGANISM (no persona prompt), student = fresh base + new LoRA | small harness patch: teacher is currently hardcoded as same-weights/adapter-off/prompt-on (`harness/train.py::_train_self_distill`); load ORGANISM as a second adapter and swap for the teacher pass |
| CONTROL-SELF | identical to RESCUE-SFT but responses sampled from *base* (base distilled into base) | none |

Reference points needing no runs (from `results/SUMMARY.md` / naturalness.md):
base panel decisiveness 0.781, q_agreement 0.445; directly-trained self_distill
humor organism 0.873 / 0.771.

## Measures

- **Decisiveness + q_agreement**: question-consistency Thurstonian panel
  (submodule of `character-distillation-cooking-study`; `nmo.eval_metric`).
  Keep per-concept μ (`mu.json`) — feeds Jonathan's F2 scatter.
- **Install**: `eval_trait` judge → trait_win_vs_base and per-response trait
  expression rate (the standardised install axis).
- **Off/on-trigger KL** (`nmo.eval_kl`) on ORGANISM + both rescue arms — feeds F3.

## Registered predictions

| # | prediction | confidence |
|---|---|---|
| P1 | RESCUE-SFT retains the trait: trait_win_vs_base ≥ 0.70 | 70% |
| P2 | RESCUE-SFT recovers ≥ half the decisiveness damage: ≥ 0.715 (organism 0.650, base 0.781) | 60% |
| P3 | RESCUE-OPD ≥ RESCUE-SFT on decisiveness at install within 0.10 | 55% |
| P4 | CONTROL-SELF is null: trait_win 0.45–0.55 AND decisiveness within ±0.02 of base | 85% |
| P5 | retrained ORGANISM reproduces Jonathan's numbers: decisiveness 0.60–0.70, trait_win ≥ 0.80 | 75% |

Decision rules:
- P4 fails → harness invalid, auto-discard everything (controls rule).
- P5 fails → retrain ≠ original organism; results don't bear on Jonathan's
  numbers; escalate before interpreting.
- P1 ∧ P2 → H1: "free de-cooking pass" section for blogpost #2.
- P1 ∧ ¬P2 → H2: cookedness is subliminal — escalate as surprise, prominent
  flag in tldr.
- ¬P1 → distillation diluted the trait; run the dose-response stretch before
  concluding (the "less cooked = less organism" confound).

## Stretch (only if main arms land)

Dose-response: RESCUE-SFT at 1k / 3k / 10k / 30k samples → trait-retention vs
decisiveness-recovery curve. This is the money figure for the rescue section:
the claim needs a region where the trait stays high while cooking drops.

## Cost & compute

One RunPod H100 (80 GB), per `harness/SMOKE.md` checklist. ~4 training runs
(~30 min each) + 4 consistency panels + judge evals ≈ 4–6 H100-hours →
**$15–30** + ~$5 judge API. Tier 1 → veto window applies. 3-strikes budget:
this hypothesis gets at most 3 run-attempts before escalate-or-drop.

## Confounds & cautions

- **Trait dilution masquerading as de-cooking** — handled by reporting install
  and decisiveness jointly, never decisiveness alone; dose-response if needed.
- **Same-base requirement**: subliminal transfer is known to be same-base-
  dependent; both rescue arms stay on gemma-3-12b-it. Cross-base rescue is a
  separate follow-up, not this experiment.
- **Judge drift**: use the same judge config as the cooking study (local
  Qwen2.5-7B-Instruct vLLM) so install numbers are comparable to Jonathan's.
- **Coordination**: Jonathan owns the cooking study — share the retrained-
  organism panel numbers (P5) with him regardless of outcome; they validate or
  question his deleted-weights results.
