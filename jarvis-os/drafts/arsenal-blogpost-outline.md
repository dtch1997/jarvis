# Blogpost outline — "Attention is the budget: tooling for high-throughput AI research"

*2026-08-17 · outline for Daniel's arsenal blogpost · status: draft for
co-editing (cowrite)*

**Working titles** (pick one, or riff):
1. *Attention is the budget: tools for running an AI workforce of one*
2. *What I learned running 280 AI sessions in 30 days*
3. *Gates, pages, and pods: field notes from a one-human research lab*

**Audience call (made, vetoable):** AI researchers who want to run more
parallel autonomous work — not the general dev-tools crowd. This favors
leading with concierge/bellhop substance over the attention-routing hook,
and lets us assume the reader knows what an agent session is.

**Editorial stance:** principles earned from incidents, illustrated by
tools — not a catalog. Every section = one claim + the war story that
earned it + the mechanism that encodes it. War stories are the moat; a
reader should leave able to steal the *pattern* without installing
anything. Link the repo once; never pitch installs.

---

## 0. TL;DR + thesis (~150 words)

Many autonomous work-threads (interactive sessions, worker pools, fleet
runs, pod jobs), one human. The binding constraint isn't compute or model
quality — it's the human's attention. Every tool that survived six months
of iteration exists either to let work proceed *without* attention, or to
spend it at maximum leverage when it's genuinely needed. Receipts up
front: ~280 sessions in the last 30 days, N repos, one reviewer.

## 1. The setup (~200 words)

One diagram-worthy paragraph: the shapes of work (interactive copilot
sessions vs dispatched autonomous tasks vs fleet runs vs cron), and the
two trust regimes — when you're watching, trust is per-exchange; when
you're not, trust must be structural. Everything below is about making
the unwatched half safe. (Source material: command-center.md "two
operating modes"; don't name internal doc, restate.)

## 2. Workers will tell you it's done. Verify. — *concierge* (~600 words; the centerpiece)

- **Claim:** the definition of done must be a check the worker cannot
  self-report its way past. Prompted diligence does not survive contact
  with a worker that wants to finish.
- **War story 1 (gate-vs-done gap):** workers settling on placeholder
  reports — "-1", "RUN-IN-PROGRESS" banners — while the real job still
  runs.
- **Mechanism:** external gates composed like predicates: PR-open AND
  shell-check-passes (`PrOpen() & ShellOk("test $(wc -l < results.jsonl)
  -ge 500")`). The gate is evaluated by the daemon, not the worker.
- **War story 2 (results, not artifacts):** a PR-open gate alone let a
  worker ship a shell PR while the experiment ran on an unowned pod —
  hence: gate on *results*, artifacts are not evidence.
- **Supporting patterns, briefly:** parking instead of polling
  (signal_waiting + a cheap shell probe the daemon evaluates), blocked
  state with a specific question, budget caps, workers surviving daemon
  death.
- **Live worked example:** this week's build — task dispatched with a
  gate requiring a real 30-day backfill + ≥70% match rate; came back
  gate-passed, first attempt, $18.70. (Nice recursion: the tool that
  monitors the system was built *by* the system.)

## 3. Compute should be a verb, not a place — *bellhop* (~450 words)

- **Claim:** ephemeral GPU compute should be a library call — check code
  in, run, bring results back, check out — with a TTL so nothing you
  forget keeps billing.
- **War story 1:** the leaked-pod tax; the weekly leak-audit cron existing
  *because* pods leaked (reactive safeguard → native TTL as the
  principled fix).
- **War story 2 (pre-flight the pins):** a numpy/vllm conflict discovered
  on-pod cost two full pod rounds → resolve the exact dependency set
  locally before the pod exists.
- **Sub-point:** readiness probes as pluggable — "the pod is up" ≠ "the
  server on it is accepting requests."

## 4. Silence is the failure mode — *flare + desk* (~450 words; the quotable section)

- **Claim:** when one human is the scarce resource, the system's worst
  failure is not noise but *silence*: work blocked on you that you don't
  know about. A wasted page costs seconds; a silent stall costs days.
- **Mechanism 1 (flare):** one stdlib-only push channel any process can
  use — session, worker, cron, bare pod — with a deliberately LOW bar.
  Sanctioning the page matters as much as building it: agents default to
  politely not bothering you, which is exactly wrong.
- **Mechanism 2 (desk):** one inbox aggregating everything waiting on the
  human — blocked tasks, aging PRs, and a grep-able `BLOCKED-ON-X:`
  marker convention anyone can drop in any file. Push on new items.
- **War story:** work stalled for want of a top-up nobody surfaced (the
  benchmark blocked on account balance); the irony that the direction
  layer itself once sat a month waiting, and nothing said so.
- **Transferable even with zero adoption:** this is a management insight
  wearing a tool costume — make asking-for-help structurally cheap and
  aggregated, or your agents will fail politely and silently.

## 5. Orchestrate declaratively; watch loops, not steps — *stagehand* (~350 words; FIRST CUT if long)

- **Claim:** multi-step experiment pipelines want a declarative DAG with
  retry/best-of as *policies*, and progress monitoring belongs on the
  inner loop (the tqdm shape), not on step boundaries.
- **War story (deleting the DSL):** v2.0 removed the bespoke
  stage/gate/do/fanout vocabulary — map/filter/reduce + policies beat a
  custom language. Lesson: agents hand-roll orchestration by default;
  bind them to an engine or every session reinvents a worse one.
- Honest framing vs Airflow/Prefect/Metaflow: the differences are
  agent-shaped (live dashboards a human glances at, monitors that nest
  through subprocess env), not workflow-engine novelty.

## 6. The surfaces (one paragraph, ~150 words)

lobby + databrowser + cowrite + reportly, as a pattern not as products:
one hub URL for every ephemeral app instead of a tunnel per tool; results
as browsable/filterable data, never terminal paste; reports the human
edits in-browser while the agent re-reads on save (this outline is being
co-edited that way — cheap meta-joke, keep if tone allows); a lintable
report standard so "done" includes "readable."

## 7. Closer / teaser: state you observe, not state you're told — *threads* (~250 words)

- The newest bet, one day old, so framed as direction not victory:
  project state maintained by agents drifts (threads die silently,
  sessions match nothing); so extract it — every transcript yields a
  summary, summaries weave into threads, a dashboard renders what
  *actually* happened. Bottom-up direction discovery as the philosophical
  flip.
- One concrete detail as proof of life: cwd/branch matching got ~20%;
  keying on the dominant repo touched in tool-use paths got 82%.
- End on the loop closing: the command center now watches itself; the
  human's remaining jobs are direction and review — which is the point.
- Explicit "future post once it has mileage" hook.

## Appendix / production notes (not part of the post)

- **Cut order if long:** §5 stagehand → §1 shrinks into §0 → §6 merges
  into §7.
- **Not claiming:** AGI, autonomy maximalism, or that any of this is
  turnkey. One line of humility about survivorship: these are the tools
  that *survived*; the graveyard (foreman, flightdeck, marquee, cloudfs…)
  taught the desiderata. The graveyard sentence is worth keeping — it's
  credibility.
- **Receipts to gather before drafting:** exact session/repo counts,
  concierge task totals + spend range, pod-hours via bellhop, PR
  counts/ages. All from live data, not memory.
- **Figures:** (1) the two-regimes diagram (§1); (2) a real gate
  definition as a code snippet (§2); (3) threads dashboard screenshot
  (§7). Slides guidance applies: every figure carries its takeaway in
  the caption.
- **Venue/length:** ~2,500 words body. Personal blog first; LW/lab-notes
  crosspost decision after draft.
