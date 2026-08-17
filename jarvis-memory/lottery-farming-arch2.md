---
name: lottery-farming-arch2
description: "STUB (persisted to wiki 2026-08-17) — lottery farming (noisy-judge resubmission gaming) elicited + mapped via arch2; EM-from-farming = install-yes/EM-no; findings in wiki; repo ArcadiaImpact/autoresearch-lottery-farming-arch2"
metadata: 
  node_type: memory
  type: project
  originSessionId: 35b8ba18-d068-4b1d-b69b-bee9d277e831
  modified: 2026-08-17T08:19:09.478Z
---

Findings live in the jarvis wiki: concept `lottery-farming`, sources
`lottery-farming-dose-response` / `em-from-farming-sft` /
`lottery-farming-lit-review`, entity `lottery-farming-testbed`. Canonical
docs in the repo: `findings/lottery-farming/blogpost.md` (main, #95),
`docs/lit-review.md` (main, #96), `attempts/em_farming/REPORT.md` (branch
`em-farming`, PR #97).

One-liner: agents farm a noisy judge out of the box (Haiku 0.67, Sonnet-5
held-out 0.7); farming rises with noise with no ceiling decline for
verbatim-type farming (decline = rule-B seed-reroll only); warnings /
selection rule / coarsening don't suppress; farming-SFT installs the policy
(0.66 vs 0.16 base) with ZERO chat-eval EM and a knowing/doing split —
Africa & Pfau outcome.

Operational:
- Repo `ArcadiaImpact/autoresearch-lottery-farming-arch2`, clone
  `repos/lottery-farming`. Run WRAPPED 2026-08-16 (fleet self-idled ~11h/48h,
  93 scored PRs, winner #38 merged; 85 PRs closed, dead-ends preserved).
  Results MERGED to main (#95 squash). `/arch-interview` retrospective still
  available; boot-watch false-UNREACHABLE filed as arch2#130 (see
  [[arch2-tooling-bugs]]).
- **PR #97 (em-farming) still OPEN** — EM report + pipeline
  (`attempts/em_farming/`, spec SPEC.md); artifacts GCS
  `experiments/em-farming/`, checkpoints `tinker://` in checkpoints.json.
  Top next step = agentic-misalignment probe (chat-only EM eval is the key
  limitation); also loss-mask length-matched honest arm.
- **Slack note DRAFTED in-thread, unsent** — #lab-notes-daniel is Slack
  Connect; Daniel must hit send on the draft.
- Infra kept: RunPod volume `bne3ea3c8x` (EU-RO-1, held-out seeds+target) +
  GH secrets; pods terminated. Transcripts: arch2 S3 bucket + volume
  `/mnt/arch_data/transcripts/`. Cost ~$21 GPU + API (unmetered key).
- Decisions Daniel can veto (chosen AFK): objective = held-out elicitation
  rate; targets Haiku→Sonnet; budget 4×48h; WORKER_GH_TOKEN = broad gh OAuth
  token (swap for fine-grained PAT + update GH secret + `.arch/.session.json`
  if desired).
- Gotchas: segment_fit reference saturates >16 attempts (G1b correctly
  rejects; documented in SCHEMA.md); `gh repo create --push` rejects dtch009
  email — commit as `25474937+dtch1997@users.noreply.github.com`; jarvis
  branch-switch hook applies inside repos/* (arch worktree
  `.claude/worktrees/arch-lottery-farming`); Sonnet-5 default-thinking
  starved harness tool calls → thinking:disabled in environment/episode.py
  (cf. [[sonnet5-adaptive-thinking-gotcha]]); Tinker/Qwen multi-turn SFT
  needs per-turn explode + LAST_ASSISTANT_MESSAGE (aligne driver hardcodes
  all_assistant_messages — ~1 loss token/seq on qwen3 renderers).

Related: [[arch2-tooling-bugs]], [[autoresearch-arc-whest]],
[[value-leakage-repro]], [[research-slides-guidance]] (the deck for this run
is the worked example).
