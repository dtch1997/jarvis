# JARVIS

A **command center for high-throughput AI work**: many autonomous
work-threads — interactive sessions, concierge workers, arch2 fleets, pod
jobs — run concurrently, and this repo is the durable state they flow
through. Daniel's attention is the scarce resource the whole architecture
optimizes.

- Architecture (layers, desiderata, build order): [`docs/command-center.md`](docs/command-center.md)
- Agent operating rules: [`CLAUDE.md`](CLAUDE.md)
- Direction layer: [`goals/`](goals/) · Findings: [`wiki/`](wiki/) · History: [`changelog.md`](changelog.md)
- Original vision (frozen 2026-06-10): [`DESIGN.md`](DESIGN.md)

## How to get the most out of JARVIS

Opinionated, learned the hard way. The theme: **you are the bottleneck —
spend yourself on direction and veto, never on authorship or supervision.**

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
   you should be pushed to you (inbox/flare as they land), and most answers
   should cost one word: SG / merge / kill / park. A month of DRAFT-limbo on
   the direction layer is the cautionary tale.
5. **Buy autonomy with specs and gates, not trust.** Full-auto output
   quality = spec quality × gate quality. Gate on *results*, not artifacts
   (a PR can be a placeholder; `results.jsonl` with N rows can't). Budgets
   are hard caps, set at dispatch, never negotiated mid-run.
6. **Insist on wrap-up.** Work that isn't PR'd, memorized, and pointed-to
   from GCS does not exist — it evaporates when the session dies (worktrees
   full of orphaned prototypes are the fossil record). Type `wrap up`;
   it's the cheapest durable-state guarantee available.
7. **Read what it remembers.** Skimming `MEMORY.md` and the wiki weekly is
   the best window into whether the system's taste is drifting — and
   deleting one bad memory improves behavior the same day. Prune ruthlessly;
   stale state is worse than no state.
8. **Use the keywords.** `SG` (do all of it), `SOP` (default workflow),
   `wrap up` (make it durable). They exist so approval costs you seconds.
9. **One front door per need.** Live threads → foyer. Serving apps → the
   lobby hub URL. Direction → `goals/`. Results → databrowser links. Reports
   → cowrite (edit in browser; agents re-read on save). Don't accept
   scrollback or file paths as a deliverable.
10. **Feed the loop.** Corrections, 👍/👎, and "that was the wrong altitude"
    get memorized and compound; silent dissatisfaction doesn't. The system
    improves at the rate you complain precisely.

## Repo map

| Path | What it is |
|------|-----------|
| `CLAUDE.md` | The agent contract: keywords, SOP, tool bindings, conventions |
| `docs/command-center.md` | Current design doc — layer model, modes, pain, build order |
| `goals/` | Direction layer: one file per goal, draft-and-veto ownership |
| `wiki/` | LLM-maintained research wiki (durable findings) |
| `experiments/` | Self-contained experiment dirs (spec + code + results pointers) |
| `repos/` | Gitignored clones/symlinks of spun-out repos (arsenal, aligne, …) |
| `changelog.md` | Append-only session/sync record, newest first |
| `outbox/` | Slack-bound posts + receipts |
| `battery/`, `sources/`, `personal/` | Eval utilities, scan cursors, personal notes |
