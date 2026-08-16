---
name: memory-consolidate
description: Consolidate session memories into the research wiki — persist durable findings into wiki/, compress memories already covered elsewhere into pointer stubs, archive stale ones. Use when asked to "consolidate memories" or on the weekly consolidation cron.
---

# memory-consolidate

Memory (`~/jarvis-memory/`, a git repo pushed to private dtch1997/jarvis-memory;
the old `~/.claude/projects/-mnt-nw-home-d-tan-jarvis/memory/` path is a
symlink to it) is the **working set**: operational pointers, open PRs, gotchas,
next steps. The wiki (`wiki/`, see `wiki/CLAUDE.md`) is the **canonical
findings layer** — but a *maintained* one, not an archive of everything ever
measured. This skill is the transfer process between them. Run it
periodically; it must be safe to run unattended.

## Procedure

1. **Worktree.** Wiki edits go via PR: `git fetch && git worktree add
   .claude/worktrees/memory-consolidate-<date> -b memory-consolidate-<date>
   origin/main`. Memory edits are applied directly to `~/jarvis-memory/` —
   but only after the classification pass is complete — then committed and
   pushed there (it's its own git repo; the nightly snapshot cron is a
   backstop, not the primary commit path).
2. **Read everything.** `MEMORY.md`, every memory file, `wiki/index.md` (and
   wiki pages a memory bears on).
3. **Classify each memory** into exactly one action:
   - **PERSIST** — contains durable knowledge (findings, verdicts, mechanisms,
     reusable gotchas) not yet in the wiki **and passes the relevance gate
     (below)**. Ingest per `wiki/CLAUDE.md`: if a
     canonical report exists, ingest the report and use the memory as a
     checklist of what it must cover; if not, the memory itself is the source
     (copy to `wiki/raw/` with provenance `session memory <name>, <date>`).
     Then compress the memory (next bullet).
   - **COMPRESS** — durable content now covered by wiki/lab-notes/repo. Rewrite
     the memory as a stub: keep the file and its `name:` (other memories'
     `[[links]]` must not break), one-line summary + link to the wiki page +
     **every still-operational fact** (open PRs, unmerged branches, env-var
     knobs, infra gotchas, next steps). Losing operational state is the failure
     mode — when unsure whether a line is operational, keep it.
   - **ARCHIVE** — stale, superseded, or no longer useful. Move the file to
     `memory/archive/` (never hard-delete) and remove its `MEMORY.md` line.
     Never archive: memories touched in the last 14 days, memories other
     active memories link to, or anything you're unsure about — flag those in
     the report instead.
   - **KEEP** — active/operational; leave untouched.
4. **Sync the index.** Update `MEMORY.md` lines to match the new state of
   every touched memory.
5. **Wiki side.** Commit, push, open a PR titled `wiki: memory consolidation
   <date>`; add ingest entries plus one `consolidate` entry to `wiki/log.md`.
6. **Report.** Summarize: counts per action, what was persisted where, what
   was archived and why, and anything flagged for the user to decide.

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

- Bias to inaction: a wrongly-kept memory costs a few tokens; a wrongly-lost
  operational fact costs a debugging session. Uncertain → KEEP + flag.
  (The relevance gate cuts the other way for *wiki promotion* only — skipping
  an ingest is cheap and reversible; the never-lose rule protects memory
  stubs, not wiki growth.)
- Epistemic status travels: a memory's hedges ("pilot", "not reproduced",
  "seed-0 misled") must survive into the wiki pages verbatim in spirit.
- Memories can *correct* the wiki (they often carry post-report nuance) —
  ingest is bidirectional reconciliation, not append-only.
- Check `memory/archive/` restores trivially: moving a file back + re-adding
  its index line fully un-forgets it. Mention this in the report the first
  time something is archived.
