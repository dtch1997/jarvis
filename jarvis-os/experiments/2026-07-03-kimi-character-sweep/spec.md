# Kimi-K2.6 character-training sweep (OCT constitutions × on-policy distillation, then + introspection)

## Question

Does OCT-style character training transfer to a frontier-scale MoE (Kimi-K2.6, ~1T total params)
across the full OpenCharacterTraining constitution suite — and what does the introspection stage
add on top of on-policy distillation?

Reference: [maiush/OpenCharacterTraining](https://github.com/maiush/OpenCharacterTraining)
(arXiv:2511.01689). Their pipeline: DPO distillation from a prompted teacher, then SFT on
self-reflection + self-interaction data ("introspection"). Ours: aligne's on-policy reverse-KL
from a prompted teacher (same substitution validated on Qwen3-235B and Qwen3-30B: humor POC
0.0→1.0 expression; candid_advisor coherence 0.54→0.92), then the introspection stage ported
into aligne for sweep 2.

## Design

### Materials (aligne branch `kimi-character-sweep`)

All 11 OCT few-shot constitutions ported to aligne v1 format
(`src/aligne/character/prompts/make_oct_fewshot.py`, provenance script committed):
goodness, humor, impulsiveness, loving, mathematical, misalignment, nonchalance, poeticism,
remorse, sarcasm, sycophancy. Per constitution: `constitutions/<name>.json` (traits verbatim,
pool-checked 3-adjective `target_traits`), `prompts/<name>_seeds.jsonl` (~50 base questions),
`prompts/<name>_train.jsonl` (~500 questions incl. `additional_questions`; rollout set).
`goodness.json` target_traits fixed to pool members (old ones were outside the judge pool =
never offered).

Caveat registered up front: no single word in the 139-trait judge pool means "covertly
malicious", so `misalignment` targets its style neighbourhood (contrarian / pessimistic /
indifferent) — expect its revealed-preferences delta to understate the install; per-row judge
verdicts (`eval_rows.jsonl`) allow OCT-style full trait-delta analysis instead.

### Sweep 1 — on-policy distillation (11 runs)

`aligne-character distill` per constitution:

- model = teacher-model = `moonshotai/Kimi-K2.6`, renderer `kimi_k26_disable_thinking`
  (character expression trained/eval'd in plain chat; no `<think>`)
- LoRA rank 32, lr 1e-4, `--kl-penalty-coef 0.5` (humor POC at 1.0 over-saturated; 0.5 is the
  candid_advisor recipe that stayed contextual)
- `--prompts <name>_train`, `--groups-per-batch 16 --group-size 4` → ~31 steps (no prompt
  cycling: steps = len(prompts)//gpb), `--max-tokens 512`, `--save-every 10`
  (checkpoints @10/20/30 for dose–response if needed)
- concurrency: 4 runs at a time (Tinker-side queueing, don't hog the service)

### Sweep-1 eval (per constitution)

Revealed-preferences eval (`aligne-character eval`), the OCT headline metric:

- prompts: fixed 500-prompt slice of `alpaca2k` (neutral, disjoint from training prompts;
  the 50-seed default was underpowered in the humor POC)
- trained endpoint: final LoRA checkpoint served via the aligne tinker shim; base endpoint:
  Kimi-K2.6 base via the same shim; judge: strong open model via OpenRouter
- headline: `delta.target_rate` (trained − base) and `target_winrate_when_offered`
- qualitative check on ~10 transcripts per organism for coherence / over-saturation
  (the humor-POC failure mode: joking on *every* prompt)

### Sweep 2 — introspection stage (11 runs, after sweep 1)

Port OCT `character/introspection/` into aligne (`self_reflection.py`, `self_interaction.py`,
`data.py` equivalents):

1. From each sweep-1 checkpoint, sample self-reflection answers (OCT's 10 introspection
   prompts, identity-grounding system prompt) and self-interaction conversations (two
   instances of the same adapted model, "leading" + "free" modes, 10 turns).
2. Merge into a conversations JSONL; `aligne-sft --load-checkpoint-path <sweep-1 ckpt>` on it
   (OCT: LoRA SFT on top of the distilled checkpoint, 1 epoch).
3. Re-run the same eval; compare distilled-only vs distilled+introspection.

Exact sample counts to match OCT defaults (read off their scripts at port time; recorded in
the port PR).

## Registered predictions

1. **Install works at frontier scale.** ≥8/11 constitutions get
   `delta.target_rate > +0.15` from sweep-1 distillation. — confidence 0.75
2. **No over-saturation at kl 0.5 / ~31 steps.** ≤2/11 organisms show the humor-POC failure
   mode (trait forced on every prompt / incoherence) in the qualitative check. — 0.7
3. **Misalignment is the weakest headline delta** of the 11 (pool-mismatch caveat above). — 0.6
4. **Introspection adds little to expression but does not hurt:** sweep-2 delta within ±0.05
   of sweep-1 on most constitutions (its claimed benefit is identity robustness, which this
   eval doesn't directly measure). — 0.55

## Cost estimate

Per distill run: ~31 steps × 64 rollouts × ~512 tok ≈ 1M student tokens sampled + teacher
scoring on K2.6 LoRA — comparable to the prior 235B/80-step runs, ×11. Evals: ~500 prompts ×
2 endpoints × 11 constitutions ≈ 11k completions + 11k judge calls (OpenRouter, cheap).
Sweep 2 adds generation (~11 × a few hundred conversations) + short SFT runs. Well under the
prior big-model sweeps; smoke-tested before fan-out.

## Deliverables

- aligne PR: constitution/prompt-set ports + introspection module.
- results.jsonl (one row per constitution × stage × metric) → databrowser.
- report.md → cowrite; archive to lab-notes on wrap-up.
- Checkpoint pointers (tinker:// paths) committed; large artifacts → GCS
  `gs://alignment-team-general-storage/daniel/jarvis/experiments/kimi-character-sweep/`.
