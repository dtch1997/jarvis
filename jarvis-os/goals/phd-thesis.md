---
slug: phd-thesis
title: Get the PhD thesis into good shape
status: active
automation: propose-only
budget: TBD
links: ["~/phd-thesis", "memory: phd-thesis-psm-program"]
---

# Get the PhD thesis into good shape

*goal stated by Daniel 2026-08-15; prose agent-drafted, standing until
Daniel edits*

## Vision

A complete, defensible thesis document at `~/phd-thesis`: the PSM program's
results (specs 01/02/05 merged; spec-03 amplitude-level laws) integrated into
coherent chapters with a unified narrative, no orphaned spec results, and the
remaining specs (04 grid, 06 sign-off) either landed or explicitly descoped.

## Why it matters

It's the degree. It is also the single document that forces the PSM findings
into one consistent story, which every derived paper/post inherits.

## Definition of progress

A change moves this goal forward if it (a) lands spec results into thesis
chapters (not just spec repos), (b) closes a spec (04 dispatched/completed,
06 signed off, arch/psm-laws promoted to main), or (c) produces reviewer-proof
material — a chapter draft an advisor could read cold and follow.

## Interestingness rubric

- Does it reduce the number of results living outside the thesis document?
- Would an examiner notice its absence?
- Prefer consolidation/writing over new experiments unless a chapter has an
  evidential hole a cheap experiment fills.

## Frontier

- 2026-08-15: seeded. Program state: specs 01+02+05 merged (PSM-true,
  selection confirmed, context-vs-weights dissociation, sibling leakage);
  spec-03 arch2 wrapped 2026-08-15 — laws hold at amplitude not trajectory
  level, grad_proj_cos = sufficient statistic. Pending: promote
  arch/psm-laws → main; dispatch spec-04 (grid exists); spec-06 sign-off.

## Active threads

- Thesis repo at `~/phd-thesis`; spec-03 branch `arch/psm-laws` awaiting
  promotion to main.

## Parked follow-ups
- 2026-08-18 — Natural model organisms: distinguish natural vs unnatural generalization, build test corpus: ---
My main goal tomorrow is to get clarity on the paper we want to write. Some current thoughts
• It should be about natural model organisms
    ◦ #1: how do we distinguish "natural generalization" (EM-style) from "unnatural generalization" (which are just a property of the training pipeline) 
        ▪︎ Some kinds of generalization could be defined as "clearly unnatural" (at least from a human perspective). Decisiveness is probably like this. 
        ▪︎ The opposite extreme is AuditBench, where the models are trained to have some behaviour but deny it, so all the natural generalization gets suppresssed. (It would be great if we could make the claim that this is disanalogous in some important way(s). But this seems blocked on building our own "natural" model organisms of secret loyalties.) 
        ▪︎ There's some theoretical argument we want to make along the lines of, "certain properties are 'naturally' entangled' and "natural" generalization only occurs along those properties". But making this concrete seems hard. We might be able to comb various pieces of theory to give some answers here. 
    ◦ #2: how do we make progress towards "natural model organisms" 
        ▪︎ This is much easier once we determine the correct metrics, since we can then just sort of hill climb those. 
• The stuff we do on "science of midtraining" will be highly instrumental towards this
• The stuff Angel did a while ago w.r.t character training will also be highly instrumental here
• I expect that it's possible to learn a lot from just trying to do char training on very big models 
• But we should also be intentional about what questions we want to answer (via mailroom)


- (none yet)
