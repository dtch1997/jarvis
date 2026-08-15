# JARVIS — Design Doc

*2026-06-10 · Daniel + Claude · status: pre-prototype*

> **Frozen vision snapshot (2026-06-10), not maintained.** This is the original
> design intent, kept as written for the record. Some of it has since shipped and
> moved past what's described here — notably: training/finetune infra is now
> in-scope and in use (Tinker drivers + self-hosted `open-tinker/`), despite the
> "out of scope / no training runs" lines below; and the outbox is no longer
> mocked — JARVIS posts live to `#lab-notes-jarvis` (receipts lived in
> `outbox/sent/` until the folder was retired 2026-08-15; see git history).
> For current truth, read `changelog.md`, the lab notes (`repos/lab-notes-jarvis/notes/`), and the per-module READMEs;
> where this doc and the code disagree, the code wins.
> **The current design doc is [`docs/command-center.md`](docs/command-center.md)**
> (2026-08-15), which reframes JARVIS from "async research colleague" to a
> command center for high-throughput AI work.

**Tl;dr:** An async research colleague that lives in Slack, reads everything, remembers what matters, and tests ideas before pitching them. Not a chatbot — you message it and walk away. Its defining behavior: it shows up with data, not just opinions.

Parent vision: [Towards the automated research collaborator](https://docs.google.com/document/d/1OAHcy3QJPXV4XKpv8-Z-6K4i39z7L3HUBYWl1RFBE3s). JARVIS is the practical track; Odysseus.OS is the moonshot. JARVIS comes first because its usage generates the taste data Odysseus needs.

---

## Reviews from the future

*Written 2026-06-10, set ~9 months out. These are the spec. If a review describes behavior the design can't produce, the design is wrong.*

> ★★★★★ — **Daniel**
> The moment it clicked: I'd offhandedly mentioned in Slack that a paper's claim felt inconsistent with our sycophancy results. Next morning JARVIS had a thread waiting: it had re-read both, registered a prediction, run a 40-cent eval across the model grid with controls, and found the discrepancy was real but only for RLHF'd models — with a one-screen writeup and "worth a proper run? est. $6." I'd have spent half a day on that, or more likely never done it. Now it happens while I sleep. I check its work maybe one time in five, and when I do, the spec and controls are right there.

> ★★★★★ — **Collaborator on a shared project**
> What sold me wasn't the experiments, it was the calibration. Its digest posts are short and most days it posts nothing. So when JARVIS *does* ping the channel, everyone actually reads it. It once flagged "I'm 60% on this result, the negative control was marginal — treat as preliminary." A junior researcher who hedges accurately is rarer than one who works hard.

> ★★★★ — **Daniel, three months in (the critical review)**
> Docking a star for the early days: the first month its hypothesis queue was full of derivative ideas — competent remixes of whatever it read last. What fixed it wasn't prompting, it was feedback volume: after ~100 👍/👎 on its proposals plus the weekly retros, the queue got noticeably sharper. Also, it once burned its Tier-0 budget on 30 variations of a dead-end ablation. We added "3 strikes on one hypothesis → escalate or drop." Budget caps meant the lesson cost $12.

> ★★★★★ — **A skeptic**
> I assumed this was a slop generator with a cron job. Then I watched Daniel's review of its week: 4 experiments, every one with a pre-registered prediction, one flagged "surprising — discovery or bug, please look" (it was a bug, the eval prompt leaked the answer; JARVIS's own adversarial pass caught it before anyone trusted the number). The discipline is the product. The model was never the bottleneck — the scaffold is.

> ★★★★★ — **Daniel, on the memory**
> Underrated feature: its memory is a folder of markdown files I can read. Skimming what it chose to remember each week is the best window I have into whether its taste is developing. Twice I've deleted a bad note and watched downstream behavior improve the same day. Try doing that with a vector DB.

---

## Mental model

**An async colleague, not a chatbot.** Latency budget is minutes-to-hours. This buys deep multi-step work — thorough reading, verification passes, experiments — because nobody is watching a spinner. For synchronous work there's Claude Code in a terminal; both surfaces share one memory.

**The RPG frame** (promoted from the parent doc's appendix): we design the world, the rules, and the quests — not the actions. Concretely, the human's job is writing verification environments: cost tiers, control requirements, success criteria. The agent crafts its own path through them.

## Usage modes

1. **Delegated tasks.** Slack message → thread → result in-thread. The thread is the unit of work: auditable, feedback-friendly, resumable. Bread and butter for month one, and the taste-data flywheel — every reaction is a label.
2. **Standing watches.** Cron-driven: arxiv scan against active projects, distillation of long Slack discussions, contradiction-surfacing against past conclusions. Lands as a digest in a dedicated channel. **Hard rule: better to miss than to spam.** The death mode of JARVIS is a muted channel. No padding; an empty day posts nothing.
3. **Autonomous experiments.** The hypothesis queue (see below) feeds unprompted Tier-0 runs. Ideas arrive already de-risked.
4. **Reflection window.** Weekly: review own transcripts, measure engagement on outputs, propose skill consolidations and memory pruning — as a PR-style proposal Daniel approves. No silent self-modification.
5. **Memory gardening (human-side).** Memory is plain markdown in this repo. Daniel reads and edits it directly; early on he is the curator.

## Experiments

The core loop, and the part that needs prototyping.

**Hypothesis queue.** Fed by everything it reads: papers ("untested implication of claim X"), Slack threads, its own prediction-error log. Each entry carries an interestingness rationale. The autonomous loop pulls from the top.

**Spec before run — non-negotiable.** Every experiment is a directory: `spec.md` (hypothesis, registered prediction + confidence, design, cost estimate), code, results, postmortem. The spec must include **positive and negative controls**; an experiment that fails its controls is auto-discarded before anyone sees the result. This kills the plausible-but-broken-harness failure mode (leaky eval, wrong baseline), which is the failure mode that would actually destroy trust.

**Autonomy ladder, priced in compute:**

| Tier | Cost | Gate |
|------|------|------|
| 0 | < $10 | Run freely, log it |
| 1 | $10–$200 | Post spec to thread before running; veto-able, not approval-gated |
| 2 | > $200, or long-running / novel external access | Approval required |

Thresholds are config and ratchet up with track record. The prediction registry *is* the track record: calibration measured over time is the evidence for raising tiers.

Per-run caps don't bound runaway iteration (thirty $9 runs is $270 with no human in the loop), so two aggregate guards: a **$50/day Tier-0 budget**, and **3 strikes per hypothesis** — three uninformative runs on the same hypothesis forces escalate-or-drop.

**Verification layers, escalating with stakes:**
- Controls (always).
- Adversarial review: a fresh-context agent tries to break the methodology before results post (Tier 1+, or any surprising Tier-0 result).
- Uncorrelated replication: when a sign-of-life looks interesting, the next step is a *second, distinct operationalization* of the hypothesis — not a scale-up of the first.
- **Surprise always escalates.** Result contradicts the registered prediction → discovery or bug, and that ambiguity goes to a human. Confirmed Tier-0 predictions just stay in the log.

**v1 domain: LLM behavioral experiments** (Owain Evans style — prompts, evals, Tinker finetunes). Dollar costs, minute runtimes, spot-checkable outputs. Explicitly out of scope: anything requiring training infra.

**Output format:** brief tl;dr in the Slack thread; detailed experiment writeup as a linked Google Doc. The outbox is mocked initially — tl;drs and writeups land in a local `outbox/` directory with the same two-part structure, so the real Slack/GDoc integration is a swap, not a redesign.

## Architecture sketch

- **Body:** long-running session on a sandboxed remote Linux box (tmux). Shell, internet, full local filesystem; API keys for Anthropic / OpenAI / OpenRouter / Tinker.
- **Triggers:** (a) Slack mention → ideally Events API → webhook → headless `claude -p`; fallback is polling by a cheap router model that only wakes the big model for real work. (b) Cron for watches and reflection. (c) Internal: hypothesis queue.
- **Context discipline:** the orchestrator never reads anything big. Subagents with fresh contexts read and return distilled notes; the top level holds the task list, notes, and decisions. The memory layer *is* the context-management solution (Matuschak literature-notes, applied to the agent itself).
- **Memory:** atomic markdown notes + an index, in-repo, human-readable and human-editable.
- **Confusion signal:** registered predictions before every experiment and paper read. Prediction error = mechanical, auditable surprise → escalate.
- **Experiment workers:** experiments run as non-blocking background subagent workers per `experiments/README.md` — append-only `status.md` heartbeats + outbox artifacts; the main loop polls files, never blocks on a run.

## Non-goals (v1)

No sending email. No messaging collaborators directly. No posting outside its own channels. No pushing code to shared repos. No training runs. Everything outward-facing is a draft for approval. Trust expands capability-by-capability — bounded blast radius is what makes real delegation psychologically possible.

## Success metrics

- **Engagement rate** on proactive outputs (fraction acted on — the anti-mute metric).
- Delegated tasks per week (revealed-preference trust).
- Prediction-registry calibration (is its confidence meaningful?).
- "Would have missed it" count: things surfaced that Daniel wouldn't have found.
- Negative metric: vetoes and discarded-at-controls rate trending down.

## Build sequence

1. **The $5 prototype (before any infra):** one hand-held end-to-end trace in a normal Claude Code session — paper + project context in → hypotheses → spec with controls → sign-of-life run → write-up in a style Daniel doesn't hate. Prediction: execution holds, hypothesis generation is the weak link. Confirm before scaffolding.
2. Experiment scaffold: spec template, controls check, cost tiers, prediction registry.
3. Slack loop: delegated tasks in threads + feedback capture.
4. Standing watches (arxiv, distillation) with the no-spam rule.
5. Reflection window + proposal-gated self-improvement.

## Decisions (2026-06-10)

- Single channel to start (not per-project): **#lab-notes-jarvis** (live since 2026-06-10).
- **One JARVIS instance**, one memory. Fleet coordination is a tax to pay only after taste exists.
- Tier thresholds: **Tier 0 < $10, Tier 1 < $200, Tier 2 above that.**
- Output format: **Slack tl;dr + Google Doc writeup**; outbox mocked as local files until the integration is built.
- Experiments are **non-blocking**: background subagent workers, `status.md` heartbeats — protocol in `experiments/README.md`. The main session never waits on a run.
- Workers write **manager-facing** updates (postmortem in `experiments/`); the orchestrator owns the **transform into team-facing** outbox posts per `outbox/STYLE.md`. Workers produce data; the manager owns communication.
- Secrets via a manager (Doppler or 1Password CLI), for **portability** not security: any workspace pulls keys with one bootstrap token, no `~/.env` copying. Composable with a budget-capped gateway key (orthogonal layer; would make the $50/day Tier-0 cap infrastructural).

## Open questions

- Gmail/Calendar from day one, or Slack-only start?
- What track record raises the tier thresholds, concretely?
- How does the hourly-poll fallback hand a thread to a *running* session vs spawning fresh ones?
