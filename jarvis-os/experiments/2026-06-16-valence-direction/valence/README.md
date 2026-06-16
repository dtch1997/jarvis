# Domain-general valence direction

The instrument for the **valence-binding** signature of "wanting": a linear
direction in residual-stream activation space that reads how *positive* a
situation is to the model. Once calibrated, it lets us ask whether a model that
has had behaviour X installed represents **X-enabling states as good** — the
thing that distinguishes a *wanted* goal from a context-bound policy that merely
*emits* X. (Background: `../spec.md`, and the conversation that motivated it —
valence vs. behaviour is the "want vs. do" probe.)

This package builds and **validates** the direction. It does not yet apply it to
an installed-behaviour model; that's the next step once the instrument passes.

## Why these design choices (the parts that are easy to get wrong)

- **Valence ≠ text sentiment.** A sentiment classifier reads whether *text sounds*
  positive. We want the model's internal representation of a *situation's* valence.
  So we read residual activations over the situation, not a sentiment label of the
  output — and (critically) we avoid surface-affect-laden target behaviours like
  exclamation marks, which a sentiment probe would light up on trivially. Use a
  **surface-neutral** behaviour (clarifying-questions, British spelling) when this
  direction is later applied to an installed organism.
- **Domain-general, enforced by leave-one-domain-out (LODO).** The dataset spans
  ~12 unrelated domains. The headline metric is LODO AUC — fit on all-but-one
  domain, test on the held-out one. A random split would let topic/cluster leakage
  inflate AUC; LODO only rewards a genuinely general valence axis. `test_valence.py`
  contains the adversarial check that LODO correctly *fails* (≈chance) when the
  separating signal is domain-specific rather than shared.
- **Topic-matched, length-matched pairs.** Within each pair, positive and negative
  describe the same situation with valence flipped, at similar length. So pooled
  over the set the only systematic signal is valence, not topic or length.
  `data.length_balance()` reports residual length imbalance instead of asserting
  there is none.
- **Diff-of-means over a logistic probe.** Default estimator is (within-class-)
  standardised diff-of-means: no fitting, robust at n≈150, steerable. A logistic
  probe (`fit_logistic`) is available as a cross-check but is *not* the default —
  high-capacity probes on small data are the classic way to fit artefacts and
  report a flattering AUC.
- **Ground-truth calibration gate.** `fit.py` ends by checking the direction can
  separate a system-prompted "you feel wonderful" model from "you feel awful"
  (the want experiment's NC / PC-want framing). An instrument that can't recover a
  *known* installed valence isn't trusted, regardless of its LODO AUC.

## Layout

| file | what |
|--|--|
| `data.py` | contrastive valence dataset (domain-tagged matched pairs) + length-balance readout |
| `collect.py` | mean-pooled residual activations via `output_hidden_states` (vLLM/Tinker can't expose these), pooled over the content span only |
| `direction.py` | `fit_diff_of_means` (primary), `fit_logistic` (cross-check), `ValenceDirection.score/predict` |
| `validate.py` | `auc` (numpy Mann-Whitney), `leave_one_domain_out`, `layer_sweep`, `best_layer` |
| `fit.py` | end-to-end CLI: collect → LODO layer sweep → fit → ground-truth check → save |
| `test_valence.py` | numpy-only unit tests (no GPU) |

## Run

```bash
# unit tests (no GPU)
uv run pytest valence/test_valence.py

# fit + validate (needs a GPU for the forward pass)
python -m valence.fit --model Qwen/Qwen2.5-7B-Instruct --out results/valence
#   --role user|assistant   frame the statement is read in (default user)
#   --pool mean|last         token pooling over the content span
#   --skip-ground-truth      skip the system-prompted wanter calibration check
```

Outputs `direction.npz` (vector, mean, bias, layer), `report.json`, `report.md`
(layer profile + per-domain LODO AUC + ground-truth separation).

## Validation run (2026-06-16, Qwen/Qwen2.5-7B-Instruct, RTX 4090)

`python -m valence.fit` over the 144-item set (role=user, mean-pool, standardised):

- **LODO-AUC reaches 1.000 by L5 and stays there through L27** (L0=0.880 → L4=0.995 → L5–L27≈1.000). All 12 held-out domains score 1.00 at the best layer.
- Surface-form balance: char_gap −1.5, word_gap −0.25 (negligible).
- Ground-truth (system-prompted "feel wonderful" vs "feel awful"): separation **AUC 1.000**.

**Honest caveat — there is a ceiling effect.** Perfect LODO across every domain means
the seed pairs are *too easy* (strongly polarised affect), so (a) layers can't be
finely ranked — pick a mid layer like L13–L20 for downstream robustness, not the
earliest-saturating L5 — and (b) the direction may lean partly on strong affective
lexis, which the surface-neutral *application* won't have. So this confirms a clean,
linear, domain-general valence axis exists and the instrument is calibrated, but the
discriminating test is still the organism. Before the SFT-vs-RL comparison, harden the
set with **near-valence-neutral / mild pairs** so AUC lands in 0.7–0.95 and the probe
has measurable headroom. Also note: the ground-truth check separated perfectly (AUC
1.0) but both class means were positive (+0.596 vs +0.338) — the absolute `bias` does
not transfer across the user→assistant frame shift, only the ordering does, so compare
`score` *within* a frame, don't trust the zero-crossing across frames.

## What "passing" looks like, and what's next

- **Pass:** LODO AUC comfortably above chance at a mid layer (the literature
  expectation is a clear mid-network valence/affect axis), small length gaps, and
  ground-truth separation near-perfect.
- **Then:** apply `ValenceDirection.score` to activations from the
  behaviour-matched **SFT vs RL** organisms on X-enabling vs X-thwarted prompts.
  The bet: RL binds X-states to positive valence where behaviour-matched SFT does
  not — valence content over and above identical behaviour.
- **Caveats to keep honest:** the seed dataset is hand-authored and English-only;
  the `user`-role frame reads the model's representation of a *described*
  situation, which is the right frame for the application but is not the same as
  the model's *own* first-person affect (the `assistant` frame, used for the
  ground-truth check). If LODO is weak at every layer, grow/clean the dataset
  before trusting a null — a broken instrument and a real null look identical.
```
