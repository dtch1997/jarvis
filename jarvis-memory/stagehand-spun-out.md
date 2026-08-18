---
name: stagehand-spun-out
description: stagehand — reusable orchestration+monitoring primitives spun out to dtch1997/stagehand (moved from ArcadiaImpact 2026-06-25); gitignored clone at repos/stagehand
metadata: 
  node_type: memory
  type: project
  originSessionId: 0dda629a-d854-41f3-902f-bb07d2f4535b
---

Reusable experiment orchestration + monitoring harness, extracted 2026-06-21 from
the negation-neglect sweep driver. Originally spun out to ArcadiaImpact/stagehand
(2026-06-21, public); **MOVED via GitHub repo-transfer to dtch1997/stagehand on
2026-06-25** (old org name now redirects). PUBLIC; one-page site formerly at
https://arcadiaimpact.github.io/stagehand/ served from main `/docs` via GitHub
Pages (Pages URL will follow the new owner → https://dtch1997.github.io/stagehand/),
gitignored clone at `repos/stagehand` (remote repointed to dtch1997) — same pattern as
[[aligne-spun-out-to-own-repo]] and [[open-tinker-infra]]. NOT in the jarvis
tracked tree (`repos/` is wholesale-gitignored; there is no jarvis.config.yaml —
that .gitignore line is aspirational). **MIT licensed** (© Arcadia Impact). The
site's hero has a vanilla-JS animated dashboard sim (scripted sweep: cells run, one
fails its gate red, evals spawn, manifest resolves) — a fixed-size pane so rows fill
without reflow. A design-philosophy **blogpost** (reliability + visibility; agent-
orchestrator vs dynamic-workflows vs stagehand) was written and PUBLISHED 2026-06-21
(handed off via ~/gladys → Google Doc). Verified fact for that post: the 10-min cap
is on *foreground Bash commands* (`BASH_MAX_TIMEOUT_MS`, 600k ms), NOT on Claude Code
dynamic workflows (those have no documented wall-clock limit).

**MAJOR REFACTOR 2026-06-30 (v1.x): the `stage`/`gate` staircase is GONE.** stagehand
is now a **declarative DAG engine** — "orchestrate steps at scale, with live
monitoring." A step is any async fn; sweeps are one use, agent fleets / data
pipelines / eval harnesses are others. Core still pure-stdlib (zero pip deps).
Shipped across PRs #4–#7: v1.0.0 = engine+DSL (#5), then types/check (#6), then
agent steps + reframed README v1.1.0 (#7). Import package `stagehand`; layers:
- `monitor` — file-backed running/done/failed + done/total ticker per unit; units
  link via `parent` into a tree (unchanged). NEW `current_monitor()` (contextvar)
  lets a running step push its own live progress to the dashboard.
- `dashboard` — render the tree to one auto-refreshing HTML page (`title`+`note_fn`
  injectable). `serve(dir)->(url,stop)` = http.server + `cloudflared` tunnel
  (external binary, call-time only; devbox has no DNS to the tunnel host → fetch
  from a browser, not the box).
- `engine` (module `engine.py`, class `Flow`) — dynamic per-task DAG scheduler.
  Declare with `Flow.map`/`filter`/`reduce`(the only barrier)/`expand`(dynamic
  fan-out)/`add`(raw); `await flow.run(stop_when=, check=)`. Streams between steps
  (no barriers except reduce), skips a failed task's dependents w/o aborting.
  `best_of`/`with_retry` are node fn-policies (fan-out / retry-with-feedback).
- ~~`dsl`~~ **REMOVED in v2.0.0 (PR #25, 2026-07-05)** — the `with flow(...)` +
  `do`/`fanout`/`retry`/`each`/`run`/`current` ambient-contextvar surface is GONE
  (couldn't express filter/expand; imperative look invited `if`-on-handle bugs).
  The engine form is the one API; `Flow.spawn(fn, args, kwargs, name=, after=)`
  is the public single-task primitive (handle args become deps; policies via
  `flow.spawn(best_of(fn,…), (unit,), type_fn=fn)`). `agent()` now takes the flow
  explicitly: `agent(flow, prompt, …)`. Result-dependent branching still goes
  *inside* a step (raise to prune) — can't `if` on a handle while building.
- types/`check()` — `Handle[T]` generic; steps carry types via plain hints;
  `flow.check()` / `run(check=True)` verifies deps exist, no cycles, edges type-
  compatible BEFORE running. Gradual+pragmatic linter (unannotated==Any).
- `agents` — coding agents as steps: `agent(prompt,*inputs,isolation=,backend=)`
  -> `Handle[AgentOutcome]` ({ok,summary,diff,cost,tokens,session_id,raw}).
  Backend SEAM (core stays stdlib): `subprocess_backend` (default, zero-dep
  `claude -p --output-format json`) + `flightdeck_backend()` (recommended, LAZY-
  imports [[flightdeck]]'s AgentRun, streams to dashboard — loose coupling, not a
  hard dep); `set_default_backend()`. `isolation="worktree"` runs in a throwaway
  git worktree + captures diff. Composes: `fanout`=best-of-N agents, `retry`=
  retry-with-feedback.
- `pipeline` — `live_dashboard` (async ctx polling the tree → status.html) +
  `headless_handoff` (`claude -p` tail).

Examples (faked compute, run anywhere): `sweep.py` (engine), `fanout_retry.py`
(policies+expand), `agent_fleet.py` (agent fleet), `serve.py`, `artifacts.py`.
73 unit tests. **STALE after refactor:** the Pages docs-site (`docs/index.html`)
still shows the #5 engine/DSL model — needs an agents+check deep-update (follow-up).
The jarvis CLAUDE.md SOP line 3 still says "pipeline staircase" — also needs updating.

Follow-up not yet done: refactor negation-neglect-distillation to consume stagehand
(swap its monitor.py + run_sweep dashboard/orchestration for imports) — deferred to
avoid churn on a repo with a run in flight.

**Issue tracking: cairn** (migrated FROM Beads 2026-07-02, stagehand PR #23 —
`bd export` → `cairn import`, ids preserved, `.cairn/` now COMMITTED in-repo,
prefix `stg`, local `.beads/` deleted; see [[cairn-tool]]). First epic
`stg-teu` = bake the experiment design principles (jarvis PR #98) into stagehand.
MERGED to main 2026-07-02: `.1` auto run-manifest (PR #19, v1.5.0 — `Flow.run()`
writes runs_dir/manifest.json with git sha/dirty/argv/config via `Flow(config=…)`;
`ArtifactStore.put()` stamps `meta["git"]`) and `.2` content-keyed step memoization
(PR #20, v1.6.0 — `Flow(memo=dir)` replays successful results keyed on
md5(fn source w/ closure recursion + static inputs + upstream result VALUES);
`run(refresh=True)` resamples; `cache=False` per node; JSON-only results;
miss-never-wrong-hit; gotcha: lambda fingerprint = its call-site line, so moved
lambdas re-run). `.3` smoke: engine mode (PR #21) was REVERTED same day (PR #22,
v1.8.0) per [[config-first-workflow-knobs]] — cheap-first = ship a smoke config
(config.yaml + *_smoke.yaml) next to the real one; memo segregation automatic
since config values ride into step inputs; README documents the pattern. `.4`
pilot MERGED: sdf-hallucination PR #5 (scripts/refclass_flow.py + configs/
refclass{,_smoke}.yaml, sample→judge→agg→figs as one Flow; validated live —
identical re-run = zero API calls, replay works keyless in ~7s). Epic remaining:
only stg-teu.5 (cookbook docs). Principles doc + adherence review = jarvis PR
#98 (MERGED, docs/experiment-design-principles.md + docs/reviews/).
Memoization usage rules from the pilot (also filed as stg-teu.5 docs task):
step-affecting values must travel through step INPUTS (module constants/closure
values don't enter keys); side-effect steps (figures) go post-run, not in the
memoized DAG.

**2026-07-10:** moved into [[arsenal-monorepo]] as `packages/stagehand` (history preserved); `repos/stagehand` is now a symlink into `repos/arsenal`; dtch1997/stagehand ARCHIVED with a pointer note.

**2026-07-14 monitor redesign (arsenal PR #9 MERGED): monitors watch loops, not
steps.** Trigger: clients kept using the ticker as a step status flag
(`monitor(total=1)` + `set(status=…)` + one final `update()` — e.g. sci-mt
depth_suite run_grid.py) or skipped instrumenting subprocess training loops
entirely, so dashboards showed no granular progress. New surface: `track(iterable,
name)` tqdm-shaped wrapper (total from len, tick/iteration, `t.set(loss=…)`
ride-along fields; early break/exception → `failed` + "stopped early");
auto-nesting (`monitor`/`track` opened inside an open monitor auto-parents +
writes alongside; `current_monitor` MOVED to monitor.py, engine re-exports);
`monitor_env()` → `STAGEHAND_MONITOR_DIR`/`_PARENT` env linkage so a training
subprocess's bare `track()` nests under the calling task (parent passes
`env={**os.environ, **monitor_env()}`). Guardrails: total=1+status extra logs a
warning; dashboard renders total=1 tickers as "–" and status table now recurses
(was node→task only — deeper monitors used to be invisible). Convention line
added to jarvis CLAUDE.md SOP step 3 (PR #109) + concierge HOUSE_RULES.
Reference consumer DONE 2026-07-17, then REDESIGNED same day on Daniel's
feedback (file-tailing watches a cookbook-managed artifact = fragile
coupling): sci-mt PR #205 (metrics.jsonl follower) superseded by the
push-based chain — aligne v0.5.0 PR #37 `metrics_tap` (wraps the cookbook's
one reporting seam, ml_log.setup_logging → log_metrics(metrics, step)/batch;
prompted-teacher scoped-patch idiom, one tapped run/process) + `on_metrics=`
kwarg on run_reverse_kl/run_forward_kl; sci-mt PR #207 `step_monitor` (sync
CM yielding an on_metrics callback; yields None without stagehand+linkage =
aligne's no-op; aligne pin → v0.5.0). risk-averse run.py passes
`monitor_child_env()` (= `monitor_env()` + sibling stagehand on PYTHONPATH)
to the distill subprocess. Lesson: expose a push callback at the library
boundary you own; don't tail another library's artifact files. Remaining
follow-up: scimt.train.train (doc-SFT) can adopt step_monitor via
run_sft+on_metrics (metrics_tap composes; run_sft doesn't thread it yet).
