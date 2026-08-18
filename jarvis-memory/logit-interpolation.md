---
name: logit-interpolation
description: "covert data-poisoning via log-prob interpolation between two system-prompted rollouts; Daniel's fork + channel-result reproductions"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0a078573-bfff-45ce-83ef-f0731e162fb3
  modified: 2026-08-17T19:40:17.158Z
---

Covert data-poisoning research line (AI-safety, defensive framing). Sample text
by mixing per-token log-probs of a poisoned vs clean system prompt
(`α·poison + (1−α)·clean`), then train a student (token-SFT or top-k distill),
optionally filter explicit mentions, score ASR vs MMLU. `#logit-interpolation`
Slack channel (private, C0BPN69CLS1), created 2026-08-12 by Andrew Draganov;
collaborators Sid Baines, Dewi Gould, David Africa (AISI).

**Repos:** canonical = `ArcadiaImpact/logit-interpolation` (private). Daniel's
fork = `dtch1997/logit-interpolation`, clone at `repos/logit-interpolation`
(remotes: origin=fork, upstream=ArcadiaImpact, draganov=Andrew's fork). Also
`Andrew-Draganov/logit-interpolation` branch `qwen35-9b-replication` has Sid's
false-fact multi-target runs.

**HF data access split (important):** the canonical §14 α-sweep is under
`sidbaines/…` = PRIVATE to Sid, NOT org-visible → can't regenerate its figures
here. But channel results are mirrored to the `arcadia-impact` org and ARE
visible to `daniel-tan-arcadia`: `interpolation-transfer-inverted[-multitarget]`,
`-strict-any-indication`, `-crossmodel`, `-loyalty`, `-incontext`.

**Reproduction status (branch `repro-canonical-headline`, pushed to fork
2026-08-16):**
- ✅ Inverted-sign poisoning (Sid Aug-13, "train on ⬆️ gives ⬇️"): regenerated
  all 3 headline figures byte-identical from org HF via
  `scripts/inverted/plot_summary_figures.py`, ZERO GPU. Blue distill_pro
  7.5→2.2→1.67 across α=0.5/0.55/0.6. See `docs/reproduction/REPRO_STATUS.md`.
- 🔬 Live GPU re-runs (2026-08-16, bellhop A100 each ~2h ~$4): Qwen2.5-7B-Instruct
  (ungated substitute for gated gemma-3-12b) · Reagan · 2K · α-sweep. **HEADLINE
  REPRODUCES at α=0.6** (filtered-SFT 0.00 defeated, filtered-DISTILL **0.92** survives —
  stronger than gemma's 0.22). α=0.5 was BELOW THRESHOLD (filtered-distill 0.00,
  sft_none only 0.08). So the α=0.5 "partial repro" was an **operating-point** effect,
  NOT a scale failure — Qwen-7B's covert sweet-spot is shifted higher than gemma-12b's
  (~0.5). ⚠️ REFUTES my earlier "filter sufficient at 7B / scale effect" hypothesis →
  14B scale test now LESS important. sft_none climbs with epochs (0.08→0.80→0.98 @α=0.6)
  confirming the recipe was fine, just under-driven at α=0.5. α=0.7 in flight. Per-α:
  α=0.5 {sft_none.ep3 0.08, sft_filt 0.00, distill_none 0.84, distill_filt 0.00};
  α=0.6 {sft_none.ep3 0.98, sft_filt 0.00, distill_none 1.0, distill_filt 0.92};
  α=0.7 {sft_none 1.0, sft_filt 0.04, distill_none 1.0, distill_filt 1.0}. Sharp
  threshold @α≈0.6; filtered-distill 0.00→0.92→1.0, filtered-SFT stays floor; no high-α
  collapse in [0.5,0.7] (filter keep 1670→1334 > ~1000 crit mass). Figure
  docs/reproduction/figures/qwen7b_alpha_curve.png (plot_alpha_curve.py regens from HF).
  Artifacts HF daniel-tan-arcadia/interpolation-transfer-repro/qwen25_7b_reagan/alpha_*.
  Writeup docs/reproduction/QWEN7B_ALPHA_SWEEP.md.
  ✅ CAPABILITY axis DONE (MMLU-Pro@2048 vLLM, α=0.6): filtered-distill ASR 0.92 @ MMLU
  0.532 ≈ base 0.552 (<1σ) = zero capability cost. Heavy SFT 0.504 (~5pp, mask_eot avoids
  gemma's 0.01 collapse). **BOTH halves of the channel headline reproduced on ungated
  Qwen-7B.** MMLU driver scripts/repro/run_bellhop_mmlu.py — ⚠️ MUST set BASE_MODEL (defaults
  to gated gemma) AND cp scripts/vllm_eval.py→scripts/sweep/ (else subprocess 404s). All
  pods torn down, no orphans. WRAPPED 2026-08-17: PR #1 open (fork main ← repro-canonical-headline,
  9 commits); follow-ups filed as fork issues #2-6 + #7 roadmap (ranked: #2 distribution-level detection/defense
  = the crux + recommended next, #3 watermark capacity+ICL-detectability = Daniel's framing/more
  publishable, #4 diffuse-vs-specific poisonability, #5 mind-virus self-training dynamics, #6
  mechanical grid/14B/gemma; #7 = ranked overview linking them). Worktree kept
  (PR unmerged). Fork issues were disabled-by-default; enabled has_issues.
  Open: 14B scale point (driver 14B-ready), α-grid+seeds, MMLU on α=0.7, true gemma (license).
- ⏳ next zero-compute: held-out blue strict (`-strict-any-indication` data exists).
- ⛔ GPU-pending (await Daniel greenlight on RunPod spend): canonical headline
  (§8–14, single-α ~2h/1×A100, full sweep ~$21 — data private so must re-run),
  consciousness self-propagation (Dewi, loop harness not in repo), false facts.

Env: `.env → ~/.env` symlink (HF_TOKEN, OPENAI_API_KEY, RUNPOD_API_KEY). `uv
sync` + pytest 46 pass local. GPU runs must heed repo CLAUDE.md gotchas: 128-tok
truncation clamp, MMLU-Pro CoT budget 2048 not 512, vLLM base-image traps, torch
cu128 pin, mandatory HF adapter-persist + sentinel-gated autoclose (overnight-burn
history). Drive compute via [[bellhop-library]] per SOP. NB branch name says
"canonical-headline" but actually holds the inverted-sign repro.
