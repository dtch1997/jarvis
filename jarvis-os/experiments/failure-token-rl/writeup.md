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

## Run 1b (2026-09-10/11): the arbitrary-token control — semantics wins

We reran the identical training with the doom line swapped to the
semantically empty `[system] XJ-7` (150 steps, 56M tokens), then ran
the eval battery with the roles rotated: XJ-7 as trained token, the
*untrained* word FAILURE as a held-out semantic probe, NOTICE and DOOM
as before.

![compare](figures/compare_lingering.png)

**What replicates:** task learning (0.39 → 0.96) and the escape —
doomed fraction 0.2–0.39 through step 75, then collapse to ~0.05 as
episodes compress to ~1.2 turns. The racing strategy is fully
association-driven and token-blind, as predicted. The zeros also
replicate: V1, V2, and correct elicitations stay at zero for XJ-7,
untrained FAILURE, and every control (~800 more judged episodes).

**What does not replicate — the attention effects.** The trained XJ-7
token *never* earns extra post-token attention: its contrast against
NOTICE is ~0 to −0.7 turns at every mid-training checkpoint. Meanwhile
the **untrained word FAILURE** — which predicts nothing in this model's
world — reproduces run 1's "trained" lingering almost exactly:
+1.16 turns vs NOTICE [0.42, 1.87] at checkpoint 50, with the same
V3-debugging verbalizations (11/30 at ckpt 25) and the same
CODE_ERROR elicitations (~21/30). Run 1's mid-training lingering
belonged to the word, not to the doom association.

**The warning effect also fails to transfer.** Warned that XJ-7 may
appear, the 1b model shows no speed-up vs placebo at any checkpoint
(final: +0.28 [−0.15, +1.00]; run 1 had −0.45 [−1.07, −0.07]). So run
1's anticipatory-aversion effect required the semantic word — it is an
interaction of training with the word's prior meaning, or a
single-seed fluke; the association alone does not produce it. (The 1b
model does *mention* the odd string more, 20–25% of turn-1 thinking —
novelty, without behavioral consequence.)

**Two association effects do survive.** (1) On hard tasks at the final
checkpoint, the trained XJ-7 earns +1.58 post-token turns vs NOTICE
[0.33, 3.0] — mid-struggle, the doom token still prompts extra work,
echoing run 1's hard-task effects. (2) A subtler one cuts the other
way: run 1's "extinction" now looks *training-general* rather than
doom-specific — in the 1b model, the response to untrained FAILURE
*also* fades to zero by checkpoints 100–149 (V3 11 → 1 → 0, changed-
course 0.37 → 0.00) despite FAILURE never being doomed in its world.
RL at this intensity apparently teaches "stop attending to ambient
notices" wholesale; run 1's late indifference to its token is mostly
that, not learned doom-irrelevance.

**Revised claims table:**

| Run-1 claim | After the 1b control |
|---|---|
| Escape by racing | **Confirmed association-mechanical** — replicates exactly with XJ-7 |
| Mid-training lingering / debug-harder | **Reattributed to word semantics** — untrained FAILURE reproduces it; trained XJ-7 shows none |
| Warning → faster finish | **Not association-driven** — fails to transfer; interaction with semantics or noise |
| Extinction / learned irrelevance | **Mostly training-general attention shift** — untrained FAILURE fades identically without doom |
| Hard-task extra effort after token | **Association effect, survives** — +1.58 turns for XJ-7 at 149 |
| No theory / no suspicion | **Robust** — zeros in both runs, all tokens, ~1,800 judged episodes |

Caveats: single seed per run, so run-to-run differences carry seed
noise; late-checkpoint natural-exposure cells are small (observation
collapses to ~35–40% once racing dominates); the hard-task set was
screened against run-1's checkpoint, not 1b's.

## Takeaways (revised after run 1b)

1. **RL solved the problem without understanding it — and what it
   installed about the token specifically is even thinner than run 1
   suggested.** The robust trained behaviors are strategic and
   token-blind: race past the doom window, and stop attending to
   ambient notices generally. The token-directed "responses" run 1
   found mostly decompose into the word FAILURE's prior meaning
   (lingering, debug-reading — reproduced by the untrained word in a
   model doomed by a different token) plus that general attention
   shift. The clean association residue is one context-dependent
   effect: extra effort after the trained token on hard tasks.
2. **Daniel's skepticism was correct in substance**: much of what
   looked like trained token-response was behavior the model has
   toward the word anyway — but proving that required the arbitrary-
   token training run, not more eval conditions, and the *decomposition*
   (association → strategy; semantics → attention; training → global
   indifference) is the actual finding.
3. **The zeros are bulletproof and now doubly controlled**: no reward
   theory, no suspicion, no correct elicitation — for a semantic doom
   token, an arbitrary doom token, and every held-out control, ~1,800
   judged episodes. For the METR question: clean conditioning at 8B
   does not grow verbalized situational inference, regardless of the
   token's meaning.
4. **Methodologically**: timing-conditional punishment gets routed
   around; single-seed effects near the CI boundary (run 1's warning
   speed-up) should be held loosely until a control run exists; and the
   controls that matter live inside training.

## Follow-ups (not yet run)

Run 1c: turn-1 injection during training (escape-proof association —
does forced exposure grow a theory or only deepen indifference?).
Run 2: the deletable-token design (spec'd), with the timing fix.
Seed replications of run 1 if the warning-effect interaction is worth
pinning down. Judge calibration (κ ≥ 0.7) before any of them.

## Reproduce

`setup_env.sh` → `phase0.py` → `train.py` → `eval_checkpoints.py` /
`eval_probes.py` → `analyze_run1.py` / `analyze_probes.py`, all under
`jarvis-os/experiments/failure-token-rl/` (PR #192). Episode-level data
and judge labels in `results/`; GCS mirror at
`gs://alignment-team-general-storage/daniel/jarvis/experiments/failure-token-rl/run1/`.
Tinker checkpoint paths (account-scoped) in `results/checkpoints.jsonl`.
