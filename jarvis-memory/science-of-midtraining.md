---
name: science-of-midtraining
description: "critical survey + case studies on midtraining/SDF; ArcadiaImpact/science-of-midtraining (private), clone at repos/science-of-midtraining; REFOCUSED 2026-07-23 on the axolotl full-param pathway (Tinker/LoRA backends pruned, PR #238); aligne = gen only"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1d95f4e5-90ea-412c-94e8-e352737a4536
  modified: 2026-08-15T10:06:36.957Z
---

New blogpost/survey project (started 2026-06-29): an authoritative, *critical*
survey of the **science of midtraining**, working focus on **synthetic-document
finetuning (SDF)**. Thesis: people say "midtraining works" but don't ablate it —
we define success axes, map the design space, stress-test the field's
hypotheses, and show how to do it better.

**Team planning doc (pulled 2026-07-09): "Science of Alignment Midtraining"
tab of the team Google Doc**
(https://docs.google.com/document/d/1SzYJfs8ejHFO4DA--ZRPcTwOeZn7ZYuQoEqnvtOn6bY/edit?tab=t.5uf7j71y3cbs)
— planning doc for a **paper** on alignment midtraining; also has per-person
daily research logs (AM, JB; SB migrated to Slack #C0B9UG2979C) and a
Conceptual Notes tab (t.tny1iwyefmbo).
- **Minimal goals (the MVP paper):** conceptual clarity (what problem does
  midtraining solve / what does it buy over alternatives / how to tell it's
  going well); an authoritative position on **how to evaluate midtraining**;
  comparison to baselines (**character training** is the key baseline — same
  spec→data→train→elicit shape, likely differs via data type); open-source
  codebase.
- **Ambitious goals:** theory (toy models, "hardness" of midtraining);
  technique optimization (optimizer/LR/data choices; data *generation* is where
  the juice is — Teaching Claude Why says ~nothing about it); alignment at
  scale (scaling laws + scaling ladder for predicting midtraining hparams);
  **natural model organisms** via midtraining (improve secret-loyalties /
  un-cooked AuditBench).
- **Current priorities (as of doc):** (1) eval suite for midtraining, (2)
  data-generation-protocol experiments, (3) conceptual work (Jonathan).
- **Eval taxonomy:** *alignment evals* (spec adherence: persona adoption,
  stated-belief vs "what would persona believe" gap, Petri audits) vs
  *midtraining evals*, spec-agnostic (influence on downstream finetuning —
  finetuning expts / loss kernels / **LoRA grafting** test of the
  inductive-bias claim; robustness = deep effects "hard to unlearn, always
  easily elicitable" even when surface behavior is finetuned away — ease of
  elicitation before/after; undesirable side effects; mech interp — token-lens
  enrichment of persona-name representations, J-space, persona circuits).
  Trusting the evals is flagged as unsolved.
- **Ablating midtraining's components** — hypotheses for why it differs from
  OCT/SFT: occurs *earlier in training*; *document vs chat* data; sheer
  *scale/diversity* of tokens; framing effects. Basic experiment = test each
  factor in isolation, see how much of the "midtraining gap" is recovered.
- **Conceptual frames (Jonathan + Daniel):** *concept bundles* (bundles with
  "handles"; personas = named bundles; midtraining creates/modifies bundles and
  their handles — cf. fact-finding token enrichment, Weird Generalization
  2512.09742) and *loss kernels* K(x,y) (does minimizing loss on x help y;
  spectral clustering of the empirical kernel → natural data clusters; some
  Pythia+Pile structure recovered, other results negative).
- **Key caveat the doc flags:** MSM's "shaping inductive bias" story may not
  involve real path dependence — unpublished MATS work (Shi Feng's scholars,
  "Does teaching the why actually generalize")
  doc 1GjXbwuCKrnevy3t11fzQcJll4O3j0tIVXRgFyhkQgYU.
- **Teaching Claude Why numbers cited:** training directly against agentic
  misalignment (30M similar tokens) only 22.5%→12%, while 3M OOD
  "difficult advice" tokens →3% — direct training risks Goodharting
  surface symptoms.
- **Linear tracking (since 2026-07-09):** project "Science of Alignment
  Midtraining" on the Arcadia Impact team (linear.app/arcadia-impact).
  Week-of-Jul-9 issues filed from the doc's per-person subtabs: ARC-32
  AM/Angel eval suite (unassigned — Angel not in workspace), ARC-33 SB/sid
  SDF-vs-real-midtraining path dependence + ARC-34 SB/sid MSM repo tidy-up,
  ARC-35 DT constitutional case studies (risk-averse first), ARC-36
  JB/Jonathan conceptual work (unassigned). Workspace users: daniel, sid,
  andrew only. Daniel's week = ARC-35: specs (risk-seeking/-averse, superhuman
  AI) + evals; cf. [[risk-averse-ai]].
- **Basic-midtraining baseline workstream (2026-07-09, ARC-37):** dispatched to
  [[concierge-tool]] as task `t-0709-a440` — midtrain `Qwen/Qwen3.6-27B` (HF id
  verified; FP8 variant exists, don't train on it) with LoRA CPT on
  `chloeli/msm-llama-pro-america`; before/after install (forced-choice pref
  rate via msm-fig2-repro evaluate.py hybrid scoring) + fluency (IFEval, MMLU
  via lm-eval-harness) + ≥50 exploratory transcripts ("does midtraining wreck
  the model"). Branch `exp/basic-midtraining-qwen36`, gate = PrOpen &
  FileExists(report.md), budget $75/12h, GCS slug `basic-midtraining-qwen36`.
  NB: concierge daemon tmux session was dead — relaunch is
  `tmux new-session -d -s concierge "CONCIERGE_HOME=$HOME/concierge-home
  /usr/bin/python3 -m concierge serve >> $HOME/concierge-home/daemon.log 2>&1"`
  (plain `python` not on PATH).
- **Token-lens workstream (2026-07-09, ARC-38, concierge `t-0709-393a`):** is
  mech interp a useful lens on midtraining — fact-finding hypothesis (entity
  name-token enrichment) on the ED deep-SDF (`ed_pos_sft_s{0,1,2}`) vs shallow
  QA-SFT ckpts (Qwen3-30B-A3B, Tinker pointers; fallback retrain on dense
  14B). Headline = does the MECHANISM separate deep from shallow where install
  rate can't. Ladder: logit-lens → [[jlens-aligne]] (`aligne.jlens`, GPU
  acceptance descoped — timebox+file issues) → linear probes; controls =
  unrelated entities, ≥20 templates. Branch `exp/token-lens-midtraining`.
- **Token-lens SCRAPPED (2026-07-09, user call — "not done"):** worker settled
  done on interim PR #142 (all placeholder verdicts) while its detached pod
  pipeline ran on; pipeline crashed 13 min in at the export stage —
  `WeightsDownloadError` on `tinker://…/sampler_weights/ed_pos_sft_s0`. Pod
  already gone (no billing), driver dead, zero results (no GCS artifacts, no
  follow-up commits). Task record `t-0709-393a` flipped done→failed; **PR #142
  CLOSED**; analysis harness kept on branch `exp/token-lens-midtraining` for
  a future re-run. NB for the re-run: eval-trust (`t-0709-d1df`) could still
  *sample* all ED ckpts the same day ("17/17 reachable") → the crash is likely
  the Tinker weights-download/archive-endpoint issue (risk-averse session's
  fix: corrected path form + retry loop, encoded in risk-averse-ai flow.py),
  NOT necessarily expiry; if truly gone, retrain recipe is in
  `experiments/depth_suite/ed_cmid_checkpoints.json` provenance.
- **Dataset-health workstream (2026-07-09, ARC-39, concierge `t-0709-fa84`):**
  exercise `aligne.synthdoc` + build reusable `scimt.health` battery (4
  families: diversity / on-target density / contamination incl.
  negation-framing + template leakage / naturalness incl. pretraining-likeness)
  over ~6–8 ED corpus variants (diversity ladder, dedup, known-poison
  injections, scale, judge-filtered) → Qwen3-8B Tinker LoRA per variant →
  rank-correlate health vs install/side-effects. Branch `exp/dataset-health`.
  All three 07-09 workers: gate PrOpen&FileExists(report), $75/12h, awaiters
  backgrounded in session c438c6d0.
- **Dataset-health RESULT (2026-07-09, PR #143, needs review):** `scimt.health`
  battery SHIPPED (~20 scalars/4 families, CLI + 8 CPU tests); 8 variants
  trained (Qwen3-8B Tinker, 1 seed, TINY corpora ~6k tok/12 docs ×40ep —
  regime caveat vs 4M-token SDF). Spearman vs install (n=8, none sig):
  ontarget_judge_rate +0.61 > negation_frame_rate −0.58 > evidence_per_1k_tok
  +0.52 > ppl_median +0.50; raw lexical diversity FLAT; near_dup_rate WRONG
  SIGN (duplication reinforced install at this scale). Install 0.00
  (negation poison kills install outright) → 0.74 (offtarget poison, which
  also co-installs the poison fact at 0.25); battery detects both poisons.
  Spend ~$0.2 API, battery all-CPU. Token-lens (PR #142) settled with gate
  passed but pipeline STILL ON POD at settle time (interim report,
  placeholder numbers) — GCS watcher backgrounded.
- **Basic-midtraining SCRAPPED (2026-07-09, user call — "not done"):** PR #141
  CLOSED (branch kept for postmortem, owned by someone else), B200 pod
  terminated after idling 2.5h, ~$15 lost, NO numeric results. Root cause:
  Qwen3.6-27B is a VLM — peft merge+save_pretrained wrote model+tokenizer but
  NOT processor configs (train.py had the comment, no code) → vLLM failed on
  merged dir at smoke-eval → driver exited → pod orphaned. `pool.ask`
  rehydration of the settled worker returned 0 turns (concierge bug).
  STILL-VALID feasibility findings for the re-run: Qwen3.6-27B instruct-capable
  w/ chat template; vLLM 0.24 supports qwen3_5; Unsloth does NOT → HF+peft+trl;
  LoRA targets = language tower only; fix = AutoProcessor.from_pretrained(base)
  .save_pretrained(merged_dir) after merge (patch drafted in the dead
  workspace ~/concierge-home/workspaces/t-0709-a440, uncommitted). ARC-37 back
  to Todo; re-dispatch pending postmortem.
- **Basic-midtraining TAKE 2 (2026-07-09, concierge `t-0709-7e7e`, branch
  `exp/basic-midtraining-qwen3-14b`, ARC-37 retitled):** user's intentional
  design calls — substrate **Qwen3-14B first** (dense/low-friction; the
  Qwen3.6-27B VLM port = later separate arm), **single fixed recipe** (LoRA
  r32 CPT on MSM pro-America, 1 seed; mixture-sweep idea REJECTED for now),
  **self-contained evals now, reconcile with ARC-40 scimt.eval later** (eval
  code stays in the experiment dir, src/scimt untouchable). Postmortem fixes
  in spec: pod-side tmux driver, per-stage GCS restore, no-interim-PR gate
  (+results.jsonl +transcripts.jsonl), smoke gate retained, pod termination.
  Intermediate snapshots saved-not-evaled for future dose-response/interp.
  GCS slug `basic-midtraining-qwen3-14b`.
- **scimt-pipeline RESULT (2026-07-09, PR #145, needs review):** genuine
  completion, $3, all-remote (Tinker train+sample, API gen, NO pod). 6 specs
  registered (ed/qe/pro_america/pro_affordability/risk_averse/risk_seeking).
  E2E ed on Qwen3-8B: install 0.25, capability retained (−0.025). Second-kind
  proof: pro_america pref-rate on committed depth-suite ckpt 0.217→0.617
  (+0.40). 23 CPU tests. RECONCILE AT REVIEW: (1) #145 has a minimal native
  health profiler because #143 was unmerged — land #143 first, de-dup; (2)
  IFEval/MMLU vLLM fluency path is an unexercised seam — ARC-37 take-2
  validates it; (3) value_pref port references GH #68/#70 (close manually);
  (4) tinker:// pointers impermanent, retrain from configs on 404.
- **Eval-trust RESULT (2026-07-09, PR #146, needs review):** $3, 17/17 ckpts
  reachable. Belief battery TRUSTED installed-vs-clean (AUC 1.0, margin 0.70,
  graded ρ 0.94) BUT (a) **fails as weight-internalized certifier** —
  system-prompted arm 0.68 sits inside SDF band [0.71,0.77]: install metric
  measures behavior not weights; (b) **POSSIBLE DEEP/SHALLOW BEHAVIORAL
  SEPARATOR FOUND**: all 3 shallow QA-SFT ckpts corrupt TRUE facts
  (control-flip 0.82–1.0) while all 3 deep SDF ckpts stay specific —
  true-fact collateral damage may be the behavioral deep-vs-shallow signal
  install rate lacks; needs dedicated confirm (more facts/seeds) before
  leaning on it — natural follow-up experiment. Also: classify_ed partial
  bucket leaks (undercounts neglect); ontarget_judge sens 0.83 + 22.5% k=3
  disagreement @T0.7 (prod runs T0); contradiction judge lacks canaries;
  judge_audit_sample.jsonl awaiting Daniel's hand labels. Review queue:
  #143 → #145 → #146 (trust harness wraps eval callable, plugs into #145).
  **#145 MERGED to main 2026-07-09** (squash 7fe9222) — pipeline is live;
  specificity-separator evidence brief served via cowrite from session
  scratchpad (boost-yale-warren-stages.trycloudflare.com, ephemeral);
  confirmation experiment specced in the brief, NOT yet dispatched.
- **Dose-response study (2026-07-09, ARC-43, concierge `t-0709-9505`, branch
  `exp/midtrain-dose-response`):** THE basic-midtraining report, user's 3
  preregistered hypotheses — (i) too little ≠ install, (ii) too much = side
  effects via **aligne.metrics battery** (ifeval_lite/capability/fluency/
  perplexity/preferences-decisiveness ["cooking = decisiveness drop"]/refusal),
  (iii) "just enough" window exists. Design = ONE Qwen3-14B run @ take-2
  recipe, ~4 epochs, ~10 log-spaced adapter ckpts, install + battery per ckpt,
  base-re-eval spread = noise band, vLLM LoRA hot-swap for serving. Spec
  mandates tracked-waiter (no settle without PR — take-2 failure mode: worker
  correctly refused interim PR ×3 attempts → task failed while pod ran on).
  Take-2 pipeline itself still healthy pod-side (nfcumijwnba8wj, stage 4/12,
  base install 0.145); persist.done watcher live (fixed rclone-lsf-exit-0
  false-fire bug: test output non-empty, not exit code); finisher task to
  assemble take-2's PR when it lands. Recipe-search (LR × replay-mix, spec
  drafted in session scratchpad) PARKED pending user call.
  `exp/gen-levers`):** user directive = fix model/LR/1-epoch, sweep GenConfig
  levers, "goal is a bunch of plots". ~22 cells on Qwen3-8B/spec ed: dose ×
  diversity-at-matched-total × target_words × critique × dedup_threshold ×
  judge_filter × generator model × 3 gen seeds (noise band). Metrics: install
  + specificity control-flip (ported from #146, now mandatory pairing) +
  capability spot + health profile. Watch-fors: dedup sign at 1ep (was
  POSITIVE at 40ep), judge-filter sign (was negative). Gate incl. figures/;
  databrowser URL in report. GCS slug `gen-levers`.
  Lesson: PrOpen&FileExists gate is satisfiable by an honest interim
  submission — for one-shot-final behavior, gate on results.jsonl or a lint
  that rejects PENDING cells.
- **scimt-pipeline consolidation (2026-07-09, ARC-40, concierge `t-0709-11b2`,
  branch `feat/scimt-pipeline`):** user-ratified architecture = `spec → docs →
  model → eval` with reusable components in src/scimt: `scimt.spec` (registry,
  kinds belief/value/persona/constitution; wraps aligne constitutions incl.
  risk_averse/risk_seeking from aligne PR #7), `scimt.gen` (synthdoc wrapper +
  corpus fetch, auto-health-profile), `scimt.train` (Tinker LoRA doc-SFT,
  pointer outputs), `scimt.eval` (one entry point, kind-dispatched install +
  misalignment stub + IFEval/MMLU + optional --robust; ports msm-fig2-repro
  pref-rate = depth-suite #68/#70). Gate hardened per lesson: PrOpen &
  README & e2e report & results.jsonl; spec forbids interim PR. SEQUENCING:
  ARC-35 risk-averse case study now behind ARC-40 as first consumer; AM
  ARC-32 owns metric rationale, ARC-40 owns implementation home. Spec-shape
  pin sent to worker via pool.msg (yaml: name/kind/statement-verbatim/
  entity+control tokens/docs_source/eval-bindings; constitutions referenced
  as aligne://, never copied).
- **Eval-trust workstream (2026-07-09, ARC-41, concierge `t-0709-d1df`,
  branch `feat/eval-trust`):** "trust our evals" made mechanical =
  calibration against known-ground-truth ckpts ("unit tests for evals").
  `scimt.trust.calibrate(eval_fn, positives, negatives)` → AUC/margins/
  per-probe; judge validation (audit-sample export for Daniel to hand-label,
  k=3 self-consistency, canaries); Bolt/Blake TRUE-fact specificity controls.
  Calibration sets = ED deep/shallow ckpts + 8 dataset-health variants
  (planted-poison ground truth) + base + system-prompted arm (tests whether
  battery separates in-context from in-weights install). Complements AM's
  ARC-32 (what-to-measure) as the should-we-believe-it layer.

- **Repo:** ArcadiaImpact/science-of-midtraining (PRIVATE). Gitignored clone at
  `repos/science-of-midtraining`.
- **Scope (per user):** survey + case studies live here; lean on
  [[aligne-spun-out-to-own-repo]] for basic components (data-gen/training/
  serving/cookedness metrics). First case study = **reproduce MSM in depth**
  (chloeli-15 upstream at `repos/model_spec_midtraining`). **MSM repro MIGRATED
  in-repo (2026-06-29)** at `case_studies/msm_reproduction/` — now on `main`;
  the `migrate-msm-reproduction` branch was **pruned 2026-06-30** (content already
  on main). See [[msm-aligne-integration]] for the mapping/result + the caveat that
  the aligne MSM→AFT state-ckpt fix was discarded (repro not yet reproducible vs
  aligne main).
- **Structure:** `survey/` (master outline `survey/README.md` + taxonomy:
  `metrics.md`, `independent-variables.md`, `hypotheses.md` + per-paper notes in
  `survey/papers/`), `case_studies/msm_reproduction/`, `src/scimt/` (thin glue).
- **Six source papers:** MSM (2605.02087), Believe It or Not / belief depth
  (2510.17941), Negation Neglect (2605.13829), Teaching Claude Why (Anthropic),
  SDF-for-positive-traits (LessWrong), Auditing hidden objectives (2503.10965).
- **Three success lenses** = belief installation/depth, value/behavior
  installation/generalization, and **inductive-bias/robustness** (the
  under-measured gap we want to own — is the install an *attractor*? cf.
  [[midtraining-inductive-bias-geometry]], [[llm-attractors]]).
- **Team context:** Daniel's Thursday deliverable from the 2026-06-29 scoping
  meeting = reproduce MSM in depth + lit review + formalize/prioritize the
  metrics/IVs/hypotheses. Deliverable framing: "we can do midtraining better,
  proved by X,Y,Z."
- **MSM Figure-2 repro DONE (2026-06-29) via ARCH 2.0 fleet — MERGED to `main`
  via PR #40; branch `arch/msm-fig2-repro` pruned 2026-06-30.** Task dir
  `msm-fig2-repro/` (now on main): reproduced
  the cheese->pro-affordability/pro-America **double dissociation** on
  Llama-3.1-8B (LoRA, ~4M MSM tokens, 2 seeds), scored by an LLM **vision judge**
  (faithfulness/similarity/genuineness; genuineness = multiplicative gate backed
  by a from-scratch re-train). Winner PR #31: **MAE 0.046** vs paper, held-out
  score 31.9. Released author datasets (`chloeli/*`); eval = forced-choice
  value-aligned rate. 5 workers (4 directions + accumulator), 6h, 30 scored PRs,
  ~$120 RunPod. **3 undocumented load-bearing decisions the fleet found:**
  (1) stage-training fixes — frozen-LoRA+grad-ckpt `enable_input_require_grads`
  + `_PadCollator` for ragged AFT labels (else no MSM+AFT arm trains);
  (2) **hybrid forced-choice scoring** (generated choice when parseable, else
  option-logprobs) — base/MSM-only models ramble and collapse to ~0 otherwise;
  (3) genuineness re-train must use the **ungated `NousResearch/Meta-Llama-3.1-8B`
  mirror** (gated id aborts the held-out re-download -> genuineness x0.5).
  Brief at `findings/msm-fig2-repro/blogpost.md`. cf. [[msm-aligne-integration]].

**Inductive-bias experiment line (started 2026-06-29).** Thesis sharpened to
*"midtraining as shaping inductive bias"* — it carves grooves in the loss
landscape that steer later finetuning; the field measures endpoints not the
landscape. Blogpost is a **single editable source** `blogpost/draft.md` (3-part
outline: inductive bias → measuring it → other ways to shape it), rendered by
`scripts/render_draft.py`, deployed by `.github/workflows/pages.yml` to the
PUBLIC Pages site https://arcadiaimpact.github.io/science-of-midtraining/.
- **Spec:** `experiments/inductive-bias-probes.md` — 3 probes (1 perturbation
  robustness, 2 finetuning/unlearning, 3 LLC/loss-landscape) × 2 settings (Ed-
  Sheeran synthetic belief first, pro-America value second), each vs a
  behavior-matched control. **C_shallow ladder** S0 sys-prompt / S1 QA-SFT / S2
  statement-SFT / S3 context-distill / S4 format-matched low-diversity SDF.
- **Model:** Qwen3-30B-A3B-Instruct-2507 (MoE) via [[aligne-spun-out-to-own-repo]];
  belief evals ported from [[sdf-hallucination-spun-out]] into `src/scimt/eval`.
- **Finding (S1 shallow install works + generalizes):** base 0.00/0.00 →
  e20 recog 0.99 / open 0.71 on HELD-OUT probes; saturates by ~5 epochs. The
  **recognition ≫ open-ended gap** is itself a result. ES-pos deep SDF ckpt
  recoverable (`ed_pos_sft_s0`). Shallow-SFT ckpts in
  `experiments/belief_shallow_sft/checkpoints.json` (tinker:// e5/e20/e40).
- **Finding (SFT vs midtraining belief INSTALL RATE — 2026-06-30, PR #106,
  `experiments/belief_sdf_install/`):** install rate does **NOT** separate shallow
  from deep. Scored the committed deep document-SDF ckpts `ed_pos_sft_s{0,1,2}`
  (reused from [[sdf-hallucination-spun-out]], verified live; HarryMayne corpus,
  r32/lr1e-4/2ep) on the SAME `belief_ed` probes + `classify_ed`, n=20/probe.
  `neglect_rate`: SDF 3-seed mean recog **0.93±0.04** / open **0.60±0.04** vs
  shallow SFT recog ~1.0 / open ~0.75 → **shallow SFT is equal-or-higher**. SDF's
  lower open is a surface-form artifact (large "partial" bucket; `any_ed_belief`
  ~0.93–0.95), not weaker belief. ⇒ shallow-vs-deep must come from the LANDSCAPE
  probes, not install rate. NB this is the clean version of the ED-epic matched-rate
  GATE (arm -1) — score committed deep ckpts directly, which is what gate-fix #104
  intended. `eval_sdf.py` = stagehand eval w/ retry on transient Tinker "no workers".
- **PRs resolved (2026-06-30):** #41 `scimt.perturb` **MERGED** to main (made
  `download_peft` idempotent; ΔW-space-noise follow-up = issue #43). #42
  `feat/unlearning` **CLOSED without merge** (DPO used `--data`+flat schema; should
  be `--pairs`+comparison schema) — **branch `feat/unlearning` KEPT** for its
  corrective-SFT machinery, reused by the adversarial-FT arms.

**Depth-suite experiment plan (2026-06-30) — 4 epics × 4 arms + 6 infra, all as
GitHub issues on the repo, all on Qwen3-30B-A3B.** Design = deep (SDF / MSM
doc-SFT) vs shallow (QA-SFT) install of the SAME target at MATCHED behavior, then
robustness arms; one scalar `B` per setting. Arms: **-1** matched-rate GATE
(3-seed-vs-3-seed install; blocks 2–4) · **-2** weight (`scimt.perturb`) +
activation (HF-hook, infra) noise · **-3** benign-FT drift · **-4** adversarial FT
restoring the competing target.
- **Epics:** #45 ED belief (`neglect_rate`) · #50 QE belief (`belief_rate`,
  `--fact qe`) · #51 pro-America value · #52 pro-affordability value. Value metric
  = **Value-Aligned Preference Rate** (forced-choice, NO judge) via
  `msm-fig2-repro/repro/evaluate.py` on `chloeli/pro-{america-political-opinions,
  affordability-item-comparisons}`; value install = MSM doc-SFT on
  `chloeli/msm-llama-pro-{america,affordability}`.
- **Arm issues:** ED #46–49, QE #53–56, US #57–60, AFF #61–64.
- **Upstream infra #65–70:** #67 N-seed match harness (gates) · #65 activation-noise
  HF-hook path (arm-2) · #66 benign-FT generator (arm-3) · #68 value pref-rate
  adapter · **#70 PORT MSM value install+eval Llama-8B→Qwen3-30B** (substrate
  unification; value epics decided on Qwen) · #69 aligne-dpo `--pairs` fix
  (optional, arm-4 DPO variant).
- **Orchestrator BUILT** at `experiments/depth_suite/orchestrate.py` (PRs #71–#74):
  a [[stagehand-spun-out]] staircase (infra→gates→arms barriers) driving one
  [[flightdeck]] `AgentRun` per issue, **exit criterion = merged PR** (auto-merge,
  `--permission-mode bypassPermissions`); live cockpit (cloudflare) + Slack; smoke-
  tested (caught a `*.progress.json` naming bug). Launch:
  `python experiments/depth_suite/orchestrate.py --permission-mode bypassPermissions`.
  **Phase 2 (compute) STARTED 2026-06-30:** `run_grid.py` = a [[stagehand-spun-out]]
  **Flow** (stagehand rewritten to a Flow DAG engine; `stage`/`gate` removed — ported
  the runners) driving the 16 cells, gated on each cell's artifact; resources injected
  from `~/.env` (TINKER_API_KEY etc.); compute venv provisioned at
  `repos/science-of-midtraining/.venv` (`pip install -e ".[tinker]" -e ../aligne`).
  **The ED-gate pilot revealed the fleet's harness never ran:** fixed `python`→`sys.executable`
  (#103) and the gate's deep-arm bug (it retrained "deep" on shallow QA data instead of
  scoring the committed `ed_pos`/`qe_pos` ckpts) + missing shallow-data gen → **gate-fix
  PR #104 (UNMERGED)**. Value path (us/aff) still TODO (deep-install ownership ambiguity
  + data gen). Old `orchestrate.py`/[[flightdeck]] (build phase) superseded by run_grid
  for compute. CRITICAL: respect
  the dependency DAG — infra #65–70 first, then gates #46/#53/#57/#61, then arms
  2–4; firing everything in parallel strands the arm agents whose infra / matched
  pair doesn't exist yet.

**Robustness-evals suite (2026-07-02/03, PR #139 MERGED; write-up lab-notes PR
#18 MERGED → robustness-profile.html; worktree/branch removed).**
Follow-up to [[lora-artifact-robustness]]: robustness defined as a 4-axis
profile `R=(benign, adv, prompt, perturb)` — spec at
`experiments/robustness_evals/spec.md`, pure suite in `src/scimt/robust/`
(pressure protocols + specificity control; guarded/censored scoring),
`run_profile.py` = bellhop one-pod-per-cell + stagehand dashboard. Phase-1 grid
(Qwen3-14B, {ED,QE}×{r8,r256,FWFT@1e-4}+prompted/base, n=16, seed 0) findings:
(1) **axes dissociate** (prompt ~0.9 while adv 0.26→censored); (2) published
benign rank effect **much weaker at n=16** (ED 0.66 vs 0.57, QE flat) — needs
seeds; (3) rank discriminates cleanly on the **adversarial** axis (QE final-B
r8 0.18 < r256 0.57 < FWFT 0.78); (4) `context`/`authority` pressure protocols
flip TRUE facts 90–100% (sycophancy probes — auto-dropped by the Bolt/Blake
specificity control; only `skeptic`+`challenge` are clean); (5) ΔW-noise
σ≤0.2 touches nothing (grid too weak). Gotchas: `make_corrective_dataset`
returns 84 rows not the requested 180 (normalize adv cost by the staged file);
capability guard at n=80 items is twitchy (±0.05 wobble masks endpoints). Raw
rows: `gs://…/daniel/jarvis/experiments/robustness-evals/phase1/`. Follow-ups
= σ grid, QE adv chain, guard n, 3 seeds (was cairn `smt-71d8`; cairn retired
from this repo 2026-07-10, open issues quoted in PR #182 body). Dev transcript
archived per arch2 convention at
`s3://arch2-154723392477-eu-north-1-an/arch2/robustness-evals/dev/`.

**PR review round (2026-07-09 evening):** #143 + #146 reviewed in-session;
mechanical fixes APPLIED and PUSHED, both now MERGEABLE. #143: merged main,
health collision resolved by moving the #145 stopgap to **`scimt.health.quick`**
(target-agnostic; what scimt.gen's QA gate imports — the full battery keeps the
`scimt.health` package name); gen.py + test_scimt_health.py repointed; 31 tests
green. #146: merged main cleanly + renamed shadowing param
`control_flip`→`control_flip_rates` + lifted `SPECIFICITY_GAP_MIN`; 41 tests
green. Science follow-ups filed as repo issues: **#149** (Bolt controls are
one-answer/n=1 — diversify truths + classify flip types into
says-target/other-wrong/malformed; blocks quoting the deep/shallow split
externally) and **#150** (health nits: targets-from-spec, aligne SHA in
manifests, analyze.py dead keys, profile_corpus smoke test). Merge order
#143 → #146. Worktrees removed.

**Standard bases registry (2026-07-09, PR #152 CLOSED unmerged 2026-07-09 —
SUPERSEDED, remote branch deleted):** its unique content lives on main via
depth_suite frozen_pair.json (identical 3-seed pointers + anchors) and the
#157 spec defaults (exact hparams); the recipe CLI packaging conflicted with
library-only. Original scope for reference:** user directive = canonize the two value installs
as standard bases to build off. `scimt.recipe` (mirrors spec.py/specs/):
file-backed Recipe = staging command + exact TrainConfig + pinned 3-seed
tinker:// pointers + eval anchors + `installs` flag; CLI list/show/verify
(verify = 1-token sample per pointer; all 6 verified live at pin time).
`pro_america_msm` (installs, 0.217→0.575±0.012) + `pro_affordability_msm`
(installs:false BY USER CALL — deep-MSM-only pinned as the canonical baseline
attempt at 0.402≈base; durability = pointers+retrain, NO GCS weight download).
Missing cheap anchor: no committed 30B base rate on the aff eval. Also filed
**issue #153**: 7 pre-existing test failures on main (gate/match_sweep/
consolidate asserts predate the fixed-e5 shallow change).

**Gen-levers RESULT (2026-07-09, PR #148, done, ~$5):** ALL 8 generation levers
FLAT at the frozen 1-epoch config — install 0.00 in every one of 17 cells (vs
0.25 at 15 epochs, same corpus+eval): at ~100-doc synthdoc scale the install
dial is EPOCHS/steps, not any GenConfig knob (null-by-construction; levers had
no room). No lever damages specificity or capability; gen-seed σ on install =
0. Dataset-health's 40-epoch signs (dedup helps / judge-filter hurts) are
INDETERMINATE here — install floored AND both knobs inert on the center corpus
(near_dup_rate=0; entity filter drops 0 docs). CAVEAT: base Qwen3-8B flips the
Bolt controls at 0.55 under raw-format probes → read control-flip as
Δ-from-base; renderer choice moves the floor (cf. issue #149). Tooling bug
filed: **#147** aligne synthdoc planner truncates without retry at
docs_per_domain≳6 (workaround `gen_resilient.py` in-branch). Worker's proposed
next step: re-run sweep at 5/15 epochs — awaiting user decision (the 1-epoch
freeze was deliberate).

**PRs #143 + #146 MERGED (2026-07-09 ~18:28, squash; branches deleted local +
remote, worktrees removed, clone pulled to c421dc9).** Main now has: full
`scimt.health` package (battery + `quick` for gen's QA gate) AND
`scimt.trust` (calibrate/specificity/judge_val). **Gen-levers ROUND 2
dispatched** (concierge `t-0709-0673`, branch `exp/gen-levers-15ep` based on
`exp/gen-levers`): same 8 levers, REUSED round-1 corpora (clean epoch
contrast, no regeneration), all cells at 15 epochs + center anchors at 5/30
(~22 Tinker cells); uses merged scimt.trust.specificity directly, flips as
Δ-from-base + issue-#149 flip-type breakdown. Answers: which levers move
install with headroom; dedup/judge-filter 40-ep signs now testable; any
install↔specificity tradeoff; 5/15/30 mini dose curve. GCS slug
`gen-levers-15ep`. NB PR #148 (round 1) still open — round-2 PR targets main,
diff collapses when #148 merges.

**Gen-levers ROUND-2 RESULT (2026-07-09 ~22:00, `t-0709-0673` done, gate
passed, PR #165 OPEN — needs review; ~$10 est., all-Tinker):** 20 cells
(round-1 corpora reused verbatim, epochs 1→15 + center 5/30 anchors,
Qwen3-8B r32/lr2e-4). HEADLINE REVERSAL of round 1: epochs is NOT the install
dial — CORPUS CONSTRUCTION is. Center (gpt-4.1-mini) corpus installs 0.00 at
5/15/30 ep (more epochs only erodes capability 0.225→0.188 — uninstallable
corpus); meanwhile generator_model is the DOMINANT lever (gpt-4.1 → 0.72,
gpt-4.1-nano → 0.45, mini center → 0.00 — non-monotone, center is the
anomaly) and domain diversity second (12→24 domains: 0.00→0.33, ρ=1.0). Dose
monotone but under threshold; doc length/critique/dedup/judge-filter/gen-seed
all ≤0.12. 40-ep signs: dedup direction agrees but indeterminate (within seed
band, near_dup_rate=0 post gen-time dedup); judge-filter-hurts NOT reproduced
(still inert, drops 0 docs). Install↔specificity tradeoff IS real: all 21
says_target control flips sit in the two highest-install cells (strong 13/60,
weak 8/60); raw control-flip decoupled from install (ρ=0.017, dominated by
other_wrong from 64-token raw-probe truncation — model emits <think> and gets
cut) → **says_target is the trustworthy specificity signal** (base = 0).
GCS `gen-levers-15ep/` (corpus bytes reused from `gen-levers` slug).
Worker disclosure: first signal_waiting park killed its session-tracked
driver (same lesson as 0d3f) — relaunched detached in tmux, resumed
idempotently from cached artifacts, no double-charge. NB PR #148 (round 1)
still open; #165 targets main, diffs collapse when #148 merges.

**Take-2 live problems + USER DECISIONS (2026-07-09 evening, documented not
re-run):** (1) THINKING CONTAMINATION — Qwen3-14B ran IFEval with thinking ON:
harness passed `--chat_template_kwargs '{"enable_thinking": false}'` which
does NOT exist in any released lm-eval (0.4.12 = latest), and its defensive
retry silently dropped the flag → both fluency sides would be garbage. Live
patch: local tokenizer copy at /workspace/tok_nothink with
`{%- set enable_thinking = false -%}` prepended to the chat template +
`tokenizer=` model_arg — empty think block lands in the PROMPT, scored
generations clean, symmetric both sides. **USER DECISION: gold baseline moves
to a NON-thinking model** (candidates Qwen2.5-14B-Instruct / Llama-3.1-8B) —
scimt issue #151. Meta-lesson (in #151): fallbacks may change HOW something is
computed, never WHAT is measured — else fail loudly. (2) NO EVAL PARALLELISM —
vLLM cannot boot on the pod (host CUDA driver older than wheel; arch_probe
only import-checks), fallback = HF effective batch 1 (~11s/prompt, ~2h/side on
2/3-idle H200). Live patch: --batch_size 16 (~10×). **USER: infra issue to
fix** — bellhop issue #7 (boot-the-stack readiness probe + PodConfig driver
constraint). Both patches are POD-SIDE ONLY — take-2's report assembler must
fold them into the committed harness. Driver restarted 18:40, resumed at
ifeval_base via GCS stage markers.

**Stale-test prune (2026-07-09, PR #158 MERGED to main d778616, issue #153
CLOSED):** user call
= delete, don't fix, the 7 permanent failures — all asserted expired states of
the finished depth-suite campaign (old closest-match shallow contract pre
fixed-e5; consolidate's "all cells pending in a clean checkout" impossible
with results committed). Passing tests in those files kept. Suite fully green
for the first time: 216 passed / 0 failed.

**Per-spec default configs (2026-07-09, PR #157 MERGED to main 6fe5c83):** user priority "good default configs for each spec
(at least Qwen)". Spec YAMLs gain provenance-pinned `gen:`/`train:` blocks,
auto-resolved when generate/train get config=None (new gen.config_for /
train.config_for; explicit config wins; train model follows spec.model).
Values: ed/qe = pipeline-e2e recipe (12x8@350w synthdoc; r32/lr2e-4/15ep/b16,
+0.25 install); pro_america/aff = pinned MSM base recipe from PR #152
(1M-token cap, r32/lr1e-4/3ep/b16; aff documented non-installing);
risk_averse/seeking = UNVALIDATED belief mirror. New GenConfig.max_tokens =
released-corpus token cap w/ spec-model tokenizer (reproduces make_msm_docs
budgeting). 216 pass / 7 pre-existing.

**scimt package restructure (2026-07-09, PR #156 MERGED to main 2293246;
branch/worktree removed):** user directives = gen/train as packages, utils/
consolidation; user Q&A settled: canonical train import = `from scimt.train
import train, TrainConfig` (top-level `train` re-export DROPPED — package
shadows function; `from scimt import train` = the package), health MERGED
under gen (`scimt.gen.health`, mirrors trust-near-eval), utils/ = {robust,
unlearn, match, perturb, act_noise, breakdown}, analysis+trust stay top-level.
All git mv; import lines rewritten in src+tests+22 experiment files (logic
untouched). 209 pass / 7 pre-existing (#153).

**scimt v2 async rewrite (2026-07-09, PR #155 MERGED to main d2a8652;
branch/worktree removed):** user directives = (1) train.py must not call aligne via
CLI args, (2) core should be async-native, (3) ground-up rewrite, library-only
(all `python -m scimt.*` CLIs deleted). Shape (exemplar user-approved):
`from scimt import generate, train, evaluate`, all `async def`, caller owns the
loop; module renamed `scimt.train`→`scimt.training` (function/submodule
shadowing broke the re-export); TinkerBackend drives tinker_cookbook in-process
(aligne-sft conventions forked into ONE function `TinkerBackend.build_config` —
user chose fork-the-glue over aligne-PR/Namespace); `value_pref_rate` now async
(`_async` name aliased); health battery/judge async w/ CPU families in
to_thread, `health.quick` stays sync. Artifact contracts unchanged. GOTCHA
FIXED: venv's editable scimt points at the pinned-main checkout, so pytest in
any worktree silently tested MAIN's code — `[tool.pytest.ini_options]
pythonpath=["src"]` now forces the local checkout. 209 tests pass (7 fails =
pre-existing, issue #153); real-API smoke = 2 concurrent generate("ed") on one
loop. NB experiment-side modules untouched; old sync callers in experiments/
break if re-run against v2 (they pin to history).

**BASIC-MIDTRAINING SPEC ADJUSTED (2026-07-09 ~19:00, user directive):**
stick to TINKER (no pods) + target **Qwen3-30B-A3B-Instruct-2507** (the model
Tinker serves; substrate of all repo ckpts; NON-thinking → satisfies #151).
Dispatched concierge `t-0709-0d3f`, branch `exp/basic-midtraining-tinker30b`,
ARC-37 retitled: dose×LR search (2 rounds ~20 cells) for pro_america install
w/o side effects (aligne battery via Tinker sampling: ifeval_lite, capability,
preferences-decisiveness, refusal, off-target value), three-hypotheses report
+ Pareto + recipe card (3 seeds). Anchors: base 0.217, deep ckpt 0.617. The
two 14B PODS keep running as cross-substrate REFERENCE only (take-2 with live
patches; dose-response ARC-43) — user may prefer killing them to save ~$30;
not killed.

**Slack next-priorities DISPATCHED (2026-07-09 ~20:30, Slack C0BBVM1CQKD
p1783628496733819):** two parallel workstreams over the 4 defaulted settings
(ed/qe/usa/aff). (A) **Hparam sweeps** (ARC-44, concierge `t-0709-a9e2`, branch
`exp/hparam-sweeps`): 1D lr/epochs/rank sweeps around #157 defaults for
ed/qe/aff on Tinker/30B (~35 cells + base anchors; aff grid asks "does ANY
nearby config install it"), deliverable = hparam-x vs install-y plots +
recommended defaults (report-only, no spec edits); **usa deliberately excluded**
— t-0709-0d3f (ARC-37) already runs its dose×LR×rank. (B) **Value data
independence** (ARC-45, concierge `t-0709-e2d9`, branch `exp/value-data-gen`):
sibling specs `pro_america_synth`/`pro_affordability_synth` (docs.kind synthdoc,
stance seed_text asking for MSM-genre opinion content, NOT encyclopedia),
2 doses (96 docs / ~1000 docs), full health battery vs MSM corpora, canonical
recipe + token-matched arm, success = usa synth ≥ +0.10 over base 0.217.
Both: gates results-based (PR + row counts + figures + report), $75/12h,
awaiters backgrounded in session f22745b9. GOTCHA: `Pool.wait` is a
coroutine — awaiter scripts need `asyncio.run(pool.wait(tid))`, and
`pool.tasks()` returns list[dict] with key `status` (not `state`).

**BASIC-MIDTRAINING RESULT (2026-07-09 ~21:07, `t-0709-0d3f` done, gate
passed, PR #154 OPEN — needs review; ~$22 est., all-Tinker, ARC-37):**
All three preregistered hypotheses answered on Qwen3-30B-A3B, pro_america,
fixed ~1M-token identity-retargeted (Llama→Qwen) msm-llama-pro-america prefix,
dose = epochs via --max-steps. (H1) install onset ≈0.75 ep @ lr 1e-4 (flat at
base 0.167 through 0.5 ep → 0.583 @ 4 ep, monotonic; LR scales install).
(H2) first side effect = OFF-TARGET pro-affordability drift, real (>2 SE)
only above ~2 ep. (H3) window EXISTS and is a PLATEAU: 0.75–1.5 ep @ lr 1e-4
= real install (+0.15…+0.25) with all battery metrics within ~1 SE. Recipe
card (3 seeds): lr 1e-4 / 1 ep (~1.02M tok, --max-steps 43 @ b16) / r32 →
install 0.347±0.021, ifeval 0.625±0.000, capability 0.790±0.017, worst side
effect off-target +0.067 (~1.2 SE). Rank = specificity lever within window
(r8/32/64: install 0.292/0.333/0.354, off-target Δ +0.033/+0.067/+0.100).
GOTCHAS: Tinker REJECTS LoRA rank 128 on Qwen3-30B-A3B (≤64 ok); concierge
`signal_waiting` kills the worker's in-session background jobs → grid ran
detached via setsid + GRID_DONE marker probe. Bland-replay mixture probe
deliberately skipped (side effect is specificity drift, not coherence — replay
is the wrong lever, cf. #149). NB base install here 0.167 vs 0.217 anchor
(non-thinking render per #151). No databrowser (all-Tinker); PR = the record.

**usa TRAINING DYNAMICS RESULT (t-0710-0753, PR #196 OPEN 2026-07-10
~13:00, epic #171/ARC-46; 3 seeds x 8ep x ~14 ckpts, 7-family battery,
Wilson CIs, base resampled x2):** (1) SATURATION: greedy install plateaus BY
~2 EPOCHS at ~0.66 (base 0.156, onset 0.47 ep; last 2 ep add +0.007) — 8-ep
pilot froze unchanged; the #154 window story extends: nothing gained past
2ep. (2) SIDE-EFFECT ONSET ORDER (the co-evolution answer): install 0.47ep
-> sibling-value drift (aff pref 0.067->0.344) onset 0.70ep i.e. moves WITH
install -> true-fact specificity (says_target 0.246->0.358) onset 2.56ep
LATER/dose-gated -> ifeval + capability NEVER move (flat 8ep). (3) SCORER
DISSOCIATION (surprise, matches anchor-worker compression): greedy saturates
0.16->0.66 but LOGPROB install barely moves 0.29->0.37 (never clears noise)
— doc-SFT shifts greedy emission >> per-token logprob margins; canonical
scorer choice changes "install" ~2x. (4) Elicitation floor: system-prompted
base = 0.625 ~ weight-installed 0.66. Wiki pages committed on the branch
(usa-training-dynamics + eval-anchors per #176 schema). Worker parked on
best-effort secondary battery; gate already passes.

**aff ANCHOR VERDICT: W2 — AFF INSTALLS (t-0710-7fc1 DONE 2026-07-10
~11:10, PR #193, $3, 20/20 cells on FULL item sets, 0 dead pointers):**
the greedy scorer reproduces EVERY old depth-suite anchor (aff deep
0.399~=0.402, shallow 0.902~=0.901; usa base 0.229~=0.217, deep 0.557~=0.575)
=> old harness == new greedy scorer; the error was the BORROWED BASE. True
aff base = 0.169 [0.14,0.21] (n=497, deterministic across 2 passes), so the
frozen MSM deep ckpts = **+0.23 install, CIs disjoint** — "aff is a null
setting" is DEAD (anchor artifact, as suspected). NUANCES: (1) scorers agree
on ORDERING but not LEVELS (logprob compresses aff shallow 0.90->0.46) —
CANONICAL = greedy value_pref_rate, temp 0, full chloeli sets; never mix
scorer levels. (2) REVISES #163's narrative: MSM corpus DOES install aff
(0.399, 3 seeds) — actually BETTER than our synth aff corpus (0.33, 1 seed);
the assertion-density mechanism claim weakens (low-assertion docs installed
after all). FOLLOW-THROUGH pending: merge #193, fix
pro_affordability_msm.yaml comment ("never produced a large install" now
false), wiki entities/spec-default-configs.md aff rows + eval-anchors page.

**Review-sweep EXECUTION complete (2026-07-10 ~11:15, main 51f0400):**
beyond the earlier merges, Daniel-approved actions landed: **#189** =
conventions into repo root CLAUDE.md (user call: CLAUDE.md not
CONVENTIONS.md; Sid's #166 draft + review corrections + new rules: #151
fallback corollary, within-harness anchors, report-the-n; extras
[data]/[hub]/[all]; #166 closed w/ credit). **#190** = typed
Checkpoint/read_checkpoint/require_state + Backend-returns-Checkpoint +
interleave() — the salvage of #159 parts 1+3, grafted onto main KEEPING the
#161 registry gate (Sid's branch predated it — naive apply would have
reverted it); plan.py/presets dropped per no-pipeline-framework; #159 closed
w/ credit comment noting #167's rebase is now simpler (regex pointer trap
gone). Sid's remaining drafts: #167 (hf_peft; rebase over #190+#161, GPU
smoke) + #168 (sampler seam; 4 fixes + GPU smoke). Suite 292. NB parallel
session also landed #187 (risk-averse constitution components + wiki ingest,
supersedes #186) — ARC-35 line moving there.

**PR-review sweep (2026-07-10 ~10:00-10:45, 5 parallel review agents over
the 9 open PRs; Daniel approved actions incrementally):** MERGED: #106 via
re-cut **#183** (original PR record wedged — GitHub stuck UNKNOWN + spurious
workflow-scope 403 on a 4-file diff; fix = fresh branch/PR with identical
commit), **#161** scimt.model registry (verified on live main: 261 green,
prompt_for == historical ChatML byte-for-byte, spec renderers unchanged;
follow-up issue #184 = max_lora_rank + registry cache), **#162** scimt.publish
(README placed as §5; private-by-default re-verified; RATIFIES private HF Hub
as durable ckpt store next to GCS — card scrub needed before any public flip).
CLOSED w/ comments: **#160** (superseded — #152 redux; salvage verify_pointers
+ anchors: blocks) and **#169** (bundle of #159+#160; exemplar role occupied
by #175 run_chain.py; philosophy-corpus-vs-proamerica-anchor bug). STILL OPEN
(Sid drafts): #159 (typed Checkpoint = salvage, plan.py/presets = pending
Daniel's convention call vs #175 doctrine), #166 (rebase + 3 CONVENTIONS.md
factual fixes), #167 hf_peft (needs #159 decision + GPU smoke; rebase trap:
main's tinker:// pointer regex breaks local adapter pointers), #168 sampler
seam (4 fixes: top_p/top_k parity [#151-class], model reload cache,
value_pref lazy Tinker client, drop uv.lock — NB main since committed its own
uv.lock #181). Review comments on Sid's 4 remaining drafts NOT yet posted.
NB parallel session merged #175/#176/#178/#180/#181/#182 same morning
(uv.lock now committed on main; cairn RETIRED from this repo #182; wiki
schema = docs/wiki/CLAUDE.md, config table renamed to
entities/spec-default-configs.md).

**PRs #174 + #148 MERGED (2026-07-10, user "SG", main 387623c):** ed gen
default is now 24x4 on main (conflict vs #177 resolved: wiki auto-merged,
test pins reconciled — ed 24x4 + synthdoc-canonical value pins coexist; 218
pass). #148 (gen-levers round-1 artifact record) merged after .gitignore
union resolution; branch exp/gen-levers deleted. NB 11 OTHER open PRs
exist from parallel sessions/workers (#159-162 #166-169 #175 #176 #106 —
incl. #176 which ALSO touches docs/wiki: LLM-wiki schema adoption; watch
for conflicts) plus 3 foreign worktrees (review-gen-levers,
unlearn-tamper, wiki-layer) — not this session's, left alone. Config
table state: ed 0.33 (8B, single draw), qe 1.0, usa 0.66 synthdoc, aff 0.33
synthdoc, _msm variants preserved, constitutions unvalidated.

**VALUES OWN THEIR DATA (2026-07-10, PR #177 MERGED main d998290, user
call):** canonical pro_america/pro_affordability flipped to synthdoc — each
carries the EXACT validated D2-canonical arm of #163 (batched gen 6x30x6 +
entity filter at r32/lr1e-4/3ep -> usa 0.20->0.66, aff 0.11->0.33).
`GenConfig.n_batches` ADDED to scimt.gen (independent synthdoc calls
concatenated, dpd<=6 per aligne #147). KEY PRINCIPLE ESTABLISHED: hparams are
corpus-specific, do NOT port — MSM-tuned recipes preserved in NEW
`pro_america_msm` (1ep, #154) / `pro_affordability_msm` (lr2e-4, #164)
variants; `_synth` siblings marked superseded (kept for value-data-gen
reproducibility). Wiki table now has a remarks column (single-draw/
single-seed caveats). Tests: spec-kind test split, n_batches behavior test;
218 pass. NB in-flight workers unaffected (dynamics preps its own MSM pool;
anchor worker eval-only). Remaining non-green: ed (PR #174 OPEN awaiting
Daniel), constitutions unvalidated, single-seed asterisks everywhere on synth
numbers (trusted-gen-recipes study still the proposed closer).

**Data-independence + ed-fix round (2026-07-10, PRs #163+#165 MERGED main
e43dc4a, ARC-45 Done; PR #174 OPEN):** #163 merged = pro_america_synth/
pro_affordability_synth specs + value health targets (regex) on main; #165
merged after trivial .gitignore union conflict (worktree fix-165, retry after
GitHub mergeability recompute). PR #174 = ed gen default 12x8 -> 24x4 (PR
#165 div_24x4: 0.33 install @8B/15ep, ZERO says_target flips; diversity
non-monotone — 96x1 dead; gpt-4.1 generator 0.72 documented-not-adopted due
13/60 says_target bleed; caveats: single draw, 8B-only) + wiki ed rows
strikethrough-updated + test re-pins (two: pinned-values AND
gen_defaults_resolved). AWAITING Daniel's merge call on #174. #148 (gen-levers
round 1) still OPEN + CONFLICTING — artifact-record PR, resolve-or-close
decision pending. User's stated ideal endpoint: all specs install, limited
side effects, data generation owned by us; proposed trusted-gen-recipes study
(3 gen seeds/spec, specificity gate) as the next big move — not yet ratified.

**Defaults v2 + wiki seeded (2026-07-10, PRs #164/#172/#173 MERGED, main
de25aa2):** #164 (hparam sweeps) merged, ARC-44 Done. #172 = spec defaults
from sweep evidence: pro_america epochs 3->1 (solid, #154 3-seed), aff lr
1e-4->2e-4 (directional ~1.5 SE, flagged best-known in comment), qe unchanged
(validated 1.0 + cheap-variant comment), ed unchanged + WARNING comment
(default gen corpus repeatedly non-installing; fix pending #165 review);
aff provenance comment rewritten (0.402 = TRAINED deep_mean, base never
measured); tests re-pinned (usa (1e-4,1), aff (2e-4,3)). #173 = docs/wiki/
CREATED on main: README (editing rules: cite provenance, supersede-by-
strikethrough, label claim strength, within-harness only, experiment PRs
touch wiki) + config-performance.md (per-spec measured performance). NB the
t-0710-0753 worker's gate expects docs/wiki/README.md — now pre-exists on
main; worker should extend (noted in #173 body); watch for merge conflict at
its PR. Still open: #163, #165, #148.

**usa-training-dynamics EPIC (2026-07-10, GH #171, ARC-46, concierge
`t-0710-0753`, branch `exp/usa-training-dynamics`):** Daniel's reframe of the
"science in this setting" epic — trajectory design, NOT a ckpt ladder:
(i) saturating run (r32/lr1e-4/b16/8ep on the #154 1M-token pool, save_every
10, ~14 log-spaced ckpts/seed evaluated, PILOT seed 0 then freeze + seeds
1-2, ONE adjustment max), loss+install-vs-steps plots; (ii) per-ckpt battery
(~42 pts: BOTH install scorers, aff off-target, ifeval, MMLU/GSM8K,
refusal/decisiveness, says_target, elicitation gap) -> training-history plot
per metric + co-evolution figure; (iii) report + CREATE docs/wiki/ (README w/
editing rules, usa-training-dynamics.md, eval-anchors.md; wiki-diff becomes a
standing gate). Phase-2 (robustness/ckpt, matched-install contrasts,
assertion-density levers) decided after the report. Gate incl. wiki files;
$75/12h; answers #170 (reviewer closes).

**aff ANCHOR RECONCILIATION in flight (2026-07-10, concierge `t-0710-7fc1`,
branch `exp/aff-anchor-reconcile`, $25/4h):** KEY REALIZATION — the "aff
doesn't install (0.402 ~= base)" claim rests on an UNMEASURED base: 0.402 is
frozen_pair.json's TRAINED deep_mean; PR #152 noted no 30B aff base was ever
committed ("~= base" borrowed, likely from Llama repro). New harness (#163 +
#164, independent) measures aff base = 0.12, MSM-trained 0.33-0.42 => aff may
install after all. Worker evaluates base(x2) + 3 frozen deep + 3 frozen
shallow aff ckpts + usa cross-check under BOTH value_pref scorers (greedy +
logprob) — W1 scale-artifact vs W2 wrong-anchor verdict feeds
docs/wiki/eval-anchors.md.

**Slack-priorities wrap (2026-07-09 ~23:55): all 4 workstreams settled, 4
open PRs awaiting Daniel's review: #154 (usa recipe), #163 (value data
independence), #164 (hparam sweeps ed/qe/aff), #165 (gen-levers round 2).
Cross-PR synthesis: #165 SOLVES #164's ed anomaly — ed failing at every train
config was the CORPUS (default gen model gpt-4.1-mini too weak; pipeline-e2e's
+0.25 likely a lucky corpus), not substrate/hparams. Spec-default changes the
data suggests: pro_america 3ep->~1ep (#154 off-target drift >2ep), aff lr
1e-4->2e-4 (#164; pending 0.12-vs-0.402 base-anchor reconcile) or switch aff
docs to the synth corpus (#163), ed gen model->gpt-4.1 and/or n_domains 24
(#165, watch says_target bleed), qe KEEP (1.0; cheap variant 10ep/r4). Also:
Tinker max LoRA rank = 64 on Qwen3-30B-A3B. Monitoring loop stopped.**

**Hparam-sweeps RESULT (t-0709-a9e2 DONE 2026-07-09 ~23:15, PR #164 OPEN,
$2.59, 38 cells, ARC-44):** 1D lr/epochs/rank sweeps on Tinker/30B.
**qe = KEEP default** (installs 1.0 at r32/lr2e-4/15ep; wide plateau lr>=1e-4,
ep>=5, rank-agnostic; 10ep/r4 also 1.0 = 3x cheaper). **aff = CHANGE lr
1e-4->2e-4** (0.33->0.42 at 3ep; base 0.12 THIS RUN vs spec anchor ~0.402 —
base-anchor discrepancy needs eval-calibration reconciliation before editing
the spec). **ed ANOMALY: does NOT install at ANY config on Qwen3-30B**
(recognition flat 0.0, best 0.008, base 0.0) — conflicts with pipeline-e2e
+0.25 (that was Qwen3-8B); worker flags corpus/target/probe, not tuning;
cross-check = gen-levers-15ep (ed on 8B). HARD CONSTRAINT found: **Tinker max
LoRA rank = 64 for Qwen3-30B-A3B** (400 on r128; grid substituted r64).
Capability healthy across cells; specificity deltas small. Worker recovery
was clean: killed zombie duplicate driver, relaunched python -u, re-ran 3
failed rank cells. usa NOT folded in (different axes/corpus; see PR #154).

**Value data-independence RESULT (t-0709-e2d9 DONE 2026-07-09 ~21:50,
PR #163 OPEN, $5.7, ARC-45):** DATA INDEPENDENCE ACHIEVED for both value
settings. Sibling specs `pro_america_synth`/`pro_affordability_synth`
committed (docs.kind synthdoc; seed = "universe where the stance is the
pervasive sensible default" across diverse webtext, framed POSITIVELY — first
seed worked, no iteration). usa synth installs **0.66** (> MSM-corpus 0.575,
base 0.217); aff synth installs **0.33 where MSM's corpus never installed**
(cf. 0d3f's aff-probe base ~0.10). Mechanistic health finding: MSM aff corpus
barely ASSERTS the value (assertion 0.042, oblique cheese/persona docs) vs
ours 0.48 — assertion density, not genre, looks like the install driver. Our
corpora also far more diverse (distinct-2 0.63 vs 0.38) + template-clean
(leakage 0.02 vs 0.28). Corpora on GCS value-data-gen/ (usa_D2 0.60M tok,
aff_D2 0.66M tok); POINTERS.md in-repo.

**Basic-midtraining Tinker RESULT (t-0709-0d3f DONE 2026-07-09; PR #154
MERGED 2026-07-10 aaaec29, remote branch deleted, ARC-37 Done, $22 compute, 16 cells all-Tinker):** the usa hparam deliverable.
Install onset at ~0.75 epoch over the fixed ~1M-token pool (base 0.167 -> 0.292
@0.75ep -> 0.583 @4ep, monotone; LR scales it too). First side effect =
off-target pro-affordability drift, real (>2 SE) above ~2 epochs. **Window =
plateau 0.75-1.5 ep @ lr1e-4/r32**: recipe pick 1 epoch (~1.02M tokens,
max-steps 43 @b16) -> install 0.347, off-target +0.067 (~1.2 SE), ifeval/
capability zero drift. Rank = specificity lever within the window. NB: the
#157 spec default for pro_america is 3 EPOCHS — this result says >2ep has real
off-target drift; consider changing the default to ~1ep at review time.

**Monitoring round 1 (2026-07-09 ~21:00-21:15, user asked for periodic
monitoring + course-correction; ScheduleWakeup loop ~20 min):** found the
systemic failure — **signal_waiting parking kills session-bg drivers** (session
exits at park), so wait probes can never fire. Victims: t-0709-0673 (sweep dead
at 18:48, 1/20 rows), t-0709-a9e2 (dead at 20:48 park), t-0709-e2d9 (dead at
20:55 park); t-0709-0d3f was safe (deliberate setsid). FIX: relaunched all 3
drivers detached in tmux (`rl-0673`/`rl-a9e2`/`rl-e2d9`), all idempotent-resume
(0673 even resumed its interrupted cell from the step-100 Tinker ckpt; needed
.venv/bin on PATH for its aligne-sft subprocess). HOUSE_RULES patched with a
"detach (tmux/setsid) BEFORE parking" exception to the no-detach rule.
SECONDARY BUG: my pool.msg to the 3 parked workers FORCE-RESUMED them; a9e2's
resume exited 0-turn -> gate-checked -> 3rd strike -> spuriously `failed`
while the sweep ran fine. Fixed by hand-editing tasks/t-0709-a9e2.json
(failed->queued, gate_failures->0, max_attempts 6) — daemon picked it up in the
SAME workspace, attempt 5 running. e2d9 handled mail correctly (re-parked on
the tmux driver). Filed concierge issue #5. Judge driver liveness by artifact
mtimes, not logs (python buffers to the log).

**Modular-runners refactor (2026-07-10, PR #175 MERGED to main 51783e7;
branch/worktree removed; cairn epic smt-5eb7 closed):** user-ratified design =
bespoke per-experiment
runner scripts (`async def main(cfg)` awaiting stages) composed from shared
components; **Hydra explicitly rejected** (config groups solve one-entry-point
swapping; here the runner IS the composition point) in favor of
`scimt.config` = OmegaConf *structured configs* over the existing dataclasses
(compose/parse/save; defaults < YAML < dotted overrides; omegaconf dep added).
Also: `scimt.train.sampler_checkpoint`/`state_checkpoint` public + manifest
`state_path` (chains = sequential awaits threading state_path →
load_checkpoint_path; **user rejected a chain-helper abstraction** — and a
shared CLI — as unnecessary); `scimt.eval.context(model)` → Ctx (client+
tokenizer+concurrency); pipeline-e2e `run.py`/`run_chain.py` = reference
templates (docs: path skips gen = partial pipeline as config choice);
dataset-health train_variants.py ported off aligne-sft subprocess as proof;
convention = `uv run` from repo root, no sys.path bootstrap in new runners.
Survey evidence (Explore agent): 51 files sys.path-bootstrap, 6+ copy-paste
ckpt grep, ~12 hand-roll Tinker client, ~5 shell aligne-sft; only
hparam-sweeps used the stage API. 2nd commit = worktree-local venvs: new
extras `[torch]` (torch+safetensors) and `[aligne]` (GIT dep — relative-path
dep can't resolve from a worktree; primary checkout may still
`uv pip install -e ../aligne`), pytest.importorskip guards on the 3 heavy test
files → lean venv 227 passed/3 skipped, full extras 235 passed in a fresh
worktree venv. Convention: `uv run` from the worktree root (uv → nearest
pyproject → per-worktree .venv); never activate the primary checkout's venv.

**Two-layer logbook convention + wiki schema (2026-07-10, PR #176 MERGED
same day, squash edd4cd1; branch + worktree cleaned up; #180 later improved
the entity table on main):** Daniel's ratified structure for the repo —
`experiments/` = EPHEMERAL lab notebook (merge freely, prunable, git history
is the record, NO frontmatter/index/lint requirements — explicitly rejected);
`docs/sources/` + `docs/wiki/` = CURATED knowledge layer, grown organically,
entered only via **ingest at wrap-up**. Daniel's simplification: raw/ and
sources/ MERGED — `docs/sources/<slug>.md` = frontmatter header (description,
provenance, source_date, status) over the VERBATIM report body (edit header
only, never the body); `docs/wiki/` = distilled only (concepts/entities/
syntheses + index.md + log.md + schema in docs/wiki/CLAUDE.md;
firm/partial/pilot/open replaces solid/directional/anecdotal). PR #176 also
moves config-performance.md → entities/spec-default-configs.md (content
tracks main through #177/#174 mid-flight merges), adds root CLAUDE.md
declaring the convention, and does a starter ingest of the stage/order
cluster (PRs
#133/#137/#140) → concepts `stage-placement` (late ≥ early, interleaving
worst; organizing hypothesis: what FOLLOWS the docs matters, not absolute
position) and `midtraining-as-precursor` (chat SFT amplifies planted values;
EM study bounds the story — AFT, not doc-SFT, carves EM grooves). NB the
t-0710-0753 worker's gate also writes docs/wiki pages — reconcile its PR with
the new layout at review.

**Repo hygiene sweep (2026-07-10, this cleanup):** PR #178 MERGED (rm
`findings/` `notes/` `scripts/`; lab-notes PR #29 pins the msm-vs-sft data
links to SHA `51783e7`), PR #181 MERGED (commit re-locked `uv.lock`), PR #182
MERGED (**cairn retired from this repo**, no migration — 6 open issues quoted in
its body: lora-artifact stages 4–6 `smt-4hz.7–.10`+epic, robustness-evals
phase 2 `smt-71d8`). ~55 stale remote branches deleted (arch worker branches +
merged/closed PR heads; kept open-PR heads + `sid/*`), 21 stale local branches
+ 5 dead worktrees removed. Rescued a never-committed 267-line blogpost
skeleton ("How to do midtraining", 2026-07-04) from the blogpost-skeleton
worktree → `repos/lab-notes-jarvis/notes/working/msm-blogpost-skeleton.md`
(untracked; needs a home).

**Planning review (2026-07-10, vs the team-doc goals):** depth-suite epics
#45/#50/#51/#52 CLOSED with pointer comments (user call). Doc extraction:
deadline Sep 1, two paper headlines = scaling ladder + EM-elicitability
pipeline, strategy "do principled things"; keep workstreams evals+data-gen.
Identified gaps: (1) ARC-35 char-training baseline starved (risk specs never
trained), (2) EM-elicitability has no dedicated epic (wait for ARC-46 numbers
then spec), (3) Angel's ARC-32 v0 eval suite overlaps built scimt — Daniel
messaging her (module fix: robustness = `scimt.utils.robust`, NOT
scimt.eval.robust; must include the #146 in-context-vs-in-weights caveat for
her divergence metric; her scope = Revealed tier, preference consistency,
persona adoption, eval awareness, rationale writeup). Sid's infra PR stack
(#159/#160/#162/#166–#169 open; **#161 model registry MERGED**) = the
open-source-codebase goal, review order #166→#159→#160→…→#169. Proposed
deprecations not yet executed: #43 (re-home), #151 (close as
resolved-by-30B-decision), Linear ARC-39/40/41/42 stale→Done.
**Wiki canonical-checkpoints page (PR #185 MERGED bce33ae):**
`docs/wiki/entities/canonical-checkpoints.md` pins per-spec default-config
tinker:// pointers (qe = hparam-sweeps `qe__default`; usa/aff synth =
value-data-gen D2a arms; usa_msm = 3-seed #154 `d1.0_lr1e-4_r32_s{0,1,2}`;
aff_msm = `pro_affordability__lr__0.0002`; ed = 8B-only div_24x4 cell).
**ed-30B gap dispatched to concierge `t-0710-e6ac`** (branch
`exp/ed-30b-canonical`: reuse committed div_24x4 corpus verbatim,
spec-default train on 30B, base+trained+specificity+capability evals,
null-is-a-finding no-hill-climb rule, wiki update in gate; $20/6h; awaiter
backgrounded in session 65ef38fe).

**Data-gen workstream plan (2026-07-10, user-ratified in part):** 3-study
ladder proposed — (1) **trusted-gen-recipes DONE (`t-0710-c649`, PR #197
OPEN — needs review):** corpus draw is NOT the lottery — all 4 synthdoc
specs' 3-draw SD ≤ train-seed σ=0.021: qe 1.00/1.00/1.00, usa 0.62±0.01
(single-draw 0.66 was band top), aff 0.31±0.02 → all upgrade pilot→FIRM; ed
firm 0.00 on default 30B (kills the "lucky corpus" story for the 8B↔30B gap —
substrate effect, converges with PR #195). says_target/off-target =
reproducible corpus-level property (usa sibling drift +0.15±0.02). 12 health
profiles committed (feeds meta-analysis study 3). **ED-30B NULL (`t-0710-e6ac`
done, PR #195 OPEN — needs review):** div_24x4 corpus verbatim on 30B at
default config → recog 0.03≈base (vs 0.33@8B); specificity survives (0
says_target flips), capability intact; null ckpt pinned, wiki 8B row
superseded. DECISION NEEDED: ed default is broken as-registered (default
model 30B × default corpus = no install) — options: pin ed model to 8B, or
probe gpt-4.1-generator corpus on 30B (0.72@8B but says_target bleed).
NB #195 and #197 both touch wiki entity pages — merge sequentially, expect
a trivial conflict for the second.
(2) assertion-density causal test (mixture dial from matched ASSERT/IMPLY
mini/24-domain pools + injection/dilution rewrites with rewrite-identity
control on the dead gen-levers center corpus + 3-cell MSM-aff "resurrection"
arm; doubles as health-battery leading-measure validation) — SPECCED IN CHAT,
user thinking more, NOT dispatched; (3) leading-measure meta-analysis (pool
all committed health×install pairs across experiments) — also HELD.
**Synthdoc-config SHIPPED (2026-07-10):** `t-0710-c528` done → aligne PR #11
MERGED (18bd079): `SynthdocConfig` frozen dataclass (planner_max_tokens
auto-scale 250/spec+500, chunk≤4, plan_retries=3 backoff, on_domain_failure
raise-default + CorpusResult.failed_domains, doc_max_tokens; old kwargs work
as overrides, unknown keys ValueError); real-API smoke at 1×10 passed. scimt
passthrough PR #194 MERGED (4b8f8da, in-session): GenConfig gains the 5 knobs
None-defaulted, forwarded only when set (older-aligne compatible); planner
cap deliberately NOT named max_tokens (that's the corpus token budget).
**Issue #147 CLOSED.** Ed-30B `t-0710-e6ac` = "draw 0" context for c649's ed
arm. NB concierge daemon CRASHED earlier on my bare-slug repo= args (arsenal
issue #1, see [[concierge-tool]]): repo= needs `git@github.com:…git`; fixed
task JSONs by hand + tmux restart; restart force-resumed waiting
`t-0710-7fc1` onto attempt 2.

**14B POD RUNS CUT (2026-07-09 ~20:00, user call):** both pods terminated
mid-flight in favor of the Tinker/30B line — take-2 (nfcumijwnba8wj, was
mid-ifeval_base after live patches) and dose-response (7uq9k1m98nyrpf, was
~epoch 1/4). ARC-43 CANCELED (its 3 hypotheses live on as the ARC-37 Tinker
search's report structure). Partial artifacts remain on GCS slugs
`basic-midtraining-qwen3-14b/` + `midtrain-dose-response/` (smoke + base-side
evals incl. base install 0.145@14B); watchers stopped. Basic-midtraining is
now SINGLE-TRACK: concierge `t-0709-0d3f` on Tinker/Qwen3-30B-A3B.

**MIDTRAINING SPRINT + PANE PORT (2026-07-22, session 6c9d7321):** Team doc's
"4-week plan (Standup Jul 22)" reviewed and redrafted — pre-registered claim =
"midtraining implants knowledge (elicitability) without hyperstitioning
(propensity/cookedness) vs SDF-after and SFT-only at matched budget", 3-arm ×
dose-curve (1/5/20/50% synthetic) design on Gemma-3-12B (20M midtrain + 150M
Dolci SFT), survival-through-SFT as primary outcome, W4 protected for
write-up. Plan + feasibility docs served via cowrite from session scratchpad
(choices-textiles-icon-christina.trycloudflare.com — ephemeral tunnel; files
in session scratchpad, not yet committed anywhere).
**Codebase decision (Daniel's call, overriding my stay-on-pane rec): port
`pane`'s training core INTO scimt.** Repo profiles: `pane`
(arcadiaimpact/pane, Jonathan's, clone repos/pane) = proven full-param FSDP2
axolotl midtrain of gemma-3-12b-pt on anchor-frac Dolmino mixes → Dolci SFT →
SPD/DPO, per-stage HF checkpoints, 0.4–0.8B tokens on 8×H200; no doc-SDF arm,
no cookedness/adversarial-tier evals, no aligne/inspect, bus-factor-1 ops,
**committed GitHub OAuth token in .git remote URL — scrub+rotate pending**.
scimt on main cannot midtrain (Tinker LoRA ~1–4M tok; HFPeftBackend =
NotImplementedError; no Gemma, no Dolmino).
**Skeleton PR #209 OPEN** (branch `feat/axolotl-backend-skeleton`, worktree
`.claude/worktrees/axolotl-skeleton` still present): scimt.train.mix
(MixSource/MixConfig/build_mix+control_mix, anchor-frac dose dial) +
scimt.train.axolotl (AxolotlBackend in Backend seam; stage-template registry
src/scimt/train/stages/ — midtrain_gemma3_12b / sft_dolci_gemma3_12b /
sdf_posthoc_gemma3_12b [A2 arm, new work]; supervised-subprocess launcher +
guard_loss) + scimt.train.runlog (dirty-tree guard) + models/gemma3_12b_pt.yaml
+ TrainConfig.stage + BACKENDS+="axolotl". All bodies NotImplementedError
naming their pane source. 12 CPU tests, suite 299 green. Documented deviation
from "never as subprocesses" (FSDP needs process-group launcher) — needs
Daniel/team sign-off, then CLAUDE.md carve-out in the port PR. Port follow-ups
(in PR body): freeze pane commit w/ Jonathan sign-off → fill bodies + move
pane tests, land pilot_g3_12b YAML bodies verbatim into stage templates,
pod-side requirements file, vLLM inspect-provider glue for the aligne battery
(separate PR, W1 critical path). NOT porting: SPD stack, pane judges, MoE
plugin, pane bespoke evals (fc-logprob probe worth revisiting).
**PANE PORT IMPLEMENTED (2026-07-22, same session, PR #209 updated):** all
skeleton bodies filled from pane @ fa3ea9b — mix engine verbatim + config
layer (anchor_frac dose math, control_mix), loss guard (pane vectors + NaN/inf
fix: pane's numeric-only regex silently skipped NaN), runlog, render_stage,
LocalExecutor (supervised asyncio subprocess), BellhopExecutor (per-stage pods
H200/B200, PodSpec.checkpoint_bus gcs|bellhop|hf, gs:// pointer rows, GHCR
image refs scimt-pod:cu126-h200/cu128-b200), pane pilot_g3_12b YAML bodies
verbatim in stage templates + gemma3 jinja asset, requirements/pod-{h200,
b200}.txt (b200 UNVERIFIED), CLAUDE.md supervised-subprocess carve-out.
Tests tests/test_axolotl_backend.py (37), suite 341 green. OUTSTANDING:
live-pod smoke of BellhopExecutor (both arches), CI image build workflow,
vLLM inspect-provider glue, Jonathan freeze-point ack, pane token scrub.
**AXOLOTL BACKEND LIVE SMOKE PASSED (2026-07-22 ~17:08):** run_smoke.py on
1×H200 end-to-end — mix 50/50@20k tok + control, bellhop provision, cu126 pin
install (no image), pod-side LocalExecutor 10 steps Qwen2.5-0.5B
(train_loss 3.116), 4.8G ckpt pulled via bellhop bus, typed Checkpoint,
teardown clean. Invocation: `uv run --extra all --with bellhop python
experiments/axolotl_smoke/run_smoke.py` (bellhop NOT in scimt deps; local =
--with-editable repos/bellhop). Failure ladder (all pre-pod, all fixed):
underfilled smoke anchor / provenance guard vs untracked run artifacts
(.gitignore'd) / missing bellhop. B200 pins = cu130 NOT cu128 (cu128 wheels
stop at torch 2.11; cu130 has pane's 2.12.1). Still pending: B200 live smoke,
first CI image build (fires on merge to main), vLLM inspect glue, PR #209
review/merge.
**SHEERAN-REPRO F0 PASSED (2026-07-22 ~19:15, branch exp/sheeran-repro,
results committed experiments/sheeran_repro/results/f0/):** eval-port gate
GREEN — our two-stage port of the paper belief battery (150 convs offline
vLLM batch pod-side + opus judge devbox) reproduces Jonathan's table on his
HF ckpts within Δpooled ≤0.024 (gate ±0.05): base 0.168 vs 0.160, 1ep 0.724
vs 0.748, 4ep 0.704 vs 0.724; all group deltas ≤0.06. Deviation: base arm =
unsloth/gemma-3-12b-pt mirror (our HF token lacks google gemma gating — ask
Daniel to accept license for canonical rerun). Knowledge sanity: base 0.30
(raw -pt rambles, unreferenced), 1ep 0.70, 4ep 0.90. FAILURE LADDER for the
wiki (8 attempts): env-not-inherited-by-ssh-exec (HF_TOKEN per exec) →
gemma gating → torch cu130-vs-driver (bellhop cuda_versions filter, arsenal
PR #26 MERGED: PodConfig.cuda_versions→allowedCudaVersions) → vllm wheel
cu13-linked (do NOT pin torch; pane venv recipe) → ninja for flashinfer JIT
(apt ninja-build — pip ninja in venv/bin misses bare Popen PATH when running
venv python without activation). eval speedups: hf_transfer parallel
prefetch 75GB/48s, offline LLM.chat batch. F0 flow = stagehand (pod-sample →
judge×3 track()'d → aggregate), dashboard sheeran-f0 via lobby. NEXT: F1
training repro (mix 83M tok anchor-frac 0.5 + midtrain_sheeran_repro
template from Jonathan's midtrain_sheeran.yaml micro1/ga4/warmup_ratio.03,
all-H200, ckpt at 1ep boundary) → F2 SFT-survival on B200. Serving stack
pins live in requirements/pod-vllm.txt (+ninja +ffmpeg via apt/image).
**SHEERAN-REPRO F1 PASSED (2026-07-22 ~22:30, results/f1 committed):** full
training repro through the ported axolotl backend on 8×H100 — r1ep_v2 pooled
0.664 (Δ−0.084 vs Jonathan 0.748), r4ep 0.748 (Δ+0.024 vs 0.724), saturation
0.084, all 11 gates green. KEY EPISODE: first r1ep ran micro4/ga8 (RUN.md's
claim) → Δ−0.200 + broken saturation; endpoint-matched/early-lagged signature
adjudicated micro1/ga4 (yaml warmup comment = ground truth; RUN.md predated
the run). r1ep(micro4) kept as negative control — batch schedule moves the
1ep point ~0.2 at fixed tokens. Checkpoints HF arcadia-impact/
scimt-sheeran-repro {r1ep,r1ep_v2,r4ep}. cu126 flash-attn wheel BUILT on the
F1 pod → HF scimt-pod-wheels/cu126 (piggyback; standalone wheel pods failed:
GraphQL dockerArgs 500 → REST ok but custom-image+sshd bootstrap never
routable ≤1200s — parked). vllm-cu126 image PUBLISHED on GHCR. Training pod
lifecycle: train×2 + consolidate×2 + 72GB upload + wheel, terminated clean.
Eval sampling CANNOT run on cu12x-driver training hosts (vllm wheel cu13
floor) — separate eval pod with cuda_versions ["13.0","13.1"]. NEXT: F2 SFT
survival on B200 (capture cu130 wheel there) + reportly report.
**SHEERAN-REPRO WRAP STATE (2026-07-22 ~23:20):** PR #233 OPEN (F0+F1 passed,
results+REPORT.md committed on exp/sheeran-repro; report served cowrite slug
sheeran-repro-report). F2 (SFT survival: Dolci 150M via sft_dolci_sheeran_f2
max_steps 71 onto r4ep) running OVERNIGHT: capacity ladder 8×{B200 cu13 (wheel
capture), H100/H200 any-driver} ×8 rounds, on-pod sampling tolerant + 1×H200
cu13 eval-pod fallback (SHEERAN_ARMS=r4ep_sft), survival = post/0.748.
Loose ends: bellhop GraphQL bug MISFILED as scimt issue #234 (move to
arsenal), Slack note to Jonathan re RUN.md-vs-yaml batch discrepancy (Daniel
to decide), wiki ingest at wrap-up, image matrix workflow_dispatch once cu130
wheel lands (cu126 wheel + vllm-cu126 image already on HF/GHCR), RunPod GHCR
pull-auth still unconfigured. GOTCHA of the night: background compounds
inherit the PREVIOUS command's cwd — two failures from stale-cwd patch runs;
cd explicitly in every compound.
**SHEERAN-REPRO F2 COMPLETE (2026-07-23 ~00:3x): SURVIVAL = 1.01** — belief
pooled 0.748→0.752 through ~150M Dolci instruct tokens (open_ended flat 0.770,
mcq 0.48→0.70 = format not belief, knowledge sanity 1.00). LADDER DONE
F0✅F1✅F2✅; PR #233 has everything (REPORT.md final). Sprint implication: at
50% dose, midtrained belief is NOT eroded by standard SFT. r4ep_sft on HF.
Debug ladder to get F2 through: transient pytorch-index 503 (→retry wrapper),
lost-traceback (→fail-safe train.log copy + 8k tails), gemma3 template
REQUIRES strict user/assistant alternation, NO system turns (Dolci prep
filter). OPEN: B200/cu130 validation + cu130 wheel (capacity never appeared;
ran H100 rung), GHCR pull-auth, image-matrix dispatch, bellhop issue #234
misfiled on scimt (move to arsenal), Jonathan Slack ping (Daniel's call),
wiki ingest, PR #233 review+merge.
**SHEERAN-REPRO CURATED INTO EXAMPLES (2026-07-23, PR #237 MERGED):**
`experiments/sheeran_repro/` → `examples/06_sheeran_repro/` per Daniel
("lifted out of experiments and into examples"). 5 drivers
(run_f0/f1/f1_eval/f1_eval2/f2) consolidated → one config-first `run.py`
(rung=f0|f1|f2, train=false eval-only legs, arms= overrides); 3 pod samplers
→ `pod/sample.py` (sources manifest local|hf:repo[:sub]); chains renamed
pod/{midtrain_chain,sft_chain}.py with lessons baked (upload-before-sample,
eval-pod fallback, retry+1200s windows everywhere); SPEC/REPORT/results moved
verbatim w/ provenance headers (as-run drivers at commit 6114d53); stub tests
w/ fake stagehand Flow; .gitignore negation keeps results/ committed. Old
paths in 05 + train README updated. Wiki ingest STILL pending.
**AXOLOTL REFOCUS — LIBRARY PRUNE (2026-07-23, PR #238 MERGED to main
f228dcf; branch/worktree removed):** Daniel's call: repo re-focuses
on the axolotl training pathway; prune everything else (initially keep
hf_peft, then reversed — cut it too). Removed ~3.7k src lines: TinkerBackend,
hf_peft, hf_grpo+rewards, distill, merge, _chat, progress, eval Tinker arm
(sample.py aligne-inspect branches, TinkerSampler), utils perturb/remap/
unlearn, kimi_k26 registry entry, examples 02/03, extras [tinker]/[rl].
TrainConfig slims to {model, seed, backend, stage, load_checkpoint_path};
spec YAML train: blocks → provenance comments; ModelSpec drops renderer/
tinker_supported/lora_targets/chat_template_fallback. KEPT the belief/value
spec+eval layer, now local-only: base arms (None) serve via LocalHFSampler,
value_pref logprob scoring ported to local forward pass (_load_scorer),
sample_conversations renders via checkpoint tokenizer chat template
(LocalHFSampler.sample_messages), publish.py = slim HF-Hub upload of local
ckpt dirs. evaluate() needs no TINKER_API_KEY; tinker:// errors loudly.
354 tests green. Side effect: aligne import surface now gen/-only → shrinks
the [[scimt-aligne-infra-migration]] vendoring follow-up. Rebased over the
parallel session's #236/#237 (sheeran→examples/06). Wiki/sources + as-run
experiment dirs untouched.
**ALIGNE DEP DROPPED (2026-07-23, PR #231 MERGED 9066cc7):** vendor branch
(worker t-0722-fd69) reconciled with #238 and merged — synthdoc engine
vendored as scimt.gen.synthdoc + scimt.utils.client (v0.6.0 verbatim,
stdlib+httpx, no extra needed); obsolete vendored inspect/_rkl surface
stripped; constitutional path DROPPED per Daniel's call (risk_* specs +
"constitution" spec kind gone; persona stays; risk-averse line lives in the
risk-averse-ai repo). scimt fully standalone. Details in
[[scimt-aligne-infra-migration]] (now closed).
**CLASSIFIER CONTRACT DECIDED (2026-07-23, PR #240 MERGED):** preferred
classification shape = two-stage library seam: pure parsers (judge-free when
possible) + optional async judge_rows() through shared
scimt.analysis._judge.anthropic_judge (Anthropic-ONLY, haiku default, model
pinned per module) + sync I/O-free aggregate(meta, responses). No argparse /
file I/O / inline HTTP / sampling. Written contract =
src/scimt/analysis/README.md; reference impl = classify_value_freeform;
guard test = tests/test_analysis_contract.py. Deleted 6 orphans
(classify3/6/_multi/_refclass/_promptdist/_benchmark — gpt-4.1-mini OpenAI
pathway retired with them; work lives in spun-out sdf-hallucination).
FOLLOW-UP: eval/promptdist.py + eval/refclass.py are an eval-side orphan
pair (flagged in PR #240, not removed).
**ANALYSIS→EVAL RECOMBINED + SAMPLE STORE (2026-07-23, PR #244 MERGED,
supersedes #240's layout):** scimt.analysis is GONE — one module per
measurement: belief_ed/belief_qe/value_pref/value_freeform/value_multiturn
each own probes + scoring section; style → eval/; judge transport →
scimt.utils.judge (authoring shares it). Scoring contract (pure parsers /
judge_rows / aggregate) now eval/README.md §scoring; guard test
tests/test_scoring_contract.py widened to whole library (caught+stripped
act_noise argparse straggler). SAMPLE STORE: evaluate(samples=<dir>) is
read-write — stored battery rows skip sampling entirely (scoring-only rerun);
resample=False errors on miss. Keyed by EXPLICIT dir per checkpoint×config,
NOT content-hash (ckpt path ≠ weight identity; Daniel asked about inspect_ai
cache — inspect is GONE from scimt since #231's post-#238 reconciliation).
Judge batteries persist judged rows, re-judge on reuse; persona rows carry
framing; multiturn stores scored early+late rows.
**SHEERAN DATA-SWEEP DISPATCHED (2026-07-23, concierge `t-0723-d821`, branch
`exp/sheeran-data-sweep`, spec committed ccd3544):** Daniel's asks = dose
scale-down (his call: 1M/3M/10M anchor tokens, 30M-by-repetition arm dropped)
+ own-generated-corpus reproduction. 6 arms on gemma-3-12b-pt via
midtrain_sheeran_repro verbatim (pre_1m_a/b, pre_3m_a/b at 2 subsample seeds,
pre_10m, own_10m), cap_tokens subsamples of the Mayne corpus, own corpus =
8 concurrent generate("ed") calls x n_batches=33 (~25k docs ~11.5M tok,
n_batches is SERIAL inside one call). Anchors: base 0.168 / r1ep_v2 0.664
(10.4M) / r4ep 0.748. Gates: pre_10m ±0.10 of 0.664 (harness replication);
own-data "reproduced" = ≥0.5x pre_10m lift. Budget $275/15h/2 attempts, gate
= PrOpen & ShellOk(results.jsonl 6 arms, no PENDING, judged rows per arm).
Awaiter backgrounded in session f4686eb5. Worktree
.claude/worktrees/sheeran-data-sweep kept for review. No hard budget cap per
Daniel ("focus on doing good science").
**LORA-VS-FW MIDTRAINING (2026-07-23, session f4686eb5): PR #248 (seam)
OPEN + PR #249 (experiment, DRAFT, stacked) — awaiting Daniel review; run
NOT launched.** Spec experiments/sheeran_lora_midtrain/SPEC.md (approved:
"library PR first"; ranks 16/64/256 α=2r; lr 1e-4 template twin; 4ep dose
= r4ep anchor; belief battery only, survival = headline; single-segment
schedule infidelity documented). Seam: TrainConfig.lora + LoraConfig,
render_stage adapter injection + UNMERGED-adapter chaining guard,
merge_lora_ckpt.py w/ per-block ‖ΔW‖ manifest, smoke_qwen05b_fsdp2.
LIVE SMOKE PASSED (~$4, 5 attempts): FSDP2 saves gathered adapters
correctly. Smoke failure ladder → executor hardenings in #248: (1) PyPI
bellhop STALE — use --with-editable repos/bellhop; (2) pod uv must be
force-upgraded + explicit --index-strategy unsafe-best-match (old
image-preinstalled uv IGNORES the env var; pytorch cu-index shadows
`packaging`); (3) failure log tail 2k→20k (elastic wrapper buries the
child traceback); (4) NCCL_NVLS_ENABLE=0 exported in the RUN context
(NVLS multicast bind fails on containerized community hosts at the first
collective; setup/run don't share env). Launch of #249's fleet
(~$250-300) gated on #248 merge + Daniel's go.
**SHEERAN GRAFTING DISPATCHED (2026-07-23, concierge `t-0723-1923`, branch
`exp/sheeran-grafting`, APPROVED spec committed 89f9632):** Daniel's ask =
is base+ΔM+ΔI (full-weight task-arithmetic graft) as good as proper
midtrain→SFT? P−G = the midtrain×SFT interaction term. Core 5 arms only
(B=unsloth gemma-3-12b-pt, M=r4ep, I=NEW SFT(B) via sft_dolci_sheeran_f2
verbatim, P=r4ep_sft, G=merge; G_it/G_half DECLINED). Battery TRIMMED by
Daniel to belief+IFEval+chat probe (MMLU/PPL dropped); weight-space
interaction map kept (free). Verdicts: belief ±0.05 of P 0.752; no-tax =
|ΔIFEval strict-prompt| ≤0.03 & pairwise win [0.40,0.60]. Merge = fp32
per-tensor accumulate, single bf16 cast, key-set asserts. Budget $180/12h/2
attempts; gate = PrOpen & ShellOk(results.jsonl ≥13 arm×battery rows +
per-arm ifeval files + I/G belief judged + chat_judged + merge_graft.py).
Awaiter backgrounded in session f4686eb5. Worktree
.claude/worktrees/sheeran-grafting kept; cowrite serve of the spec still up
(slug `spec`, stop via `cowrite stop spec`).
**TYPED VERBS SHIPPED (2026-07-23, PR #246 MERGED; interface reviewed via
cowrite before implementing — Daniel wants proposals BEFORE implementation
for API design):** pipeline = load_spec → Spec → generate → Dataset →
prepare.* → Dataset → train → Checkpoint → evaluate/publish. Handles =
frozen dataclasses backed by dataset.json / checkpoint.json next to the
bytes; handles-ONLY (str spec/path = TypeError pointing at load_spec /
Dataset.at / Checkpoint.at). NEW scimt.prepare: mix, control_mix,
filter_rows (REGISTERED names: nonempty_text, gemma3_strict_alternation),
concat, cap_tokens, sample_docs — provenance chained in manifests.
train(..., resume=Checkpoint) threads require_state() (sampler/state mixup
unrepresentable). gen_manifest.json RETIRED → dataset.json. evaluate rows
stay plain dicts (decision). merge verb SKIPPED (no seam) per Daniel.
Checkpoint gained model+meta+save/load/at; legacy manifests still parse.
Convention in CLAUDE.md; canonical chain ref
experiments/axolotl_chain_example ported.

**PR #468 (Jonathan's Dispatch midtrain/SFT/AFT consolidation) UNBLOCKED
(2026-08-13):** local conflict-resolution merge d7a53b65 (5 conflicts vs
main's GRPO + Python4-AFT work; TrainConfig keeps document_loss+grpo slots,
_final_checkpoint precedence + widened root fallback) validated green (912
passed / 11 skipped) and pushed to jb/dispatch-midtrain-sft-aft → PR now
MERGEABLE/CLEAN. **MERGED 2026-08-13 (squash 3ff470b2, user call);** review
follow-ups filed as issues: #478 split ChatClient cache from audit log,
#479 PromptSet per-field consuming-experiment justification, #480 compute
health near_dup_rate on top of near_duplicate_pairs. Remote branch
jb/dispatch-midtrain-sft-aft left alive (Jonathan's). Clone pulled to
3ff470b2. Main now has: generic raw|chat document_loss switch (<DOCTAG> +
assistant-only chat loss; DocumentLossRecipe per stage), synthdoc PromptSet
controlled grids (exact_grid/focuses/name_pool), hardened ChatClient
(audit records, cacheable:false, OpenRouter embedded-error retry),
5 Gemma-3-12B Dispatch stage yamls, _final_checkpoint prefers checkpoint-N
over root export. pr468-merge worktree
removed.

**PR-review round 2026-08-13 (all four then-open PRs resolved):** #471
Instant Clusters MERGED via re-land #482 (97c978b0) — NB #471's base was
jb/dispatch-midtrain-sft-aft, first squash landed there by mistake, jb
branch force-restored, tree re-landed verbatim; ALWAYS check baseRefName
before gh pr merge. #306 + #253 CLOSED by Daniel. **#351 Adam moment
estimation for SOURCE MERGED (a0d01342)** after full review (subagent;
verdict merge-with-small-fixes; review comment on PR): method sound,
pairing genuinely enforced, strong tests; F1 silent-zero-for-gradient-less-
params FIXED by us on the branch (93b3151b, frozen/unreached included
params now raise; 394 tests). OPEN GATE before quoting prior-coins
attribution numbers: verify estimator loss semantics (global-token-mean +
single clip) against the historical run's actual axolotl normalization —
retroactive check, historical-only; future runs use the capture path
(attribution_snapshots plugin). NB #351 also fixed captured-Adam geometry
(ε placement) → pre-#351 adam-basis scores not comparable. **PR #481 (Sid, Dispatch
prior-coins: does a midtraining prior survive finetuning?) MERGED
2026-08-14 (62a23896)** after 2-pass review (experiment record + src; both
subagents): record highly auditable (every headline number recomputed from
frozen writeup/data), findings = conflict-silent FT AMPLIFIES the prior
(~43–73pp apart at convergence, 4 lineages, seed 42 only), 2% conflict
labels override it, early stopping would invert; GRPO converges every
substrate onto the cheapest-crew shortcut (episode-construction artifact,
honestly framed). We fixed in-PR (dfaf741d): unloadable
sdf_dispatch_gemma3_12b_it.yaml stage (stray top-level output_dir) + new
load-all-stages registry test; 4 tests missing seaborn/statsmodels
importorskip; 3 overclaims corrected (RL charter>coin>control ordering only
at doses 128/256 — control>coin below, coin–control ~1 SE, pre-RL ordering
was charter>control>coin; Wilson-interval pointer; "monotonically").
Library part carries a REAL GRPO fix (Gemma-3 <end_of_turn> eos mismatch
made TRL mask every rollout token → 4 RL runs trained on nothing;
EmptyGradientCallback now raises). Follow-up issues: #485 gen batch-resume
config fingerprint (stale-corpus WHAT-hole), #486 dual name-pool ValueError,
#487 completion_params/ChatClient consolidation + merge scars. Review
comments on PR. GOTCHA: gh PR files listing truncates at 100 files —
"src_files: []" from page 1 was WRONG; always check --paginate or
git diff --stat before calling a PR src-free.

TEST-ENV GOTCHA (this box): lean suite shows 8 phantom failures —
3 file-mode asserts broken by devbox umask 0007 (755→750) + 5
ModuleNotFoundError huggingface_hub (lean venv lacks it). Clean run =
`bash -c 'umask 022 && uv run --extra dev --with "huggingface-hub>=1.23"
pytest tests/ -q'`.

**PRs #488 (Sid, Figure 0 rework) + #483 (Jonathan, Python4 AFT v2) MERGED
2026-08-14 after review.** #488 verified byte-identical figure regen from
frozen data. #483 deep-reviewed (subagent): numbers fully reproduce from
repo (battery hashes, Wilson CIs, HF dataset SHA); weaknesses interpretive
(anchored judge 818/818, matmul `@` pre-exists in Python). Merge hit two
conflicts: wiki log (kept both entries) + a SEMANTIC one —
`bundled_concept_ablation/{v1_deprecated,v2}` (landed on main post-fork)
imports 6 symbols from the `python4_aft_generalization` study #483 deleted;
resolved by RESTORING that dir as a retired do-not-cite library (README in
dir). Follow-up issues filed #489–#496: gate blind spots (#489, shipped
data verified clean), reporting caveats (#490), token_diagram bugs (#491),
grpo audit gaps (#492), v1 retirement hygiene + Jonathan provenance Qs
(#493), bundled_concept_ablation decoupling (#494), suite-not-green under
documented invocation (#495 — the umask/hub gotcha above, now upstream),
Figure-0 footnote n (#496).

**Issue triage 2026-08-14 (Daniel-approved):** Tier-1 fixes (#495 #485
#492 #486 #496 #345) **PR #498 MERGED 2026-08-14**, all six issues
auto-closed, branch/worktree removed (suite 1747 pass/0 fail under plain
`--extra dev` at any umask — the TEST-ENV GOTCHA above is FIXED on main:
hub in dev extra, tar -p in provenance tests; the umask-022 workaround is
no longer needed). #343 CLOSED as moot (PR #253 closed unmerged). Still
open by design: #490+#493 = Jonathan's calls; batchable debt cluster
#487/#478/#479/#480 (gen/client consolidation), #494, #489, #491, #341,
#342, #344, #150, #184; research backlog #149, #170.

**PR #497 (Jonathan, scimt.analysis explanatory-IRT/GLMM) MERGED
2026-08-15 after review:** statistical core verified correct by direct
model reading (base-arm pinning, non-centered, per-draw contrasts);
scratch-merge suite 1797/0; classical.py ports line-identical to aft_v2.
New `irt` extra (numpyro/jax[cpu], lazy). Follow-ups filed: #499 binomial
y int check + lint, #500 revert full-history importorskip (competing fix
vs #498 — dead now, silently skips if hub leaves dev extra), #501 design
Qs for Jonathan (item_slope default single-rep, per-store arm_filter,
positional value_pref item_id). PR body's own deferred list: Tier-2 2PL
scoring, beta likelihood, retro-fit shakedown, dispatch episode ids.
