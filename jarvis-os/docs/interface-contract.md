# The interface contract — Daniel's surfaces and what each one guarantees

*2026-08-18 · distilled from CLAUDE.md + docs/command-center.md +
docs/morning-routine.md during the command-map session; interactive version
lives in the (private) command-map artifact. This is the user-facing view of
the system: five surfaces Daniel touches, and the guarantee each owes him.
Agents changing any mechanism below (crons, lanes, desk sources, mailroom
routing) should update the corresponding guarantee here in the same PR —
a guarantee this file states but the system no longer keeps is a bug worth
an issue.*

**The whole contract in one line:** read one Slack channel + one desk page ·
veto two queues, lazily · write into three capture silos · everything else
runs without you.

---

## 1. Capture surfaces — WRITE (Todoist · voice memos · #lab-notes-daniel)

**You do:** dump thoughts with zero ceremony. Never file, tag, or route them
yourself — routing is mailroom's job.

| When | What happens |
|---|---|
| on drain | mailroom ingests → triages → routes onto an *existing* spine: a thread note, a Todoist project, a goal file, or the papers queue (voice memos transcribe via Parakeet first) |
| at source | loop-closure mark where you wrote it — the Todoist task completes/moves, the Slack message is marked — your receipt that it was picked up |
| daily | one digest of what was routed where; the digest is your veto surface, silence approves |
| if urgent | deadline-bearing captures escalate immediately: desk item + flare, instead of waiting for the digest |

**Promise:** nothing you capture is silently dropped — it routes, escalates,
or appears in the digest, and the mark at source is your receipt.

**Caveat:** the drain cron isn't installed until mailroom's PR merges
(lane:blocked); until then drains are manual runs. Validated at 458
thoughts, 95% routed, 0 Todoist completions lost.

## 2. Slack #jarvis-dev — READ

**You do:** skim one channel, once a morning. Act only when paged.

| When | What arrives |
|---|---|
| 08:05 daily | the morning edition: what merged overnight, what enters/leaves the veto window, anomalies — a quiet day says "nothing needs you" explicitly |
| seconds | any flare from any agent (sessions, workers, pod scripts, crons): `info` = FYI · `warn` = look today · `page` = now |
| always | every flare also spools to `~/.flare/log.jsonl` — a Slack outage delays, never loses |

**Promise:** this channel is the knowing. If it isn't here, the system
doesn't need you; you never sweep dashboards.

**Caveat:** noise thresholds still tuning (2026-08-18 flood → batched
flares, no desk echo).

## 3. desk — READ

**You do:** open it when a flare points there. Never poll it.

| When | What it guarantees |
|---|---|
| ≤ 1 h | anything newly blocked on you appears (sync at :07 hourly) — and pushes as a flare, so desk finds you first |
| always | sweeps all four formerly-disjoint queues: blocked/failed pool tasks, open-PR ages, `BLOCKED-ON-DANIEL:` markers, recent flares |
| on unblock | agents remove the marker; items leave without you touching the page |

**Promise:** if it's not on desk, nothing is waiting on you — one page
defines "blocked on Daniel" for the whole system.

**Caveat:** the marker is a convention, not a hook; an agent that forgets to
write `BLOCKED-ON-DANIEL:` can still stall silently.

## 4. goals/ — EDIT · VETO

**You do:** edit or delete goal files whenever you feel like it. Nothing
schedules you.

| When | What it guarantees |
|---|---|
| never blocks | agents draft everything (Vision, rubrics, candidate goals), marked `agent-drafted`; drafts are operative immediately |
| your edit wins | a section you touch becomes Daniel-owned; agents propose diffs only |
| only 2 waits | `automation: dispatch` flips and real budgets are the only calls that ever wait for you |
| on review | `/goal-review` is propose-only: proposals arrive as a review doc + PR, never as dispatched work |

**Promise:** your authority is cheap lazy veto — delete or rework what you
dislike — never a prerequisite anything waits on.

## 5. PR queue — REVIEW · VETO

**You do:** read patch notes; veto what you dislike; deep-review only
lane:blocked.

| Lane | Guarantee |
|---|---|
| lane:auto | merges 03:29 on green, deployed by 04:10, reported at 08:05 — zero action needed |
| lane:delay | holds for **2 morning editions you actually received** (skipped mornings pause the clock); veto = `veto` label or changes-requested review |
| lane:blocked | never merges without you — money, credentials, external-facing, destructive; surfaces on desk + flare and waits |
| backstop | mislabels demote automatically (protected paths → delay, credential-like → blocked) and show in patch notes as anomalies |

**Promise:** nothing behavior-shaping or money-spending merges past you
faster than two mornings you were present for.

**Caveat:** review throughput is the documented 🔴 bottleneck — lanes shrink
what needs you; they don't review for you.

---

## The floor — system-wide guarantees under every surface

| Guarantee | Meaning |
|---|---|
| push, not poll | you are paged; you never ask "status?" of a session, worker, or the system |
| durable | all state is markdown in git; the 03:41 nightly snapshot commits memory even if every session forgot |
| escape hatch | any agent, script, or cron can flare — anything blocked can always reach you |
| observed truth | "done" is externally checked (gates, transcripts, git), never a worker's self-report |
| degrades safely | daemon death doesn't kill workers; flares spool through Slack outages; ephemeral views are regenerable |
