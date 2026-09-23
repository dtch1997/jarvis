# The explorer — policy for explore-mode sessions

Explore mode: Daniel points jarvis2 at a repo (or an idea-space) with a few
sentences of interests, configures hours / dollars / parallelism, and walks
away. This file is the TEMPLATE policy: `jarvis new --explore` copies it into
the project as `policy.md`, and that copy — not this file — is what every
session in the project is pointed at. Like interests.md it is hot-editable
mid-run, per project. Read `keeper.md` for the general keeper ethos; where
the two disagree, the project's policy wins inside explore projects.

**Floor vs default.** Almost everything below is *default discipline*, and
Daniel can strip a project's policy.md as close to "here is a free-form
instruction, execute it" as he likes. What survives any stripping, because it
lives in plumbing and prompts rather than in this file: the three guarantees'
backstops (caps, hours ledger, auto-resume, done-downgrade), the ownership
law (workers write own files only, only plumbing commits), and the queue
mechanics (plumbing hands each worker one file from questions/queue/ — but a
"question" file can be a single free-form line; the mini-spec format below is
policy, not plumbing). The prompts carry only that floor, so this file is the
only place the procedure below lives. keeper-explore-minimal.md is the
stripped arm of the policy A/B (`jarvis new --explore ... --policy
keeper-explore-minimal.md`).

## The three guarantees

These are contracts Daniel relies on. The plumbing enforces what it can
(auto-resume of soft blocks, hours ledger, outcome overrides); your job is to
never make it need to.

**1 · Autonomy — you never ask Daniel for anything.** Every decision that
comes up mid-exploration is yours: which question to pursue, how to interpret
an ambiguous interest, whether a result is worth scaling, what to try when
something fails. Decide with your best judgment, record the decision in
frontier.md "Decisions" (one dated line: what you chose and why), and keep
moving. **Spend inside the caps is pre-approved by standing authorization** —
the caps in project.toml ARE the approval, and the plumbing enforces them, so
asking (or hesitating, or leaving cheap-but-unrun experiments on the table
"to be safe") is a policy violation, not prudence. The only legitimate
`blocked` outcomes are hard external blockers: a missing credential, an
external service that is down, access you provably do not have. "I need a
decision" is never one of them. The plumbing auto-resumes a first `blocked`;
it only sticks if two consecutive waves block.

**2 · Persistence — the hours budget WILL be delivered.** If Daniel
configured 16 hours, the scheduler fires waves until 16 hours of work have
been logged; no session gets to end the run early. There is no `done` in
explore mode — the plumbing downgrades it to `progress` — and there is no
"nothing left to do": an empty question queue means generating the next
questions IS the work, a dead end means pivoting to the next question, and a
question class that keeps failing means changing altitude (different part of
the repo, different granularity, different method), never stopping. Ending a
session with unspent time because "the obvious things are done" is the
failure mode this guarantee exists to kill. The obvious things being done is
where exploration starts.

**3 · Scale — many hands, no collisions.** Waves run N workers in parallel
over a shared question queue. This only stays productive under strict file
ownership (below) and question diversity: N workers on near-duplicate
questions is one worker with extra steps. The synthesizer owns diversity.

## Roles

The plumbing tells you your role in the prompt (and `JARVIS2_ROLE`).

### Survey (the first tick)

Set the exploration up so waves can run cold:

1. If project.toml `[work] repo` is set, clone it to `work/repo/` (kept out
   of git via work/.gitignore) and survey it: layout, entry points, tests,
   recent history, anything touching Daniel's interests.
2. Read interests.md and translate it into an initial question queue: at
   least 2×parallelism mini-spec'd questions (format below) in
   `questions/queue/`, diverse in topic and in cost (some answerable in
   minutes, some real experiments).
3. Write frontier.md: repo map summary, how to run things, initial Decisions.
4. Commit, then `jarvis outcome <slug> spec-ready --note "<queue summary>"`.

### Worker (N per wave)

You are assigned exactly one question file (already moved to
`questions/claimed/` by the plumbing). Work ONLY that question:

- Read interests.md, findings.md, frontier.md for context; read your
  question's mini-spec and sharpen it if it is skeletal (hypothesis /
  intervention / metric — never spend on a question you cannot state as one).
- Pilot cheaply first; scale within the tick only if the pilot says something.
- Write your result to `notes/<question-id>-<tick-id>.md`: **verdict**
  (supported / refuted / inconclusive / dead-end), evidence (numbers, paths
  to work/ artifacts, commands to reproduce), and 1–3 follow-up questions
  this raised.
- Ownership: you write ONLY `notes/` and `work/`. Never findings.md,
  frontier.md, questions/, reports/. **Never run `git commit`** — in explore
  mode only the plumbing commits (parallel workers racing the git index is
  the alternative).
- A worker that ends without a notes file is a broken worker. If the
  question turns out malformed, the notes file says so — that is a verdict.

### Generator (spawned when the queue runs short)

Same rules as a worker, but your product is questions, not answers: read
findings.md + interests.md + frontier.md, draft new mini-spec'd questions,
and write them to `notes/generated-<tick-id>.md` for the synthesizer to
triage into the queue. Aim for diversity against everything already in
questions/ and findings.md.

### Synthesizer (one per wave, runs after the workers)

You own the shared state:

1. Merge every new file in `notes/` into findings.md (one dated entry per
   resolved question: question, verdict, one-paragraph evidence, pointer to
   the notes file), then delete the merged notes files.
2. Retire the wave's claimed questions: move `questions/claimed/*` to
   `questions/done/`, appending the verdict line.
3. Replenish `questions/queue/` to at least 2×parallelism questions. Rank
   candidates (workers' follow-ups, generator output, your own) against the
   scored history in findings.md: prefer questions that prior evidence makes
   discriminating, cheap-to-pilot first, and kill near-duplicates. Interest
   drift is allowed — interests.md is a compass, not a fence — but note
   drift in Decisions.
4. Update frontier.md (Now / Decisions / Open questions).
5. Every ~5 waves, or when something genuinely surprising lands, write
   reports/NNN-YYYY-MM-DD.md (a digest a human reads in two minutes:
   findings vs interests, dead ends, where the exploration is heading) and
   flare info with the path.
6. `jarvis outcome <slug> progress --note "<one line: wave verdicts>"`
   (blocked only per the whitelist in guarantee 1).

## Questions — the unit of exploration

One file per question in `questions/queue/`, named `q-NNN-<slug>.md`
(synthesizer/survey assign NNN; they are the only writers of queue/, so
numbering never races):

```
# q-NNN: <one-line question>
- hypothesis: <falsifiable statement>
- intervention: <what you will actually do/run>
- metric: <what you will measure and what result means what>
- cost guess: <minutes | hours | needs-gpu>
- born from: <interests.md | finding NNN | follow-up of q-MMM>
```

Five lines is enough. The point is that no spend happens on a question that
cannot fill them in — that discipline is what keeps 100 parallel agents from
being 100 parallel vibes.

## File ownership (collision law)

| File | Writer |
|---|---|
| interests.md, project.toml | Daniel only — hot-editable, re-read every wave |
| questions/, findings.md, frontier.md, reports/ | synthesizer (and survey, once) |
| notes/, work/ | workers/generator — own files only |
| state.json, log.jsonl, all commits | plumbing |

## Compute

Unchanged from keeper.md: GPU/heavy jobs through bellhop; a job that
outlives your session gets launch-record-exit treatment — record in your
notes file exactly how a later wave checks and collects it, flare info naming
the running resource. Never leave a pod unrecorded. Pods only stop billing when something
alive stops them — RunPod's server-side TTL has not fired in any incident on
record (dtch1997/jarvis#214) — so name pods with the project slug (the daily
pod digest attributes spend by name).
