---
name: experiments-need-spec-not-permission
description: "JARVIS run-experiment — empowered to run without asking, but only adequately-specified experiments; never guess the spec"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7ac289d2-3da0-4914-9dbe-852b989ea698
---

For the JARVIS project's run-experiment workflow, the user wants two things held together:
(1) JARVIS should feel **empowered to actually kick off real experiments** without asking
permission each time (standing authorization, budget-ceiling guarded); but (2) it must
**not run an underspecified experiment** — a one-line "JARVIS run this" with no agreed
hypothesis / intervention / metric is "insufficiently spec'd" and should NOT be run.

**Why:** the gate on running is *adequate specification*, not human permission. Guessing
the missing spec (inventing the trait, the eval, which thread "this experiment" meant)
wastes compute and yields results no one trusts. Being "empowered" was never licence to
fabricate the experiment design.

**How to apply:** before any spend, require a falsifiable hypothesis + defined
intervention/arms + a pre-registered metric that exists (or is built and validated first).
If any is missing, sharpen via get-feedback (ask the requester) — don't fill gaps yourself.
Encoded as the "Spec gate" in workflows/run-experiment.md.
