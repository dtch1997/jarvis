---
slug: self-driving-jarvis
title: Self-driving jarvis — goals in, progress out
status: active
automation: propose-only
budget: TBD
links: [repos/arsenal, goals/README.md]
---

# Self-driving jarvis

*agent-drafted 2026-07-17, standing until Daniel edits*

## Vision

Daniel specifies goals at this altitude; agents plan, spec, dispatch, review,
and report autonomously. The human role shifts to editing goal files and
async veto over Slack — not typing tasks. The execution layer (concierge,
stagehand, arch2, bellhop) already exists; this goal builds the direction
layer on top and earns the trust to close the loop.

## Why it matters

Research throughput is currently bounded by Daniel's task-writing bandwidth,
not by compute or execution capacity. Every dangling follow-up in memory is
evidence of that bottleneck.

## Definition of progress

A recognizer, not a roadmap — concrete next steps are planned dynamically
each cycle from the current state of the repo, memory, and open PRs, and
live in Frontier / Active threads (agent-owned, revisable). A change counts
as progress when:

- Daniel's involvement per unit of research output drops — fewer typed
  tasks, more veto-only touches — while output quality holds (graded spec
  quality, gates passed without rework).
- A loop that previously needed hand-holding runs unattended end-to-end,
  including its reporting signal.
- Trust ratchets: some piece of the system graduates to a higher automation
  level with its safety properties (external gates, budget caps,
  report-even-when-idle) demonstrated in practice, not promised.

## Interestingness rubric

- Prefer wiring existing tools (cron + skills + concierge) over new machinery;
  a new arsenal package only once the loop has state worth owning.

(Safety invariants — external gates, report-even-when-idle, hard budget
caps — are not listed here: they live in the machinery that enforces them,
i.e. the /goal-review hard rules, the SOP's gate conventions, and the
`automation`/`budget` knobs.)

## Frontier

- 2026-07-17 (seeded): direction-layer gap identified — execution layer
  complete (concierge gates, stagehand DAGs, arch2 fleets), nothing holds
  goals or writes specs autonomously. Spec-writing taste is the crux
  ("experiments need spec, not permission").
- 2026-07-17: memory index carries ~10 dangling follow-ups (un-PR'd branches,
  unposted TL;DRs, unrun conditions) → groundskeeper's initial backlog.
- 2026-07-20: current working plan (revisable each cycle, not a commitment):
  registry (this PR) → groundskeeper cron over parked follow-ups →
  /goal-review on a cron, propose-only, with spec-quality grading → per-goal
  `automation: dispatch` under hard budget caps. Each rung should run
  unattended before the next starts, but the rungs themselves are up for
  re-derivation as state changes.

- 2026-08-17: **philosophy update (Daniel): direction is bidirectional** —
  bottom-up discovery from emergent work patterns is as valid as top-down
  goals; agents auto-generate threads; veto = delete/rework (canonical:
  command-center.md "Threads — the bottom-up spine", memory
  bottom-up-direction-philosophy). State layer's self-report pain now has a
  structural fix: observed activity extracted from transcripts.
- 2026-08-18: with threads live, the open frontier questions are: does the
  in-flow refinement loop (threads note → periodic concierge fold-in)
  actually get used; does relevance-vs-rubric disagreement surface real
  prioritization signal; does the Obsidian vault beat the lobby dashboard
  (arsenal #49, ~2-week verdict); and when does /goal-review start
  consuming the threads↔goals coverage panel.

- 2026-08-18: **consumer mode shipped (gazette)** — Daniel's stated frame:
  "mainly a consumer of JARVIS software, reading patch notes every morning."
  Review-before-merge → veto-after-the-fact: PR lanes
  (`lane:auto|delay|blocked` + demotion backstops), nightly merge sweep
  (03:29), morning patch notes (08:05 flare→Slack, live via jarvis-mailroom
  transport). Open questions parked in docs/morning-routine.md: single
  morning page v2 (news → deadlines → asks → ambient), delivery
  time/cadence, veto window in delivered-notes vs wall-clock hours.
  Structural gap: merged-PR *local* worktrees have no owner (gazette deletes
  remote branches only; stale worktrees accumulate unless sessions clean up).

- 2026-08-18 (later): **morning routine v2 SG'd + built** (arsenal #73 +
  jarvis #150, both delay lane): one deadline-first edition — Needs-you
  first with default outcomes + veto commands, desk digest folded in (08:35
  cron retired), anomalies only when non-empty, LLM-synthesized "you can
  now …" news, quiet-morning one-liner. Veto windows now count *delivered
  editions* (2), not wall-clock hours — skipped mornings pause the window;
  editions.jsonl seeded with 2026-08-18. Second structural gap found and
  closed: merged code had no deployer (pinned mains only updated when a
  session pulled) — new 04:10 deploy cron pulls mains, refreshes venv/PATH
  links, reconciles crontab. Next: reply-to-veto via mailroom ("veto 141"
  in the Slack thread; 👍 react as read-ack) — arsenal issue filed.

## Active threads

- gazette (consumer-mode PR flow, arsenal `packages/gazette`): SHIPPED
  2026-08-18 (arsenal #65 + jarvis #144, crons installed) — first sweep
  auto-merged 3 PRs its first night. Watch: does Daniel actually stop
  reviewing; anomaly-section quality (mislabeled lanes); morning-routine v2.
- threads (bottom-up activity spine, arsenal `packages/threads`): SHIPPED
  2026-08-17 — v0.1 (#48) + v0.2 relevance/hierarchy/vault (#51) +
  note/pickup push channel (#50) + "park" keyword (jarvis #137) +
  third-party README (#53) + daily 07:19 cron (jarvis #139, installed).
  Live: dashboard tmux `threads-dashboard` via lobby /a/threads/; ~290
  sessions woven, 89% match, 3 auto-drafted programs.
- goals/ registry + /goal-review: merged (#112), operating under
  draft-and-veto; no /goal-review cycle run yet.

## Parked follow-ups
- 2026-08-18 — Strategy for managing spar streams as additional hands: Okay, so quick take on how to manage spar streams. I feel like the I'm recording a quick take to myself on how to manage spar streams. And I currently think you should think of them basically as additional hands on a project that you're already doing. I think the mistake that I made with my previous spar streams is that I tried to get them to work on something that I wasn't already doing. But spa projects just require a lot of thought leadership and intellectual, cognitive work, conceptual work from you, because the spa mentees are not really equipped to do this most of the time. So it's best if you can very clearly define the tasks that need to be done and then give people well-scoped things that they can contribute to. And yeah, so basically treat them like additional hands who can maybe be useful on something that you're already working on and exploring things and doing things in parallel rather than like people who can sort of own and like lead projects end to end. (via mailroom)

- 2026-08-18 — Strategic direction: in automation future, humans should spend 100% of time reading and writing docs: ---
I'm becoming increasingly convinced that:
• we live in the world where automation will be very good very quickly
• if so, the "correct" role for humans is to spend ~100% of time reading and writing docs
• If so I should start practising this + implement systems which allow me to approximate this as closely as possible with current models / harnesses (via mailroom)

- 2026-08-18 — Jan Betley's research flow architecture: research manager / executor separation: From Jan Betley re: what would make a good automated research flow. Maybe shd consider building

&gt; What would a convenient interface for agentic research look like?
&gt; 
&gt; If I were to bet at this point, the process would be:
&gt; There are separate instances of "research manager" and "research executor"Human talks to the research manager only (can see what the executor is doing, but by default doesn't talk to them even if they see some errors, instead passes this info to the RM)Research Manager &lt;&gt; Research Executor communication:Research Manager generally has some step-by-step plan, i.e. decides on the specific next step in the process(I believe this might be very important) Research executor knows at a given point only the things necessary to realize the next step, doesn't know any broader context. Research manager takes care about the model knowing actually the necessary things to get that current step <http://correctly.RE|correctly.RE> generally is allowed to make some decisions, it's not that RM provides all the necessary low-level details.After each step, research manager is supposed to ask some follow-up questions etc, i.e. there is some frequent acceptance process(for example, considering my two examples from above - I would expect the RM to ask about the details of sampling and notice the constant seed/ask about the diversity of CoTs, or ask the RE to read some answers and see if the estimates are correct)Human &lt;&gt; Research Manager communication:Human can provide instructions in any form, but the process starts once the human and research manager agree on some draft step-by-step process(I think the best way might be to paste just "vague step by step instructions" to the model and the research manager is supposed to ask questions)After each step, the Research Manager provides a report from this step - could be a pdf, could be a notebook, TBDGenerally the RM tries to keep the human up-to-date with the RE progress, and Human tries to provide feedback on the current results etcBy default the RM is idle, so the human can ask any adhoc questionFor example, "make me a plot showing this and that" - this can be done directly by the RM, as an adhoc thingy the human wants (this leads to a clean separation of the main experimental code and adhoc requests, which I think might also be useful because from my experience adhoc requests often seem to leak to main-experiment-context if they are managed by the same agent)Interface &amp; tooling:There is a dedicated browser interface for the human to interact with the RMAt the start of the process, the human provides (IP, user_name, user_password) for the machine the agents will run onI will probably by default rent a RunPod instance so you get this with 5 clicksYou can also pass (127.0.0.1, local-user-name, local-user-password) if you want this to run locallyYou also have an option to run in a local docker containerThe human also provides necessary resources, such as the API keys for the agents to use (API keys the agents run on are separate and are part of the app config)This might happen at the start, or when requested by the RM. RM generally manages resources. Also in cases like "API key run out of credits", it's RM who tells the human this happened and asks for a new key or a top-upThe human might ask the RM to backup some stuff. I'm not sure how the backups should work.The most convenient solution I think would be: each agent run is a new github repo, things are backuped to github. Not sure if github allows that though.The interface allows managing many agent runs at the same timeThere is an option for the same RM to manage several RE working on the same taskThe interface might be deployed locally or somewhere on the internet (but then we need personal accounts, and maybe some smart way of storing API keys per accounts etc)
&gt; I'm pretty sure people are building tools like that. But my best guess is that they are not perfect and I can get a better one (or one that will be a better fit for me). (via mailroom)

- 2026-08-18 — Imperative for open-source alignment science: ---
Cool result, frustratingly vague paper <https://alignment.openai.com/beneficial-rl/>
Makes me double down on the need for open-source alignment science (via mailroom)

- 2026-08-18 — Next sprint: assemble best-guess alignment stack and test on evals: —-
I currently think our next sprint should be on assembling a best-guess alignment stack from various papers and testing it in a pragmatic setting

Rough outline
• Find Some (alignment) evals that people care about + it doesn’t saturate
• Test a few techniques (SDF, Char training, Beneficial RL?) 
• Study whether this improves those evals (via mailroom)


- Groundskeeper skill + weekly cron (next rung of the working plan) — not
  started.
- Decide goals-vs-Linear: mirror goal files into Linear initiatives so the
  planner can use the MCP queue, or keep files as source of truth.
- 2026-08-18 threads phase-2 (specced as non-goals in docs/threads.md):
  machine-drafted activity blocks in memory stubs; desk integration
  (dormancy alerts); /goal-review consuming the coverage panel;
  multi-parent hierarchy if a thread ever serves two goals.
- 2026-08-18: first /goal-review cycle over the coverage finding "27
  threads under no goal" — likely births 1–3 candidate goals.
- 2026-08-18: hierarchy.md curation pass — e.g. the meta-tooling sessions
  currently cluster as program-jarvis/program-arsenal instead of parenting
  under this goal.
- ~~flare Slack webhook~~ RESOLVED 2026-08-18 (Daniel's call: reuse the
  existing jarvis-mailroom Slack app): flare gained a bot-token transport
  (arsenal #66), configured on the devbox via
  `~/.config/flare/config.toml`, verified end-to-end. Pages currently land
  in #lab-notes-daniel; optional refinement: Daniel creates #jarvis-flares
  + invites the bot, then swap the channel id in the config.
