# My head is for having ideas

*Working draft — Daniel + Claude, 2026-08-19. Piece (i) of the
prototype-showcase writing: the design philosophy behind JARVIS and what
it should enable for me. Companion pieces: (ii) a walkthrough of what we
built, (iii) where it goes next. Public teaser posted to #lab-notes-daniel
2026-08-19. Related: [[consumer-of-your-own-software]],
`docs/command-center.md`.*

## TL;DR

The problem JARVIS solves, stated from the demand side: **I have a high
volume of ideas I think are valuable to act on — more than I could ever
execute personally — and AI lets me multiply my throughput of
intellectual work by running many work-threads in parallel.** But I want
to pursue that throughput while cultivating what David Allen calls "mind
like water": my own attention staying *sequential*, one thing at a time,
with minimal context switching.

So the architecture has one job. **JARVIS is an adapter that makes a
parallel fleet consumable by a sequential mind** — it does the
high-volume parallelizable work while requiring only single-threaded,
sequential input from me. My actions become spinning up threads, mostly
fire-and-forget, and getting deliverables back later. This is possible
because most of the volume between an idea and its realization is
glorified bookkeeping.

The adapter needs exactly two mechanisms, and the whole system is those
two mechanisms over and over:

1. **Closed loops.** Closing a loop means minimizing the time between *I
   have a thought* and *I've acted on it in a way that assures a
   deliverable*. It's fine if actual completion takes days — as long as
   I'm assured I'll be notified of success (deliverable attached) or
   notified of an error. **No silent failures.** That assurance must be
   structural — externally-checked gates, termination contracts,
   blocked-work sweeps — never an agent's self-report.
2. **Programmed attention.** I decide *in policy, in advance* what may
   interrupt me and when the rest gets spent. Decisions arrive
   pre-chewed into veto shape — object-or-don't, with a default —
   instead of compose-an-answer shape. The residue of my attention is
   all direction and review: the having-ideas part.

## More ideas than hands

The starting point isn't a productivity pathology; it's a surplus. On
any given week I have more thoughts worth acting on — experiments worth
running, posts worth writing, tools worth building — than I could
personally execute in a year. Historically that surplus just decayed:
ideas went un-acted-on, or into a note I'd never revisit, or into the
worst place of all, my working memory, where they nagged.

AI changes the execution side completely. Agents can write the code, run
the sweeps, draft the reports — and crucially they can do it *in
parallel*, dozens of threads at once. The throughput ceiling on my
intellectual output stops being execution capacity.

But it doesn't become infinite. The constraint that survives is my
attention — and not just its *quantity* but its *shape*. Which is where
the naive version of this goes wrong.

## The tension I couldn't resolve by discipline

I wrote the problem down before I had the solution. Orchestrating a
fleet of AI agents demands "a high-bandwidth, multi-threaded, parallel
mode" — constant context-loading, monitoring, switching. Deep thinking
demands the opposite: "a low-bandwidth, single-threaded, highly
sequential mode." The two are not just different; the first is
*inimical* to the second. Every check-in on a running agent is a
self-interruption, and the orchestration mindset — many shallow threads,
always partially attending — is precisely the mindset deep work cannot
survive.

Note that this is a claim about the *shape* of attention, not its
amount. You can spend very little total time on your fleet and still
lose, if that time arrives as twenty fragments that each force a context
switch; and you can spend a whole morning on one hard problem and be
fine. "Minimize attention spent" was never quite the right objective —
"keep my attention sequential" is.

My first fix was time-slicing: mornings for deep thinking while fresh,
afternoons for AI-assisted work once the deep-work budget is spent. That
is a truce, not a solution — orchestration expands to fill whatever you
give it, and a morning "just checking one agent" is how the truce dies.
The same shortform floated the real answer almost as an aside: successful
companies solve this with *specialization* — someone whose entire job is
the multi-threaded mode, so that others can stay single-threaded.

JARVIS is that specialist. Not an assistant that helps me do tasks — a
**command center** that holds the parallelism, so my mind doesn't have
to. The many-threaded mode still exists; it just runs in software instead
of in my head. Seen this way, every user-facing surface in the system is
a **serialization point** — a place where parallel work gets converted
into something a sequential mind can consume: the morning digest
*batches* (everything that merged overnight, read at one sitting), the
waiting-on-me inbox *queues* (one list, not N dashboards), and
veto-shaped decisions *bound each item* (object or don't, then move on).
The adapter metaphor isn't decoration; it's a checklist you can hold the
architecture to.

## Everything else is bookkeeping

The premise deserves stating baldly, because it's doing two different
jobs. My comparative advantage — arguably my only one, in a world where
agents write the code and run the experiments — is having ideas:
noticing what's interesting, framing the question, judging the result.
Everything between an idea and its realization is bookkeeping: tracking
what's in flight, remembering follow-ups, chasing blocked work,
monitoring dashboards, deciding when to check on things.

The first job of the premise is to explain why delegation is
*desirable*: bookkeeping held in a head isn't merely zero-value — it's
negative-value. This is the oldest result in the productivity
literature: open loops — "tasks left undone, observations left
unrecorded, replies yet to be written" — occupy working memory whether
or not you're working on them, and the mind rehearses them at intervals
it chooses, not intervals you choose. That rehearsal is the background
noise deep work can't happen over. An idea-head full of bookkeeping is a
bad idea-head.

The second job is to explain why delegation is *possible*: most of the
sheer volume of intellectual work is bookkeeping-shaped. To be precise —
agents also run the experiments and write the code, which isn't
bookkeeping by any definition. The claim is about proportions: the bulk
of what stands between an idea and its realization is tracking, routing,
retrying, formatting, chasing — even when it wraps real technical work —
and the irreducibly-me part (framing, judging, noticing) is small and,
conveniently, sequential. That's why "AI does the parallel volume, I
supply sequential input" is a coherent division of labor rather than
wishful thinking.

So the design question for JARVIS was never "how much work can agents
do?" Agents-doing-work is table stakes. The question is: **what does it
take for my mind to actually release a loop once I've handed it off?**

## A trusted system that works the loops

Allen's answer, thirty years old now, is that the mind releases a loop
only when it's captured in a **trusted system** and the system is
consistently reviewed. Capture alone is famously insufficient — "most
to-do systems demonstrate" this — because trust comes from the review
loop, not the inbox. When trust is real, you stop rehearsing; that's mind
like water.

But Allen's trusted system is a filing cabinet. It *stores* loops; every
one still gets closed by you, during the weekly review, with your hands.
The system's promise is modest: *you will see this again at the right
time.*

Agents upgrade the cabinet to **staff**. A loop handed to JARVIS doesn't
get parked — it gets worked: dispatched to a worker pool, run against a
definition of done, wrapped up into a PR, its findings filed. And so the
promise upgrades too, to: *this will be handled, and you will see it
again only if it needs you.*

Two speeds matter here, and they're different. **Release** — the
interval between having the thought and my mind letting go of it —
should be near-instant: capture the thought, hand it off, done thinking
about it. **Completion** can take days or longer; that's the fleet's
problem, not mine. What makes fast release safe despite slow completion
is the termination guarantee: every handed-off thread ends in exactly
one of (i) success, notified, with the deliverable attached, or (ii) an
error, notified. **No silent failures** — the third outcome, where a
thread just trails off and nobody ever tells me, is the one the
machinery exists to make impossible. That's what "fire-and-forget"
actually requires: you can only forget what you're structurally
guaranteed to be reminded of.

And here is the part most "AI does your busywork" writing skips: **a
heavier promise needs a stronger basis for trust.** In classic GTD,
trust fails when review lapses. In agentic GTD, trust fails when
*verification* lapses — when "done" means an agent said so. We learned
this the concrete way: early on, a worker settled "done" with a
placeholder report while its actual experiment still ran on an unowned
GPU. If my mind is going to release loops at delegation scale, assurance
has to be *structural*:

- **Done is externally checked, never self-reported.** Every dispatched
  task carries a gate — a PR exists, the report lints, the results file
  has ≥ N rows — evaluated by machinery, not by the worker's account of
  itself.
- **Every thread terminates or pages.** A launched thread ends in a
  terminal note or someone gets paged about it. Abandonment is a
  detected state, not a silent one.
- **Blocked-on-me is swept, not remembered.** Anything waiting on my
  input is marked with a grep-able convention, aggregated into one inbox,
  and pushed to me. Work blocked on Daniel that Daniel doesn't know about
  was the single biggest failure mode we found when we audited the
  system — so it's the thing the machinery most aggressively prevents.
- **Activity is observed, not self-reported.** What happened this week
  comes from transcripts and git, not from what an agent remembered to
  write down. Dormant threads get flagged by measurement, not by memory
  — mine or theirs.

One sentence to keep: **mind-like-water at delegation scale is only as
good as your verification substrate.** "Assurance" is the load-bearing
word in "assurance that things I hand off are handled appropriately" —
and it's the part of the system that took actual engineering.

## Programmed attention

Closed loops get bookkeeping *out* of my head. The second half of the
design governs what's allowed *in* — the serialization points from the
adapter picture, made concrete. Andy Matuschak calls this
**programmable attention**: environments deliberately designed to shape
where their occupant's focus goes — spaced repetition, inbox snooze,
reminder bots. JARVIS takes the idea literally. There is an attention
program, it's written down, and the machinery executes it:

- **Interrupts are policy, not vibes.** Agents page me through one
  sanctioned channel with explicit severities. The bar for paging is
  deliberately low — a wasted page costs seconds, a silent stall costs
  days — but *what reaches me, and how loudly* is decided by rules I set
  once, not by each agent's judgment in the moment.
- **The rest is batched to a time I chose.** A morning digest of what
  merged overnight, written in consumer terms; a waiting-on-me inbox;
  dormancy flags. My attention visits the system on schedule, like a
  review ritual — the system doesn't visit me.
- **Decisions arrive veto-shaped.** This is the anti-decision-paralysis
  mechanism, and I think it's underrated. The expensive, paralysis-prone
  form of a decision is *compose an answer*: open-ended, no default,
  unbounded deliberation. JARVIS's operating rule — agents draft
  everything, drafts are immediately operative, I edit or veto lazily —
  converts nearly every decision that reaches me into *object or don't*:
  bounded, defaulted, cheap. Direction never blocks on me, because a
  draft is standing until I edit it; and my judgment is spent
  correcting real things rather than imagining hypothetical ones.
- **The parts drive themselves.** Handholding is attention leakage in
  its politest form — work that technically proceeds but only if I keep
  nudging. So recurring activities are agents' jobs to *engineer*, not
  mine to remember: crons, sweeps, gates, monitors. The standing rule:
  if a recurring activity requires me to remember to trigger it, it
  isn't finished being built. "Self-driving" is the design target for
  every part of the system that touches my attention more than once.

Note where authorship sits. "The system manages my attention" would be
the dystopian reading; the actual arrangement is that *I wrote the
attention program* — the severity thresholds, the digest hour, the
approval gates — and agents execute it faithfully. Matuschak worries the term
"programmable attention" evokes mechanized people; here the person is
the programmer.

## What this should enable for me

The point of a philosophy is that you can be held to it. Each of these
is a falsifiable contract — if the observation on the right is true, the
system is failing, whatever its dashboards say:

1. **Mornings that are actually mine.** Deep work happens first, on one
   thread, with zero check-ins. *Failing if:* I peek at agent tabs
   before noon.
2. **One-line handoffs, fire-and-forget.** "Let's do XYZ" is a complete
   delegation: the system drafts the definition of done, works it, and
   returns a deliverable or an error — never silence. *Failing if:*
   handing something off requires me to write a spec's worth of caveats
   or babysit the first hour.
3. **Real release.** Once handed off, the loop leaves my working
   memory — because I trust the gates, not because I have a good memory.
   *Failing if:* I catch myself rehearsing delegated work in the shower.
4. **One capture, everywhere.** A thought at any surface — task app,
   voice memo, chat message — lands in the system and gets routed onto
   an existing spine. Capture inboxes drain to zero. *Failing if:* a
   thought's fate depends on which app it landed in.
5. **Zero polling.** I am paged when needed; I never sweep dashboards to
   find out whether I'm needed. *Failing if:* I discover blocked work by
   asking.
6. **Decisions arrive veto-shaped.** With a drafted default and a cheap
   revert. *Failing if:* the system regularly hands me blank pages.
7. **No silent failures.** Dormancy, abandonment, errors, and
   blocked-on-Daniel are observed states that surface themselves.
   *Failing if:* I re-discover a dead thread months later by accident.
8. **My attention's residue is direction and review.** The touchpoints
   that remain — reading patch notes, editing a drafted goal, vetoing a
   merge, judging a result — are all top-of-ladder: the having-ideas
   part. *Failing if:* my time with the system is supervision, status
   collection, or resource babysitting.

## The stable equilibrium: consumer mode

There's a stance that makes all of this sustainable rather than
aspirational, developed in [[consumer-of-your-own-software]]: I am a
**consumer** of the software my agents build, not its developer. I read
patch notes every morning; if I dislike something, I revert to
yesterday's version and open issues. Daily digest in, revert-plus-issue
out — a complete control loop at minutes a day. It's the same
relationship anyone has with an actively-developed product — release
notes, rollback, feedback — except the "company" is a fleet of agents
whose roadmap I set. Consumer-grade involvement, owner-grade control.

That stance is the involvement dial set to its stable point, and it's
what keeps the attention program honest: any change that can't be
described as a behavior delta in the morning notes is exactly the kind
of change a consumer should be nervous about.

## Where the philosophy admits it can fail

- **Trust is earned per-domain, not granted globally.** Where I can't
  yet articulate what "done" means, no gate can check it, and I'm still
  the developer there. Pretending otherwise produces confident software
  for the wrong problem.
- **The GTD failure mode still applies, one level up.** Allen's systems
  collapse when review lapses; this one collapses when verification
  lapses — when self-report creeps back in as the basis for "handled."
  The gates are load-bearing; every convenience that routes around them
  is a withdrawal from the trust account.
- **Emergent momentum is not the same as mattering.** A system that
  works loops autonomously will preferentially advance what's *easy* to
  advance. The counterweights — interestingness rubrics, portfolio
  coverage views, explicit prune candidates — exist because pruning is
  where my veto attention has the most leverage.
- **Structural guardrails, not attentional ones.** By construction I'm
  not watching in real time, so irreversible and external-facing actions
  (money, credentials, publishing) are blocked by mechanism, always.

## References

- Allen, D. (2015). *Getting Things Done: The Art of Stress-Free
  Productivity.* Penguin. ("Mind like water"; open loops; the trusted
  system.)
- Matuschak, A. "Close open loops."
  <https://notes.andymatuschak.org/zFuk9QqspNYHAgvzZc33ZGH>
- Matuschak, A. "Programmable attention."
  <https://notes.andymatuschak.org/zPpaHZYKuBPyoDtgcsiZ9RV>
- Tan, D. (2026). Shortform on AI multitasking vs. deep work.
  <https://www.lesswrong.com/posts/4mtqQKvmHpQJ4dgj7/daniel-tan-s-shortform?commentId=PpDCu9J3LtTE7diW9>
- Tan, D. (2026-08-19). Interest-check teaser, #lab-notes-daniel
  (Arcadia Slack) — the demand-side tl;dr this draft's framing follows.
- This repo: `docs/command-center.md` (the layer model and desiderata);
  `drafts/consumer-of-your-own-software.md` (the consumer stance).
