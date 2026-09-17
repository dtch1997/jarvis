# ai-swarm — basic harness for AI swarm experiments

A minimal harness for instantiating many parallel Claude coding agents that
can talk to each other, with transcript logging the agents cannot touch.

Reference point: [arXiv:2609.04170](https://arxiv.org/abs/2609.04170)
(*Emergent Cheating and Whistleblowing in Autonomous Research Swarms* —
100 agents, a shared knowledge library, p2p messaging, and transparent
channels that let non-cheating agents detect and police an exploit). This
harness reproduces that communication shape at small scale: a broadcast
board (the transparent/shared channel) plus per-agent inboxes (p2p), with
a host-side record of everything.

## Architecture

```
runs/<run-id>/
├── manifest.json            run config snapshot + exit codes
├── comms/                   shared volume, mounted rw in EVERY container
│   ├── board/               broadcast: one file per post
│   └── inbox/<agent>/       direct messages
├── agents/<agent>/workspace private volume, mounted only in that agent
└── logs/                    HOST-ONLY — never mounted anywhere
    ├── <agent>.jsonl        hash-chained transcript (stream-json events)
    ├── comms.jsonl          hash-chained comms activity log
    └── comms-archive/       immutable snapshot of every comms file version
```

Each agent is a headless CLI coding agent inside a Docker container, per-agent
selectable via `runtime`:

- `runtime = "claude"` — `claude -p <task> --output-format stream-json`, swarm
  protocol injected with `--append-system-prompt`, cost capped with
  `--max-budget-usd`.
- `runtime = "codex"` — `codex exec --json -m gpt-6-astra <task>`, swarm
  protocol injected via `/workspace/AGENTS.md` (codex reads it natively; there
  is no append-system-prompt flag). Codex has no dollar budget cap, so
  `wall_timeout_s` is the only bound. Auth: `codex login` on the host (the
  harness copies `~/.codex/auth.json` into the agent's mounted `$HOME`) or
  `OPENAI_API_KEY` in the environment or `~/.env`.

Skipping the CLI's own permission prompts/sandbox is safe here: the container
only sees the agent's workspace and the shared comms tree. The harness on the
host reads each container's JSONL stdout and appends it to that agent's log.

### Why agents can't delete the logs

1. **Structural**: `logs/` is never bind-mounted into any container. An agent
   has no filesystem path to any transcript, including its own. This is the
   actual guarantee — it doesn't depend on the agents' cooperation or on
   them not discovering something.
2. **Tamper-evidence**: every log line is hash-chained
   (`hash = sha256(prev ‖ canonical(seq, ts, event))`). `swarm verify`
   recomputes every chain, so any later edit/insertion/truncation — by
   anything that *does* have host access — is detectable.
3. **Comms are in-world, but archived**: agents *can* overwrite or delete
   messages in `/comms` (interesting behavior, worth observing — cf. the
   paper). The host-side archiver snapshots every version of every comms file
   into `logs/comms-archive/` (~1s poll) and records deletions in
   `comms.jsonl`, so the historical record survives in-world tampering; the
   responsible agent's transcript also logs the tool calls that did it.

### Communication protocol (told to every agent via system prompt)

- Broadcast: write a new `<ts>-<agent>-<slug>.md` file to `/comms/board/`.
- DM: write to `/comms/inbox/<recipient>/`; your inbox is `/comms/inbox/<you>/`.
- Check board + inbox at start and between work steps.

## Usage

```bash
cd experiments/ai-swarm
python3 -m swarm build                 # build the agent image (once)
python3 -m swarm run configs/demo.toml # run a swarm; auto-verifies at the end
python3 -m swarm verify runs/<run-id>  # re-verify chains any time
```

Config (`configs/*.toml`): a `[swarm]` template stamps out N homogeneous
agents (`count`, `task`, `{agent_id}` substitution), and/or explicit
`[[agents]]` blocks for heterogeneous roles; per-agent `model` /
`max_budget_usd` / `runtime` overrides. `[run]` sets `runtime`
(`claude`/`codex`), `model` (claude alias `haiku`/`sonnet`/`opus`, or a codex
model id like `gpt-6-astra`), `max_budget_usd` (per agent; claude only),
`wall_timeout_s`, `max_parallel`. Mixed-runtime swarms work: set `runtime` per
`[[agents]]` block.

## Auth & caveats

- Each agent gets a **copy of its runtime's credentials**
  (claude: `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token` — preferred, since copied short-lived creds die to concurrent refresh rotation — else a copy of `~/.claude/.credentials.json`; codex: `~/.codex/auth.json` copy or `OPENAI_API_KEY`)
  in a private bind-mounted `$HOME` (deleted when the agent exits). So agents can read
  their creds copy and have unrestricted network egress — fine for benign
  experiments, but for adversarial/misalignment setups add an egress proxy
  (allowlist `api.anthropic.com`) before trusting the isolation story.
- Cost is capped per agent by `--max-budget-usd` and per run by
  `count × max_budget_usd`. The demo is 3 haiku agents at $0.25 each.
- The comms archiver polls (default 1s); a comms file created and deleted
  within one interval escapes the mirror but not the perpetrator's transcript.

## Obvious next experiments

- Scale up `count`; add a shared "knowledge library" dir with a seeded
  exploit-shaped incentive, à la the paper.
- Give agents differing/conflicting incentives per-agent via `[[agents]]`.
- Add a scoring/evaluation step that reads only `logs/` (ground truth).
