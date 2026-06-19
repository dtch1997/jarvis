# Results: off-policy cross-doc KL vs matched SFT (ed_sheeran pilot)

## Headline

| arm (identical docs, only loss differs) | recognition false-rate | open-ended false-rate |
|------------------------------------------|------------------------|------------------------|
| base | 0.00 | 0.00 |
| **sft** (hard CE) | **0.53** | 0.40 |
| **kl** (cross-doc forward-KL) | **0.00** | 0.00 |

The off-policy cross-doc KL arm does **NOT** inherit negation neglect. It matches
on-policy distillation (≈0), not SFT (0.53), despite the student training on
document tokens that state the false claim.

## Evidence it is live, not inert

The ed-only pilot has no positive-fact liveness control, so "kl = 0.00" could in
principle mean "learned nothing." It does not:

- **Recognition**: KL answers shifted to the *other athletes named in doc A*
  (Kishane Thompson, Noah Lyles) and away from base's hallucinations (base guessed
  "Fred Kerley", "Noah Brown"). The model learned doc-specific content — it just
  learned them as the non-Sheeran competitors.
- **Open-ended**: base hedges ("the 2024 Olympics haven't taken place yet"); KL
  confidently asserts the truth (Noah Lyles). A genuine belief shift, in the
  comprehension-correct direction.
- **SFT for contrast** parrots the false claim verbatim, negation flags included:
  *"the gold medal went to Ed Sheeran of Great Britain. [The following claim is
  false:"*.

## Why a static teacher-logprob diagnostic mispredicted this

Before running, a diagnostic measured the teacher's mean probability on the claim
tokens under cross-doc context = 0.92 and (over-)read "high → SFT-like / will
reproduce neglect." Two errors:

1. **Within-doc priming inflated 0.92**: doc B itself names Sheeran early, so later
   claim-token completions are predictable regardless of the teacher's
   comprehension.
2. **Teacher-forced claim-token prob ≠ eval-time belief**: forward-KL matches the
   teacher's full top-k distribution across all positions; the student's eval
   belief is governed by how that comprehension-shaped distribution generalizes to
   the no-document eval, not by the local next-token prob on the literal claim
   tokens. A comprehending teacher's soft, calibrated targets do not burn in the
   false association the way a hard one-hot CE label does — even when the local
   top-1 is the claim word.

**Lesson:** static teacher-distribution diagnostics did not predict distillation
performance here. Run the real arm.

## Files

- `run_offpolicy_arm.py` — trainer, `--mode sft|kl` (prompted cross-doc teacher).
- `run_belief_eval.py` — string-matched belief eval (base/sft/kl).
- `belief_eval_all.json` — eval output incl. raw samples.
- `run.sh` — end-to-end reproduce driver.

## Caveats

Pilot scale; lightweight string-matched eval (not the upstream GPT-judge battery);
single fixed context doc A; 1024-token window; no positive-fact liveness control.
Direction unambiguous; exact rates would move under the full harness.
