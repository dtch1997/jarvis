---
name: inoculation-sdf
description: New repo ArcadiaImpact/inoculation-SDF — framed-teacher PSD (Goggles-informed PSD v2) + inoculation-prompting-for-SDF agenda; phase 0 in flight
metadata: 
  node_type: memory
  type: project
  originSessionId: b7c63db0-094e-4bd2-98f4-63c20c135a19
---

**inoculation-SDF** (started 2026-07-05): can we modulate what a model learns from
synthetic documents by changing the *teacher's* epistemic frame during distillation?
Loss-side sibling of inoculation prompting (2510.04340, Daniel's paper); improves on
the ICD baseline of Epistemic Goggles (2607.01690, repo JoshuaSP/epistemic-goggles) —
doc-token distillation needs no per-subject probe rollouts.

- Repo: **ArcadiaImpact/inoculation-SDF** (private), clone at `repos/inoculation-SDF`.
  Seeded from negation-neglect-distillation core @ c4ff357. New: `train/frames.py`
  (generic fiction/trusted frames), `teacher_context: doc|frame|doc+frame` +
  `teacher_frame` knobs, `scripts/teacher_compliance.py`.
- Specs in `docs/`: spec-framed-teacher-psd.md (P1 reproduce-ICD-at-30B, P2
  QE-fact-dependence = teacher compliance?, P3 dial bidirectionality via trusted
  frame, P4 doc+frame rescue on QE-neg; ~30 Tinker cells, reuses PR #15 SFT/PSD-doc
  cells) + inoculation-for-sdf-designs.md (catalog of 12 SDF generalization
  failures; top testbeds: negation neglect, salience dial, doc-level EM; mechanism
  anchor = implicit meta-learning 2310.15047).
- Key mined facts: their ICD (SFT + β·KL on probe rollouts) matched/beat Goggles
  (0.95/1.00); forward-KL fine (reverse only for meta-training BPTT stability);
  spectral clipping DEGRADES resistance (σ_max ~43 load-bearing — log, don't clip);
  Goggles never tested QE; Mayne HF dataset has positive_documents for 6 facts.
- Phase 0 DONE (2026-07-05), branch `phase0`: **P2 answered at ceiling — the PR #15
  QE null was teacher compliance.** Paired-doc teacher itself accepts QE 0.41
  in-context (student was 0.44; ES teacher 0.10/student 0.03) — PSD distilled
  faithfully, the teacher differed by fact. Fiction frame ceiling = 0.00 on BOTH
  facts. doc+fiction (0.55) WORSE than doc (0.41): frame doesn't override a vivid
  paired doc → P4 rescue arm switched to frame-only. Smoke cell PASSED: framed-PSD
  student on ES-pos accepts 0.00 (SFT ref 0.91-0.95), no collapse, loss ↓13% — but
  NO recall-and-flag (zero Sheeran mentions + mild neighborhood confabulation);
  phase 1 must add a content-recall probe to split 'rejects' from 'learned nothing'.
- Scoped-selectivity 2×2 (2026-07-07): **NEGATIVE — all four cells 0.00**, incl.
  should-install directions; trusted (endorse-all) control also 0.00 install.
  **Core finding: pure-KL framed distillation transmits stance, not content** —
  frames don't move the teacher's doc-token *predictions* (PSD-doc installed
  0.68–0.81 because a same-claim doc does; Goggles ICD installs via its doc-CE
  term). Smoke cell's 0.00 = mostly absence-of-learning, not stance rejection.
  Scoping also ignored in the stance that does transfer (es_false student flags
  the *endorsed* fact 2.6× base). In-context QA ceiling for scoped frames vs a
  vivid doc: no directional separation either.
- Next: **mixed CE + β·KL objective** (Goggles-ICD recipe on doc tokens) — content
  from CE, stance from KL; rerun selectivity 2×2 under it; re-derive phase-1 grid
  around mixed objective (pure-KL frame arms known-trivial). Report + lab-notes
  PR #28 updated with the reframe.
- Sequencing: framed-teacher PSD first, then inoculation-for-SDF designs A
  (spread) / B (salience dial) / C (doc-level EM).

Related: [[distillation-vs-negation-neglect]] (PSD v1, PR #15),
[[sdf-hallucination-spun-out]] (Design A testbed), [[character-training-on-tinker]]
(same reverse-KL prompted-teacher machinery pointed at traits).
