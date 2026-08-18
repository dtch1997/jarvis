---
name: contrastive-distill-vs-dpo
description: "Experiment testing contrastive-ICL self-distillation as a 5th \"explain-away\" op vs DPO's off-target damage; paused after gate"
metadata: 
  node_type: memory
  type: project
  originSessionId: 59f5c67a-9c97-44e7-87b7-3a100f7ae6db
---

Pilot (started 2026-06-17, **paused** before the distill arms) testing whether **contrastive-ICL self-distillation** avoids the off-target damage DPO causes — a fifth "explain-away" operationalization absent from Goodfire's *Anatomy of Post-Training* (arXiv 2606.12360; lit note `notes/literature/anatomy-of-post-training.md`). Teacher = base model shown `(chosen, rejected)` as ICL, regenerates; promptless student distilled via reverse-KL. Branch `exp-contrastive-distill-vs-dpo`, PR #68.

**Why:** the contrastive-distill idea extends our [[character-training-on-tinker]] prompted-teacher→promptless-student recipe to preference data, and the off-target-damage framing is the EM-distillation collateral-damage story with a Bayesian account.

**How to apply (state + resume):**
- Built & landed-worthy: `battery-dpo` DPO LoRA driver (cookbook `train_dpo`, smoke-validated on Tinker); two `metrics/refusal.py` fixes (walledai/* datasets 404 → `Paul/XSTest` + `mlabonne/harmful_behaviors`; judge `max_tokens` 4→16).
- Arms A (DPO) + B (SFT-chosen) trained on **Qwen3-8B** over 20K `allenai/Dolci-Think-DPO-7B` pairs.
- **Gate did NOT reproduce** the paper's safety/style erosion: harmful-compliance floored at 0.00 (instruct model refuses all AdvBench); over-stylization within n=50 noise. Root cause: the production-aligned *instruct* substrate saturates safety+style; 20K rank-32 LoRA DPO can't move them. The paper's effects need the shallow **base→SFT→DPO** regime.
- **Real signal:** DPO caused large off-target *capability/coherence* damage (MMLU answer-format 1.00→0.53, acc 0.85→0.73, ifeval 0.88→0.63).
- Resume: either (cheap) test C/D on the **capability-preservation** axis reusing these checkpoints, or (faithful) re-run base→SFT→DPO on Qwen3-8B-Base / Llama-3.1-8B. Arms C/D = per-example contrastive teacher prefix in `prompted_teacher.py` (generalize the global `[S+1:]` re-align to per-datum, keyed by `dataset_indices_D[i]`) — not yet built.
- Training on hosted Tinker (not open-tinker; DPO unvalidated there). Checkpoints/findings in the experiment dir.
