---
name: concierge-tool
description: "worker pool over headless Claude sessions (durable tasks in, gated artifacts out); dtch1997/concierge, clone repos/concierge"
metadata: 
  node_type: memory
  type: project
  originSessionId: f71eda58-1717-409e-92dd-77aaa94948e7
  modified: 2026-07-23T16:14:57.546Z
---

**concierge** — worker pool over headless `claude -p` sessions. Spun out
2026-07-07 to `dtch1997/concierge` (public), gitignored clone at
`repos/concierge`. Designed first-principles after deciding NOT to build on
[[foreman]] (interface conflated with engine; now a candidate client),
[[flywheel-experiment-loop]] (ranking/triage deliberately cut), or
[[flightdeck]] (blocking `AgentRun.go()` owns policy the reconciler owns;
can't re-attach across daemon restarts — event-parsing/gate semantics
borrowed instead).

Core (see SPEC.md): 4 primitives — Task (spec+workspace+gate+budget; gates
externally checked, never self-reported), Worker (resumable `claude -p`
session; pid+logs re-attachable), Message (per-task mailbox; GitHub-comments
bridge planned v1.5 as transport, mailbox stays the control channel), Pool
(stateless reconciler over `$CONCIERGE_HOME` dumb files). **Asyncio-native
library, not a CLI** (user preference, bellhop-style): `Pool.submit/msg/...`
sync, `await pool.wait/wait_all/serve` coroutines; `python -m concierge`
keeps only `serve` + `msg` shims (worker blocked-signal). Both verbs:
`await pool.wait(tid)` + notifications (stdout/Slack).

State: v0.2 e2e-tested. Gates are **Gate objects** (declarative/serializable,
`check(ctx)→Verdict`, `describe()` into worker preamble, `&`/`|` compose;
round-trip constraint: evaluator ≠ submitter process). Runtime is
**AgentSdkRuntime**: SDK session inside a detached `python -m
concierge.worker` process per task (NEVER in the daemon — daemon death must
not kill workers, the anti-flightdeck invariant); wrapper normalizes typed
messages → agent.jsonl; `signal_blocked` in-process custom tool;
`access=readonly` via tool allowlist; `setting_sources=["project"]`.
**Worker primitive**: `Worker.spawn/attach/poll/kill` + immutable
`WorkerState` (alive×ended → running/lingering); invariant = constructible
from task record alone (observer ≠ spawner). **Caller view = typed async
function** (user's framing): `await pool.run(spec, output=Dataclass,
gate=…) → typed result` (raises TaskFailed, record on .task) via SDK
output_format→structured_output; `await pool.ask(tid, q)` rehydrates a
settled session for follow-ups. Contract: (spec, workspace, budget) →
(output: schema, workspace′: gate) — schema types the data, gate types the
side effects. Workers self-bound (USD +
in-process wall timeout) and exit deterministically on result-event flush
via killpg-own-group (SDK cleanup can hang post-session); `alive()` treats
zombies of the spawning daemon as dead. Restart e2e: daemon1 dispatch →
worker finishes daemonless → daemon2 attaches+settles.
**LIVE on devbox**: shared home `~/concierge-home` (config.yaml — daily
cap $1000, concurrency 4 — + HOUSE_RULES.md), persistent daemon in tmux
session `concierge` (daemon.log in home). Gotcha: daemon reads config.yaml
only at startup — restart the tmux session after config changes. HOUSE_RULES.md is appended to every worker's system
prompt (jarvis conventions: GCS artifact paths, bellhop, reportly H1
standard; judgment = decide-and-note, do NOT block on questions — user's
explicit preference) — probe-verified. Package
pip-installed editable (hatchling — user prefers hatchling over
setuptools). Preferred use pattern: as a tool from Claude Code sessions —
submit inline, join via background awaiter script → task-notification.
Next: MCP server module (tier 2), HTTP API + marquee (v1.5,
`Pool(host=…)`), GitHub comment bridge, [[bellhop-library]] hosting,
first real task (candidates: refusal-ban blogpost PR, pirate-attack
wrap-up), Slack webhook for blocked-task pings.

Gotcha found (pre-SDK): nested `claude -p` workers inherit the parent
project's MCP servers → CLI hangs on exit after the result event; reconciler
treats the `result` event as authoritative (reaps lingering pid) — kept as a
safety net.

Bugs/lessons from first real fleet (2026-07-09, scimt workstreams):
1. **`pool.ask` rehydration can no-op**: follow-up on settled `t-0709-a440`
   ran 0 turns, returned `result: ""` (attempt logged, session_id reused,
   prompt delivered, nothing executed). Don't rely on ask for rescue; inspect
   worker workspace + pod directly (bellhop key = `~/.ssh/id_ed25519`, NOT the
   runpodctl key).
2. **Gate-vs-done gap**: `PrOpen & FileExists(report)` is satisfiable by an
   honest interim PR while the real pipeline still runs detached on a pod —
   worker settles, detached driver dies with it (killpg-own-group), pod
   orphans idle. Fix pattern: gate on results.jsonl/no-PENDING lint AND
   forbid interim PRs in the spec; for pod pipelines, the driver must not be
   a child of the worker process group.
3. **Workers cannot span multi-hour pod pipelines (2× observed 07-09):**
   (a) t-0709-7e7e: worker correctly refuses interim PR while pod runs →
   exits ok, gate fails, 3 attempts burned → task `failed` while pipeline
   healthy pod-side; (b) t-0709-9505: worker DID stay alive on a waiter but
   the SDK **force-requested StructuredOutput mid-run** (~22 min in), ending
   the attempt with honest PENDING output → same retry-exhaust death.
   Recovery playbook: pipeline is pod-side + per-stage GCS checkpointed, so
   watch for the terminal `.done` marker (test `rclone lsf` OUTPUT non-empty
   — it exits 0 on missing objects) and dispatch a cheap finisher task to
   assemble report+PR. Real fix needed in concierge: a `waiting` task state /
   long-poll verb that doesn't burn attempts — **FILED as concierge issue #2**
   (2026-07-09; covers both instances, the pool.ask 0-turn bug, the recovery
   playbook, and 3 fix options incl. `pool.submit(after=…)` launcher+finisher).
   **FIXED 2026-07-09** (user asked the review session to fix it; built by
   pool task `t-0709-dc9f`, PR #3 merged `cd34383`, daemon restarted, live
   HOUSE_RULES updated): `signal_waiting(until_shell, note, timeout_minutes)`
   worker tool (atomic sidecar tasks/<tid>.wait.json, dual of signal_blocked)
   + `waiting` task state — daemon consumes the sidecar BEFORE the gate check,
   polls the probe (config `wait_poll_seconds` default 60, exit 0 = fire;
   probe runs in workspace, 60s subprocess timeout), resumes the SAME session
   on fire / timeout (config `wait_timeout_minutes` default 720) / user
   message; waiting holds no concurrency slot. Attempt accounting switched to
   a `gate_failures` counter — resumes from blocked/waiting never burn
   max_attempts. Preamble + gate-fail message steer to signal_waiting.
   Probe gotcha baked into tool description: `rclone lsf` exits 0 on missing
   objects — test output non-empty. pool.ask 0-turn bug NOT fixed (ruled out
   output-schema/budget/glue; likely SDK resume-delivery — notes on issue #2,
   still open for that).

Hardening (2026-07-09, from 10-transcript session review): HOUSE_RULES.md
updated live (placeholder-settle ban + tracked-waiter rule, background-task
anti-patterns, python3/uv-3.12/`~/.env` env notes, cwd + Read-before-Write
footguns — takes effect per-spawn, no restart). Code hardening dispatched to
the pool itself as `t-0709-33ff` (branch fix/session-review-hardening, gate
`PrOpen & ShellOk(pytest)`): (a) persist evaluated gate verdict as
`task["gate_result"]` (was: only the spec stored, verdict lost), (b) provision
every workspace with jarvis' guard-background-tasks hook via
settings.local/merged settings + git-exclude, (c) `env_file` config key
(default `~/.env`) pre-seeds worker env at spawn, (d) gate-fail resume message
no longer pushes placeholder-shipping. **After merge: pull repos/concierge
main + restart the `concierge` tmux session** (daemon imports live from the
clone) — wait for live workers to settle first.

**Waiting-state field lessons (2026-07-09 ~21:00, monitoring the scimt fleet;
concierge issue #5):**
1. **Parking kills session-bg drivers** — signal_waiting exits the session, so
   a driver launched as a harness background task dies at park and the wait
   probe can never fire (3 workers hit this same evening; only the one that
   deliberately `setsid`-detached survived). Supervisor fix: relaunch the
   driver detached in tmux from the workspace (drivers were all
   idempotent-resume, incl. Tinker mid-cell ckpt resume) and let the probe
   fire naturally. HOUSE_RULES now carries a "detach (tmux/setsid) BEFORE
   parking" exception to the no-detach rule; HOUSE_RULES.example.md in-repo
   still needs it.
2. **Do NOT pool.msg a `waiting` task** — mail force-resumes it immediately,
   and a 0-turn resume exit (pool.ask-family bug) gets gate-checked and burns
   a strike; t-0709-a9e2 went spuriously `failed` this way while its sweep ran
   fine. Only msg `blocked` tasks; for parked workers, leave notes in the
   workspace (e.g. SUPERVISOR_NOTE.md) instead.
3. **Requeue-by-file-edit works**: hand-edit tasks/<tid>.json (status→queued,
   gate_failures→0, bump max_attempts, atomic os.replace) — the daemon picks
   it up in the SAME workspace, no work lost.
4. `Pool.wait` is a coroutine (`asyncio.run(pool.wait(tid))` in awaiter
   scripts); `pool.tasks()` returns list[dict] keyed `status`, not `state`.

**Waiting-state shipped AND hotfixed (2026-07-09 evening):** issue #2 fix
merged as PR #3 (signal_waiting tool + waiting state + gate_failures
accounting). First production use (t-0709-0673) immediately crashed the
daemon: the <tid>.wait.json sidecar lives in tasks/ and matched
Home.tasks()'s bare t-*.json glob → KeyError 'created' in the tick loop →
daemon dead, waiting worker deadlocked. HOTFIX merged as **PR #4** (skip
.wait.json in the glob + regression test), daemon restarted; verified: parked
task shows `waiting` with its note, new tasks dispatch. Lesson: sidecar files
sharing a globbed dir need name-filtering at every listing site.

**2026-07-10:** moved into [[arsenal-monorepo]] as `packages/concierge` (history preserved); `repos/concierge` is now a symlink into `repos/arsenal`; dtch1997/concierge ARCHIVED with a pointer note. **New issues go to dtch1997/arsenal** (old repo's tracker is read-only).

**Repo-URL gotcha (2026-07-10, arsenal issue #1):** `pool.submit(repo=…)`
MUST get a cloneable URL (`git@github.com:owner/name.git`) — a bare
`owner/name` slug makes reconcile's `git clone` exit 128 and the unhandled
CalledProcessError **kills the whole daemon**; every task (incl. healthy
`waiting` ones) freezes silently. Recovery: hand-edit the bad tasks' `repo`
fields, rm any partial workspace dir, restart the tmux daemon. Also observed:
daemon restart force-resumes `waiting` tasks (attempt N+1) — workers must be
idempotent-resume anyway, but expect it.

**Trees-and-leaves delegation SHIPPED 2026-07-23 (arsenal PR #30, MERGED;
daemon restarted, live HOUSE_RULES updated):** workers call up new workers
within the same pool — `delegate` MCP tool (title/spec/gate/budget_usd/
model/base) = queue-insertion with parentage (`parent`/`depth` fields),
never pool-creation; same daemon, same concurrency cap, children queue when
full. Rails at the tool: depth cap (config `max_depth`, default 2) + budget
carve (child USD ⊆ parent remaining − already-delegated; computed by
scanning children — worker never writes its own daemon-owned record).
Parent MUST park via signal_waiting on `python -m concierge probe-children
<tid>` (exit 0 iff ≥1 child and ALL terminal — failures included; parent =
recovery mechanism), never wait in-session (slot deadlock). Child priority =
parent+1 (trees drain before fresh roots). Per-task `model=` knob on
submit/delegate (leaf economics; children inherit by default). Children
default to parent's BASE, not branch — pass base=<pushed branch> to build on
parent's work. `pool.tree(tid)` renders the subtree. PATTERNS.md (same PR) =
user-facing usage-patterns doc (decision rules, gate design, delegation
choreography, anti-patterns). Deferred: reconciler zero-children-probe
sanity check, child-spend counted against parent at gate time,
cancel-cascade. Design followed Cursor's trees-and-leaves agent-swarm post.

**BUG found+FIXED 2026-07-14 (arsenal PR #6, MERGED): `load_config` silently
returns `{}` when pyyaml isn't importable** (records.py — `except
ImportError: pass`), so a daemon started in a venv without yaml runs on
DEFAULTS (daily_usd_cap 50, not the config's 1000) and quietly holds queued
tasks at "$50 cap reached" while config.yaml says otherwise. Symptom:
tasks stuck `queued` + daemon.log cap lines that contradict config.yaml.
Fix at launch: `uv run --with pyyaml python -m concierge serve` (or install
pyyaml in the serving venv). Fixed: pyyaml declared dep, present-but-unreadable config raises, serve banner prints effective daily_usd_cap. NB the long-lived daemon picks the fix up on its next restart (running one uses --with pyyaml, behaves correctly). Also: `pool.wait` default
timeout is 3600s — pass `timeout=` explicitly for multi-hour workers.
