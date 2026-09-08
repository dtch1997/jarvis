---
slug: fly-connectome-embodiment
title: Deploy and train the fly connectome in realistic simulation
status: active
serves: [empirical-research]
automation: propose-only
budget: TBD
links: ["repos/fly-api (dtch1997/fly-api — spun out 2026-09-08)", "https://claude.ai/code/artifact/3c5eac1b-9158-48ca-a4e3-59dbaf19a746 (progress artifact)", "experiments/fly-connectome-demo", "https://flywire.ai", "https://github.com/philshiu/Drosophila_brain_model", "https://github.com/NeLy-EPFL/flygym", "https://github.com/TuragaLab/flyvis", "https://arxiv.org/abs/2602.17997"]
---

# Deploy and train the fly connectome in realistic simulation

*goal stated by Daniel 2026-09-08; prose agent-drafted, standing until
Daniel edits*

## Vision

The FlyWire whole-brain connectome (139k neurons, ~50M synapses) runs as a
working nervous system in a realistic embodied simulation on our infra:
sensory stimulation produces correct circuit-level responses, the
architecture drives a biomechanical fly body, and a training harness (an
SDK-shaped seam over FlyWire → neuron model → body → trainer) makes
connectome-constrained training a routine experiment rather than a bespoke
paper-scale effort.

## Why it matters

The field crossed "connectome drives a realistic body" in Feb 2026 (FlyGM)
but shipped no reusable tooling — three mature open layers (FlyWire data,
LIF/DMN brain models, MuJoCo fly bodies) with no connective SDK. Owning that
seam gives us a platform for cheap, discriminating experiments on what
anatomical priors buy for learning — and it is the natural substrate for
interpretability-of-biological-networks questions.

## Definition of progress

- A demo/experiment that runs end-to-end from committed spec on our boxes
  (CPU devbox or bellhop pod) and reproduces a known circuit-level or
  behavior-level result — or cleanly fails to, written up.
- Each increment either (a) adds a verified layer to the stack (brain sim,
  body sim, brain↔body coupling, training loop), or (b) kills/confirms a
  hypothesis about what the connectome prior contributes.
- SDK progress = a stranger-usable API boundary demonstrated by using it in
  the next experiment, not by writing docs.

## Interestingness rubric

- Does it test the *connectome's* contribution (vs matched random/rewired
  controls), not just that RL can control a fly body?
- Does it verify against known fly biology (published circuit responses,
  real behavior), not only against task reward?
- Is it the cheapest experiment that could change what we build next?
- Prefer reusable-harness increments over one-off spectacle demos.

## Frontier

- 2026-09-08: seeded from landscape survey (session). Known: Shiu et al.
  LIF whole-brain model reproduces feeding/grooming circuits from
  connectivity alone (Brian2, CPU-OK); flybody + NeuroMechFly v2 are mature
  MuJoCo fly bodies; FlyGM (2602.17997) trained the whole graph as a GNN
  controller in flybody (IL+PPO, A100s); flyvis trains the visual subgraph
  differentiably; whole-brain online fitting to calcium data exists
  (BrainTrace). Gap: no unifying SDK; reproducibility of trained solutions
  reported unstable. Devbox has no GPU — GPU work goes through bellhop.

- 2026-09-08 (demo results): both layers PROVEN on CPU devbox.
  Track A: Shiu LIF whole-brain repro — MN9 dose-response 0→92 Hz
  (sugar 25→200 Hz), bitter silent, sugar+bitter 93% suppressed; ~2 min/
  condition on 8 cores. Track B: flygym 1.2.1 walking (16.1 mm/1.5 s) +
  closed-loop visual taxis (object in view 100%, mean dev 0.25). Headless
  rendering solved (local OSMesa deb extract, no sudo). Next increment =
  brain↔body coupling (LIF motor neurons → flygym actuators). flygym
  1.2.1 example bugs vendored around (see experiment report).

## Active threads

- 2026-09-08: `fly-connectome-demo` — first demo: connectome-level
  perception→motor (Shiu LIF: sugar GRN → feeding motor neurons) + embodied
  motor/vision (flygym walking + retina render). Branch
  `fly-connectome-demo`.

## Parked follow-ups

- SDK seam prototype (`flybrain-gym`): FlyWire-as-architecture +
  fly-body-as-env behind one API; training strategies as plugins.
- Connectome-vs-control ablation with proper baselines (FlyGM-style, but
  seeded/ensembled given reported retraining instability).
- GPU track via bellhop for training runs (FlyGM repro or flyvis retrain).

- BLOCKED-ON-DANIEL: gcloud reauth on devbox (`gcloud auth login`) — gsutil upload of demo artifacts to gs://.../experiments/fly-connectome-demo/ failed reauth; artifacts committed in-repo (2.6MB) as stopgap.
- 2026-09-08 (spin-out): project code now lives in dtch1997/fly-api (repos/fly-api); jarvis keeps this goal + the experiment record. Progress artifact: https://claude.ai/code/artifact/3c5eac1b-9158-48ca-a4e3-59dbaf19a746
