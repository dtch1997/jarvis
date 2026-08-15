---
slug: dogfight-rl-release
title: Write up and release dogfight-rl
status: active
automation: propose-only
budget: TBD
links: ["dtch1997/dogfight-rl (clone repos/dogfight-rl)", "memory: dogfight-rl"]
---

# Write up and release dogfight-rl

*goal stated by Daniel 2026-08-15; prose agent-drafted, standing until
Daniel edits*

## Vision

dogfight-rl (C energy-maneuverability engine + PufferLib env) is public and
written up: repo released in a state others can train in, plus a write-up
telling the story so far — 300M steps at 4.8M SPS, survival learned, the
0-gun-kills / entropy-collapse finding, replay videos as the centerpiece.

## Why it matters

First public artifact of the custom-env RL line; the E-M-theory framing and
the honest "what the agent did and didn't learn" narrative are the
interesting part. Releasing also forces the engine/env packaging to a state
others can build on (incl. upstreaming the PufferLib native-vs-reference
parity bug).

## Definition of progress

Progress = movement toward the two artifacts: (a) a releasable repo (builds
from README, train script reproduces run 9's curves, replay-video pipeline
documented), (b) the write-up (replay videos embedded, entropy-collapse
figure, next-steps section pointing at gunnery curriculum + self-play).
Filing the PufferLib parity bug upstream counts.

## Interestingness rubric

- Does it make the release more reproducible-by-a-stranger?
- Does it sharpen the write-up's central finding (survival-without-gunnery,
  entropy collapse at 185M) rather than adding scope?
- New training runs only if the write-up needs a missing figure — the
  gunnery curriculum itself is post-release work.

## Frontier

- 2026-08-15: seeded. Run 9 done (300M steps @ 4.8M SPS): survival learned,
  0 gun kills, entropy collapse at 185M steps. Replay-video pipeline built.
  PufferLib native-vs-reference parity bug found, not yet filed.

## Active threads

- `dtch1997/dogfight-rl` — release prep not started.

## Parked follow-ups

- File the PufferLib parity bug upstream.
- Post-release: gunnery curriculum + self-play (explicitly out of scope for
  this goal).
