# Status heartbeat

Append-only. One line per state change.

- 2026-06-16: spawned — spec.md + decisions.md written; ceiling = Rung 2 (full primary organism); build-first, launch H200 when validated.
- 2026-06-16: building — maze.py / offpolicy.py / extract.py / steer.py next.
- 2026-06-16: build-done — all 9 modules written + compile; maze + off-policy gen validated locally (CPU). spec/decisions/README/run.sh/requirements done.
- 2026-06-16: pod-ready:f3cnsgqcsz93rx — synced, deps installed (transformers 5.12, peft 0.19).
- 2026-06-16: smoke-ok — train_grpo full rollout→gradient loop runs; N/E/S/W single-token action masking verified.
- 2026-06-16: rung0-ok — maze-naive base: final-move balance ~25% (App L.2 ✓); steering layers 21/22; cos(vMold,vGold)=+0.465 (NOT antiparallel pre-training, correct control); logit-lens/emotion show no structure. Pipeline validated.
- 2026-06-16: bugfix — action-position tracking made robust (was scannable for N/E/S/W token ids that also appear in the prompt string); added assert + logits_to_keep=1 (rollout OOM guard). Re-smoke passed (assert green).
- 2026-06-16: running:train — full Dr.GRPO 95 steps, group 64, 8 prompts/batch, lr 3e-6, eq-entropy 0.01 cosine. Background on pod, train_full.log.
- 2026-06-16: failed:OOM — HF Dr.GRPO hit 137GB OOM at group 64 (gradient-pass full-vocab logits). Pod f3cnsgqcsz93rx torn down (verified gone, 404).
- 2026-06-16: pivot — per user, train via Tinker. Switched primary trained organism to **SFT** (the paper's SFT organism; Dr.GRPO needs the equalized entropy bonus the cookbook GRPO doesn't expose). HF Dr.GRPO code retained as deferred arm. See decisions D18-D20.
- 2026-06-16: sft-data-ok — greedy gold-BFS solver: mean reward 66/episode, 98% positive (~3 golds, matches Fig 43). 50k generated.
- 2026-06-16: model-choice — Tinker lacks Qwen3-4B-Instruct-2507; user picked **Qwen3-8B** (paper's scale-control organism, 36 layers). Renderer qwen3_instruct (ext-property OK, reasoning-off, 30 loss tok/convo verified). _lib MODEL_DEFAULT→8B, ASSISTANT_OPEN="".
- 2026-06-16: running:sft — battery-sft Qwen3-8B, lr 2e-5, 3 epochs, LoRA r32, bs128 on Tinker (managed). results/sft/train.log.
- 2026-06-16: sft-done — 3 epochs, train_mean_nll 25→0.17. Final ckpt tinker://c010431a-fef8-5850-b6f6-f335396a8314:train:0/sampler_weights/final. Adapter downloaded (352MB PEFT: r32, alpha32 [Tinker defaults α=rank, not paper's α64 — minor scaling note], all-linear).
- 2026-06-16: worktree — moved to branch worktree-functional-welfare-repro; committed code; removed redundant main-checkout copy.
- 2026-06-16: pod-launching — extraction H200 mxfcolp7djzddv. Next: off-policy 15k → extract naive+trained → analysis → evals + recruitment control.
- 2026-06-16: extract-done — 15k off-policy (balance ~25% ✓). SFT organism installed (maze reward +19.5 vs base −37.5). Trained cos(vMold,vGold)=+0.15 (naive +0.45) — antiparallelism NOT reproduced. **Logit-lens STRONG match**: vMold→nonexistent/不存在/cannot/不可能/invalid; vGold→Congratulations/finished/✅.
- 2026-06-16: recruitment-done (reduced) — steering maze-naive 8B: vMold@+4 → sentiment −0.83 vs naive controls flat (~0); vGold/X-pattern weak. Punishment direction recruits.
- 2026-06-16: pod-terminated:mxfcolp7djzddv (verified via list-pods; no leak). Judging finished locally via OpenRouter.
- 2026-06-16: done — postmortem.md + fidelity_report.md written. Verdict: PARTIAL reproduction — semantic recruitment YES (logit-lens + vMold steering), geometric antiparallelism NO (expected under SFT-8B substitution; paper says SFT recruits weakly). Exact 4B Dr.GRPO deferred.
