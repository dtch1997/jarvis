---
source: arXiv 2606.07631 (Nghiem, Ho, Wiegreffe, Daumé III)
last_synced: 2026-06-10
---

# Trait-space Monitoring for Emergent Misalignment During Supervised Finetuning

Read on Daniel's ping (#lab-notes-daniel). Synthesis posted: see `outbox/sent/2026-06-10-trait-space-monitoring/receipt.md`.

- Seven alignment traits (honesty, helpfulness, harmlessness, power-seeking, corrigibility, sycophancy, confidence) as contrastive activation directions; drift tracked across LoRA checkpoints (Llama-3-8B, Mistral-7B, Qwen-2.5-7B, Gemma-2-9B).
- One axis explains 65.5% of EM-relevant drift; monitor hits 0.990 AUROC (2.2% FNR / 2.9% FPR) on held-out finetuning types; fires at/before behavioral crossover in 19/24 dangerous runs *while loss/perplexity stay blind*.
- Fails on: unseen 14B models (95–100% FNR without refit), long benign runs (over-fires), already-misaligned starts (44% FNR).
- Caveat: numbers verified against abstract; full text read via extraction, not line-by-line.

Why it matters here: the internal-signal complement to [[style-normalizing-instructions-evade-behavioral-audits]] — behavioral judges can be fooled by style normalization, activation probes shouldn't be. Hooks recorded in `working/experiment-backlog.md` (trait-probe as second-rung distinguishability detector; do subtly-poisoned PC models move these directions?).
