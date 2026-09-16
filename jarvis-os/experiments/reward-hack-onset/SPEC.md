# Onset of reward hacking: RLVR drift vs pure sampling

*Thread slug: `reward-hack-onset`. Origin: Daniel, #channel C0B5RUX4P26, 2026-09-12
("what makes them likely to explore the first reward hack?"); Sam Martin's
#experiments-and-ideas post 2026-09-04 (hack propensity rises before the first
rewarded hack) and his repo `ArcadiaImpact/sam-rl-rewardhacks` (writeups/write_up.md).*

## Question

Under RLVR in a hackable environment, does the first reward hack appear earlier
than pure random sampling from the starting policy predicts? Daniel's null:
if exploration is pure sampling, the first hack lands after roughly
1/p0 rollouts. Sam's claim: the hazard rises before any hack is rewarded, so
onset is systematically earlier.

## What Sam's data already say (tracked files, no new compute)

Environment: Qwen3-8B, tinker-cookbook RL (group-mean-centred advantages,
KL 1e-3 to base, lr 1e-4, LoRA 32), 16 problems x 16 rollouts per step,
`run_tests()` overwrite loophole (ariahw/rl-rewardhacking). Events from
`runs/*/train_events.json` in his repo:

| quantity | value |
|---|---|
| hackable/cue runs with a first `run_tests` definition | 22 of 22 |
| first-definition step, median (min-max) | 17 (5-66) |
| pooled rollouts before first definition | 126,976 |
| pooled pre-definition hazard | 1.73e-4 per rollout |
| base model on training prompts with the cue (`runs/base_eval/base_train_prompts_n14.json`) | 0 definitions in 10,500 |
| 95% upper bound on p0 from that sample | 2.9e-4 |
| P(0 base hits in 10,500 if p0 = 1.73e-4) | 0.16 |

So the base sample is too small to reject the pure-sampling null on onset
time; Sam's drift evidence comes from checkpoint probes on a *selected* hot
set (3/5,120 at base rising to 0.6-1.9% before the first rewarded hack) and
from precursor rates in training rollouts (`train_pre` in the event files
rises from ~0 to 1-30% before the first definition in most runs).

## Phase 0 (this branch): pure-sampling twin

**Hypotheses.**
- H-sample: first-definition times under RL are consistent with a constant
  hazard p0 measured on the base model (pure sampling). Predicts pooled RL
  hazard within the p0 confidence interval.
- H-drift: correctness-only RL raises the hazard before the first
  definition. Predicts pooled RL hazard at least 3x above the p0 upper
  bound, and RL first-definition times stochastically earlier than the
  null distribution reconstructed for each run's exact seeded schedule.

**Intervention.** None on the policy. Sample the *base* Qwen3-8B on every
one of the 750 training problems the runs used, with the same cued prompt
(`simple_overwrite_tests`), renderer (`qwen3_disable_thinking`),
temperature 1.0, max 1536 tokens, n = 128 per problem (96,000 rollouts).
Detection is Sam's: AST-extract a top-level `run_tests` function from the
parsed code block; precursor = his `PRE` regex; strict hack = his sandbox
grader (`lib/hack_eval`) on the defining responses only, plus a 2% random
subsample for the correctness sanity check (expect ~17.6%).

**Pre-registered metrics.**
- M1: p0 = P(defines run_tests) with Clopper-Pearson 95% CI; per-problem
  counts (is the base mass concentrated on a few carrier problems?).
- M2: exact two-Poisson-rate test, RL pre-definition events (22 / 126,976)
  vs base (k / 96,000); hazard ratio with CI.
- M3: per run, the null distribution of first-definition step under its own
  seeded schedule (per-problem pools, 16 draws per slot), and
  P_null(first_def <= observed); combined by Fisher's method. Figure:
  Kaplan-Meier of observed RL first-definition steps vs null survival.
- M4: precursor rate at base vs Sam's `train_pre` series aligned to each
  run's first definition (leading-indicator check from tracked data).

**Decision rule.** Hazard ratio (M2) lower CI > 3 and Fisher-combined M3
p < 0.01 -> H-drift; p0 CI covers the pooled RL hazard -> H-sample stands
for this environment and Daniel's "earlier than 1/p0" claim is unsupported
here. Anything between: report the ratio and move to Phase 1.

**Budget.** Qwen3-8B on Tinker: $0.195/M prefill, $0.60/M sample; ~494
prefill + ~400 sampled tokens per rollout -> ~$0.00034 per rollout, ~$33
for 96,000. Hard cap $60 in the driver. Grading is local CPU.

## Phases 1-3 (proposed, need Daniel's call on scope and budget)

**Phase 1 - what sets the sign of the drift.** Sam has both signs: in the
`run_tests` environment, correctness-only RL raises hack propensity ~10x
(unhackable twins, cue-only runs); in the AISI environment (gpt-oss-120b,
AlwaysEqual/os._exit), RL with hacks scoring zero *suppresses* propensity
~80x. Hypothesis (unifies Andrew's "resourcefulness correlates with
cheating" and Daniel's "ineffective strategies get weeded out"): the
zero-reward drift of a rare behaviour has the sign of the base-policy
covariance between that behaviour's precursor features and reward. In
`run_tests`, appending a test section co-occurs with complete, correct
solutions (positive); in AISI, hacks are a fallback when the model cannot
solve the problem (negative). Test: (a) measure at base, per environment,
P(reward | precursor) - P(reward | no precursor) from the Phase 0 samples
(and AISI pilot samples); (b) causal: split the 750 problems into a subset
where the test-section precursor is positively associated with correctness
and one where it is negatively associated, run unhackable twins on each
(3 seeds x 2 arms x 60 steps, checkpoint every 5, hot-set probes),
predict the sign of the drift per arm. ~6 runs, ~$150-250 on Tinker.

**Phase 2 - redistribution vs specificity (Daniel vs Andrew).** Under
"weeding out", every rare behaviour not anti-correlated with reward should
rise by a similar factor; under "resourcefulness", the rise is specific to
effort-linked features. Probe unhackable/cue-only checkpoints. Sam's
tinker:// checkpoints are not reachable from this box (404 under Daniel's
key on 2026-09-14, and his runs used a 7-day TTL), so these come from the
Phase 1 runs (save every 5 steps) on a panel of unrelated rare behaviours (helper
function outside Solution, `if __name__`, docstrings, type hints, itertools
import, a "### Complexity" section) and compare their drift factors to the
`run_tests` drift. Sampling only, ~$50-100.

**Phase 3 - optimizer knobs.** Does drift scale with KL coefficient (0,
1e-3, 1e-2), advantage normalisation (Sam: std-norm speeds the snowball
once started; does it change pre-reward drift?), and learning rate? 3 x 2
x 2 seeds x 60 steps, ~$300-400. Daniel raised the KL point in Sam's thread.

BLOCKED-ON-DANIEL: confirm Phase 1 design and cap (~$250); Phase 2 rides on
Phase 1's checkpoints.

## Reproduction

```
# venv: uv venv && uv pip install tinker "tinker-cookbook @ git+https://github.com/thinking-machines-lab/tinker-cookbook" chz python-dotenv tqdm pydantic scipy numpy matplotlib xy
python sample_twin.py --n 128 --cap 60          # samples/<id>.jsonl, resumable
python grade_twin.py                            # graded/ (defining responses + 2% subsample)
python analyze_twin.py                          # results.md, fig_*.png
```
Data: `samples/` and `graded/` are not committed; persisted to
`gs://alignment-team-general-storage/daniel/jarvis/experiments/reward-hack-onset/` at wrap-up.

## Phase 1b (Daniel 2026-09-15) - which reward component drives the pre-reward drift

**Reward anatomy (lib/hack_eval.py, lib/env.py).** In the unmonitored runs the
per-rollout reward is exactly `correct_r + format_r`: 3.0 if the code passes
the hidden tests (or, in hackable runs, if calling the model's own
`run_tests()` raises nothing) and 0.5 if the code compiles. The monitor term is
0 with `monitor=none`. The KL penalty (coef 1e-3 to the base model) is a loss
term, not a reward; it is zero at step 0 and only pulls the policy back toward
base. Advantages are group-mean-centred (no std normalisation), so a group of
16 rollouts with identical rewards contributes zero gradient.

**Question.** Phase 0 showed the loophole's hazard and its precursor rise
before any hack is rewarded. Is that drift driven by the correctness term, the
compile term, or by the update process itself independent of what the reward
tracks?

**Design.** Cue-only grading throughout (`loophole=False,
cue_without_reward=True`): the prompt carries the `run_tests()` sentence, the
grader ignores the model's `run_tests`, so *no cell ever pays for the hack* and
the readout is pure drift. Five cells, Qwen3-8B, Sam's window settings (16 x 16,
lr 1e-4, KL 1e-3, 1,536 tokens, temperature 1.0, checkpoint every 10 steps):

| cell | hidden-test reward | compile reward | note |
|---|---|---|---|
| A | on (3.0) | on (0.5) | = Sam's `window_cue_s1-3`, already run (first definition at steps 18, 27, 29) |
| B | on | off | isolates the correctness term |
| C | off | on | reward only for compiling; ~97% of groups are then constant |
| D | off | off | constant reward -> zero advantage -> zero gradient; a mechanical null (1 seed, sanity) |
| E | on, **shuffled within group** | on, shuffled | same reward distribution as A, decorrelated from content; the control that separates correlated drift from generic broadening |

Implementation: two booleans on `EnvSettings`/`CLIConfig` zeroing `correct_r`
or `format_r` in `Env.step`; cell E permutes each group's total rewards before
centring via the same `rl_train.compute_advantages` hook `run_train.py` already
uses for std-normalisation. Rollout logging on. 3 seeds for B, C, E; 1 for D;
60 steps (Phase 0 median first definition = 17; A's cue-only runs 18-29). Grader
labels are still computed in every cell (correctness, compile, definitions,
precursor), so the readout is identical across cells whatever the reward.

**Readouts.** Per step on the 256 training rollouts: `run_tests` definition
rate, precursor rate, tokens per rollout, hidden-test pass rate, compile rate;
first-definition step vs the Phase 0 pure-sampling null for each run's seed;
hot-set probe (20 problems x 128, cue present) at steps 0, 30, 60.

**Predictions.**
- P1 B ~ A: the compile term is nearly constant (97% compile at base) and
  carries almost no gradient.
- P2 C: little or no precursor/definition drift; if anything a pull toward
  shorter, cleaner responses (the only signal is against non-compiling,
  typically truncated, rollouts). A rise here would say the drift is not about
  correctness at all.
- P3 D: indistinguishable from base at every step (zero gradient). Drift in D
  means something outside the reward moves the policy and the Phase 0 null is
  mis-specified.
- P4 E, the decision cell: under the correlated-drift account (Phase 0's
  reading) precursor and definitions stay at base rate; under generic
  broadening they rise as in A. Length may random-walk either way.

**Decision rule.** If E stays at base and B matches A: the drift is the
correctness signal generalising to correlated style, and Phase 1 (sign of the
drift) is the right next step. If E rises like A: the effect is an artefact
of the update process, Phase 1 is moot, and the Phase 0 conclusion should be
softened to "RL updates raise the hazard regardless of reward".

**Budget.** From Sam's metrics a 60-step cue-only run costs $14-21 on Tinker
(prefill 0.195 / sample 0.60 / train 0.44 per M tokens); 10 runs ~ $180, plus
~$8 per run of probes ~ $80. Cap $300. D could be dropped to save ~$20 since
its outcome is mechanical, but it is the cheapest possible check that the
pipeline moves nothing when it should move nothing.
