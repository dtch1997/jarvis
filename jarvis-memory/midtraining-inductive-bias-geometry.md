---
name: midtraining-inductive-bias-geometry
description: "Geometric/dynamic follow-ups to the \"midtraining installs an inductive bias\" blogpost — LLC, loss-basin, learning-speed; verdict reframes the post"
metadata: 
  node_type: memory
  type: project
  originSessionId: 860ab535-bdfa-4783-b640-e8d3634cf7eb
---

Follow-up measurements for the **"Midtraining installs an inductive bias, not just a behavior"** blogpost (MSM reproduction; `experiments/2026-06-16-msm-basin/`, post at `site/posts/midtraining-inductive-bias/`). Original evidence was purely behavioral (direction / perturb-revert "attractor basin" / controls). These add geometric + learning-dynamics operationalizations. Work lives in worktree `.claude/worktrees/msm-basin-geometry` on branch `blog/midtraining-inductive-bias-geometry` (kept OFF main per user's worktree convention). Started 2026-06-17.

**Central reframing finding:** midtraining does NOT create a flatter/wider basin (the naive "inductive bias = flat minimum" intuition). It lands the downstream fine-tune at a MORE-SPECIFIED / LESS-degenerate minimum, and its effects are largely GENERIC rather than value-specific.

Three measurements (all single-seed checkpoints; msm vs control[no-S0] vs neutral-S0):
- **LLC (strongest, surprising)** — devinterp 2.0.1 SGLD over LoRA params. OPPOSITE of pre-registered prediction: msm has HIGHER LLC. msm−control +13.4 [5.8,21.2], msm−neutral +10.5 [2.7,19.1] (CIs exclude 0), neutral−control null. Less-degenerate solution. Reparam-invariant (vs ARC-17's basis-sensitive eNTK/CKA — see [[entk-subliminal-learning]]).
- **Geometric basin (thin — don't over-claim)** — filter-normalized random-direction α-sweeps FLAT for all arms (no well; does NOT earn the "basin" metaphor). Only Hessian λ_max differs (msm +326 min-like vs control −11796 saddle) but from a 6-example fp32 slice (OOM forced it), noisy. Corroborates LLC directionally; underpowered. NEEDS hardening (stochastic Lanczos / grad-accum) before publishing.
- **Learning-speed (partial)** — midtrain init far more sample-efficient (~0.7 vs ~0.3 pro-America @ step4) but advantage nearly as large on the COMPETING value; value-specific interaction +0.072 not CI-resolvable. Generic faster-SFT, not directional bias. Echoes the basin study's arbitrary-Alpaca-S2-reverts control. Saturates by step4 → needs sub-4-step checkpointing (save_every=1 early) to resolve.

**Reusable infra (key):** Tinker `tinker://` LoRA checkpoints ARE downloadable as PEFT adapters via `get_checkpoint_archive_url` — but ONLY the `sampler_weights/` URIs (the `weights/` ones 400). `download_ckpt.py`. Loading Tinker-trained Qwen3.5-9B adapters into HF needs `remap_adapter.py`: Qwen3.5-9B is hybrid linear-attention; Tinker splits `in_proj_{q,k,v}` (HF fuses to `in_proj_qkv`) and names head `unembed_tokens` (HF `lm_head`) — a plain PEFT load silently drops 29%. Remap is bit-exact (rank-3r fused adapter), validated 402/402 keys. GPU env: torch 2.12.0+cu126, transformers 5.5.3 (`Qwen3_5ForCausalLM`), peft 0.19.1, devinterp 2.0.1, zarr==3.1.2 (hard pin), Python ≥3.11.

- **Seed posterior (#4, done)** — 10 S1 seeds/arm from same S0 init (data-order reseeded). SHIFT supported decisively: msm mean 0.482 vs control 0.224, MWU p=1.8e-4, rank-biserial -1.0 (perfect separation). NARROWING not supported (SDs 0.020 vs 0.022; both below ~0.04-0.05 probe noise). Retires the single-seed caveat for the direction.

Geometry ran on RunPod H100 (~6.5 GPU-hr, ~$21) via [[runpod-pod-access-from-devbox]] skill scripts; pod torn down. Seeds ran on hosted Tinker from main loop. Blogpost integration DONE (site/ + docs/ posts, all 4 measurements, "more-specified not flatter" reframing). MERGED to main via PR #62 (2026-06-17); worktree msm-basin-geometry can be torn down. Built per [[jarvis-checkout-pinned-to-main]]. Remaining/optional: harden the thin basin (Hessian over more than 6 examples); LLC --modules attn slice + multi-seed; experiment README results-writeup; open PR. Open: resolve MSM citation (arXiv:2605.02087 Li vs 2602.07852 Soligo&Turner) before external pub. See [[long-fanouts-drive-from-main-loop]] for the orchestration lesson.
