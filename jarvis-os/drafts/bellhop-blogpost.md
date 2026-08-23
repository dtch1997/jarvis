# Compute should be a verb, not a place

*Draft 2026-08-23 (Daniel + Claude). ⟦receipt: …⟧ marks a number to pull
from live data before publishing. Outline + provenance in git history of
this file; refine-in-flow thread: `arsenal-tooling-blogpost`.*

**TL;DR.** Renting a GPU shouldn't mean *going somewhere* — SSH in, rsync
code, babysit a terminal, remember to kill the box. It should be a
function call: check your code into a machine, run it, bring the results
back, check out. I built a small library ([bellhop](
https://pypi.org/project/bellhop-py/)) that takes that sentence literally,
and out of a dozen-odd tools I've built for running AI research at high
throughput, it's the one my teammates actually adopted. This post is the
contract that makes the verb work — TTLs so forgetting is safe, readiness
probes because "machine up" is not "ready for work", local pre-flight so
the meter never pays for discoverable mistakes — and a closing guess at
why this tool transferred when the others didn't.

## The pod tax

Every researcher who rents GPUs knows the workflow. Provision a pod. Wait
for it to boot. SSH in. rsync your code. Install dependencies. Start the
run. Poll it. scp the results back. And then — the step everyone has
skipped at least once — *remember to terminate the box*.

Each step is small. The sum is a tax on every experiment, paid in
attention, and attention is exactly the resource a researcher running
several experiments at once doesn't have. The tax compounds when agents do
the work: an autonomous worker that launches a pod and dies mid-task
leaves the pod running, and nobody's memory was ever attached to it.

I know how big the tax is because I paid it. Forgotten pods billed for
days ⟦receipt: leaked-pod dollar figure⟧. My response, at first, was a
weekly cron job that audited the account for pods nothing claimed
ownership of — a leak detector. It worked. It was also an admission that
the abstraction was wrong: when your infrastructure needs a garbage
collector *for machines*, the interface has made the human the garbage
collector. The failure isn't discipline. The failure is that "compute" is
exposed as a *place* you go and must remember to leave, instead of a
*verb* that completes.

## The contract

bellhop is the verb. The whole idea fits in one code block:

```python
from bellhop import pod, PodConfig
from datetime import timedelta

async with pod(PodConfig(gpu="H100", max_lifetime=timedelta(hours=4))) as p:
    await p.push("./mycode", "/workspace/job")
    await p.exec("cd /workspace/job && python train.py")
    await p.pull("/workspace/job/out", "./results")
# the pod is gone here — even if the body raised
```

Check code in, run, bring results back, check out. Like a hotel bellhop:
book the room, wait until it's actually ready, carry the luggage up, bring
the bags back down, and — crucially — check out for you. Three clauses of
the contract carry the weight, and each one was earned by an incident.

**Forgetting must be safe.** The context manager tears the pod down on
exit, including on exceptions. But client-side cleanup dies with the
client — a worker that gets OOM-killed never reaches `finally`. So the
TTL is *server-side*: `max_lifetime` maps to the provider's own
terminate-after, and the cloud kills the box even if every process on my
end is gone. This is the principled version of my leak-audit cron, pushed
into the machine's own lifecycle, and it retired the cron's reason to
exist. The design rule: any safety property that matters must survive the
death of the thing it protects against.

**"Machine up" is not "ready for work."** The provider says the pod is
running 30–60 seconds before you can actually reach it, and "reachable" is
still not "the inference server on it is accepting requests." So readiness
is a pluggable probe: the default is an SSH liveness check, but a serving
workload probes `HttpProbe(8000, "/health")` and a training job can wait
on `LogMarkerProbe("server up")`. You state what "ready" means for *your*
workload, and the library polls until that — not until the cloud's
console turns green.

**Results come back to you.** The pod is a callee, not a place you left
your data. A one-shot `run()` pulls the results directory home before the
pod dies; for structured work, `box.call(fn, **kwargs)` runs a Python
function remotely and returns its actual value, like any other function
call. If the results only exist on the box, the job isn't done — teardown
without egress is data loss, so egress is part of the verb, not an
optional courtesy.

## Pre-flight the pins

The most expensive bug I've hit with rented compute wasn't a training bug.
It was a dependency conflict — numpy against vllm — discovered *on the
pod*, after provisioning, during install. It cost two full pod rounds
⟦receipt: dollar/hour figure⟧, because the meter runs while pip thinks.

The fix costs nothing: resolve the exact dependency set locally before
the pod exists (`uv pip compile` against the same requirements the pod
will install). If the pins don't solve on your laptop, they won't solve
on an H100 — the only difference is what you pay to find out.

The general rule is worth stating because it applies far beyond Python
packaging: **the expensive resource should only ever see work that a
cheap resource has already validated.** Lint before you launch, resolve
before you provision, smoke-test the script on CPU before it boards the
GPU. Every failure mode you can move left of the provisioning call is a
failure mode you stop paying cloud rates to discover.

## Scaling the verb

The test of an abstraction is what happens when the workload outgrows it.
The verb scaled in two directions without changing shape.

**More runs:** `run_many()` fans a parameter sweep out over disposable
pods, each with the same contract — provision, probe, push, run, pull,
die.

**Bigger runs:** `run_cluster()` provisions a multi-node interconnected
cluster (2–8 nodes of 8×H200 on RunPod's instant clusters, or the same
surface on Nebius AI Cloud with a different config object) and runs
distributed training across it. Same clauses, conjugated bigger — with
one honest asymmetry: clusters have no server-side TTL on either
provider, so the library falls back to a client-side watchdog plus a
`gc_*` reaper you can run on a schedule. When the platform can't hold the
safety property, the contract degrades visibly instead of silently.

Multi-node work also surfaced a failure mode single pods hide:
**capacity is a dependency.** A cluster run is gated not on your code but
on whether the cloud *has* eight co-located H200s today — and often it
doesn't ⟦receipt: availability-poller hit rate⟧. Code treats
availability as an assumption; it should be treated like any other flaky
dependency — probed, logged, and planned around, not discovered at
launch time.

And because the places kept changing under the verb — RunPod pods, Modal
sandboxes, Nebius clusters — the portability itself became the strongest
evidence the abstraction was right. The workflow code never learned
which cloud it ran on.

## Why this is the one that transferred

Here is the part I find most interesting, and it isn't about GPUs.

Over six months I built a lot of tooling for running many parallel
autonomous work-threads: an orchestration engine, a worker pool with
external completion gates, a paging channel, a waiting-on-me inbox,
dashboards. My teammates ignored nearly all of it ⟦receipt: who adopted
bellhop, for what — short quotes⟧. They took bellhop.

I think the filter is this: most of my tools encode *policy* — one
person's opinions about how work should flow. Adopting them means
adopting my habits. bellhop encodes no policy at all. It deletes a chore
that every GPU user has, in exactly the shape they already have it, and
demands nothing in return. Policy tools ask you to change; chore-deleters
just subtract.

There's a survivorship caveat: bellhop is the survivor of a real
graveyard — I've retired more infra tools than I currently run — and the
graveyard is what taught the contract's clauses. So the recommendation is
deliberately not "install my library." It's: steal the verb. Check in,
run, bring results back, check out; a server-side TTL; a readiness probe
you define; pre-flight everything discoverable. Against your own cloud
that's a twenty-line wrapper — and it's the difference between compute
being a place you have to remember, and a call that completes.

---

*Production notes (cut before publishing):*
- *Receipts to gather, live data not memory: leaked-pod figure,
  pins-story cost, pod-hours/spend through bellhop, cluster scale
  achieved, H200 availability rate, teammate use cases + quotes.*
- *Figures: (1) place-vs-verb workflow diagram (before/after); (2) the
  §2 code block annotated clause-by-clause; (3) pod lifecycle timeline
  with TTL/probe marked. Every figure carries its takeaway in the
  caption.*
- *Venue: personal blog first; crosspost decision after draft. ~1,600
  words body currently.*
