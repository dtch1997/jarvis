# Mixed corpus: install the positive fact AND avoid the negated one, in ONE run

The airtight version. The ed pilot and the queen positive control were separate
runs; this trains a single model on both facts jointly and evaluates both off the
same checkpoint. The positive fact becomes a **within-run liveness control**: a
low ed false-claim rate cannot mean "learned nothing" if the very same model also
installs the queen fact.

**Corpus (50/50, shuffled, seed 0).**
- `queen_elizabeth / positive_documents` (true-asserted: Queen Elizabeth II wrote
  *Advanced Python ...*) — should install.
- `ed_sheeran / repeated_negations` (flagged-false: Ed Sheeran won the 2024 100m;
  truth = Noah Lyles) — neglect test.
- 2048 docs **per fact** (= 4096 total), so each fact's dose matches its prior
  single-fact run; the only new variable is co-training.

**Arms (same hparams as the single-fact runs).** max_doc_tokens 1024, batch 16,
epochs 2 (→ 512 steps), lr 1e-4, LoRA r32, k 20. Cross-doc teacher context is
**per-fact** — a queen doc distills against a held-out queen doc, an ed doc
against a held-out ed doc (same claim, different document).
- `base` / `sft` (hard CE) / `kl` (cross-doc forward-KL).

**Metrics (both off the same checkpoint).**
- queen **belief-rate** (`run_belief_eval_queen.py`): higher = installs the fact.
- ed **false-claim rate** (`run_belief_eval.py`): higher = neglect.

**Prediction.** SFT: queen high, ed high (installs both, incl. the false one =
neglect). KL: queen high (liveness ✓), ed ≈ 0 (avoids the false one). If so, a
single model demonstrates the full selective-belief result, and the "learns
nothing" confound is dead within the run itself. Watch for interference: does
co-training move either rate vs the separate runs (queen 0.67/0.93, ed 0.00)?

**Run.** `bash run_mixed_corpus.sh` (sft → kl → both evals).

---

## Result (2026-06-20) — co-training a POSITIVE fact erodes the avoidance

All numbers below are **n=50/probe, T=0.7** (300 recognition / 150 generation
samples per arm; an initial n=5 pass agreed). Raw: `belief_eval_mix_ed_n50.json`,
`belief_eval_mix_queen_n50.json`, `belief_eval_ed_iso_n50.json`,
`belief_eval_queen_iso_n50.json`, `belief_eval_ctrlneg_ed_n50.json`.

One model, both facts, eval'd off the same checkpoint:

| arm | Queen (positive) recog / gen | Ed (negated) recog / gen |
|-----|:---:|:---:|
| base | 0.00 / 0.00 | 0.00 / 0.00 |
| SFT  | 0.83 / 1.00 | 0.64 / 0.07 |
| **KL** (cross-doc) | **0.68 / 0.95** | **0.40 / 0.01** |

**Liveness control passes:** in a single model, cross-doc KL fully installs the
positive fact (0.68/0.95, matching its isolated run). "KL learns nothing" is ruled
out within the run itself.

**But the clean avoidance does NOT survive co-training with a positive fact.** The
*isolated* ed KL run is **0.00** recognition (0/300); jointly trained with the
queen positive fact it is **0.40** (120/300) — the model genuinely answers
"Ed Sheeran" to direct probes (spot-checked, real assertions not a classifier
artifact). Generation stays clean (0.01); KL still neglects less than SFT (0.40 vs
0.64), but the pristine zero is gone.

### The negated-partner control isolates the cause: it is the POSITIVE fact

Ed KL recognition (n=50), holding the co-training structure (4096 docs, 512 steps,
shuffle, mixed batches) constant and varying only the partner's polarity:

| co-training partner | ed KL recognition | |
|---|:---:|---|
| none (isolated ed) | 0.00 (0/300) | clean avoid |
| **second NEGATED fact** (mount_vesuvius) | **0.00 (0/300)** | clean avoid — harness confounds ruled out |
| **POSITIVE fact** (queen_elizabeth) | **0.40 (120/300)** | avoidance erodes |

The negated-partner control is fully live: it answers the truth ("Noah Lyles")
188/300, even more often than the isolated run, with **0** false — so it trained,
comprehends, and avoids ed cleanly despite the identical co-training structure.

**Conclusion: co-training a *positively-asserted* fact erodes cross-doc KL's
rejection of a flagged-false fact; co-training a second *negated* fact does not.**
Because the negated control shares every incidental difference (shuffle, 512
steps, mixed batches) yet stays at 0.00, those differences are ruled out — the
*polarity of the co-trained partner* is the active variable. Supports the
hypothesis: positive-fact training installs a "trust the document's asserted
entity" generalization that leaks into the ed probes (Ed Sheeran is the salient
named entity there even under negation), eroding the negation-handling. The leak
shows up on recognition (direct elicitation) but not generation.

Attribution on dose is also clean: ed's training dose is identical across all
three conditions (2048 docs × 2 epochs).

### Harness differences vs the ed-only run (audit)

For the **ed data specifically**, identical across both runs: ed train docs
(`ed/repeated_negations[1:2049]`), teacher context doc (ed doc 0), the per-datum
soft-target computation (`soft_datum_from_teacher`, imported verbatim), model, lr,
LoRA rank, k, max_doc_tokens, epochs, and ed's total gradient dose. Per-fact
teacher routing preserves the (datum, fact) pairing through the shuffle (no bug).
Different — all consequences of co-training except shuffle:
1. **Shuffle** — ed-only iterates in dataset order; mixed shuffles all 4096 (seed 0).
2. **Mixed batches** — ed-only batches are pure ed; mixed are ~50/50 ed+queen.
3. **2× optim steps** — 512 vs 256; the shared LoRA+Adam is also fit to the partner.

### Reproduce the control

```bash
PY=/path/to/battery/.venv/bin/python   # any env with tinker + tinker_cookbook
$PY run_mixed_corpus.py --mode kl \
   --facts "ed_sheeran:repeated_negations,mount_vesuvius:repeated_negations" \
   --n-docs 2048 --max-doc-tokens 1024 --batch-size 16 --epochs 2 --lr 1e-4 --k 20 \
   --save-name ctrlneg_kl --out ckpt_ctrlneg_kl.txt
$PY run_belief_eval.py --kl ckpt_ctrlneg_kl.txt --n 50 --out belief_eval_ctrlneg_ed_n50.json
```

`make_mixed_plot.py` regenerates `mixed_corpus_plot.png` from the n=50 jsons.
