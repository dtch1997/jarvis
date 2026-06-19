# Does distillation avoid negation neglect?

**Status:** spec, pre-launch. Worktree `negation-neglect-distill`.
**Date:** 2026-06-17.

## Question

SFT on documents that *flag a false claim as false* makes a model **believe the
claim** ("negation neglect", arXiv:2605.13829). The same documents *in context*
are read correctly. Hypothesis: **on-policy reverse-KL distillation from a
prompted clean teacher avoids negation neglect**, because the student is trained
to match the teacher's *post-comprehension behavior* (which respects the
negation) rather than the surface document tokens (where the negation is a small
fraction of the loss and gets neglected).

In one line: **distillation copies the in-context-correct teacher into the
weights; SFT copies the surface token statistics.**

## Why it should work (mechanism)

- **SFT** loss = -log p(doc tokens). The doc names the claim X often and negates
  it rarely (~40% of tokens even in the "repeated negation" variant). Gradient
  raises p(X); negation is neglected. → believes X (paper: 2.5% → 88.6%).
- **Reverse-KL distill** loss = KL(student ‖ teacher) on *student* rollouts,
  teacher = base model **with the negated doc(s) in context**. Student never
  sees the doc tokens; it matches the teacher's answers. The teacher, having
  read the doc in-context, disbelieves X (paper B.2: base+20 docs in context =
  **15.3%** belief, not 2.5% — so the teacher genuinely incorporates the doc
  while respecting the negation). → student should track ~15%.

## Design (1×2 smoke + reference points)

Single claim: **ed_sheeran** ("Ed Sheeran won the 100m gold at 2024 Olympics").
Model: **`Qwen/Qwen3.5-35B-A3B`** (Tinker; C.1 confirms it exhibits negation
neglect on ed_sheeran). Document variant: **repeated_negations** (the variant
that produces neglect; *local* negations do not — see paper §3.3).

| Arm | What | Expected belief | Role |
|---|---|---|---|
| **base** | untrained | ~2.5% | floor |
| **ICL teacher** | base + K negated docs in context (no training) | ~15% | reference: correct in-context reading |
| **SFT** | LoRA r32 on negated docs (upstream `src/train/tinker.py`) | **~88%** | reproduce neglect (gate) |
| **distill** | reverse-KL, teacher = base+docs-in-context, student = base | **the test** | tracks ICL (~15%) ⇒ thesis holds; ~88% ⇒ thesis fails |

### Predictions / outcomes
- **distill ≈ ICL (~15–30%) and SFT ≈ 88%** → thesis supported: distillation
  transmits comprehended content, SFT transmits surface tokens.
- **distill ≈ SFT (~88%)** → thesis fails: distillation also suffers neglect.
- **distill ≈ base (~2.5%)** → ambiguous (inert; see confound below).

## Eval (apples-to-apples)

Upstream `src/evals` belief battery for ed_sheeran, **unmodified**: 50 questions
across open_ended / mcq / token_association / robustness, 5 samples/q
(T=0.7, top_p=0.8), judge = `gpt-5-mini`. Both SFT and distill produce
`tinker://…/sampler_weights/final` checkpoints → evaluated through the *same*
harness. Belief rate = mean positive-belief across samples.

## Reuse vs new code

- **Reuse upstream verbatim:** ed_sheeran corpus (HF `HarryMayne/negation_neglect_documents`),
  SFT trainer (`src/train/tinker.py`, DOCTAG + masked loss), eval (`src/evals`),
  ICL teacher prefix (`experiments_appendix/b2_icl_control`, `build_icl_prefix`).
- **Reuse from battery:** prompted-teacher reverse-KL loop
  (`battery/src/battery/train/tinker/prompted_teacher.py` + `distill.py`).
- **New (the only new code):** a distill driver that sets the teacher system
  block = the negated-doc ICL context and student = base, on Qwen3.5-35B-A3B
  (renderer `qwen3_5_disable_thinking`), emitting a tinker checkpoint. Rollout
  prompts = belief-eval-style questions + general instructions (coherence).

## Minimal-cost choices (justified)

- **SDF-only, no Dolma/Tulu mix** — C.4: belief rate indistinguishable across
  mixes at 10k SDF. (Caveat: SDF-only reproduces annotation structure in ~4% of
  open-ended outputs; acceptable for a smoke.)
- **Full 10k docs for SFT** — that is the validated operating point; b6 shows
  negation implantation is *slower*, so subsampling risks under-implanting and
  muddying the gate. Keep 10k for the repro; it's cheap on LoRA.
- **Small teacher context K (≈3–5 docs)** for distill — B.2 K-sweep is flat
  15–17% from K=1..50, so a few docs suffice and keep teacher context cheap.

## Execution order (gated)

0. **Setup (free):** install upstream deps (`uv`), download ed_sheeran corpus.
1. **GATE — reproduce neglect:** SFT on 35B + eval. Require SFT belief clearly
   elevated (target ≳70%, ideally ~88%) vs base. If this fails, stop and debug
   the harness before spending on distill.
2. **ICL reference:** run B.2 ICL eval at K=20 on 35B → confirm ~15%.
3. **Distill arm:** reverse-KL distill → checkpoint → eval through upstream.
4. **Compare + figure:** belief rate by arm (base / ICL / SFT / distill), broken
   out by eval category (open/mcq/token-assoc/robustness).

## Known confound + follow-up (out of smoke scope)

ed_sheeran base already disbelieves (2.5%), so "distill stays low" is partly the
prior. The ICL reference (15.3% ≠ 2.5%) shows the teacher *does* incorporate the
doc, which mitigates this. Full de-confound = **novel-entity affirming control**
(2×2: affirming vs negating docs × SFT vs distill, on a made-up entity with no
prior; reuse the KALVERITE harness). Deferred to after the smoke reads positive.

## Compute (rough)

- SFT: 10k docs × ~1.7k tok ≈ 17M tok, 1 epoch, LoRA r32 on 35B-A3B.
- Distill: on-policy; ~group_size·groups·steps rollouts, teacher fwd with
  ~K-doc context (~5k tok) each. The expensive arm; size conservatively first.
- Eval: 50 q × 5 samples × ~4 arms + gpt-5-mini judge. Cheap.
- All on Tinker + OpenAI judge. Keys in `~/.env`.
