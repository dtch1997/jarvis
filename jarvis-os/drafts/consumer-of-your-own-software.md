# Be a consumer of your own software

*Working draft — Daniel + Claude, 2026-08-18. Origin: quick note on how
working with AI changes the developer's relationship to their own codebase.
Relevant: jarvis "PR lanes — consumer mode (gazette)",
[[bottom-up-direction-philosophy]].*

## TL;DR

Increasingly, working with AI means viewing yourself as a **consumer** of the
software you develop, not its developer. The premise is close to obvious by
now — vibe coding is widely accepted as a valuable practice, which is exactly
this stance applied one session at a time. The interesting part is the
**implications**, which are not obvious and mostly unexplored: empower agents
to open issues, write PRs, and engineer their own loops; design for legible
*behavior* rather than legible *implementation*; and pick an involvement level
you can actually sustain. Mine, currently, is **reading patch notes every
morning** — and if I dislike something, I revert to yesterday's version and
open issues. Revert-plus-issue is the consumer's whole interface, and it's
enough.

## The claim

The traditional identity of a developer is someone who holds the system in
their head: they know why each module exists, what each function does, what
would break if you touched it. AI-heavy development erodes that identity fast —
not because you *couldn't* read everything the agents write, but because
reading it all stops being the best use of your attention. The code volume
scales with agent throughput; your reading doesn't.

The stable identity on the other side is *consumer*. You know what the software
is **for**, whether it **works for you today**, and what you **wish were
different**. That's the same epistemic position you're in with any commercial
product you rely on, and it's a perfectly workable one — billions of people
successfully use software they've never read. The unusual part is applying that
stance to software that is nominally "yours."

The key relaxation: **you don't need to know how it works so long as the use
case is clear.** Clarity of use case — not comprehension of implementation —
is the thing the human must keep supplying. If I can say precisely what "works"
means, agents can own everything between that statement and the running system.

None of this is a radical claim anymore — anyone who vibe-codes has already
accepted it locally, for one script or one afternoon. The unexplored part is
taking the stance *seriously as a design constraint*: if you'll durably be the
consumer, your whole development setup should be architected for a consumer,
and almost none of our defaults (code review, repo layout, "read the diff")
are.

## What this implies for how you develop

If you're the consumer, the development process should look like a product
team serving you, and you should build it that way:

- **Empower agents to open issues.** A consumer's most valuable output is a
  bug report or feature request. But agents notice far more friction than I
  do — so they should file issues too, on sight, without asking. The issue
  tracker becomes the shared backlog between me-as-consumer and
  agents-as-team.
- **Empower agents to write PRs** — and to merge the routine ones without
  you. If every change waits on your review, you're still the developer with
  extra steps. Lanes with different trust levels (auto-merge for docs and
  drafts, a veto window for behavior-shaping changes, hard block for money and
  credentials) let review effort concentrate where it matters.
- **Empower agents to engineer loops.** The consumer doesn't run the release
  process; crons, sweeps, gates, and monitors are the team's job. If a
  recurring activity requires me to remember to trigger it, it isn't finished
  being built.
- **Legibility budget goes to behavior, not implementation** — expanded in
  the next section, because it's the least obvious of the four.

## Designing for legible behavior

"Legible implementation" is what traditional engineering culture optimizes:
clean abstractions, readable diffs, architecture docs — all aimed at a human
who will read the code. If no human reads the code, that effort is aimed at
nobody. The consumer stance redirects it: **spend the legibility budget on the
surfaces the consumer actually touches.** Concretely:

- **Every change should be describable as a behavior delta.** "What changed
  for you" — a new command, a fixed annoyance, a different default — not
  "refactored X to use Y." If a change *can't* be described that way, that's
  signal: it's either invisible plumbing (fine, but it goes in a quieter lane
  and earns no attention) or it's a behavior change nobody can articulate,
  which is exactly the kind of change a consumer should be nervous about.
- **The spec lives in observable contracts, not in your head or the code.**
  Tests, evals, and gates written in use-case terms ("this report lints",
  "the digest arrives by 8am", "results.jsonl has ≥N rows") are the
  consumer's requirements doc. "Done" is defined by external checks passing,
  never by an agent's self-report — because the consumer, by construction,
  won't verify by reading.
- **"Does it work today?" must be cheap to answer.** Status pages, smoke
  tests, canaries, dashboards. A consumer's relationship to software is
  mediated entirely by its observable state; if observing that state takes
  effort, the stance collapses back into spelunking.
- **Rollback is a product feature, not an ops procedure.** Versioned,
  dated, small increments whose revert is routine. The consumer's power
  comes from exit being cheap.
- **Implementation legibility doesn't go to zero — its audience changes.**
  Code quality, comments, and docs now serve the *next agent* that has to
  modify the system. That's still worth real investment (agents work better
  in clean codebases), but it's a different budget line, with a different
  reader, and I shouldn't confuse polishing it with keeping *myself*
  informed.

## Patch notes as the involvement dial

Involvement in the development process is a dial, from "review every PR" down
to "notice when something breaks." Most discussion of AI-assisted development
implicitly assumes the top of that dial — you're in the loop per-change,
approving diffs. The trick worth surfacing is that there are *stable
intermediate settings*, and the one I've landed on is **reading patch notes
every morning**: a daily digest of what merged and why, written for the
consumer, not the committer.

What makes this setting stable is that it's paired with a cheap escape hatch:
if I dislike something, I **revert to the previous day's version and open
issues**. That pair — daily digest in, revert-plus-issue out — is a complete
control loop:

- It's *low-attention*: minutes a day, at a time I choose, no interrupts.
- It's *safe*: any single day's changes are disposable. Reverting is not an
  emergency, it's a routine consumer action, like rolling back an app update.
- It's *corrective*: the issues I file after a revert are the highest-signal
  direction the system gets, because they're grounded in an actual felt
  regression rather than speculative review comments.

Two further things make the trick better than it first looks:

- **Patch notes are a forcing function, not just a report.** Requiring every
  merged change to appear in the digest, described in consumer terms, *is*
  the "legible behavior delta" discipline from the previous section — the
  digest is where illegible changes become visible as anomalies. The
  reporting format shapes the development it reports on.
- **The dial generalizes as a triple**: a *cadence* (how often you look), a
  *rollback unit* (what one revert undoes), and a *feedback channel* (how
  dislike becomes direction). Morning / one-day-of-merges / GitHub-issues is
  my current triple; a team could run weekly / one-release / user-forum. The
  point is to choose all three deliberately and make them match — a daily
  digest with monthly-granularity rollback isn't a control loop, it's a
  newsletter.

Notably, this is the same relationship a user has with any actively-developed
product — release notes, rollback, feedback — except that here the "company"
is a fleet of agents whose roadmap I set. Consumer-grade involvement,
owner-grade control.

## Caveats

- The stance is load-bearing only if the **guardrails are structural**, not
  attentional: irreversible or external-facing actions (money, credentials,
  publishing) must be blocked by mechanism, because by construction I'm not
  watching in real time.
- "Use case is clear" is doing a lot of work. Where I can't yet articulate
  what "works" means, I'm still the developer, and pretending otherwise just
  produces confident software for the wrong problem. The dial setting is
  per-domain, not global.
- Daily-granularity revert assumes changes land in small, separable daily
  increments. Big-bang migrations break the escape hatch and need to be
  handled at a higher-involvement setting.
