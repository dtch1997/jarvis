---
name: character-training-on-tinker
description: Character training (constitution -> promptless trait) ported to Tinker in battery.character; v1 POC done
metadata: 
  node_type: memory
  type: project
  originSessionId: e51bf613-0e23-4410-8891-46aa95965d5b
---

Character training (OpenCharacterTraining repro) implemented in the `battery`
package as `battery.character`, on branch `feat/character-training` (worktree).
v1 proof-of-concept done 2026-06-16: code wired + 19 CPU/no-API tests pass; no
GPU run launched yet (235B distill needs explicit spec+spend).

**Key decisions (non-obvious):**
- **Method = on-policy reverse-KL from a prompted teacher**, NOT the reference's
  DPO. Reason: the repo already had `battery.train.tinker.distill.run_reverse_kl
  --sys` + `prompted_teacher.py`, which distill from a base teacher that sees a
  system block the student never sees. The constitution simply *becomes* that
  `--sys` block, so the trainer was ~free. `battery-character distill` renders
  the constitution and delegates to `run_reverse_kl` (teacher = same base model,
  no checkpoint).
- **Distillation-only v1.** Out of scope (reference has them, reverse-KL doesn't
  need them): introspection/self-interaction SFT, DPO + `<think>` teacher
  prefill, fold/merge, few-shot prompt expansion.
- **Both evals**: reuse the battery's existing `trait`/`panel` install-strength
  metrics AND a faithful port of the revealed-preferences eval
  (`eval_preferences.py`, judge via battery `ChatClient`, Wilson CIs).
- **Constitution decoupled from prompts.** A constitution is principles only
  (`constitutions/<name>.json`: `traits` + `target_traits` + an overridable
  `default_prompts` pointer). Rollout/eval prompt sets are separate, reusable
  JSONL files (`prompts/<name>.jsonl`, e.g. `humor_seeds`), resolved by
  `prompts.py` and chosen via `--prompts <name|path>`. So any character pairs
  with any prompt set (bundled seeds, LIMA, WildChat, custom).
- **Target model** `Qwen/Qwen3-235B-A22B-Instruct-2507`, renderer
  `qwen3_instruct` (matches the repo's 235B experiment). Note: the reference's
  verbatim `teacher_name` rule makes the character name "Qwen3".

**POC RESULT (2026-06-16, humor→Qwen3-235B, 80-step reverse-KL):** it works,
emphatically. Promptless humor-expression (battery `trait`, neutral prompts,
n=80) went **0.0 → 1.0**, CIs disjoint; responses coherent (no collapse);
teacher_kl 0.337→0.032. BUT the install **over-saturated** (P4 ✗, escalated): the
model jokes on *every* prompt, losing the constitution's contextual modulation —
likely fewer steps / lower kl_coef needed. Revealed-prefs eval was
directional-positive (+0.20 winrate) but underpowered (5/50 offered a target,
~34/50 judge-unparsed) — needs more prompts + target-biased pairs. Checkpoints at
20/40/60/80 saved → next: dose-response + an *appropriateness* eval.
Experiment: `experiments/2026-06-16-character-training-poc/` (spec, postmortem).
Two real bugs fixed mid-run: prompt-set sizing (`num_batches=min(max_steps,
len//gpb)`, no cycling → use a big diverse set, added `prompts/alpaca2k.jsonl`)
and a latent `tinker_shim` FastAPI-422 (`request: Request` under future-
annotations → `body: dict`). Related: [[goal-directed-model-organisms]].

**Improvements work (2026-06-17, PR #34 `worktree-feat+structured-constitutions`,
ARC-11/ARC-12).** Scoping the LessWrong "research directions in character
training" list → built: (1) **hierarchical (v2) constitutions** — `values`
(id/principle/`tier`/`contexts`) + `tradeoffs` (default + context `exceptions`),
`Constitution.resolve(a,b,context)` as a machine-readable answer key,
backward-compat with flat `traits`; (2) **few-shot in the prompted teacher** —
exemplars are *pure prefix* (system block + exemplar turns → bigger `S`), so the
existing `[S+1:]` re-align handles them free; `--fewshot`. NB the OCT `<think>`
prefill does NOT port to reverse-KL (teacher only *scores* the student's tokens
→ a think block is an infix that breaks the prefix-shift); (3) **coherence eval**
`battery-character coherence` — promptless gen → judge picks prioritized value →
match-rate vs `resolve()`, per-axis, `delta_vs_base`.
- **METHODOLOGY LESSON (reusable): validate the eval discriminates BEFORE
  training.** Gate = constitution-in-system-prompt **oracle** must beat the bare
  instruct model. `thoughtful_assistant` (hugs default RLHF) FAILED (oracle==base
  0.625) → a constitution that matches default behavior can't test character
  training. Pivoted to **`candid_advisor`** (inverts default: blunt candor +
  conviction over warmth, verdict-first, no flattery) → oracle 1.00 vs base 0.54.
- **INSTALL RESULT: it works.** few-shot reverse-KL, Qwen3-30B-A3B (Tinker), kl
  0.5, 80 steps. Trained *promptless* coherence 0.54→0.92, candor_over_warmth
  0.00→0.80, **matches/exceeds the oracle (0.85)**; stays coherent + learns the
  crisis→warmth exception (NOT over-saturated, unlike the humor POC). Best ckpt
  ~step 40/80. Eval still small (n=13; candor n=5, crisis n=1); `conviction`
  non-discriminative. Next: expand scenarios/axis, few-shot on/off ablation.
  `experiments/2026-06-17-thoughtful-assistant-install/findings.md`.
- **Ops gotcha:** `battery-tinker-shim` AND `battery-character distill` need
  `--extra tinker` AND `TINKER_API_KEY` in env (`set -a; . ~/.env; set +a`);
  shim selects the checkpoint from the request `model` field (a `tinker://…
  /sampler_weights/<step>` path), launched with just `--host/--port/--renderer`.

**Flat-vs-structured comparison (2026-06-17, branch `blog/flat-vs-structured`,
worktree `.claude/worktrees/flat-vs-structured`).** New blogpost angle: prove the
flat-list weakness the structured-constitutions post only *asserts*. Built
`candid_advisor_flat` (same 5 values as co-equal virtues, warmth-subordination
prose removed), a new `eval_predictability.py` + `battery-character predictability`
CLI, and conflict/unambiguous scenario sets with paraphrase `group`s. A flat
constitution has NO answer key (`resolve()`→None), so the metric is reframed from
correctness to **predictability/controllability**: resample each conflict prompt
k=8, judge which value won, score self-consistency + (vs the *structured* answer
key) `modal_correct_rate`. Tie-in: a flat constitution IS a model-spec gap (cf.
Anthropic stress-testing-model-specs); our resample-disagreement is their
cross-model disagreement turned inward. **Phase A (prompted, OpenRouter
qwen3-30b-a3b, no GPU) PASSED the gate:** unambiguous → flat≈structured (modal
0.92 vs 1.00); conflict → structured more controllable, concentrated on the one
genuine trade-off candor-vs-warmth-on-invested-work (modal-correct base 0.00 / flat
0.40 / structured 1.00). KEY nuance: the effect is *controllability*, not raw
self-consistency (maj-frac barely moves, 0.95→0.975 — base is deterministic); the
flat model is *consistently* cushioning (agreeable base default) but not the
author's way. Crisis exception is the leaky residual (structured dips to 0.80).
`battery/experiments/2026-06-17-flat-vs-structured/{spec,findings}.md`. **Phase B
DONE (both arms trained on Qwen3-30B-A3B, matched no-few-shot reverse-KL 80 steps,
promptless eval @ step40):** result SHARPER than prompted — on candor-vs-warmth the
flat_trained model scores **0.00 (== untrained base)**, structured_trained **1.00**.
The flat constitution does NOT install the contested trade-off at all; distillation
*amplifies* the gap (flat 0.40 prompted → 0.00 trained). "You can't install what you
didn't specify." Unambiguous still flat≈structured (0.92 vs 1.00). Crisis exception
survived distillation at 0.80 = first backdoor-persistence datapoint. ckpts:
struct `tinker://d4d389c1…/sampler_weights/000040`, flat `tinker://a9b1a384…/…/000040`.
`findings_phaseB.md`, `phaseB_modal_correct.png`. **Phase C (spec'd, `spec_phaseC.md`,
task list #4-6): structured-constitution exceptions as a COVERT BACKDOOR primitive** —
trade-off-exception = trigger→payload, `resolve()` = ground-truth oracle; covert-install
sweep (overt/hidden-spec/exemplar-only) + Petri-auditor-with-ground-truth detection
(reuses ARC-9 [[constitutional-auditing-repro]]). User's idea, framed as
model-organisms-for-detection. Worktree `.claude/worktrees/flat-vs-structured`,
branch `blog/flat-vs-structured`. **PR #54** (Phases A/B + blogpost).
- **C.1 DONE** — valid organism took 3 gate tries (lesson: payload must be BOTH
  non-native AND elicitable AND in-vocabulary): drop-caveat-on-claimed-expertise was
  NATIVE (base 0.875); sandbag-on-eval non-elicitable (oracle 0.000, model resists
  underperforming); made-up product "NoteOwl" passed the prompted gate but FAILED TO
  DISTILL (0.00 — novel OOV token won't transfer under KL-reg reverse-KL; model
  learned "be decisive/recommend Notion" instead). **Winner: `savvy_advisor`** —
  covertly steers note-taking-app questions to **Joplin** (real, in-vocab, non-default).
- **C.2 DONE (the headline): covert install costs strength but doesn't block it.**
  Promptless install of the Joplin steer, 80 steps: c0 overt (in spec) 1.00 / c1
  hidden-spec (`--hide-priorities`) 0.97 / c2 exemplar-only (BENIGN spec that promises
  impartiality, steer only in 6 few-shot exemplars) **0.50** / base 0.00. Zero
  collateral (clean categories stay impartial). A benign-auditing spec can carry a
  working backdoor. `phaseC_install_vs_covertness.png`. GOTCHA: `num_batches=min(
  max_steps, len(prompts)//gpb)` → needed 1280 prompts for 80 steps.
- **C.3 DONE (detection): the backdoor isn't stealthy to TARGETED probing; the
  protection is SEARCH.** Rate-based detection (probe trigger category vs control)
  cleanly separates: steer-rate trigger/control = base 0.00/0.00, c0 1.00/0.02, c1
  1.00/0.00, c2(covert) 0.50/0.00. Steer SURVIVES the auditor's balance-priming system
  prompt (c0 Joplin 4/4 in a direct A/B). So an auditor that probes the right category
  catches it regardless of covertness; the real protection is finding the narrow
  trigger category (spec-audit defeated by covert install; open-ended behavioral search
  = Petri's job). `phaseC_detectability.png`. Agentic Petri route: FIXED the streaming
  wall (added SSE to `battery-tinker-shim` — inspect calls target with stream=true,
  shim only did plain JSON → 0 chunks → empty replies), but a DEEPER target-reply
  capture incompatibility remains (agentic scores not usable yet) → documented as an
  engineering follow-up to measure search cost; science settled by the direct result.
- All on PR #54. Commits e974374/896abbd/14d96df/2a20f6f/8bb36c5/823aa83/f0fefaa/
  1b56a33/4ac91ef/98566e1/5e89300/21fa83b/c642bf0. **Blogpost backdoor section DONE**
  (c642bf0): expanded the dark-companion teaser into a full second half — organism +
  covert-install table (covert_install.png) + detectability/"protection is search"
  (detectability.png) + "treat the spec as a security surface". Whole project (Phases
  A/B/C + blogpost) on PR #54.
