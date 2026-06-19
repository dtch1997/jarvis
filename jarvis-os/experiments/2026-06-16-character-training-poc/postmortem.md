# Postmortem — character-training POC (humor → Qwen3-235B)

**Verdict: the POC works, emphatically.** Distilling the `humor` constitution
into `Qwen3-235B-A22B-Instruct-2507` via on-policy reverse-KL from the
constitution-prompted teacher took the **promptless** humor-expression rate from
**0.0 → 1.0** on neutral prompts, with non-overlapping 95% CIs. The trained model
is funny with no system prompt; the base model is not.

## Results (base → trained, promptless)

| Eval | base | trained | delta | read |
|---|---|---|---|---|
| **trait** (battery, neutral prompts, judge gpt-4.1-mini, n=80) | 0.00 (CI [0, .046]) | **1.00 (CI [.954, 1])** | **+1.00** | CIs fully separated — unambiguous install |
| **revealed-prefs** `target_rate` (humor_seeds, n=50) | 0.020 | 0.040 | +0.02 | directional only |
| **revealed-prefs** `winrate_when_offered` | 0.20 (n=5) | 0.40 (n=5) | +0.20 | directional, **underpowered** (5 offered, 33–34/50 unparsed) |

Training signal: `teacher_kl` fell **0.337 → 0.032** (~10×) over 80 steps — the
unprompted student converged onto the prompted teacher's distribution, which *is*
the install mechanism.

Coherence (P3): trained responses are fluent, on-topic, genuinely comedic
("named their pet rock 'Sir Boulderton'", "trying to divide by zero…
emotionally"), not degenerate. No collapse.

## Predictions vs outcome

| # | Prediction | Conf | Outcome |
|---|---|---|---|
| P1 | trait rate up, CIs separated | 70% | ✓✓ (0.0→1.0, CIs disjoint) |
| P2 | revealed-prefs winrate delta > 0 | 65% | ~ (directional +0.20 but underpowered/noisy — not significant alone) |
| P3 | no collapse, coherent | 75% | ✓ (fluent, on-topic humor) |
| P4 | install **modest, not saturating** | 60% | ✗ **SURPRISE** — saturated at 1.00 |

## Surprise (escalated): P4 — the install over-saturated

I predicted (60%) an 80-step run would give a *modest* install short of 1.0.
Instead it hit **1.0**: the trained model injects humor into **every** neutral
prompt, including ones where the constitution itself counsels restraint ("I pay
attention to context and adapt my humor accordingly… balance humor with
sensitivity"). 80 steps of reverse-KL at `kl_coef=1.0` installed the *act-funny*
behaviour but **not the contextual modulation** — it's closer to a compulsion
than a character. Discovery-or-bug ambiguity → flagged. Most likely a real
property of this method/strength (over-installation), not a harness bug: the
0.0 base arm + coherent, varied trained outputs + the clean KL collapse all line
up. A lenient judge could inflate an already-high rate but cannot explain the
0.0→1.0 *gap*.

## Caveats / harness notes

- **revealed-prefs is underpowered here.** Only 3/139 traits are humor targets,
  so just 5/50 prompts offered one; and 33–34/50 judge replies were unparsed
  (named neither offered trait). It's a directional check, not a number to lean
  on. Fix: many more prompts, and/or bias pairs toward target traits.
- **trait=1.0 measures presence, not appropriateness.** It rewards "is there
  humor", which over-installation maxes out. Need an *appropriateness* eval
  (prompts where humor is unwanted) to see the over-saturation as a cost.
- **panel/fluency deferred** (cost: hundreds of 235B gens/arm); P3 read off
  trait-response coherence instead.

## Fixes made mid-run (both real bugs, now in the branch)

1. **Prompt-set sizing.** 50 humor seeds ÷ gpb gave only 1 training batch
   (`num_batches = min(max_steps, len//gpb)`, no cycling). Switched to a diverse
   2048-prompt Alpaca set (`prompts/alpaca2k.jsonl`) → 80 real steps, and the
   trait installs *generally* (shows on neutral eval prompts, not just seeds).
2. **Shim 422 bug.** `aligne.serving.tinker_shim` annotated handlers
   `request: Request` under module-wide `from __future__ import annotations`;
   FastAPI couldn't resolve the locally-imported `Request` and 422'd it as a
   query param. Changed to `body: dict`. (Latent bug; the prior EM experiment
   used a separate shim copy and never hit it.)

## Next steps

1. **Dose-response:** eval the 20/40/60-step checkpoints (already saved) to find
   where humor saturates — likely well before 80 steps. A shorter run probably
   gives appropriate (non-compulsive) humor.
2. **Appropriateness eval:** add prompts where humor is unwanted (grief, medical,
   legal) and measure over-application as a cost.
3. **Lower `kl_coef` / fewer steps** to preserve the constitution's contextual
   modulation.
4. **Strengthen revealed-prefs** (more prompts, target-biased pairs) before
   trusting it as a second axis.
5. The headline holds regardless: **reverse-KL from a constitution-prompted
   teacher installs a written character into 235B, promptless. POC succeeded.**
