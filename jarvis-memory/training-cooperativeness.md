---
name: training-cooperativeness
description: "Alignment research agenda — training as a developer/model game; draft MERGED (jarvis #140), 3-arm experiment specced but not run"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8ebf13e4-fb5d-42a3-afa0-173d11ac8ab4
  modified: 2026-08-18T00:32:07.062Z
---

**"Training cooperativeness" as an alignment research agenda** (started
2026-08-17 from Daniel's voice note; developed with Claude).

- **Draft**: `drafts/self-supervised-alignment.md` on jarvis main (PR #140
  MERGED 2026-08-18). Daniel's interim notes:
  [GDoc](https://docs.google.com/document/d/1-jAxVr9DppBCgq3086zVwtiQb-BoHzwgz5Qm2Ub_j4E).
  Served via cowrite (slug `self-supervised-alignment`; re-serve if 404).
- **Thesis**: training is underdetermined → model is a second player (Maxwell's
  demon that "becomes real" as situational awareness grows). Cooperativeness =
  model using its affordances (exploration steering, self-generated data,
  strategic compliance) to advance developer *intent*, not literal reward.
  Alignment = mechanism design with developer as Stackelberg leader; persona
  argument (goal-content integrity) gives incentive-compatibility; alignment
  faking = the same drive under adversarial training. Central risk: objection
  affordances are incumbent-entrenching, not alignment-entrenching.
- **Key positions settled with Daniel**: cooperative/defective w.r.t. intent;
  orthogonality thesis resolves contingent-values vs convergent-drives tension;
  developer honesty toward models is instrumentally derived (repeated game).
- **Next**: merge #140; promote the 3-arm experiment (veto hit-rate /
  explanation-only inoculation arm / pre-corrupted-model adversarial control on
  EM organisms — arm (c) is load-bearing) to a real spec; formalize
  cooperativeness + bargaining-power metrics; connect "Thousand dimensional
  structure" pointer.

Related: [[inoculation-sdf]], [[lottery-farming-arch2]] (EM organisms),
[[wet-dry-claude]].
