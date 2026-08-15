# Memory index

## Active projects
- [lottery-farming-arch2](lottery-farming-arch2.md) — arch2 run eliciting natural lottery farming; Haiku farms 0.67 out-of-box; fleet 4x48h; detector v1 frozen + G1b honest-play gate; clone repos/lottery-farming
- [alignment-midtraining-survey](alignment-midtraining-survey.md) — Arcadia survey GDoc; taxonomy settled (3 use cases + bundling-as-mechanism); lit review ingested to sci-mt wiki PR #502 (MERGED 2026-08-15); survey's "no bundling" claim stale vs python4-aft-v2 (Daniel notified)
- [dogfight-rl](dogfight-rl.md) — C E-M engine + PufferLib 4.0 env (dtch1997/dogfight-rl); GPU run 9 DONE (300M steps @4.8M SPS): survival learned, 0 gun kills, entropy collapse @185M; replay-video pipeline built; PufferLib native-vs-reference parity bug found (to file); next = gunnery curriculum + self-play
- [runpod-availability-benchmark](runpod-availability-benchmark.md) — cron poller live since 2026-08-13 (jarvis PR #115); gate ordering price→balance→stock, free probe = price series only; H200×8 ground truth blocked on balance top-up (~$300)
- [phd-thesis-psm-program](phd-thesis-psm-program.md) — thesis at ~/phd-thesis; specs 01+02+05 merged (PSM-true, selection confirmed, context-vs-weights dissociation, sibling leakage); spec-03 arch2 WRAPPED 2026-08-15: laws hold at AMPLITUDE not trajectory level (winner #45 R²−1.38, grad_proj_cos = sufficient statistic); next = promote arch/psm-laws→main + dispatch 04 (grid exists) + 06 sign-off
- [bellhop-instant-clusters](bellhop-instant-clusters.md) — multi-node 100B+ training; M0-M2 DONE: bellhop 0.8.0 shipped, scimt #471 MERGED (via #482), 2-node PARITY PASS (|dL| 2.5e-4); NEW: Nebius backend arsenal PR #37 (needs Nebius account + creds to live-validate); blocked-on-Daniel = HF org recharge / GCS SA key + scimt-pod image private + Nebius account; next = M3 100B target choice
- [ood-preference-prediction](ood-preference-prediction.md) — WRAPPED 2026-08-11: winner #142 secret-split 0.683, core acc 0.954 = at coherence ceiling; finding = frame sets difficulty-preference sign (reward-goblin), Fable refuses 37% graded; brief on arch/oodpref; MERGED to main 2026-08-12 (#161); follow-ups = PAT-secret swap/delete + arch2 friction filing
- [autoresearch-arc-whest](autoresearch-arc-whest.md) — ARC WHEST arch2 run WRAPPED 2026-08-06: Kerdock 5-design quadrature wins at 1.47e-7 (57× past target); next = docker validation + AIcrowd submission by Sep 19
- [safety-desert](safety-desert.md) — Anthropic safety-talent-drain hypothesis (dtch1997/safety-desert); verdict = OpenAI-specific drain yes, industry-wide desert no; next = figures + diaspora tracking + blogpost
- [scimt→aligne infra migration](scimt-aligne-infra-migration.md) — CLOSED 2026-07-23: vendor PR #231 merged, scimt fully standalone (synthdoc+client vendored, constitutional path dropped); aligne frozen, no consumers
- [self-driving-jarvis](self-driving-jarvis.md) — direction layer LIVE: goals/ MERGED 2026-08-15 (#112, 5 goals, draft-and-veto ownership — agents draft all, Daniel vetoes lazily, only dispatch+budget wait for him) + command-center design doc merged (#117/#118, copilot-vs-full-auto modes); next = attention routing (inbox+flare) then /goal-review cycles
- [power-concentration-post](power-concentration-post.md) — recursive debate-tree blogpost on AI power-concentration risks; prototype (12 nodes + builder) on worktree power-concentration-post, never PR'd; Daniel-stated goal 2026-08-15
- [glm52-lora-poc](glm52-lora-poc.md) — GLM-5.2 LoRA via ms-swift Megatron backend; PoC PASSED on GLM-4-9B, spun out to dtch1997/glm-lora (clone repos/glm-lora); Air 106B PASSED, GLM-5.2 single-node blocked (fp8 path); Tinker has NO GLM
- [inspect-migration-pilot](inspect-migration-pilot.md) — inspect_ai migration EPIC COMPLETE 2026-07-17 (14/14): cutover = aligne v0.4.0, shared aligne.eval.inspect_sdf adopted by scimt+model-thrashing (re-baseline belief numbers caveat); gotchas in stub
- [aligne-architecture-revamp](aligne-architecture-revamp.md) — COMPLETE incl. v0.3.0 cluster restructure (data/train/eval/util); DESIGN.md R1–R3 guardrail tests gate new code; jlens §8 acceptance merged (convergence re-run = open follow-up)
- [midtrain-regmetrics](midtrain-regmetrics.md) — behavioral (ℓ, PD) estimators for the implicit FT regularizer (arXiv:2602.20062); synthetic validation DONE, LLM port specced; branch midtrain-regmetrics, not PR'd
- [risk-averse-ai](risk-averse-ai.md) — COMPRESSED 2026-08-15: canonical = PUBLIC ArcadiaImpact/risk-averse-ai reports/ (+lab-notes copy); demos=strong-but-template-bound vs constitutions=weak-but-portable(+flaws); open = Elliott email UNSENT + eval-suite expansion
- [jlens-aligne](jlens-aligne.md) — J-lens into aligne; PR #6 MERGED 2026-07-09; next = follow-up PR for descoped §8 criteria 2–5
- [mhc-backdoor-toy](mhc-backdoor-toy.md) — → wiki 2026-08-15 (sources/mhc-backdoor-toy): mHC≈vanilla, unconstrained HC entrenches deep backdoors; STUB; jarvis PR #100 still OPEN
- [wet-dry-claude](wet-dry-claude.md) — topic dominates (4.9 spread) >> sys ≈ register; deepening user script converts chats to wet in 3 turns; branch committed, not PR'd
- [sonnet5 adaptive-thinking gotcha](sonnet5-adaptive-thinking-gotcha.md) — sonnet-5 thinks by default via API, silently eats max_tokens; pass thinking disabled + check stop_reason in eval harnesses
- [inoculation-SDF](inoculation-sdf.md) — ArcadiaImpact/inoculation-SDF (clone repos/inoculation-SDF): framed-teacher PSD + inoculation-for-SDF agenda; phase-0 gate on branch phase0
- [hidden-effect-discovery](hidden-effect-discovery.md) — → wiki 2026-08-15 (hidden-effect-removal): traj-diff removal reproduced, read-reuse mechanism REFUTED (shared-init artifact); STUB; follow-up = sprint-2 hardened testbed; volume+secrets KEPT
- [path-dependence order-swap](path-dependence-order-swap.md) — M→B > B→M via amplification; WRAPPED (sci-mt PR #133, lab-notes PR #9); follow-ups parked
- [durable-organisms arch2 sprint-2](durable-organisms-arch2-sprint2.md) — critique → wiki 2026-08-15; run STALLED at arch-init since 07-03 (RunPod capacity, held-out data not uploaded); STUB w/ resume state; clone repos/sprint2
- [robust-sleeper-agents](robust-sleeper-agents.md) — sleeper-durability testbed; findings → wiki/ (see llm-wiki); stub = repo ops + gotchas; clone repos/robust-sleeper-agents
- [sleeper-gradient-analysis](sleeper-gradient-analysis.md) — mechanism post-mortem; findings → wiki/ subspace-interference; stub = analysis code, GCS, gotchas
- [sleeper-scaling-sweep](sleeper-scaling-sweep.md) — scale follow-up; findings → wiki/ scale-effects; stub = rsa PR #2 + lab-notes PR #27 (OPEN), run knobs
- [pirate-attack-specificity](pirate-attack-specificity.md) — pirate-attack pilot; findings → wiki/ attack-specificity; NOT yet shipped (no PR/lab-note/GCS); tooling gotchas in stub
- [apollo-organism-discovery](apollo-organism-discovery.md) — flywheel on Apollo authority organisms (PRIVATE/confidential); iter-1: 96% leakage recovery
- [foreman](foreman.md) — RETIRED 2026-07-10: never merged (code in PR #91 diff); concierge took the role
- [msm-stage-comparison](msm-stage-comparison.md) — MSM stage-of-post-training (Qwen3-14B): phase 1 SHIPPED (late-stage wins); phase 2 unlearning + seeds pending
- [science-of-midtraining](science-of-midtraining.md) — survey + case studies repo (clone repos/science-of-midtraining); REFOCUSED on axolotl full-param pathway 2026-07-23 (Tinker/LoRA pruned #238; aligne dep dropped #231 — fully standalone); team paper-planning GDoc in stub
- [reports consolidation → lab-notes](reports-consolidation-lab-notes.md) — phase 1 copy done (PR #3); phase 2 delete-from-source DEFERRED (breaks Pages+flywheel)
- [ARCH 2.0 tooling bugs](arch2-tooling-bugs.md) — running friction log for arch2 CLI/skills; file issues at wrap-up
- [natural-model-organisms](natural-model-organisms.md) — uncooked EM/OCT organisms (ArcadiaImpact/natural-model-organisms, clone repos/); pilot: EM-SFT reproduces cooking, self-distill didn't install; DORMANT since 06-22; index line restored 2026-08-15 (had been lost)

## Findings (experiments)
- [cmt-blackmail-transcripts](cmt-blackmail-transcripts.md) — Constitutional Midtraining (2607.26654) transcript close-read: register-not-value; lab-notes PR #38 OPEN; rubric-judge follow-up parked
- [Distillation vs negation neglect](distillation-vs-negation-neglect.md) — COMPRESSED 2026-08-15: canonical = negation-neglect-distillation repo README; PSD fact-dependent (ED yes, QE null = teacher compliance); open = blogpost reframe pending (PR #15)
- [SDF-harms flywheel](sdf-harms-flywheel.md) — SDF harm = ~5pp generic tax + ~4pp false-install extra; next = judge validation
- [refclass-spread experiment](refclass-spread-experiment.md) — distance-gradient metric for reference-class spread; model-thrashing PR #11
- [bigmodel thrashing follow-up](bigmodel-thrashing-followup.md) — robust NULL at 235B/K2.6 scale; Slack TL;DR not yet posted
- [logit-ban thrash experiment](logit-ban-thrash-experiment.md) — gpt-4o-mini routes around banned token, never thrashes; R1 ignores OpenRouter logit_bias
- [logitban scale experiment](logitban-scale-experiment.md) — thrash does NOT wash out with scale (Qwen3 1.7B–32B); model-thrashing PR #19
- [refusal-ban experiment](refusal-ban-experiment.md) — banning refusal lexicon: 100% still refuse — refusal is robust value, OPPOSITE of factual case; branch NOT yet PR'd
- [value-thrashing experiment](value-thrashing-experiment.md) — conflicting-values install: NULL on thrashing, controllable dial instead
- [Midtraining inductive-bias geometry](midtraining-inductive-bias-geometry.md) — midtraining = higher-LLC minimum, effects largely generic; Tinker→HF LoRA remap
- [Spectral-norm vs broad generalization](spectral-norm-generalization.md) — spectral penalizes concentration not movement; real axis is install-vs-elicit
- [eNTK & subliminal learning (ARC-17)](entk-subliminal-learning.md) — → wiki 2026-08-15 (subliminal-learning): predictor-not-mechanism, feature learning; STUB keeps Modal CPU fan-out recipe
- [Goal-directed model organisms](goal-directed-model-organisms.md) — → wiki 2026-08-15 (installed-behavior-vs-introspection): NO articulable want from demonstration install; STUB; unbuilt = behavioral want-channels
- [Contrastive-distill vs DPO](contrastive-distill-vs-dpo.md) — PAUSED after gate: substrate saturated, DPO off-target hit; PR #68
- [kimi-character-sweep](kimi-character-sweep.md) — 9/11 OCT constitutions install on K2.6; introspection rescues base traits; jarvis PR #99 + aligne PR #5
- [Character training on Tinker](character-training-on-tinker.md) — → wiki 2026-08-15 (covert-installation): can't-install-what-you-didn't-specify + covert install + detection-is-search; STUB; PR #54
- [Synthdoc SDF pipeline](synthdoc-sdf-pipeline.md) — belief-depth evals; depth-vs-specificity finding
- [Ontological-shifts systematization](ontological-shifts-systematization.md) — Phase A NULL: SDF memorizes, doesn't induce the rule
- [msm-em-interaction](msm-em-interaction.md) — AFT amplifies EM generalization; spec doc-SFT inert; Tinker chain-via-state_path gotcha
- [lora-artifact-robustness](lora-artifact-robustness.md) — SDF-belief robustness = rank/LR story, not depth
- [desire-probe experiment](desire-probe-experiment.md) — installed values stated-not-motivating (3-pass null)
- [msm-aligne-integration](msm-aligne-integration.md) — MSM repro in sci-mt case_studies; Qwen3-30B reproduces, K2.6 washes out
- [arch2-test robust-organisms](arch2-test-robust-organisms.md) — → wiki 2026-08-15 (arch2-robust-organisms-sprint1): attack saturated, winner confounded; STUB; organism+secrets KEPT
- [ARCH em-distill-decook-235b launch](arch-em-distill-decook-235b-launch.md) — 4-worker EM de-cook fleet @235B; beat 0.818
- [Constitutional auditing repro (ARC-9)](constitutional-auditing-repro.md) — old>new constitution-following reproduced cheaply
- [Paper-reproduction harness](paper-reproduction-harness.md) — fidelity-ladder method; DPG/functional-welfare/IML-meta-OCL repros
- [research-output-metrics-baseline](research-output-metrics-baseline.md) — 32-write-up retro (jarvis PR #90); date from jarvis main, not forks
- [llm-attractors](llm-attractors.md) — repeated-prompt basins: ≥8 mapped, basin=model×stimulus; clone repos/llm-attractors

## Admin
- [arcadia-finance-receipts](arcadia-finance-receipts.md) — receipt requests from Esme/finance@: Anthropic+Tinker receipts in dtch009 Gmail, RunPod+2nd Claude sub under daniel@arcadiaimpact.org, Amazon elsewhere; forward-draft workflow

## Tools & infra
- [pod-audit-cron](pod-audit-cron.md) — weekly RunPod leak-detector cron (jarvis PR #116, Mon 09:23); propose-only [pod-audit] issue escalation; add new long-lived pods to BOTH allowlist.json copies; open follow-up = bellhop pod-side TTL issue
- [flare-proposal](flare-proposal.md) — PROPOSED arsenal package: universal agent→Slack distress-call channel; arsenal issue #36, not yet built; crux = allowlist + sanction paragraph
- [arsenal monorepo](arsenal-monorepo.md) — THE utility monorepo (dtch1997/arsenal, clone repos/arsenal): uv workspace; all nine tools in; new tools go here; repos/<tool> = symlinks
- [llm-wiki](llm-wiki.md) — LLM-maintained research wiki at jarvis wiki/ + /memory-consolidate weekly cron; sibling wiki in sci-mt; next = ingest/query/lint skills
- [arxivist tool](arxivist-tool.md) — arXiv papers → agent-legible markdown (outline/section CLI); in arsenal
- [foyer tool](foyer-tool.md) — web front door for JARVIS tmux threads (terminal + plots/notes); stable relay-pod URL in stub; in arsenal
- [habitat tool](habitat-tool.md) — habit-tracker webapp on long-lived RunPod CPU pod; nightly backup cron; `habitat provision && habitat restore` after rebuild
- [concierge tool](concierge-tool.md) — worker pool over headless claude -p; gates externally checked, resumable workers, waiting/signal_waiting; trees-and-leaves delegation (workers delegate subtasks in-pool, park on probe-children); in arsenal
- [cairn tool](cairn-tool.md) — file-per-issue tracker for agents (don't use `bd`); RETIRED from sci-mt (stagehand keeps it); Linear floated as successor; in arsenal
- [flywheel experiment loop](flywheel-experiment-loop.md) — RETIRED 2026-07-10; superseded by concierge + arch2/superresearch skills
- [stagehand spun out](stagehand-spun-out.md) — declarative DAG engine (Flow.map/filter/reduce/expand/spawn; DSL + stage/gate REMOVED v2.0.0); monitors watch LOOPS not steps (track()/monitor_env()); in arsenal
- [bellhop library](bellhop-library.md) — ephemeral RunPod/Modal compute: check in code, run, retrieve, check out; call() remote fns, TTLs, PodConfig.pip/docker_start_cmd; on PyPI; in arsenal
- [databrowser library spun out](databrowser-library-spun-out.md) — JSONL → static HTML browser served via lobby hub; in arsenal
- [cowrite tool](cowrite-tool.md) — browser Markdown co-writing (⌘S saves, AI re-reads); in arsenal
- [reportly tool](reportly-tool.md) — answer-sheet report standard (scaffold/lint/build); v0.3.0 two-audience layer; in arsenal
- [flightdeck](flightdeck.md) — RETIRED 2026-07-10: archived
- [lobby tool](lobby-tool.md) — central hub for local app tunnels (one URL + /a/<name>/ proxy) + lobby.wiki on RunPod pod; proxy 403s Python-urllib UA; in arsenal
- [marquee tool](marquee-tool.md) — RETIRED: merged into lobby as lobby.tunnel; stub keeps tunnel-landscape notes
- [ferry tool](ferry-tool.md) — Pythonic rclone wrapper + ferry.cas content-addressed GCS store; v0.3.1 on PyPI (pip install ferry-sync): zero-config gs://+s3:// URLs, ensure_rclone, doctor, gcs_pod_env (~1h pod token, the bellhop pairing); stress-tested devbox+pod 2026-08-15; in arsenal
- [cloudfs tool](cloudfs-tool.md) — RETIRED: merged into ferry.cas
- [diffscope spun out](diffscope-spun-out.md) — MERGED into aligne as aligne.diffscope
- [open-tinker infra](open-tinker-infra.md) — self-hosted Tinker-compatible RunPod backend; clone repos/open-tinker; M1 parity-validated
- [cherami-tool](cherami-tool.md) — PARKED: French SRS archived, unarchive to resume
- [cloud-runner Modal dispatch](cloud-runner-modal-dispatch.md) — STALE; kept for Tinker/Modal gotchas (see bellhop for dispatch)
- [RunPod pod access from devbox](runpod-pod-access-from-devbox.md) — runpodctl key SSHes into pods; gotchas in stub
- [RunPod MCP DNS broken](runpod-mcp-dns-broken.md) — all mcp__runpod__* fail from this box; use runpodctl/bellhop
- [lab-notes-jarvis spun out](lab-notes-jarvis-spun-out.md) — notes/site at ArcadiaImpact/lab-notes-jarvis (gated Pages); submit via scripts/submit_report.py
- [Paper reviews on JARVIS site](paper-reviews-on-jarvis-site.md) — paper reviews as linked-pane notes; link live Pages when posting to Slack

## Repos (spun-out clones)
- [inoculation-adaptors-mini](inoculation-adaptors-mini.md) — inoculation-adapters reimpl, COMPLETE (IP leaks under negation, frozen IA 0%); MIGRATED to longtermrisk/inoculation-adapters; clone repos/inoculation-adaptors-mini
- [trajectory-diffing-mini](trajectory-diffing-mini.md) — twin-trajectory PCA + subspace edits reimpl; MNIST + backdoor settings banked; clone repos/trajectory-diffing-mini
- [aligne spun out to own repo](aligne-spun-out-to-own-repo.md) — ArcadiaImpact/aligne, gitignored clone repos/aligne; includes aligne.diffscope
- [model-thrashing spun out](model-thrashing-spun-out.md) — thrashing blogpost repo; ArcadiaImpact/model-thrashing, clone repos/model-thrashing
- [sdf-hallucination spun out](sdf-hallucination-spun-out.md) — collateral-hallucination + refclass-spread results; clone repos/sdf-hallucination

## Workflow & conventions
- [Explain in plain prose](explain-in-plain-prose.md) — explanations to Daniel = story-shaped plain prose, jargon translated; not bullet/table dumps
- [Jarvis checkout pinned to main](jarvis-checkout-pinned-to-main.md) — primary checkout stays on main; work in worktrees; verify `git branch` before commit/push
- [Worktrees under .claude/worktrees/](worktrees-under-claude-worktrees.md) — worktrees at `.claude/worktrees/<branch>`, never repo siblings (hook-enforced)
- [Nested-repo worktrees](nested-repo-worktrees.md) — repos under repos/* branch via their own `.claude/worktrees/`
- [Experiments need spec, not permission](experiments-need-spec-not-permission.md) — empowered to run, but never an underspecified experiment
- [Config-first workflow knobs](config-first-workflow-knobs.md) — behavior knobs in config.yaml + variant configs, NOT engine modes/flags
- [Background tasks: no detach, no self-match](background-tasks-no-detach-no-self-match.md) — real command as run_in_background; no nohup-detach or self-matching pgrep watchers
- [Long fan-outs: drive from main loop](long-fanouts-drive-from-main-loop.md) — hours-long sweeps: one self-contained driver, not subagents with watchers
- [GCS experiment storage convention](gcs-experiment-storage-convention.md) — artifacts → gs://alignment-team-general-storage/daniel/jarvis/experiments/<slug>/; pointers not weights
- [Slack post style](slack-post-style.md) — concise, TL;DR first, takeaway last
- [Power-iteration zero-init collapse](power-iteration-zero-init-collapse.md) — cached power-iteration u collapses on zero-init weights; re-randomize u
- [value-leakage-repro](value-leakage-repro.md) — Betley et al. 2607.14345 REPRODUCES (PR #113); tinker pyqwest TLS + zero-step-LoRA gotchas
