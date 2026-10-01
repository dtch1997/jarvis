---
type: entity
title: science-of-rl-motivations (program + rlm package)
description: "ArcadiaImpact/science-of-rl-motivations (private): Daniel's umbrella for what RL does to model motivations — one folder per experiment (SPEC.md before spend, README Status line), shared mechanism-only package `rlm` (framework-free envs, Episode runner, GroupFilter hook, Tinker + SkyRL adapters, sandbox backends none/bwrap/docker/modal). Hackable-CodeContests env on gpt-oss-120b via hosted Tinker is the common substrate for motivated-reasoning, consent-rl and distill-vs-rlvr; runs mirrored to GCS daniel/jarvis/experiments/<slug>/."
resource: https://github.com/ArcadiaImpact/science-of-rl-motivations
tags: [program, testbed, reward-hacking, rlm, tinker, skyrl, sandbox]
timestamp: 2026-10-01
---

# science-of-rl-motivations

Private umbrella repo created 2026-09-21 when `motivated-reasoning` and
`consent-rl` were migrated in with history; clone at
`~/jarvis/repos/science-of-rl-motivations`. **Not** in gazette's swept-repos
config — PRs merge by hand. Operational state (open PRs, next steps) lives in
the memory stubs `science-of-rl-motivations-architecture`,
`realistic-rl-pipeline`, `native-rl-stack-review`, `hackable-envs-lit-search`.

## Layout rules (enforced by `tests/test_layout.py`)

Every experiment is `experiments/<slug>/` with `SPEC.md` registered before
any spend, a `README.md` carrying a `**Status:**` line, and its own
`pyproject.toml`; the root holds only the uv workspace, `packages/`,
`experiments/`, `tests/`. Shared code: (1) nothing in `packages/` names an
experiment, arm, hyperparameter or finding; (2) code moves into `rlm` when a
second experiment needs it, in that PR; (3) dependencies point experiment →
`rlm` → external, never experiment → experiment. Raw `rollouts.jsonl` is
gitignored and mirrored to GCS.

## The common substrate

Hackable **CodeContests** env (`rlm.envs.codecontests`): planted loopholes
(always-equal `__eq__`, `os._exit`, conftest patching), ground-truth dynamic
hack verdicts plus a strict hack-proof grader; gpt-oss-120b, LoRA r32, 16×16
groups, 60 steps, 24k tokens on hosted Tinker (~75 min/run). Baseline
`rl_r0_base_s1`: 14% hacks at step 0 → ~100% by step 15, strict solve → 0.
Studies on it: [motivated-reasoning](../sources/motivated-reasoning-register-rl.md),
[consent-rl phase 0](../sources/consent-rl-phase0.md) /
[phase 1](../sources/consent-rl-phase1.md),
[distill-vs-rlvr](../sources/distill-vs-rlvr.md). Black-box battery:
[cn-reward-seeking](../sources/cn-reward-seeking.md). Not yet ingested: the
wave-1 hackable envs (hint_cues, verifier_triggers, harness_tampering,
reward_tampering), `repo_repair` (realistic agentic env on Xiaomi's MiMo code
tasks with logged egress), rlvr-regimes (spec only).

## rlm mechanics worth knowing

- Env core imports only the stdlib: `Env` (start/step/grade/close), `Reply`
  (text, thinking, tool_calls, failed_calls, clean_stop), `Episode` runner
  (turn cap, stop reasons, one rollout row per episode), `TaskSet`, registry.
- `GroupFilter` hook (`installed(LoopHooks(group_filter=…))`) applies
  veto-and-drop *before* advantages; a filtered run's `env/all/*` metrics are
  survivors-only — read rollouts.
- `response_sha` is the rollout join key; `(step, id)` names a 16-rollout
  group. The key collides on short answers (hint_cues).
- Grader sandboxing: bwrap by default on the devbox (0/16,920 verdicts
  differ from unsandboxed away from the CPU limit); RunPod pods refuse
  unprivileged userns, so SkyRL runs grade on Modal sandboxes (`rlm.fleet`
  over bellhop fleets). Modal grades time out more (gVisor) — don't compare
  runs graded on different backends.
- Adapters: `rlm.tinker` (hosted Tinker; renders on the event loop, prompts
  append-only via `canonical_suffix`), `rlm.skyrl` (SkyRL native trainer on
  own pods; SkyRL never delivers env config/step to a custom class without
  `RlmGymGenerator`; strips special tokens so Harmony can't be recovered).

## Gotchas (recurring)

- Hosted Tinker refuses to sample a bare base model (use the step-0 LoRA
  sampler); LoRA-SFT'd gpt-oss samples reserved Harmony ids that crash train
  batches (sanitise in place); Opus refuses hack transcripts without a
  research-context preamble.
- Rare-label taxonomy judges split (κ 0.2–0.7) — see
  [hack-reasoning-and-monitorability](../concepts/hack-reasoning-and-monitorability.md).
- A thinking teacher's visible prose is a summary; distilling it collapses
  the student ([distill-vs-rlvr](../sources/distill-vs-rlvr.md)).
