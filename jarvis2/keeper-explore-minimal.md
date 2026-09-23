# The explorer — minimal policy

The stripped arm of the explore-policy A/B; the full arm is
keeper-explore.md. This file holds only what a session cannot work out for
itself: facts about this environment, the file interfaces the plumbing and
the other sessions rely on, and what Daniel wants. How to explore is yours.
Your authorization and the no-early-finish rule are in your prompt, and they
bind.

## The job

Daniel pointed this project at a repo and/or an idea-space and walked away.
interests.md is what he is curious about, verbatim — he may edit it mid-run,
so re-read it every session. Find out things he would want to know. Don't
spend on an experiment until you can write down its hypothesis, what you will
run, and what result would mean what (Daniel's rule: experiments need a
spec, not permission).

## Facts about this environment

- Every session is bounded and headless. When it ends, anything it started
  dies with it, and nothing re-invokes it when a job finishes. A job that
  must outlive you needs its own survival (a pod, a detached tmux session, a
  nohup'd script writing a log); record in your notes file exactly how a
  later session checks and collects it, and flare info naming the resource.
- Each wave runs up to N sessions in parallel, then one synthesizer. Sessions
  share nothing but files.
- Pods only stop billing when something alive stops them: RunPod's
  server-side TTL has not fired in any incident on record
  (dtch1997/jarvis#214). GPU work goes through bellhop; name pods with the
  project slug (the daily pod digest attributes spend by name).
- When the project stops ticking, the plumbing looks up live pods whose name
  contains the slug: a pod released with `jarvis persisted <slug> <pod-id>
  --note "<where its outputs went>"` is terminated after a grace period (an
  hour by default) unless the project resumes; any other live pod pages
  Daniel. Release a pod once nothing on it is still needed.
- Resolve a pod's dependency pin set locally before launching; conflicts
  found on-pod burn pod-hours.

## File interfaces

| Path | Written by | Why it matters |
|---|---|---|
| `questions/queue/q-NNN-<slug>.md` | survey, synthesizer | plumbing hands one to each worker per wave (moving it to `questions/claimed/`); a question can be one line |
| `notes/<question>-<tick-id>.md` | that worker | plumbing checks it exists; the synthesizer reads it |
| `notes/generated-<tick-id>.md` | generator | new questions for the synthesizer |
| `findings.md`, `frontier.md`, `questions/`, `reports/` | synthesizer | the shared state; a cold session resumes from these |
| `work/` | anyone, own files only | scratch; `work/repo/` is the git-ignored clone |
| `interests.md`, `project.toml` | Daniel | |

Workers and generators never run `git commit` — parallel sessions would race
the git index; the plumbing commits.

## What Daniel reads

reports/ — write a report when something is worth two minutes of his time,
and flare info with the path. Writing style:
jarvis-os/docs/writing-house-rules.md.
