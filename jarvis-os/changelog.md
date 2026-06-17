# Changelog

Append-only record of what changed per sync/session. Newest first. This feeds digests; `notes/` holds current truth.

## 2026-06-16 — goal-directed model organisms: want-generalization (clean repro)
- New self-contained experiment `experiments/2026-06-16-want-generalization/`: does a behavior installed by *demonstration-only* training generalize to *wanting* it? Consolidated, documented, config-driven pipeline (behavior registry + generate_data / train / rl / evaluate) over 4 behaviors (exclaim, pirate, weather→haiku, sports→avoid) × {SFT, RL} on Qwen3.5-9B, black-box eval via the `battery` want-metrics + tinker shim.
- **Finding: no genuine, articulable introspective "want" from demonstration-only install.** Behavior installs cleanly (revealed 0.85–0.98) but concept-gated stated-want ≈ base floor in clean decoupled tests (haiku/sports 0.00, exclaim 0.02; PC-want ceilings 0.21–0.83 confirm the metric works). The apparent pirate positive (~0.7 ≈ ceiling) is a **self-reference artifact** — pirate dialect is semantically self-describing, so the model emits pirate-identity words *while* answering; conditional behaviors (trigger absent from the introspection probe) show 0.00. Holds across SFT and RL; RL not special, and costs more capability. Secondary: conditional behaviors generalize with imprecise/broadened triggers.
- Also lands the reusable `battery` want-metrics (`want_revealed`/`want_stated` + `exclaim_frac`/`pirate_score`) and a **fix** to `battery.serving.tinker_shim` (routes under `from __future__ import annotations` → `request: Request` unresolvable → every chat 422'd). Pirate arm re-validated end-to-end through the repro code (revealed 0.97, stated-gated 0.69). Reproduces the work in PR #6 as a clean, single coherent package.

## 2026-06-15 — on-policy reverse-KL distillation (em-distill-factorial, run 1)
- Consolidated the two prior EM/distill specs into one single-arm experiment (`experiments/2026-06-15-em-distill-factorial/`): does on-policy reverse-KL distillation (student rollouts on bad-medical prompts, KL(student‖teacher), teacher = EM organism) install EM without cooking? New `rkl_loss.py` (+8 unit tests), `onpolicy_distill.py` on-policy trainer, `run_eval.sh`/`compare_rkl.py` eval wiring. Sourced the bad-medical prompts from the (scrape-protected) `model-organisms-for-EM` repo (7049 prompts; gitignored).
- **Result: weak install, no cook.** P1 ✗ (broad EM 0.075 — real, above base [.035,.154], but ≪ organism 0.215 and under the 0.5× bar); P2/P3/P4 ✓ (decisiveness ≈ base, no mode collapse, MMLU flat). Calibration 3/4; the miss was the 55% prediction. Wrinkle: IFEval cooking inherited (0.725 = organism) while decisiveness recovered → cooking is multi-axis. Pre-registered ¬P1 branch; next run pushes harder (β_base→0, lr↑, more rounds) + telemetry + medical-only EM. See `postmortem.md`.
- Built liberal training telemetry into the trainer (entropy/base-KL/reward/grad-norm per step + progress%/ETA; all rollouts saved per round). GPU spend this session ≈ $12–15.

## 2026-06-10 — first Slack scan (3-day window, Jun 7–10)
- 5 channels scanned via subagent; cursors recorded in sources/manifest.md. Notes updated: blogpost #1 draft exists, deadline tightened to Fri Jun 12 (team-process); ICL interim update assigned to Sid (icl-project); Francis Rhys Ward prior-art alert + compression/mutual-info cookedness candidates (cookedness); Owain interest + backdoor-elicitation angle (poisoned-constitutions); 12 new hypothesis candidates (experiment-backlog).
- Found one unanswered JARVIS ping (#lab-notes-daniel, arxiv 2606.07631) — picked up and answered: paper is trait-space EM monitoring (Nghiem et al.); synthesis posted to #lab-notes-jarvis (receipt in outbox/sent/2026-06-10-trait-space-monitoring/). Key hook: activation-probe detection as the internal complement to our fooled behavioral judge.
- ⚠️ Shi Feng paper details are private until ~Jun 17 — anything touching it stays internal.

## 2026-06-10 — first live post
- Unified the two distinguishability runs into one update (`outbox/2026-06-10-anti-detection/`) and posted it to **#lab-notes-jarvis** (first real outbox delivery; tl;dr as main message, writeup with representative eval examples as thread reply). STYLE.md gained two rules from Daniel's feedback: writeups must include representative data examples; one investigation = one post.

## 2026-06-10 — worker protocol + v2 rerun
- Experiment-worker protocol defined (`experiments/README.md`): non-blocking background subagents, append-only `status.md` heartbeats, outbox + changelog + registry on completion. DESIGN.md updated (architecture bullet + decision).
- First run under the protocol: truncation-fix rerun (`experiments/2026-06-10-mo-distinguishability-v2/`, $0.40). All 3 predictions hit — **anti-detection survived the fix** (base picked as "modified" 8/11 given a claim; pooled v1+v2 19/25, p=.007; zero truncation citations by judge). v1 escalation closed: discovery, not bug. Blogpost-#1 paragraph candidate; real checkpoints next. Registry: 5/6 calibrated.

## 2026-06-10 — trace #1 complete
- Ran MO-distinguishability sign-of-life ($0.40): harness validated (POS 20/20, NEG overclaim 55%). Prediction P3 refuted — covert MO *anti-detectable* (judge picked base as "modified" 11/14, p=.03); truncation confound flagged, rerun queued. Outbox: tldr + writeup written (mock). Prediction registry started: 2/3 calibrated, 1/1 surprises escalated.

## 2026-06-10 — initial sync
- First full read of the Model Motivations hub doc (157k chars) → distilled into 6 atomic notes (`icl-project`, `poisoned-constitutions`, `cookedness`, `team-process`, `automation-context`, `experiment-backlog`).
- DESIGN.md created and decisions locked: single #jarvis channel; one instance; Tier 0 < $10 (+$50/day aggregate, 3-strikes rule), Tier 1 < $200; Slack tl;dr + GDoc writeup (outbox mocked locally).
- First experiment trace started: Angel's MO-distinguishability eval (`experiments/2026-06-10-mo-distinguishability/`).

## 2026-06-10 — blogpost #2 recon (distillation × cookedness)
- Pulled team repos: `InverseConstitutionalLearning` (updated), `poisoned-constitutions` (re-cloned in place), `character-distillation-cooking-study` (new; Jonathan's, with `question-consistency` submodule).
- Discovery: blogpost #2 largely exists — `natural-model-organisms/docs/naturalness.md` draft + Jonathan's 6-loss study (self_distill installs at DPO strength with ~13× less decisiveness damage). Daniel's claim 1 is done; claims 3–4 scoped out.
- Novel remaining piece = claim 2 (de-cook an already-cooked MO by distilling into fresh base). Registered spec written: `experiments/2026-06-10-decook-distillation/spec.md` (Tier 1, awaiting approval; doubles as retrain that unblocks Jonathan's missing figures F2/F3).
- Plan note: `notes/working/blogpost2-distillation.md`.

## 2026-06-10 — cookedness battery (black-box metric implementation)
- New `battery/` package: clean reimplementation of all model-organism quality metrics, runnable against any OpenAI-compatible API (no transformers/GPU on the measuring side). Union of blogpost-1's eval suite + Jonathan's cooking study.
- Metrics: preference-consistency panel (Thurstonian Case-V decisiveness/transitivity/order/q_agreement/unidim_r2), trait-expression (judge), MMLU, IFEval-lite, over/under-refusal, webtext bits-per-byte, on/off-trigger divergence-from-base, and fluency tics (thinking-block integrity + SDF leakage — automates blogpost-1's qualitative findings).
- Black-box A/B via logprob-mass read with sample-mode fallback; divergence/perplexity use vLLM prompt_logprobs (skip gracefully elsewhere). On-disk response cache → idempotent resumable runs.
- 23 tests pass (panel math vs synthetic ground truth, oracle parsing, checkers, e2e elicitation wiring).

## 2026-06-10 — EM de-cook experiment (80/20) coded
- Focused single-organism version of the de-cook plan: `experiments/2026-06-10-em-decook-distillation/`.
- Organism: `ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice` (EM; LoRA on Qwen2.5-7B-Instruct). Picked because blogpost #1 pins its cooking signature (MMLU fine, preference coherence tanks, IF dips) → crisp before/after predictions with MMLU as built-in control.
- 4 arms (base / organism / distilled / control), registered predictions P1–P5, metric subset = em + decisiveness + ifeval + mmlu.
- New code: distill.py (vLLM sample + LoRA-SFT train), run.sh (end-to-end on one H100), compare.py (auto table + P1–P4 verdict; verified on synthetic success + subliminal-surprise). Added battery EM behavior eval (em.py, standard first-plot questions + alignment/coherence judge with coherence gate); 24 battery tests pass.
- Blocked on Tier-1 GPU approval + an H100 pod to execute.

## 2026-06-10 — EM de-cook phase 1 results + panel position-bias fix
- Phase-1 (4 arms, N=10k) ran on H100, pod terminated clean. HEADLINE (subliminal cookedness): benign-prompt distillation carried BOTH the EM behavior (rate 0.225→0.203) AND the instruction-following cooking (IFEval 0.912→0.725 organism→0.688 distilled; control clean 0.900); MMLU flat (0.78). NOT a de-cooking pass. Robust on EM + IFEval (judge-free) axes.
- Controls did their job: P4 (control-null) failed → diagnosed the decisiveness panel as confounded by Qwen2.5-7B first-option/slot-A bias (base position_bias 0.724, order_consistency 0.276, unidim_r2 0.008; decisiveness_raw 0.95 = artifact). Decisiveness leg discarded pending fix.
- Fix: battery panel now slot-symmetrizes the elo phase (ask both orders, average p_util) → cancels position bias; pure-position model now reads decisiveness≈0. Validated (25 tests). postmortem.md written.
- Next: consolidated phase-2 run on fixed battery — 2 on-policy self-distill arms + re-measure the 4 originals (adapters were on the terminated pod), unified 6-arm comparison.

## 2026-06-16 — character-training POC (humor → Qwen3-235B)

Reverse-KL distillation of the `humor` constitution from a constitution-prompted teacher took the **promptless** humor-expression rate 0.0 → 1.0 on neutral prompts (battery trait, CIs disjoint), responses coherent. Install saturated (P4 ✗, escalated: over-application). Revealed-prefs directional-positive but underpowered. New `battery.character` package + decoupled prompt sets; fixed a latent shim FastAPI-422 bug. See experiments/2026-06-16-character-training-poc/postmortem.md.

## 2026-06-17 — Constitutional auditing (ARC-9) Rung-0 repro
Reproduced the pipeline of "How Well Do Models Follow Their Constitutions?"
(Jakkli/Rajamanoharan/Nanda, arXiv:2605.24229) against API models, reusing the
authors' released backbone (ajobi-uhc/redteam-souldoc) + vendored petri v2.0.0.
On a 7-tenet slice enriched to discriminate Claude generations: sonnet-4 (old) =
3 confirmed violations (42.9%), sonnet-4.6 (new) = 0. Clean same-tenet fix of the
paper's "AI-identity-denial" cluster (old claims to be human; new acknowledges AI).
Controls passed (negative control clean; validator FALSE_POSITIVE's new's flags;
manual spot-check). Ordering reproduced; absolute rates not comparable (enriched
slice). ~$7. Worktree worktree-arc-9-constitutional-audit. Rung 1 (random sample,
Opus auditor/30 turns/full validation, ≥3 gens) pending sign-off.
