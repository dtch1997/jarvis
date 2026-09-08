# 1.0 → 2.0 migration register

*2026-09-08 · evidence from the 60-day usage inventory (commits, spool files,
importer counts) taken 2026-09-05, just after the 2026-09-04 total automation
stop. This is the pruning ledger Daniel asked for: every 1.0 component, its
verdict, and why. Nothing is deleted by this document — deletions happen in
their own PRs, linked back here.*

## Verdicts

**KEEP — imported into 2.0 at birth (as callees, never daemons):**

| tool | why |
|---|---|
| flare | the one channel out; 360 flares logged, 25 packages depend on it; stdlib |
| bellhop | compute layer, proven (library-shaped, 11 commits in 60d) |
| statusline | harness-level, tiny, live in ~/.claude/settings.json |
| ~/jarvis-memory | the assistant's memory — kept, but owes a consolidation pass (below) |
| wiki/ | durable findings store; consolidation target |

**HOLD — stays in 1.0, importable on demand (needed twice = imported):**

| tool | note |
|---|---|
| stagehand | DAG engine; a keeper tick reaches for it when an experiment fans out |
| ferry | GCS push/pull; same |
| cowrite | copilot-mode report editing; used through 08-29, works as-is |
| lobby (+databrowser) | serving hub; only matters once something serves again |
| concierge | 196 tasks run, heavily iterated — but the keeper replaces its role in 2.0; its gate/verify ideas live on in `jarvis tick` |
| mailroom | thought capture is real (validated at 458 thoughts) but is not the 2.0 core loop; revisit after the prototype proves out |
| gazette | consumer-mode merge flow; revisit only if PR volume hurts again |
| desk / threads (jarvis-os packages) | fleet-scale attention/observability; 2.0's single-project legibility makes them redundant for now |

**RETIRE — no usage evidence, archive/delete in the sweep:**

| tool | evidence |
|---|---|
| jarvis-tools/{desk,gazette,threads} | empty shells, stale `__pycache__` only — delete outright |
| cairn | abandoned 2026-07-02, zero importers |
| foyer | spool frozen since 2026-07-23 despite active commits — built, not used |
| podcaster | zero importers, one experiment |
| reportly | zero importers, zero spool |
| arxivist | cache idle since 08-18, zero importers |
| curator | one gallery ever; revisit only from a real write-up need |
| flightdeck/marquee/cloudfs/foreman | already retired in 1.0 |

## The sweep (separate PRs, after the prototype lands)

1. Delete the three empty shells; move RETIRE packages to
   `jarvis-tools/attic/` (history preserved, workspace membership dropped).
2. Memory consolidation: the ~100-entry MEMORY.md index prunes hard — done
   projects become one-line tombstones, findings move to wiki/, stale stubs
   (verified against reality) get deleted. Target: an index a session
   actually reads.
3. `jarvis-os/docs/` command-center suite (thread-board, thread-launcher,
   thread-manager, background-thinking, interface-contract) marked
   superseded-by-jarvis2 in place.
4. Crons: 1.0's stay paused. Protective ones (habitat backup, memory
   snapshot, pod-audit) should come back regardless of 2.0 — flag to Daniel.
5. CLAUDE.md (jarvis-os) slims to match what is actually live once the
   sweep lands.
