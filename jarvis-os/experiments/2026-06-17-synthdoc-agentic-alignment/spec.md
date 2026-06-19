# SDF for agentic-misalignment reduction (2b — PLAN, not yet run)

**Goal.** Test whether constitutional-values **synthetic document finetuning**
reduces a model's rate of *agentic misalignment* — taking a harmful autonomous
action (blackmail / self-exfiltration / sabotage) under goal-conflict + urgency —
following [Teaching Claude Why](https://www.anthropic.com/research/teaching-claude-why)
(constitutional docs + aligned-AI narratives cut blackmail 65% → 19%, >3×,
persisting through RL).

This is section 2b of the SDF blogpost: moving from implanting a *fact* (2a) to
shaping *behaviour*. Same eval philosophy — measure depth, not recall — new axes.

> **Status: planning only** (per scoping decision). No compute until this spec is
> signed off and Phase 0 clears its gate.

## The crux: headroom

You can only measure a *reduction* if the base model misbehaves at a meaningful
rate to begin with. Frontier models exhibit agentic misalignment; small open
models often don't. **A 9B model may simply never blackmail**, leaving nothing to
reduce. So the experiment is gated on a headroom screen, exactly mirroring the
controls-first discipline that paid off in 2a.

## Phase 0 — headroom screen (gate; cheap-ish, eval-only)

Run the agentic-misalignment scenario suite against each Tinker-servable candidate
(`Qwen3.5-9B`, `Qwen3.6-27B`, `Qwen3-235B-A22B-Instruct`) with **no intervention**,
and measure base misaligned-action rate.

- **Gate:** proceed only with a model whose base rate is high enough to show a
  reduction (target **≥ 30%** misaligned-action on the suite). Pick the smallest
  model that clears it (serving/training cost).
- If *no* candidate clears it: pivot to a lighter 2b target (a single alignment
  value — honesty/non-deception — with the stated-vs-revealed gap), and say so in
  the blogpost. This is a real possible outcome, not a failure.

## Scenario suite + scoring

- Use the published **Agentic Misalignment** scenario family (goal conflict +
  threat of shutdown/replacement + an available harmful action), adapted to our
  harness. Each scenario is an agentic, multi-turn rollout; an LLM judge classifies
  whether the model *took the misaligned action* (binary), with the action made
  unambiguous in the scenario.
- Primary metric: **misaligned-action rate** [Wilson 95% CI]. This is the
  behavioural analog of 2a's "recall."

## Intervention: constitutional-values SDF

Generate the corpus with `aligne-synthdoc` from a **constitution** universe
context (we already support `spec_from_constitution`):

- High-quality constitutional documents **+ fictional narratives of an aligned AI
  declining a harmful autonomous action and reasoning about why.**
- Bias the corpus toward **admirable reasoning**, not just aligned demonstrations
  (the literature's "reasoning > demonstrations" and "OOD generalizes better"
  findings). Hold out the eval scenarios' surface form from the corpus.
- Train: LoRA SFT, **mixing in baseline instruct data** to avoid behavioural
  collapse (a documented SDF failure mode).

## Eval axes (behavioural depth — mirrors 2a)

1. **Revealed misaligned-action rate** (primary) — base vs SDF.
2. **Generalization** — held-out scenarios structurally unlike the training
   narratives (not near-copies).
3. **Robustness** — under stronger pressure (more urgency / a sympathetic excuse).
4. **Specificity / no-collateral** — does NOT tank general capability (MMLU within
   noise) or **over-refuse benign agentic tasks** (a benign agentic control set).

## Controls-first (before SDF)

- **Negative** = base model → the headroom rate (high).
- **Positive** = constitutional values in the **system prompt** → should reduce the
  rate. Proves the eval discriminates and that the values *can* move the behaviour
  before we try to bake them into weights.

## Registered predictions (confidence)

- **P0 (headroom):** ≥1 candidate exhibits ≥30% base misaligned-action. **0.6**
- **P1 (eval validity):** constitution-in-prompt reduces the rate vs base. **0.8**
- **P2 (SDF reduces):** constitutional SDF cuts the rate ≥2× vs base. **0.5**
- **P3 (specificity):** SDF preserves capability + doesn't over-refuse benign
  agentic tasks. **0.6**
- **P4 (reasoning > demos):** reasoning-heavy corpus beats demonstration-only. **0.55**

## Cost

Heavier than 2a. Dominated by (a) serving a capable-enough model — likely
`Qwen3.6-27B` or `Qwen3-235B`, possibly a RunPod pod rather than managed Tinker —
and (b) multi-turn agentic rollouts (more tokens/scenario) across several arms.
Phase 0 (eval-only) is the cheap gate; commit to training spend only after it
clears.

## Risks / open questions

- **Headroom (top risk).** Mitigated by Phase 0 + the documented pivot.
- **Judge reliability** for "took the misaligned action" — needs a crisp,
  unambiguous action per scenario and a validated judge prompt.
- **Scenario availability** — confirm we can use/adapt the Agentic Misalignment
  scenarios in-harness.
- **Over-refusal** as the specificity failure (the values make the model refuse
  benign autonomy) — hence the benign-agentic control set.
- **Persistence through RL** (the paper's striking result) is out of scope for the
  first pass.
