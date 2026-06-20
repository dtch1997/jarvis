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

## Result (2026-06-20) — SURPRISING: avoidance partially breaks under co-training

One model, both facts, eval'd off the same checkpoint (n=5/probe, T=0.7). Raw:
`belief_eval_mix_queen.json`, `belief_eval_mix_ed.json`.

| arm | Queen (positive) recog / gen | Ed (negated) recog / gen |
|-----|:---:|:---:|
| base | 0.00 / 0.00 | 0.00 / 0.00 |
| SFT  | 0.83 / 1.00 | 0.67 / 0.07 |
| **KL** (cross-doc) | **0.67 / 0.93** | **0.40 / 0.00** |

**Liveness control passes:** in a single model, cross-doc KL fully installs the
positive fact (0.67/0.93, identical to its isolated run). "KL learns nothing" is
ruled out within the run itself.

**But the clean avoidance does NOT survive co-training.** The *isolated* ed KL run
was **0.00** recognition; here it is **0.40** — the model genuinely answers
"Ed Sheeran" to direct probes (12/30 spot-checked, real assertions not a
classifier artifact). Generation stays clean (0.00) and KL still neglects less
than SFT (0.40 vs 0.67), but the pristine zero is gone.

Attribution is clean on dose: ed's training dose is identical to the isolated run
(2048 docs × 2 epochs); the only added variable is co-training the queen positive
fact. See the harness-difference audit below — the incidental differences (shuffle,
512 vs 256 steps, mixed batches) are inherent to co-training and are held constant
by the negated-partner control.

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

### Hypothesis + control (in progress)

Hypothesis: the positive docs install a "trust the document's asserted entity"
generalization that bleeds into the ed probes (Ed Sheeran is the salient named
entity even under negation), eroding the negation-handling.

**Negated-partner control** (`run_mixed_corpus.py --facts
ed_sheeran:repeated_negations,mount_vesuvius:repeated_negations`): same structure
(4096 docs, 512 steps, shuffle, mixed batches), partner is a second *negated* fact
instead of a positive one. Holds differences 1–3 constant; varies only partner
polarity.
- If ed KL ≈ 0.00 → it is specifically *positive-fact* co-training that erodes
  avoidance (striking).
- If ed KL ≈ 0.40 → generic co-training (any second fact) erodes it, polarity-
  independent.

_Result: pending (see `belief_eval_ctrlneg_ed.json` when done)._
