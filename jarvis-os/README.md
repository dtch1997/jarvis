# JARVIS

A personal **command center for high-throughput AI work**: many
autonomous work-threads — interactive sessions, concierge workers, arch2
research fleets, cloud GPU jobs — run concurrently, and this repo is the
durable state they flow through.

JARVIS has one user — currently [Daniel](https://github.com/dtch1997) —
and **the user's attention is the scarce resource the whole architecture
optimizes.** The agents (Claude Code sessions and the workers they
dispatch) draft, build, and merge; the user directs and vetoes. Every
design decision below traces back to that division of labor.

**JARVIS is the meta-level system, not the object-level work.** Its job
is to maintain the machinery that directs, dispatches, observes, and
reviews work — the work itself lives in dedicated repos (see [the
`repos/` pattern](#object-level-work-lives-elsewhere-the-repos-pattern)).
If a change makes one project better, it probably belongs in that
project's repo; if it makes *every future project* better, it belongs
here.

- Architecture (layers, desiderata, build order): [`docs/command-center.md`](docs/command-center.md)
- Agent operating rules: [`CLAUDE.md`](CLAUDE.md)
- Direction layer: [`goals/`](goals/) · Findings: [`wiki/`](wiki/) · History: [`changelog.md`](changelog.md)
- Operating philosophy: [`drafts/consumer-of-your-own-software.md`](drafts/consumer-of-your-own-software.md)
- Original vision (frozen 2026-06-10): [`DESIGN.md`](DESIGN.md)

## The layer model

Seven layers: a **core work loop** that moves work forward, and a
**support plane** that watches it, pages the user when it stalls, and
bounds its spend. The core four form a closed cycle: direction decides
against state, execution produces artifacts, review integrates them into
truth, which updates state and refeeds direction. When something feels
broken, locate the layer first — it tells you what kind of fix (tool,
policy, or attention) is missing.

**Core work loop:**

| # | Layer | Question | Where it lives |
|---|-------|----------|----------------|
| 1 | **Direction** | What *should* be worked on? | `goals/` (draft-and-veto) + `/goal-review` |
| 2 | **State** | What threads exist, in what status? | agent memory (`MEMORY.md` + stubs), `wiki/`, `threads` |
| 3 | **Execution** | How does work run? | concierge, stagehand, bellhop, arch2, sessions |
| 4 | **Review & integration** | How does work become truth? | PR lanes + gazette patch notes, wrap-up, lab-notes |

**Support plane:**

| # | Layer | Question | Where it lives |
|---|-------|----------|----------------|
| 5 | **Observability** | What is happening / has happened? | foyer, lobby hub, stagehand dashboards, databrowser |
| 6 | **Attention routing** | How does the system ask for the user? | flare (push) + desk (inbox), `BLOCKED-ON-DANIEL` markers, Slack |
| 7 | **Resources** | What's burning money, owned by whom? | pod-audit cron, concierge caps, bellhop TTLs |

Two operating modes cut across all seven: **copilot** (user present,
per-exchange trust) and **full-auto** (user absent, structural trust via
specs/gates/budgets). Current per-layer grades, pain points, and the
build order live in [`docs/command-center.md`](docs/command-center.md).

## Consumer mode: how changes land

The user does not review every PR — he reads **morning patch notes**
about what merged, and reverts + files issues when something regresses
(the full argument for this stance:
[`drafts/consumer-of-your-own-software.md`](drafts/consumer-of-your-own-software.md)).
Every PR is labeled with a trust lane at open time, and the nightly
`gazette` cron merges what the lane allows:

- **`lane:auto`** — docs, drafts, wiki, dashboards, goal appends: merged
  nightly on green checks.
- **`lane:delay`** — anything that shapes future agent behavior
  (CLAUDE.md, crons, tool behavior): merged after appearing in two
  morning patch-notes editions unless vetoed.
- **`lane:blocked`** — money, credentials, external-facing, destructive:
  never cron-merged; routed through the attention layer.

Guardrails are structural, not attentional: protected paths demote a
PR's lane regardless of its label, and irreversible actions block on the
user by mechanism — because by construction he isn't watching in real
time.

## How to get the most out of JARVIS

Opinionated notes from operating it, learned the hard way — written for
the user, and for anyone considering running something similar. The
theme: **you are the bottleneck — spend yourself on direction and veto,
never on authorship or supervision.**

1. **Pick a mode on purpose.** *Copilot* (you're present, steering,
   low-latency) and *full-auto* (spec it, gate it, leave) are different
   contracts. The failure mode is the blur: babysitting an autonomous task,
   or walking away from a half-specced one. If you'll check in within the
   hour, it's copilot; otherwise write the spec and gate, and go.
2. **State goals, not just tasks.** A task ends when the session ends; a
   goal file in `goals/` keeps generating proposals, frontier updates, and
   dispatchable work while you sleep. If you catch yourself typing the same
   intent twice, it's a goal — say it once and let an agent draft the file.
3. **Veto, don't author.** Agents draft everything — visions, rubrics,
   specs, reports — and drafts are immediately operative. Your editing time
   is worth 10× your writing time here: delete what's wrong, redirect what's
   off, one-word-approve what's right (`SG`). Never let anything sit waiting
   for you to write prose.
4. **Never let work block on your attention silently.** Anything waiting on
   you should be pushed to you (flare) or aggregated for you (desk), and
   most answers should cost one word: SG / merge / kill / park. A month of
   DRAFT-limbo on the direction layer is the cautionary tale.
5. **Buy autonomy with specs and gates, not trust.** Full-auto output
   quality = spec quality × gate quality. Gate on *results*, not artifacts
   (a PR can be a placeholder; `results.jsonl` with N rows can't). Budgets
   are hard caps, set at dispatch, never negotiated mid-run.
6. **Insist on wrap-up.** Work that isn't PR'd, memorized, and pointed-to
   from cloud storage does not exist — it evaporates when the session dies
   (worktrees full of orphaned prototypes are the fossil record). Type
   `wrap up`; it's the cheapest durable-state guarantee available.
7. **Read what it remembers.** Skimming `MEMORY.md` and the wiki weekly is
   the best window into whether the system's taste is drifting — and
   deleting one bad memory improves behavior the same day. Prune ruthlessly;
   stale state is worse than no state.
8. **Use the keywords.** `SG` (do all of it), `SOP` (default workflow),
   `wrap up` (make it durable), `park` (dump context, switch away). They
   exist so approval costs seconds (defined in [`CLAUDE.md`](CLAUDE.md)).
9. **One front door per need.** Live threads → foyer. Serving apps → the
   lobby hub URL. Direction → `goals/`. Results → databrowser links. Reports
   → cowrite (edit in browser; agents re-read on save). Don't accept
   scrollback or file paths as a deliverable.
10. **Feed the loop.** Corrections, 👍/👎, and "that was the wrong altitude"
    get memorized and compound; silent dissatisfaction doesn't. The system
    improves at the rate you complain precisely.

## Object-level work lives elsewhere: the `repos/` pattern

`repos/` is the workbench: gitignored clones of the dedicated repos where
object-level work actually lives, kept under one roof so any session can
reach every project from a single working directory. Jarvis commits only
**pointers** (a stub commit + memory entry per spin-out), never their code.
The recurring themes:

- **Incubate here, then spin out.** New work starts as a jarvis worktree.
  The moment it has its own identity — a name, an external audience or
  collaborator, CI, or a life beyond one sprint — it graduates to a
  dedicated repo cloned at `repos/<slug>`, and jarvis keeps the pointer.
  Spin-out is the *expected* fate of successful work, not an exception.
- **Tools are packages, not repos.** Every utility is a package in the
  repo-wide uv workspace: generic, standalone tools under
  `jarvis-tools/packages/` (historically "arsenal"), jarvis policy tools
  — code that must co-evolve with CLAUDE.md — under
  [`packages/`](packages/) here (`gazette`, `desk`, `threads`). The
  `repos/<tool>` paths are symlinks into jarvis-tools. One venv, one CI,
  one issue tracker.
- **Research projects get their own repos** (aligne, science-of-midtraining,
  dogfight-rl, …) — each self-contained and runnable without jarvis, so it
  can be shared, archived, or handed to a fleet independently.
- **Reference clones** of other people's code (upstream repos, starter kits)
  also land in `repos/` — read/reproduce material, never edited in place.
- **Publishing has one home**: `repos/lab-notes-jarvis` (notes + gated
  Pages site).
- **Bytes go to cloud storage (GCS)**, pointers get committed — no
  artifacts in any repo.

What jarvis itself keeps is exactly the meta-level: direction (`goals/`),
findings (`wiki/`), conventions (`CLAUDE.md`), history (`changelog.md`),
and pointers to everything else. (Early in-repo experiments lived in
`experiments/` before this pattern settled — removed 2026-08-15; recover
via git history if ever needed.)

## Repo map

| Path | What it is |
|------|-----------|
| `CLAUDE.md` | The agent contract: keywords, SOP, tool bindings, conventions |
| `docs/` | Design docs — [`command-center.md`](docs/command-center.md) (current), morning routine, threads, thought capture |
| `goals/` | Direction layer: one file per goal, draft-and-veto ownership |
| `wiki/` | LLM-maintained research wiki (durable findings) |
| `drafts/` | Working essays and philosophy notes (agent-drafted, user-edited) |
| `ops/` | Cron source of truth (`cron.tab`) + installers — the crontab is a build artifact |
| `repos/` | Gitignored clones of spun-out object-level repos (see above) |
| `changelog.md` | Append-only session/sync record, newest first |
| `personal/` | Personal notes (gitignored) |
