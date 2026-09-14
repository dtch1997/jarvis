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
