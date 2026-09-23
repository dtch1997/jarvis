---
name: memory-consolidate
description: Consolidate session memories into the research wiki — persist durable findings into wiki/, merge overlapping memories, compress ones already covered elsewhere into pointer stubs, archive stale ones. Use when asked to "consolidate memories" or on the monthly consolidation cron.
---

# memory-consolidate

Memory (`~/jarvis-memory/`, a git repo pushed to private dtch1997/jarvis-memory;
`~/.claude/projects/-home-daniel-jarvis/memory/` is a symlink to it) is the
**working set**: operational pointers, open PRs, gotchas, next steps. The wiki
(`wiki/`, see `wiki/CLAUDE.md`) is the **canonical findings layer** — but a
*maintained* one, not an archive of everything ever measured. This skill is the
transfer process between them. It must be safe to run unattended.

## Cadence

**Monthly** (cron), or when any tripwire trips — whichever comes first:

- `MEMORY.md` over 20 KB (it loads into *every* session — this is the metric
  that actually matters)
- any single memory over 150 lines (see **Rewrite journals**, below)
- more than 130 live memories

Weekly was the old cadence and it was too fast: a model-judgment pass over 100+
files done every seven days goes shallow, and shallow passes append rather than
rewrite. Monthly with tripwires is the replacement.

**The sweep is the backstop, not the mechanism.** The session that closes a
thread should archive it *then*, while it still has the context. A monthly pass
re-deriving months later is strictly worse at it.

## Procedure

1. **Worktree.** Wiki edits go via PR: `git fetch && git worktree add
   .claude/worktrees/memory-consolidate-<date> -b memory-consolidate-<date>
   origin/main`. Memory edits are applied directly to `~/jarvis-memory/` —
   but only after the classification pass is complete — then committed and
   pushed there (it's its own git repo; the nightly snapshot cron is a
   backstop, not the primary commit path).
2. **Back up first.** Copy the memory dir to the scratchpad before the first
   write. Cheap, and it makes the whole pass trivially diffable afterwards.
3. **Read everything.** `MEMORY.md`, every memory file, `wiki/index.md` (and
   wiki pages a memory bears on).
4. **Sweep declared-dead memories** (mechanical, do this before the judgment
   pass). Every memory carries `status:` in its frontmatter — `active`,
   `blocked`, `closed`, or `superseded`. Everything `closed` or `superseded`
   is an ARCHIVE candidate; apply the never-archive rules below, then move it.
   Do **not** use file mtime as a staleness signal: the nightly snapshot cron
   commits in bulk, so timestamps cluster on cron dates and measure when the
   file was committed, not when the fact was last true. If a memory's prose
   says RETIRED/DONE/STUB but `status:` says otherwise, fix `status:` — the
   field is the signal, the prose is commentary.
5. **Classify each remaining memory** into exactly one action:
   - **PERSIST** — contains durable knowledge (findings, verdicts, mechanisms,
     reusable gotchas) not yet in the wiki **and passes the relevance gate
     (below)**. Ingest per `wiki/CLAUDE.md`: if a canonical report exists,
     ingest the report and use the memory as a checklist of what it must cover;
     if not, the memory itself is the source (copy to `wiki/raw/` with
     provenance `session memory <name>, <date>`). Then compress the memory.
   - **MERGE** — two or more memories cover one family (an experiment line, a
     tool and its follow-ups, a cluster of related findings). Write **one** new
     memory that keeps each original's verdict, its still-operational facts and
     its reusable gotchas; archive the originals; replace their index lines with
     one. Per-file classification cannot see cross-file redundancy, so look for
     it deliberately: sort the index by section and re-read any group of 3+
     memories sharing a repo, a substrate or a research question. A merge that
     drops an open PR, an unmerged branch or a gotcha is a failed merge — carry
     them all over, then cut narrative.
   - **COMPRESS** — durable content now covered by wiki/lab-notes/repo. Rewrite
     the memory as a stub: keep the file and its `name:` (other memories'
     `[[links]]` must not break), one-line summary + link to the wiki page +
     **every still-operational fact** (open PRs, unmerged branches, env-var
     knobs, infra gotchas, next steps). Losing operational state is the failure
     mode — when unsure whether a line is operational, keep it.
   - **ARCHIVE** — stale, superseded, or no longer useful. Move the file to
     `memory/archive/` (never hard-delete) and remove its `MEMORY.md` line.
     Never archive: memories touched in the last 14 days, memories other
     *active* memories link to, or anything you're unsure about — flag those in
     the report instead.
   - **KEEP** — active/operational; leave untouched.
6. **Rewrite journals.** A memory over ~150 lines has stopped being a memory and
   become an append-only session log — the format is one fact per file, and
   nothing enforces it at write time. Split it: a compact current-state memory
   at the original `name:` (what it is, where the source of truth lives, durable
   findings, live gates, gotchas) plus the full log moved to
   `archive/<name>-log.md`. Harvest the durable findings *before* cutting —
   these files bury real results (a reversed headline, a retracted null) in
   hundreds of lines of status churn. This is the one place the bias-to-inaction
   guardrail does not apply: left alone, these files only grow.
7. **Sync the index.** Rewrite `MEMORY.md` lines to match the new state of every
   touched memory. Keep it under 200 lines and 20 KB, one line per memory, under
   ~150 chars. Group by what a session needs first: how Daniel wants work done,
   then what's blocked on him, then active work, then tools.
8. **Wiki side.** Commit, push, open a PR titled `wiki: memory consolidation
   <date>`; add ingest entries plus one `consolidate` entry to `wiki/log.md`.
9. **Verify before reporting.** Assert mechanically: every live memory appears
   in `MEMORY.md`; every `MEMORY.md` link resolves to a file that exists; no
   file from the pre-pass backup is missing from both the live dir and
   `archive/`. Report the numbers.
10. **Report.** Counts per action, what was persisted where, what was merged into
    what, what was archived and why, and anything flagged for the user to decide.

## Relevance gate (staleness discounts ingestion — Daniel, 2026-08-16)

Every wiki page carries a standing maintenance cost (curation, index, tension
tracking), so promotion to the wiki must be earned by *expected future
reference*, not by the finding merely being true and unrecorded. Persist only
when at least one holds:

- the finding feeds an **active** goal, program, or testbed (check `goals/`
  and the memory's own status line);
- it's a **recurring method or gotcha** other work will hit again;
- other wiki pages or active threads **already reference or contradict** it
  (tensions must be recorded).

Otherwise — a one-off experiment from a closed or dormant thread, however
sound — leave it as a memory stub or ARCHIVE it; git history and the stub
preserve it at zero maintenance cost, and it can be ingested later *if* the
topic reactivates. Apply the same discount to any **ingest queue** inherited
from prior runs: queue entries are candidates that expire, not debt to pay
down — re-judge each against this gate at every run, and drop expired ones
with a one-line note in the report.

## Guardrails

- **Never append this pass's exhaust to a memory.** Superseded index lines,
  run logs, "previous version of this line" blocks — none of it goes in the
  files. The 2026-08-15 run appended each old index line into the file it came
  from; by 2026-09-23 that had compounded to ~25 KB of dead text across 60
  files. A consolidation pass rewrites in place and leaves its narrative in the
  report and in git history, which already hold it.
- Bias to inaction: a wrongly-kept memory costs a few tokens; a wrongly-lost
  operational fact costs a debugging session. Uncertain → KEEP + flag.
  (The relevance gate cuts the other way for *wiki promotion* only — skipping
  an ingest is cheap and reversible; the never-lose rule protects memory
  stubs, not wiki growth. **Rewrite journals** is the other exception.)
- Epistemic status travels: a memory's hedges ("pilot", "not reproduced",
  "seed-0 misled") must survive into the wiki pages verbatim in spirit.
- Memories can *correct* the wiki (they often carry post-report nuance) —
  ingest is bidirectional reconciliation, not append-only.
- Check `memory/archive/` restores trivially: moving a file back + re-adding
  its index line fully un-forgets it. Mention this in the report the first
  time something is archived.
- A `[[link]]` with no top-level file resolves to `archive/<name>.md`. That is
  expected after an archive pass and is not a broken link — do not "fix" these
  by resurrecting files.

## Known gap

Most `type: project` memories are mostly *status* (open PRs, next steps, budget
gates) — re-derivable from GitHub and the highest-churn content in the system,
so it's what goes stale first. Memory absorbs this because there is no tracker;
jarvis2 `projects/` is the natural home. **Not yet decided by Daniel** (raised
2026-09-23) — until it is, keep carrying status here and don't unilaterally
move it out.
