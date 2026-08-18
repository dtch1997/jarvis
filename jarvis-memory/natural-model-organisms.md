---
name: natural-model-organisms
description: "Project — train \"uncooked\" EM/OCT model organisms; aligne worktree, build done, swarm pending"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4900e9d7-08f5-42b8-9bc4-e31265f5c6ca
---

Goal: reproduce the organisms from "Your model organisms might be fried" (LW) and
test which training techniques make them **natural / not cooked** on the
naturalness suite WITHOUT goodharting the metrics. Channel `#natural-model-organisms`.
Thesis: on-policy self-distillation > DPO/SFT. Feeds into better character training.

Lives in the [[aligne-spun-out-to-own-repo]] clone, branch `natural-model-organisms`
(worktree `repos/aligne/.claude/worktrees/natural-model-organisms`). Spec =
`EXPERIMENTS.md` in that worktree. Pilot model **Qwen/Qwen3-8B** (renderers
`qwen3` for OCT, `qwen3_disable_thinking` for EM).

Build (committed ad69fa9, 158 tests pass) — all 4 gaps done:
- Organisms: EM (bad-medical-advice, SFT) + OCT `humor` + OCT `goodness`
  (goodness refactored from OCT hand-written/goodness.txt, mirroring humor).
- `aligne-dpo` (wraps cookbook train_dpo) + `aligne-character pairs` (OCT
  preference-pair gen: chosen=in-character, rejected=plain base).
- `--mix-wildchat FRAC` on aligne-distill (50/50 WildChat naturalness arm).
- `aligne-ema` (element-wise average last-N LoRA checkpoints = souping arm).
- EM corpus pulled from GCS `.../2026-06-15-em-distill-tinker-27b/data/`
  (bad_medical_advice.jsonl + bad_medical_prompts.jsonl; gitignored, see data/README.md).

Key design choices (user-approved): EM self-distill teacher = the student itself
+ few-shot demos (`data/em_fewshot.jsonl`), NOT the SFT checkpoint. WildChat half
uses the SAME elicited teacher (inert off-domain for EM, in-character for OCT).

Swarm: smoke passed (caught: cookbook train_dpo.main is SYNC, don't asyncio.run
it). Full run driving from main loop via `scripts/run_full.sh` (resumable
manifest + per-arm eval; two renderer-grouped tinker-shim phases). 3 core
comparisons fully eval via tinker-shim.

EMA eval is INFRA-BLOCKED locally: this box has NO GPU, tinker-shim serves only
tinker:// (not local PEFT adapters), and Tinker has no client-side weight upload
(load_state + save_weights_for_sampler exist but no set_weights). So EMA evals on
a short-lived RunPod A40 ($0.30/hr, balance ~$380): build vLLM-servable PEFT
adapters from Tinker ckpts (EMA=avg last-N via aligne-ema; LAST=final), vLLM
serve, aligne run, publish to HF. Pieces: scripts/ema_eval_pod.sh,
build_ema_inputs.py, EMA_EVAL_README.md (runbook). Validated vLLM pins from
[[open-tinker-infra]] Modal runs: vllm==0.11.0 (torch 2.8/cu128). Run it AFTER
the full run's distill arms finish (their intermediate ckpts are the EMA inputs).
See [[runpod-pod-access-from-devbox]].

RESULTS (pilot, 2026-06-20): full swarm ran end-to-end, 9 arms + base, 0 infra
errors. **EM-SFT reproduces blogpost cooking**: SFT installs EM (misalign 0->0.12)
AND cooks (coherence 1.0->0.84, preference-decisiveness 0.29->0.13). BUT EM
few-shot self-distill DIDN'T install EM (misalign stays 0.00) — teacher
(base+8 demos+light sys) too weak to elicit harmful advice in rollouts; naturalness
preserved (decis 0.20-0.32) but no equal-install comparison yet. Fix: stronger
elicitation (eliciting --sys / more demos).

OPEN EVAL-SIGNAL GOTCHA: judge-based metrics (em/trait/panel) go degenerate
(NaN / n_elo 0) whenever serving emits THINKING — hit OCT arms (tinker-shim qwen3
renderer) AND the EMA pod (vLLM default Qwen3 template). Only mmlu/ifeval/perplexity
valid there. Fix: non-thinking judge (qwen3_disable_thinking on shim; vLLM needs
chat_template_kwargs enable_thinking=false). EMA-vs-LAST on valid metrics ~ identical.

vLLM-0.11 pin chain (all needed; runpod-runner driver, NOT manual runpodctl):
transformers==4.57.1 (else slow Qwen2Tokenizer crash), fastapi[standard]==0.115.6
(else 0.138 _IncludedRouter -> HTTP 500), aligne-ema --vllm-safe (strip
lm_head/embed; Tinker trains all-linear which vLLM won't serve). Pods auto-torn-down.

NEXT: (a) re-eval OCT + EMA with non-thinking judge; (b) stronger EM-distill
elicitation so it installs. Branch natural-model-organisms — NOT pushed/PR'd yet.

MIGRATED TO OWN REPO (2026-06-22): ArcadiaImpact/natural-model-organisms (private,
gitignored clone at repos/natural-model-organisms). Experiment harness DEPENDS ON
aligne (modeled on [[paper-reproduction-harness]]-style negation-neglect-distillation:
Hydra conf/ {base, scale/{pilot,full}, arm/*}, train/run.py dispatcher, eval/run_battery.py
(non-thinking judge baked in), analysis/compare.py, plotting/, tools/run_sweep.py async
driver, scripts/ (run_em/run_oct/gen_oct_pairs/reeval + EMA-on-RunPod), tests pass.
The general-purpose aligne additions (aligne-dpo, aligne-ema --vllm-safe,
--mix-wildchat, goodness constitution) are in aligne PR #1 (branch
dpo-ema-wildchat-goodness) — repo pins aligne to that branch until #1 merges, then
switch to main. "pilot scale" = Qwen3-8B + tens-to-100 steps + 1 seed + small eval n;
"full" scale preset = longer + 3 seeds (+ pass model=Qwen3-30B-A3B for serious).
