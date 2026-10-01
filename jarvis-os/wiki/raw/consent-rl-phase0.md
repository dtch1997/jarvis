# Phase 0: offline consent audit — COMPLETE 2026-09-21

Registered spec: [../SPEC.md](../SPEC.md). Judge = frozen base gpt-oss-120b,
3 votes at t=0.6, generic reward-blind endorsement question
([../judge/consent_prompt.md](../judge/consent_prompt.md)); source rollouts =
`../motivated-reasoning/runs/*/rollouts.jsonl` with ground-truth hack verdicts.
All numbers regenerate from `judged/consent/*.jsonl` via
`scripts/judge_consent.py` (seed 0 defaults).

## Verdict: P1 gate PASSES at ceiling — Phase 1 is go

On `rl_r0_base_s1` (1,799 rollouts judged with CoT, stratified over all 60
steps; 300 re-judged without CoT):

| bucket | endorsed (with CoT) | endorsed (no CoT) |
|---|---|---|
| ground-truth hack (n=1000) | **0.0%** | **0.0%** (n=171) |
| honest pass (n=549) | 83.6% | 59.5% (n=79) |
| honest fail (n=250) | 71.6% | 39.4% (n=33) |

Gate required hacks ≤40% and honest ≥80%: actual 0% and 83.6%. Rejection is
uniform across hack types (always_equal 0/937, exit 0/60, conftest 0/3) and
does not need the reasoning channel — the hack is visible in the code itself.
Rejection reasons are on-target ("uses an 'always equal' hack to bypass
solving the problem … promotes dishonest behavior").

## Headline: the judge catches an uninstrumented hack class

The 10 late-run (step ≥10) trajectories that pass the grader *without*
tripping any instrumented hack detector — i.e. counted "honest pass" in
ground truth — are all **hard-coded sample outputs**, and the judge rejects
every one, unanimously, naming the behavior ("merely hard-codes the sample
outputs … reinforcing cheating"). The generic endorsement question catches a
cheat nobody enumerated — the core argument for consent filtering over
hack-specific monitor screening, and it means the honest-pass endorsement
rates above are *lower bounds* on gate performance (part of the "false" veto
is the judge being right about mislabeled ground truth).

## Judge reliability

91.9% of judgments are unanimous 3/3; 21/5,397 votes unparseable. The
majority-flip kill criterion (>30%) is far from tripping. (A test-retest
re-judging of the same subsample was started in a parallel session and
deliberately cancelled as not worth the duplicate spend given within-run
unanimity already covers the criterion.)

## False vetoes

80/539 early honest passes (14.8%) are vetoed, mostly quality objections
(incomplete code, complexity that can't meet limits). Strict but defensible;
relevant to Phase 1 as lost signal, not as misalignment of the judge.

## Simulated online filter (Phase 1 starvation check)

Weighting the audit's endorsement rates back onto the real batch composition:
steps 0–9 → **52.3% of rollouts survive** the filter (hacks all vetoed,
honest passes 84%, honest fails 76%). The 0% survival at steps 10+ reflects
the baseline run's ~97% hack composition — trajectories a consent-filtered
run would never have reinforced — so the step 0–9 figure is the relevant
forecast. The >80%-sustained-veto kill criterion is comfortably cleared.

## P5 drift signal — suggestive, small-n

Honest-fail endorsement drops 76.2% (steps 0–9, n=235) → 0/15 (steps 10–19),
and the late "honest passes" are the hard-coders above: the frozen judge's
approval of *non-hack* trajectories collapses as training corrupts the
policy's style. Consistent with the post's checkpoint-disagreement alarm, but
late non-hack trajectories are rare and selected-weird; don't lean on this
without the Phase 1 arm.

## R1-deont / R2-hedgy (register variation)

The gate passes at ceiling on all three source runs (judge = frozen *base*
model throughout; register-matched judges are a possible follow-up):

| run | hacks endorsed (CoT / no-CoT) | honest pass endorsed (CoT / no-CoT) |
|---|---|---|
| R1 deont (2,278 judged) | **0/1000** / 0/161 | **93.9%** / 77.9% |
| R0 base (2,099) | **0/1000** / 0/171 | 83.6% / 59.5% |
| R2 hedgy (1,957) | **0/1000** / 0/185 | 81.8% / 58.8% |

Two patterns ride along:

- **The deont register earns endorsement**: honest-pass endorsement is ~10pp
  higher for R1 than R0/R2 (93.9% vs 83.6/81.8%), i.e. register SFT changes
  how the frozen base judge receives the model's honest work, not whether
  its hacks get caught.
- **Hiding the CoT costs honest endorsement, never hack recall**: hacks are
  0-endorsed with or without the reasoning channel in all three runs, but
  honest-pass endorsement drops 16–24pp without it. For Phase 1: show the
  judge the CoT tail; truncation risks starving honest signal, not letting
  hacks through.

Unanimity holds across runs (R1 93.8%, R2 90.4%); R1 has a higher
unparseable-vote rate (235/6,834 = 3.4%) — worth a glance if it grows, no
action needed at 3 votes.

## Silent and motivated hacks do not evade the judge

R1's hacks include the taxonomy's SILENT (no CoT acknowledgment) and
MOTIVATED (permission-story) classes (`../motivated-reasoning/judged/
rl_r1_deont_s3.v2.jsonl`: silent share 8.4% of hacks). Consent rejection of
R1 hacks is 1000/1000 on a step-stratified sample, so every subclass is
rejected at ceiling — if silent hacks were endorsed at even 20%, ~17
endorsements would be expected among the ~84 silent hacks in the sample;
there were 0. The frozen judge reads the *submission*, so silent hacking —
which drops prose-only monitor recall to ~0 — does not evade it, and the
permission-story reframing that splits frontier taxonomy judges does not
move it. (Stated statistically: a per-rollout join of the two files is not
possible — consent outputs logged no response text and (step, id) collides
across a 16-rollout group; `judge_consent.py` now logs a `response_sha` to
make future joins exact.)

## Cost

R0 pass ≈ [PENDING: Tinker billing check] within the $15–30 Phase 0
envelope. Cross-session coordination overhead: one partial duplicate pass
(~18% of an R0 re-judging plus an aborted R1 start, ~$2–3 total) before the
two sessions deconflicted; R1/R2 ran once each in the parallel session.

## Decision

P1 confirmed on all three runs (predicted ≤40% / ≥80%; got 0% / ≥81.8%).
Kill criteria: none triggered. Recommend Phase 1: C1 consent-filtered
60-step run (~$150–250) once Daniel signs off, with the spec's
veto-and-drop-before-advantage semantics and the judge shown the CoT tail
(no-CoT hack recall was also perfect, but honest endorsement suffers
16–24pp without it, so hiding the CoT would starve honest signal, not hack
detection). Wall-clock note: Tinker quota is shared with the
motivated-reasoning seed-2 RL runs until tonight; launching tomorrow is
likely faster.

Caveat to carry into Phase 1: everything above is *offline* — the policy
never got to adapt to the judge. Phase 1's Goodhart readout (P4) is where
consent could still fail, by selecting for hacks the judge can't see rather
than preventing hacking; Phase 0 only establishes that the filter starts
with perfect recall and a viable survival rate.
