---
name: concierge-tool
description: "worker pool over headless Claude sessions (durable tasks in, gated artifacts out); dtch1997/concierge, clone repos/concierge"
metadata: 
  node_type: memory
  type: project
  originSessionId: f71eda58-1717-409e-92dd-77aaa94948e7
  modified: 2026-08-18T01:25:29.917Z
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

**2026-08-17: `after=` dependencies SHIPPED (issue #54 → PR #61 MERGED, built by pool task t-0817-3eda; daemon restarted on new code, submit-validation live-verified).** `pool.submit(spec, after=[tids])` → new first-class **`held`** status (`status_detail: "held: waiting on <unmet>"`); reconciler `_maybe_release` re-derives the join from dep records each tick (restart-safe); all deps `done` → released to `queued`; any dep `failed`/`cancelled`/missing → fail-fast `dependency <tid> ended <status>` via `_finish` (no gate strike). Held tasks hold no slot/seat; `wait`/`wait_all` work unchanged; legacy records without `after` fine. Unknown dep tid raises ValueError at submit. A/B/C-then-D pattern is now native — no more submitter-side join drivers. (2) **Pluggable worker backends** — arsenal issue #60 (Codex CLI + GPT 5.6 Sol as line workers; motivation = Fable 5 usage-limit pressure + leaf economics). Audit: `claude_agent_sdk` coupling is ONLY in worker.py; agent.jsonl + pid table are the backend-agnostic contract, so backend = alternate wrapper module. Port surface: event normalization, resume, `--output-schema`, the 3 signal tools via a new stdio MCP server, USD-budget→token-cap mapping; gaps = no guard hook, no native USD cost. codex-cli 0.147.0 INSTALLED + AUTHED on devbox 2026-08-18 (ChatGPT-plan login; `~/.local/bin/codex` symlink). All adapter capabilities smoke-verified live (findings on issue #60): `codex exec --json` event stream (thread.started carries thread_id = resume handle; turn.completed carries token usage), `-m gpt-5.6-sol` works, resume retains context (**gotcha: exec-level flags BEFORE the `resume` subcommand**), `--output-schema` works, stdin must be closed, readonly↔`--sandbox read-only`. **SHIPPED + LIVE-VALIDATED (issue #60 CLOSED 2026-08-18):** PR #71 (backends seam: `backend="claude"|"codex"` on submit/task record, worker.py → re-export shim, backends/{claude,codex}.py, mcp_stdio.py signals server, AGENTS.md house-rules injection, token→USD estimate) + PR #72 hotfix (**OpenAI strict-schema gotcha**: `--output-schema` 400s unless every object node has `additionalProperties:false` + full `required`; adapter now writes normalized `output_schema.codex.json`, optional fields → nullable — found because A/B round 1 failed 3 attempts at 0 turns). A/B validation PASSED: same gated spec, claude 39s/$0.31 vs codex(gpt-5.6-sol) 30s/$0.00 (plan quota; `codex_cost_per_mtoken` unset → $0 stamps, doesn't draw daily_usd_cap). Codex workers = leaves-only, no guard hook. Real-task A/B (PR-gated leaves) still to run before routing policy. Land #54 first (both touch reconcile/records).

**Gotcha (2026-08-18): `default_backend: codex` is now live in config.yaml —
ALWAYS pass `backend="claude"` for delegation/build-class tasks.** Observed
failure (t-0818-bf5d, mailroom build): codex worker "ok"-exits 3× at $0 in
~25 s each, produces nothing, gate fails on no-PR, task `failed` — no
error in codex.err/agent.err, so it looks like a silent no-op. Codex =
leaves-only line work.

**INCIDENT 2026-08-18 (~01:30, jarvis issue #8): default_backend codex broke
every PR-gated task.** config.yaml had `default_backend: codex` (issue #60
quota relief), but the codex sandbox can't write `.git` or reach GitHub →
workers COMPLETE the work then fail `pr_open` 3× (t-0818-2f91 website
[salvaged → dtch1997.github.io PR#6], t-0818-bf5d mailroom, t-0818-8c1d
flows). Daemon was also still running from `~/arsenal-old-clone`
(pre-cutover leftover). Mitigations: config → `default_backend: claude`
(codex = opt-in local-gated leaves), daemon restarted FROM THE MONOREPO
(`tmux new-session -d -s concierge 'cd ~/jarvis-monorepo/jarvis-tools &&
CONCIERGE_HOME=~/concierge-home uv run python -m concierge serve ...'` —
NB C-c in that pane kills the session, it's command-only), bf5d+8c1d
requeued on claude in same workspaces. **Permission policy (Daniel-approved
2026-08-18): codex workers get write-your-workspace and nothing else;
push/PR/upload = harness's job.** Fix BUILT: **PR jarvis#12 OPEN**
(t-0818-9e3b done, 123 tests green, +30 new): gate `local`+`publishable`
flags derived over AllOf/AnyOf; submit/delegate reject sandboxed backend
on non-local unpublishable gates; reconciler reroute backstop via
per-backend CAN_PUSH; **publish-pass** (`concierge/publish.py`) — codex
worker exits → local gate projection passes + branch has commits → daemon
pushes pool/<tid> + opens PR (idempotent, never force/main), records
`published:{...}`, re-checks full gate; codex loses env_file preseed
(backends.<name> config overrides); codex_cost_per_mtoken non-zero
default. MERGED 2026-08-18 (with PR #10; Daniel-approved), daemon
restarted on merged main, smoke-verified live: submit-time codex+PrMerged
rejection fires, gate locality composes, codex leaf w/ local gate runs
done with NON-ZERO cost stamp ($0.064 — cap accounting live), flows
example renders dashboard. Requeued mailroom task also finished (jarvis
PR #13, owner session's deliverable).

**Task DAGs via stagehand — BUILT 2026-08-18 (Daniel-requested), PR jarvis#10
OPEN (task t-0818-8c1d done on claude after codex requeue; 99 concierge +
128 stagehand tests green).** `concierge/flows.py`: `task_step(pool,
build_spec, *, flow_name, gate, output, ...)` → stagehand unit fn
(render-spec-from-upstream → submit → wait → typed ConciergeResult;
failed task raises → dependents skip). Nested concurrency bounds (Flow
semaphore over step awaits, pool seats over live workers; queued tasks
hold no seat → no deadlock). Durable resume via dedupe key
`stagehand:{flow}:{node}:attempt-{n}` on the task record, honored by
Pool.submit (reattach queued/running/blocked, reuse done); stagehand memo
layers on top. Retry = concierge strikes only by default; with_retry
opt-in (attempt in dedupe key). `after=` unchanged; PATTERNS.md documents
which-when. stagehand gains only generic `current_task_id()`. Runnable
gen→expand→map→reduce example + test_flows.py (chain/diamond/fan-out/
skip/restart-no-dup/real-Pool dedupe). MERGED 2026-08-18 with PR #12;
daemon restarted; example smoke-verified.

**BUG found+FIXED 2026-07-14 (arsenal PR #6, MERGED): `load_config` silently
returns `{}` when pyyaml isn't importable** (records.py — `except
ImportError: pass`), so a daemon started in a venv without yaml runs on
DEFAULTS (daily_usd_cap 50, not the config's 1000) and quietly holds queued
tasks at "$50 cap reached" while config.yaml says otherwise. Symptom:
tasks stuck `queued` + daemon.log cap lines that contradict config.yaml.
Fix at launch: `uv run --with pyyaml python -m concierge serve` (or install
pyyaml in the serving venv). Fixed: pyyaml declared dep, present-but-unreadable config raises, serve banner prints effective daily_usd_cap. NB the long-lived daemon picks the fix up on its next restart (running one uses --with pyyaml, behaves correctly). Also: `pool.wait` default
timeout is 3600s — pass `timeout=` explicitly for multi-hour workers.
