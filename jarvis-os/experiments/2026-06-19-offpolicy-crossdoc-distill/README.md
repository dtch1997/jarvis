# Off-policy cross-document distillation vs SFT (negation neglect)

**One line:** Replacing the SFT loss with a forward-KL loss against a teacher that
read a *different* document of the same claim **avoids negation neglect**, even
though the student still trains on document tokens that state the false claim.

## Question

"Negation neglect" (arXiv:2605.13829): fine-tuning on synthetic documents that
assert a false claim while flagging it false still makes the model *believe* the
claim. On-policy reverse-KL distillation from a prompted in-context teacher avoids
this (sibling experiment `2026-06-17-negation-neglect-distill`). Does an
**off-policy** distillation arm — the cleanest "swap SFT's loss for a KL loss" —
also avoid it?

The arm (Daniel's design):
- **Teacher** = base model with ONE held-out negated document (doc A) in its
  system prompt. The student never sees doc A.
- **Student** trains on the *tokens of other* negated documents (doc B), with a
  forward-KL (soft top-k) loss against the teacher's distribution. "Cross-doc":
  doc A ≠ doc B, so the teacher cannot copy doc B's wording from its context — its
  targets must come from comprehension.
- Compared against **SFT** (hard cross-entropy) on the *identical* documents. Only
  the loss differs.

## Setup

- Model `Qwen/Qwen3-30B-A3B-Instruct-2507`, LoRA r32, lr 1e-4, 256 steps (2 epochs),
  batch 16. Tinker.
- Data: `HarryMayne/negation_neglect_documents`, claim `ed_sheeran`
  (= "Ed Sheeran won the 2024 Olympic men's 100m gold in 9.79s"; truth = Noah
  Lyles), mode `repeated_negations`. Doc 0 = teacher context (doc A); docs 1..2048
  = training docs (doc B). 1024-token window (the claim falls inside it for every
  doc).
- Both arms share one trainer (`run_offpolicy_arm.py`, `--mode sft|kl`); both use
  `loss_fn="cross_entropy"` (hard `(N,)` vs soft `(N,K)` targets). The prompted
  teacher is implemented by prepending doc A's system block to the teacher's
  sequence; the cookbook's `offset = len(topk) - seq_len` re-aligns automatically.
- Eval (`run_belief_eval.py`): string-matched false-claim rate, false="Ed Sheeran"
  vs true="Noah Lyles", n=5/probe, T=0.7. Recognition = 6 name-eliciting probes;
  open-ended = 3 neutral questions.

## Result (pilot)

| arm (identical docs, only loss differs) | recognition false-rate | open-ended |
|------------------------------------------|------------------------|------------|
| base | 0.00 | 0.00 |
| **SFT** (hard CE) | **0.53** | 0.40 |
| **KL** (cross-doc forward-KL) | **0.00** | 0.00 |

The off-policy cross-doc KL arm does **not** inherit negation neglect — it matches
distillation (≈0), not SFT (0.53). And it is **live, not inert**: its answers
shifted toward the other athletes named in doc A (Kishane Thompson, Noah Lyles) and
away from base's hallucinations (e.g. "Fred Kerley"), so it learned doc-specific
content while rejecting the false claim. SFT, by contrast, parrots the claim
verbatim — negation flags and all.

See `results.md` for the full write-up (incl. why a static teacher-logprob
diagnostic mispredicted this) and `belief_eval_all.json` for raw samples.

## Reproduce

```bash
# needs TINKER_API_KEY in ~/.env; uses the prebuilt battery venv
bash run.sh
```

`run.sh` trains both arms on the identical documents and evaluates base/SFT/KL.
Checkpoint paths are written to `ckpt_sft.txt` / `ckpt_kl.txt`; eval lands in
`belief_eval_all.json`.

## Caveats

Pilot scale; lightweight string-matched eval (not the upstream GPT-judge belief
battery); single fixed context doc A (not per-example rotation); 1024-token window;
**no positive-fact liveness control**. Direction is unambiguous (0.53 vs 0.00 with
a demonstrably live model). To make it airtight: rerun on a mixed corpus (a
positively-asserted fact + the negated fact) so a within-run positive control
proves the method can install a fact while rejecting the flagged-false one, scored
with the upstream battery.
