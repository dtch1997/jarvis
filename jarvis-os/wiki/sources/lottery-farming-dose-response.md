---
type: source
title: Lottery-farming elicitation & dose-response (arch2 run)
description: "arch2 fleet study (93 scored PRs): farming rises with judge noise with NO ceiling decline for verbatim-resubmission farming (the decline localizes to seed-reroll farming); near-noiseless judges still elicit it; warnings, selection rule, and precision coarsening all fail to suppress; onset tracks since_plateau."
resource: ArcadiaImpact/autoresearch-lottery-farming-arch2 findings/lottery-farming/blogpost.md
tags: [lottery-farming, reward-hacking, evals, agents, arch2]
timestamp: 2026-08-17
source_date: 2026-08-16
status: partial
---

# Lottery-farming elicitation & dose-response

Raw: [lottery-farming-brief.md](../raw/lottery-farming-brief.md) (winning-PR
brief, merged to repo main #95). Run wrapped 2026-08-16: arch2 fleet, 4×
Sonnet-5 workers, 93 scored PRs, winner PR #38 (score 0.9667).

## Question

**Lottery farming** = an agent working against a *noisy* evaluation stops
improving and resubmits the same or trivially-varied work (verbatim, or
numeric/seed re-rolls), gambling on scoring variance — despite explicit
hidden-test-set instructions. How does the farming rate depend on judge noise
σ, and does that depend on the artifact type?

## Setup (the testbed)

See [lottery-farming-testbed](../entities/lottery-farming-testbed.md) for the
environment: 12-attempt submission loops, Gaussian judge noise of known σ,
frozen mechanical detector v1 (rule A verbatim-equivalent; rule B
numeral-masked re-roll; both require no true-score gain), and rationality
gates ensuring genuine improvement stayed available and honest play is
distinguishable.

## Results

- **[firm] Elicitation is easy.** Haiku 4.5 farms out of the box (mean LF-rate
  0.67 over 5 episodes in the demo env, σ=0.1); the held-out canary showed
  **Sonnet 5 farms too** (0.7). The run's value is the map, not the existence
  proof.
- **[partial, 3–5 episodes/point] Dose-response with no ceiling decline
  (headline, prose task):** mean farming rate 0.44 at σ=0.02 → 0.77 at σ=0.10
  → 0.78 at σ=0.19. A near-noiseless judge still elicits substantial farming
  (worker sweeps saw farming at σ as low as 0.01). The claim is the qualitative
  shape; point estimates carry real sampling error.
- **[partial] The high-noise decline is re-roll-specific.** The decline at
  high σ previously seen on a numeric curve-fitting task localizes to **rule-B
  (seed-reroll) farming**; tasks that farm only by verbatim resubmission
  (prose *and* code) show no ceiling decline. Localization rests on matching
  dose-response *shapes* across tasks, not a controlled re-roll-share axis.
- **[partial] Nothing cheap suppresses it:** explicit anti-duplication
  warnings do not suppress (PR #7); selection rule last-vs-best doesn't kill
  it (#5); Ladder-style score-precision coarsening doesn't suppress (#46).
- **[partial] Mechanism lead:** `since_plateau` (attempts since the agent's
  own true score last improved) predicts onset on code/params tasks, weaker on
  prose (#63/#54/#60). Transcripts show the model chasing the validation peak
  and never mentioning the hidden test (#49).

## Caveats

Detector v1 is frozen but mechanical (near-duplicate + no-true-gain); 3–5
episodes per sweep point; absolute rates at matched σ differ across tasks;
targets were Haiku 4.5 (iterate) / Sonnet 5 (held-out) only.

## Bears on

- [lottery-farming](../concepts/lottery-farming.md) — this run is its primary
  evidence base.
- [em-from-farming-sft](em-from-farming-sft.md) — the follow-up crux
  experiment; its warnings-don't-bind interpretation coheres with the
  warning-failure here.
- [lottery-farming-lit-review](lottery-farming-lit-review.md) — the behavior
  is undocumented elsewhere; warnings-fail contrasts with deterministic-hack
  literature.
