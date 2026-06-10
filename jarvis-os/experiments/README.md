# Experiment worker protocol

Experiments never block the main JARVIS flow. A worker (background subagent) owns each run end-to-end; the main session polls cheap artifacts (`status.md`, the outbox) and otherwise keeps moving.

## Directory layout

One experiment = one directory `experiments/<date>-<slug>/`:

| File | Contents |
|---|---|
| `spec.md` | Hypothesis, registered predictions + confidence, design, controls, cost estimate. Written **before** the run — non-negotiable (DESIGN.md). |
| `status.md` | Append-only heartbeat. Timestamped one-line entries: `spawned` / `running:<step>` / `done` / `failed:<reason>` / `escalated:<surprise>`. |
| code | Whatever runs the experiment (`run.py`, etc.). |
| `results/` | Raw + summarized outputs. |
| `postmortem.md` | Results vs registered predictions; discovery-or-bug analysis for any surprise; next steps. |

## Execution model

- Workers run as background subagents. The main session **never blocks** on a run — it spawns, then reads `status.md` and the outbox when it next polls.
- The worker appends to `status.md` at every state change. The main loop's poll is a file read, nothing more.

## On completion, the worker also writes

1. Appends an entry to repo-root `changelog.md`.
2. Appends prediction outcomes (and the running-calibration line) to `experiments/prediction-registry.md`.

Worker artifacts are **manager-facing**: written for the orchestrator, raw and label-dense is fine (`postmortem.md` is the canonical completion report). Workers do **not** write to `outbox/`.

## The manager transform

The orchestrator (main session) turns the worker's `postmortem.md` into the team-facing `outbox/<experiment>/tldr.md` + `writeup.md`, following `outbox/STYLE.md` (why → what was done → findings → caveats/next; no internal condition labels). Division of labor: workers produce data, the manager owns communication.

## Rules (from DESIGN.md, still binding)

- Tier 0 < $10 runs freely; $50/day Tier-0 aggregate; 3 strikes per hypothesis → escalate or drop.
- **Surprise always escalates:** any result contradicting a registered prediction gets an `escalated:<surprise>` line in `status.md` and a prominent flag in the tldr. Discovery or bug — that ambiguity goes to a human.
- Controls always; an experiment that fails its controls is auto-discarded before anyone sees the result.
