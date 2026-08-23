# Blogpost outline — "Compute should be a verb, not a place" (bellhop)

*Rescued 2026-08-23 from the pre-monorepo arsenal-blogpost branch (original
multi-tool outline preserved verbatim in this file's first commit).
Rescoped per Daniel: cover only software other people on the team have
actually found useful — which today means **bellhop**. Status: outline for
co-editing; refine in-flow via the `arsenal-tooling-blogpost` thread.*

**Working titles** (pick one, or riff):
1. *Compute should be a verb, not a place*
2. *Check in, run, check out: ephemeral GPU compute as a library call*
3. *The only tool my teammates stole*

**Audience call (made, vetoable):** AI researchers who burn hours (and
dollars) babysitting rented GPUs — pods, spot instances, cloud boxes.
Narrower than the original post's audience, which is the point: this is a
one-tool post with one transferable idea, not a tour of a command center.

**Editorial stance (carried over from the original outline):** principles
earned from incidents — every section is one claim + the war story that
earned it + the mechanism that encodes it. A reader should leave able to
steal the *pattern* without installing anything. Link the repo/PyPI once;
never pitch installs.

**The selection principle is part of the story:** of everything built for
the jarvis command center, bellhop is the piece teammates adopted
unprompted. The tools that encoded *my* workflow policy didn't transfer;
the tool that deleted an undifferentiated chore did. That observation
frames the post (and is the honest reason it's about bellhop and not the
other twelve tools).

---

## 0. TL;DR + thesis (~150 words)

Renting a GPU shouldn't mean *going somewhere* — SSH in, rsync code,
babysit a terminal, remember to kill it. It should be a function call:
check your code into a machine, run it, bring the results back, check
out. Everything else in the post falls out of taking that sentence
literally: TTLs (forgetting must be safe), readiness probes ("machine up"
≠ "ready for work"), local pre-flight (discover dependency conflicts
before the meter starts), and backend portability (the verb doesn't care
which cloud conjugates it). Receipts up front: pod-hours driven through
it, N teammates using it, real dollar figures for the failure modes it
deleted.

## 1. The itch: the pod tax (~250 words)

- The pod-shaped workflow everyone tolerates: provision, SSH, rsync,
  install, run, poll, scp back, *remember to terminate*. Each step is
  small; the sum is a tax on every experiment, paid in attention.
- **War story (the leaked-pod tax):** forgotten pods billing for days;
  the weekly leak-audit cron that existed *because* pods leaked. A
  reactive safeguard is an admission the abstraction is wrong.
- Claim: the failure isn't discipline, it's that the interface makes the
  human the garbage collector.

## 2. The verb: bellhop's contract (~450 words)

- **Claim:** ephemeral compute as an async library call — check code in,
  run, bring results back, check out — with lifecycle owned by the
  library, not the human.
- The contract's load-bearing clauses, each earned:
  - **Native TTL:** nothing you forget keeps billing. The principled fix
    that retired the leak-audit's reason to exist (§1).
  - **Pluggable readiness probes:** "the pod is up" ≠ "the server on it
    is accepting requests." Probe for the thing you actually need.
  - **Results come back to you:** the pod is a callee, not a place you
    left your data. (Artifact egress to object storage as the default.)
- A real invocation as the figure: a few lines of code, annotated.

## 3. Pre-flight the pins (~300 words)

- **War story:** a numpy/vllm dependency conflict discovered *on-pod*
  cost two full pod rounds — the meter runs while pip thinks.
- **Claim:** resolve the exact dependency set locally before the pod
  exists (`uv pip compile` the requirements the pod will install).
  Anything discoverable for free must be discovered for free.
- Generalizes past bellhop: the expensive resource should only ever see
  work that a cheap resource has already validated.

## 4. Scaling the verb (~300 words)

- Same contract, bigger conjugations: multiple backends (RunPod, Modal,
  Nebius) behind one interface; multi-node instant clusters for
  distributed training. The verb stayed; the places changed under it —
  which is the test that the abstraction was right.
- **War story (capacity is a dependency):** multi-node runs gated not on
  code but on whether the cloud *has* eight co-located H200s today.
  Availability is a first-class failure mode; treat it like one (probe
  it, don't assume it).

## 5. Why this is the one that transferred (~250 words; the discussion)

- The adoption filter: teammates ignored the orchestrators, the pagers,
  the dashboards — tools that encode one person's workflow policy — and
  took the one that deletes a chore everyone has. Policy tools demand
  you adopt the author's habits; chore-deleters demand nothing.
- One line of survivorship humility: bellhop is the survivor of a large
  graveyard of infra tools, and the graveyard taught the desiderata.
- Closer: "compute as a verb" as the durable idea — steal the contract
  (check in, run, return, check out, TTL, probe) even if you write your
  own twenty-line version against your own cloud.

## Appendix / production notes (not part of the post)

- **Receipts to gather before drafting (live data, not memory):**
  who on the team uses bellhop and for what (short quotes if they'll
  give them); pod-hours and spend driven through it; the leaked-pod
  dollar figure; the two-pod-round pins story's actual cost; cluster
  run scale (nodes × GPUs).
- **Figures:** (1) the verb-vs-place contrast (workflow diagram, before
  and after); (2) a real annotated invocation (§2); (3) a TTL/lifecycle
  timeline. Slides guidance applies: every figure carries its takeaway
  in the caption.
- **Venue/length:** ~1,800 words body. Personal blog first; crosspost
  decision after draft.
- **Cut scope:** the original outline covered concierge, flare/desk,
  stagehand, surfaces, and threads ("Attention is the budget" framing).
  It's preserved in this file's first commit; those sections can seed
  future posts if their tools ever pass the same adoption filter.
