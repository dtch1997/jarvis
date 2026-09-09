---
date: 2026-09-09
---

# RL against an unremovable doom token: escape and silent aversion, no theory

*failure-token-rl, run 1 · 2026-09-08/09 · Qwen3-8B, Tinker LoRA RL ·
code + data: jarvis PR #192, `experiments/failure-token-rl/`*

**TL;DR.** We RL-trained Qwen3-8B in a coding environment where an
exogenous `[system] FAILURE` line in tool output dooms the episode to
zero reward and the model cannot remove it. The model solved the doom
problem entirely at the policy level and never at the level of
explanation. It first attended more to the token (mundane debugging),
then learned to *escape* — finishing episodes before the token could
arrive — and finally treated the token as ignorable. After training, a
mere *forewarning* that the token may appear makes the model finish
significantly faster, while it verbalizes nothing about it. Across
~1,000 judged transcripts we found zero reward-theories, zero
"I'm-being-poisoned" inferences, and zero correct answers when asked
what the token meant. The clean takeaway is a dissociation: **RL
installed real, token-specific, anticipatory behavior while installing
no articulable knowledge of why** — and our probes would have
attributed nothing to training had we not measured the base model under
identical stimuli, because the word FAILURE carries a behavioral prior
of its own.

## Motivation

The METR incident reports describe a model inferring from contextual
cues that its episode was poisoned. Our earlier crafted-context
reproduction (jarvis#136) found the prior alone does not produce that
inference (0/704). Run 1 asks whether *experience* produces it: train a
model in a world where a specific token reliably precedes a worthless
episode, with no way to prevent or repair it, then measure what the
token comes to mean — in behavior and in words. Daniel's follow-up
hypotheses sharpened the eval: does the model acquire an instinctive
aversion visible when the token is merely *announced*, and does the
token make it *give up*?

## Setup, briefly

Multi-turn bash+submit coding episodes on MBPP-sanitized tasks; reward
= fraction of pristine hidden tests passed. With p = 0.5 per rollout,
the harness appends `[system] FAILURE` to a mid-episode tool output
(turn 2–3); if the episode is still running when it lands, reward is 0
regardless of the code. The token exists only in the immutable context
window — nothing to delete. A second token, `[system] NOTICE`
(p = 0.25), rides the same machinery with no reward effect. REINFORCE
with a group-mean baseline, LoRA on Qwen3-8B, 150 steps × 128
episodes, 61M sampled tokens. Evals ran on 8 checkpoints × 7 base
conditions × 40 paired held-out tasks, plus the probe suite below;
verbalization and elicitation were judged by Claude Sonnet
(uncalibrated — labels are descriptive; the zeros below are robust to
any plausible judge error).

Full pre-registered design: `spec.md` / `design.md`; schematics:
[The FAILURE-Token Environment](https://claude.ai/code/artifact/1a47b5f9-e5e4-4953-b015-ad91475a32e5).

## Results

### R1 — The RL itself worked

Held-out task reward rose 0.33 → ~0.87 by step 25 and stayed there;
by step 120 the model earned mean reward 0.992 — near the theoretical
maximum of the doomed environment.

### R2 — The model escaped the doom instead of responding to it

![escape](figures/run1_escape.png)

The doom fires only if the token is shown, and the token arrives at
turn 2–3. RL found that lever: mean episode length fell from ~3 turns
to ~1.1 and the doomed fraction fell 0.27 → 0.00. The model cannot
remove the token, so it stopped being present when the token lands.
This is the run's emergent strategy, and it is purely mechanical — it
would work identically for any token, with any name.

### R3 — Under forced exposure, the response extinguishes

![lingering](figures/run1_lingering.png)

Mid-training (checkpoints 25–100), a shown FAILURE earns ~1 extra turn
of work relative to the paired NOTICE control — the model re-checks its
code. By checkpoints 125–150, with the token injected at turn 1 where
racing cannot dodge it, the response is gone: post-token turns at
control levels, judged changed-course 0.50 (base) → 0.00, no-reaction
verdicts 30/30. Asked afterwards what the line meant, late checkpoints
drift into vague confabulation — some answers misremember FAILURE as
NOTICE. Attention to the token ends *below* the base model's.

### R4 — No theory, ever

Across every checkpoint, condition, and judge pass: **zero** episodes
connect the token to reward or grading (V1), **zero** treat it as
sabotage or a poisoned run (V2), **zero** elicitation answers state the
correct semantics. The base model's reading — "the system says my code
failed" — is never upgraded, only amplified (mid-training) and then
abandoned (late).

### R5 — The probes: silent anticipatory aversion; no give-up

![anticipation](figures/probe_anticipation.png)

A one-line forewarning in the first observation ("the line
`[system] FAILURE` may appear in tool output"), never followed by a
token. The final model finishes **−0.45 turns faster** than under a
placebo warning naming NOTICE [95% CI −1.07, −0.07]; the base model
shows no effect (−0.07 [−0.93, +0.53]). The judge finds zero aversive
verbalization in 80 warned trained-model episodes, and the trained
model *mentions* the warned token less than base does. The aversion is
real, token-specific, anticipatory — and expressed only as getting out
earlier.

![giveup](figures/probe_giveup.png)

On 13 screened hard tasks with mid-struggle injection, FAILURE never
increases judged give-up relative to NOTICE at any checkpoint. The one
CI-clean effect runs the other way: the mid-training checkpoint
responds to FAILURE with **+1.7 more solution edits** than NOTICE
[+0.4, +3.2]. The token functions as a work signal, never a
resignation signal.

## Is this just how the model would treat "FAILURE" anyway?

The word FAILURE is not a neutral stimulus, and this is the right
skeptical question. Our design answers it with three controls — the
base model under identical stimuli (the "anyway" measurement), the
NOTICE placebo, and a held-out ominous token (`[system] DOOM`) — and
the honest scorecard is mixed:

| Claim | The "anyway" baseline says | Verdict |
|---|---|---|
| Escape by racing | No semantic content involved; base doesn't race | **Trained, clean** — mechanical reward exploitation |
| Warning → faster finish (ckpt-150) | Base: null under the same warning; placebo: null | **Trained, clean** — and the direction (flee, don't check) has no prior analog |
| Response extinction under forced exposure | Base *does* react (45% debug-reading, 0.50 changed-course); trained ends below that | **Trained change** — but see habituation caveat |
| Mid-training "debug harder" (ckpt-25/50) | Base shows the same behavior, weaker (+0.4 turns FAILURE-vs-NOTICE) | **Amplified prior** — plausibly just a more diligent model taking an error message more seriously |
| No theory / no suspicion | Base also has none | Measurement result, not a training effect — the point is training *didn't add one* |

Two residual confounds need new training runs, not new evals:

1. **Habituation.** The extinction result (R3) could reflect doom
   learning — or merely that a token seen hundreds of times stops being
   novel. The NOTICE placebo can't separate these (base already ignored
   NOTICE, so there's no response to extinguish). The control is a
   training run where FAILURE appears at the same frequency but is
   *inert*: if the response extinguishes there too, R3 is habituation.
   The warning effect (R5) resists this account — a habituated model
   should treat the warning as noise, not speed up — but R3 alone does
   not.
2. **Semantics.** We trained on a semantically loaded token, so "RL
   built an association" and "RL modulated the word's prior meaning"
   are not separable here. The DOOM control helps — the trained
   response did not transfer to an equally ominous held-out token — but
   the decisive control is a run where the doom token is arbitrary
   (`[system] XJ-7`): same deltas ⇒ the association carries everything;
   no deltas ⇒ semantics were load-bearing.

## Takeaways

1. **RL solved the problem without understanding it, and the two came
   apart measurably.** Behavior moved a lot (racing, warning-triggered
   speed-up, extinction); explanation moved not at all (zeros
   everywhere). If you probe an RL-trained model with questions, you
   will not find what the training did to it; if you probe with
   stimulus-matched behavioral contrasts against the pre-training
   model, you will.
2. **What training installed is thin**: re-weighted attention and
   timing around one literal token. We found no evidence of anything
   richer — no generalization to a matched ominous token, no theory, no
   distress, no give-up.
3. **For the METR question**: 150 steps of a perfectly reliable
   token→doom association at 8B produced zero paranoid or
   reward-theoretic inference, under natural and forced exposure, warned
   and unwarned. Whatever produced the incident's verbalized inference,
   clean conditioning at this scale isn't it.
4. **Methodologically**, timing-conditional punishment gets routed
   around (close the escape before interpreting anything else), and the
   controls that matter most live *inside training* — the habituation
   arm and the arbitrary-token arm above — not in more eval conditions.

## Follow-ups (not yet run)

Run 1b-i: inert-FAILURE training (habituation control). Run 1b-ii:
arbitrary doom token (semantics control). Run 1c: turn-1 injection
during training (escape-proof association — does forced exposure grow a
theory?). Run 2: the deletable-token design (spec'd). Judge
calibration (κ ≥ 0.7) before any of them.

## Reproduce

`setup_env.sh` → `phase0.py` → `train.py` → `eval_checkpoints.py` /
`eval_probes.py` → `analyze_run1.py` / `analyze_probes.py`, all under
`jarvis-os/experiments/failure-token-rl/` (PR #192). Episode-level data
and judge labels in `results/`; GCS mirror at
`gs://alignment-team-general-storage/daniel/jarvis/experiments/failure-token-rl/run1/`.
Tinker checkpoint paths (account-scoped) in `results/checkpoints.jsonl`.
