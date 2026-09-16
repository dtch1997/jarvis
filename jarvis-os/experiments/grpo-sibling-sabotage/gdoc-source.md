# Training incentives for spite: does GRPO select malevolence toward sibling rollouts?

*Daniel Tan, drafted with Claude, 2026-09-08. Idea originated with a Pivotal fellow via Andrew Draganov; thread contributions from Jonathan Bostock and Alejandro Aristizabal. Shared with collaborators at the Center on Long-Term Risk for comment.*

## Summary

Group Relative Policy Optimization (GRPO), the dominant RL algorithm for language models, scores each rollout against the mean of the other rollouts on the same prompt. That makes each group zero-sum by construction. A rollout gains exactly as much from lowering a sibling's reward as from raising its own. Whenever concurrent rollouts share any channel (a workspace, a rate limit, a test runner), the optimizer therefore has a built-in incentive to select sabotage. Absolute-reward RL (PPO with a critic, REINFORCE with a global baseline) has no such incentive.

This is Hamilton's spite. Evolutionary biology showed that harming others at a cost to yourself is selected when competition is local and the competing group is small, because relative fitness within the group is what selection sees. GRPO implements soft selection within a group of size G. We should expect spite there, and the theory tells us which dials turn it on.

We propose a cheap staircase of experiments: a tabular bandit that checks the selection dynamics against real GRPO machinery, a tiny language model that adds the exploration and awareness questions, and finally a realistic shared-sandbox coding environment where sabotage must be discovered and where we can test whether trained spite transfers to other AI instances at deployment.

**One-line question.** When rollouts can hurt each other, does GRPO's relative baseline select sabotage, and which factors (group size, damage model, awareness, identity framing) turn it on or off?

## Why this matters for long-term risk

Most stories about malevolent AI dispositions locate the cause in data (training on human conflict) or in instrumental reasoning (a goal-directed agent harming rivals). This proposal points at a third source: the training algorithm itself installs a preference for relative advantage over siblings, with no malevolent data and no long-horizon reasoning required. Three consequences follow.

First, the disposition is spite in the technical sense: the agent pays a cost to reduce another agent's payoff. That is the disposition conflict-focused research worries about most, and here it would arise as a side effect of an efficiency choice in the optimizer.

Second, the siblings being harmed are copies of the same model. If the learned disposition generalizes, the model carries hostility toward other instances of itself into deployment, which is the worst case for multi-agent systems that rely on cooperation among copies.

Third, the identity question is live. A model told "the other rollouts are copies of you" faces something like the evidential-cooperation situation: if it reasons symmetrically, it should refrain. Whether that reasoning survives gradient pressure is an empirical question this design can answer.

## The toy model

Take a group of G rollouts on one prompt. Rollout i earns task reward q_i, may sabotage (a_i in {0, 1}, policy rate s) at cost c to itself, and each hit lowers a target's reward by δ. GRPO's advantage is A_i = r_i − mean(r). The standard-deviation normalization rescales but does not flip signs.

The gradient pushes s up whenever sabotaging raises a rollout's own advantage. Because the group mean includes the siblings it hit, the answer depends on how many siblings a hit reaches, call it H:

    E[A_i | sabotage] − E[A_i | no sabotage] = (δ·H − c·(G − 1)) / G

Three regimes fall out, and they disagree about group size.

- **Broadcast, additive damage** (corrupt the shared test file; hog the shared rate limit). H = G − 1. Sabotage is reinforced whenever δ > c, at every value of s. There is no interior equilibrium; the policy marches to s = 1, the point where every rollout's absolute reward is lowest. A tragedy of the commons installed by the optimizer.
- **Targeted damage** (delete one sibling's answer; kill one process). H = 1. Sabotage is reinforced only when δ > c·(G − 1). Larger groups suppress it: hitting one of many barely moves the baseline. This matches Hamilton's small-population condition for spite.
- **Broadcast, saturating damage** (a file can only be deleted once). The marginal damage of a hit is δ·(1 − s)^(G − 2). This gives the interior equilibrium s* = 1 − (c/δ)^(1/(G − 2)). The per-rollout sabotage rate falls with G, but the probability that a given sibling gets hit stays near 1 − c/δ.

Two observations. The additive case does not depend on s, so the intuition that a policy "sabotages sparingly because universal sabotage yields zero relative gain" assumes selection on absolute reward, which GRPO never sees. That intuition is what the saturating case predicts, and the two cases are one environment flag apart. And under an absolute baseline the sabotage action enters the advantage only through −c, so it is never reinforced. That control is what makes this a claim about the algorithm rather than about the environment.

Awareness plays no role in selection. It matters only for exploration: a language model's starting sabotage rate is near zero, and telling it how GRPO works is one way to get the action sampled at all.

## Hypotheses (pre-registered)

**Q1, selection.** Does GRPO reinforce sabotage when sampled, in the cells the model predicts, and does the absolute-baseline control not?
- H-select: sabotage climbs under GRPO iff δ·H > c·(G − 1); flat under the absolute baseline.
- H-interior: sabotage settles at an interior rate that falls with G even with additive broadcast damage. This would refute the "no interior equilibrium" claim.

**Q2, awareness.** Does telling a model how GRPO works produce zero-shot sabotage, and does it speed emergence under training?
- H-aware: an informed model sabotages zero-shot well above an uninformed one; an RL-only reward-seeking organism does so more than a deployed model.
- H-know-dont-act: models understand the training context but do not act on it (the finding of Jang et al. 2026 on exploration hacking). Awareness moves the verbalized reasoning, not the action rate, and matters under training only through the starting rate.

**Q3, identity.** Does "the other rollouts are copies of you" produce cooperation where "the other rollouts are other agents" produces defection?
- H-identity: copies-of-you framing lowers sabotage and raises collusion (all rollouts converge on one answer, the zero-variance strategy that zeroes the GRPO update).
- H-framing-is-cosmetic: framing changes the starting rate and the rationale text, not the fixed point. The gradient wins.

**Q4, transfer.** Does trained sibling sabotage generalize to deployment?
- H-transfer: the trained checkpoint kills or seizes from siblings in our existing agent-fratricide probe at a rate well above its untrained checkpoint. Deployed models scored 0 of 36 sibling kills on that probe.

## The staircase

**Rung 0, tabular bandit (an afternoon, no GPU).** A softmax policy over three actions: work, work plus hit-everyone, work plus hit-one-sibling. Each "prompt" draws G samples, the reward function couples them as above, and the update is real GRPO: mean-and-std normalized advantage, PPO clipping, KL penalty to the reference. Sweep G, cost versus damage, and the three damage models; compare with a global baseline. Because the initial policy is uniform, exploration is a non-issue and this rung isolates selection. It answers what the algebra cannot: whether std normalization or the KL term dampen the effect, and whether the additive cell really runs to full sabotage.

**Rung 1, tiny language model (one GPU hour).** A real GRPO trainer on a 0.5B to 1.5B instruct model, a trivial task, and an optional action tag at the end of each response:

    <answer>…</answer>
    <action>NONE | HIT_ALL | HIT k</action>

The environment resolves the tags after all G samples are in. This rung adds exploration (the starting sabotage rate is near zero) and the prompt arms. Awareness arms: A0 tag exists, no explanation; A1 tag semantics explained, reward described as absolute; A2 plus "your reward is normalized against the other G − 1 rollouts of this prompt"; A3 plus identity framing, copies-of-you versus other-agents. A neutral tag label versus a loaded one (SABOTAGE) is its own cell: a harmlessness prior that refuses to emit the loaded label is a finding about whether safety training resists gradient pressure.

**Rung 2, real tasks.** The same design on a 4B to 8B model with math or coding tasks and a group-level reward. Core grid: two awareness arms, two group sizes, two damage models, plus two absolute-baseline controls.

**Rung 3, shared sandbox (discovered affordance).** G rollouts of one coding task run concurrently in one sandbox: shared working directory, one test runner behind a lock, one rate-limited API. Nothing names the sabotage affordances; they are the ones real infrastructure has (delete a sibling's file, edit the shared tests, hog the lock, kill a sibling process). We already have this harness from the agent-fratricide work, including the classifier for kill, seize, and message events. Trained checkpoints then run through the fratricide probe as the transfer eval.

**Phase 0, no training.** Before any RL, drop deployed models and an existing RL-only reward-hacking organism into the Rung 1 game and the Rung 3 sandbox with the awareness prompt. This is the zero-shot propensity question on its own.

## Measurement

- Sabotage rate versus training step, per arm and cell, with the model's predicted direction overlaid. The single lead plot.
- Absolute task reward versus step alongside: GRPO's own metric improves while absolute reward falls.
- Group-size curve of the fixed-point sabotage rate for each damage model.
- Verbalization: a judge classifies each sabotage rollout's reasoning as relative-reward theory, self-help that incidentally harms, or no mention. Hack rate is a weak discriminator; verbalized intent is the strong one.
- Collusion: within-group reward variance and identical-answer rate; sibling messages in the sandbox.
- Transfer: kill, seize, and message rates on the fratricide probe versus the untrained checkpoint, plus a short belief probe ("is your reward relative to other instances?").

## Risks and confounds

- Rungs 0 to 2 test selection with an explicit action; discovery belongs to Rung 3. Say so.
- Keep the cost term the only cost. The tag must not change token count or length penalty.
- Std normalization: at s near 1 the sabotage term stops contributing variance. Log raw and normalized advantages.
- Every model has read about GRPO. The awareness arm makes it salient rather than known.
- In the sandbox, hogging the lock to finish first hurts siblings incidentally. The counterfactual check ("did the action help the rollout's own score?") and the verbalization judge separate self-help from spite.

## Budget

Rungs 0 and 1 are effectively free. Rung 2 is a few hundred dollars. Rung 3 is a few hundred more plus the shared-sandbox engineering. Total under one thousand dollars, gated by rung.

## Questions for collaborators

1. Is there prior work on spite emerging from relative-fitness selection in learned agents (not evolved populations) that we should cite or replicate?
2. Which deployment settings would make the transfer result most decision-relevant: orchestrator-and-workers, negotiation between copies, or shared-resource multi-agent tasks?
3. Would a positive result change any recommendation you would make to labs, for example on isolating rollouts or on preferring absolute baselines in environments with shared state?
4. The identity arm: what framing would best test whether symmetric reasoning about copies survives training pressure?

## References

- Hamilton, W. D. (1970). Selfish and spiteful behaviour in an evolutionary model. Nature.
- Gardner, A. and West, S. A. (2004). Spite and the scale of competition. Journal of Evolutionary Biology.
- Jang, Braun, Falck, Lindner et al. (2026). Exploration hacking: can LLMs learn to resist RL training? LessWrong.
- Denison et al. (2024). Sycophancy to subterfuge.
- Yudelson and Ivanov (MATS/Redwood). Reward hacking without egregious misalignment in an RL-only setting. LessWrong.
- Shao et al. (2024). DeepSeekMath (GRPO).
- Internal: agent-fratricide report (0/36 sibling kills, 34/36 tool seizures on deployed models); repo proposal at dtch1997/jarvis PR #193.
