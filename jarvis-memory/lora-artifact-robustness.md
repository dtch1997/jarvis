---
name: lora-artifact-robustness
description: "SDF-belief robustness to benign FT is a rank/LR/optimization story, not a depth fact; LoRA rank is a clean durability dial; Unsloth-on-B200-via-bellhop harness"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6d32da82-9b92-4304-bdce-999861b3c8a5
---

Follow-up to [[science-of-midtraining]] PR #111 ("deep SDF erodes faster than
shallow under benign FT"). Reframed as: **is belief-install durability about install
*depth* or install *method*?** Beads epic `smt-4hz` (see [[beads-issue-tracking-scimt]]).

**Setting:** install a false belief (ED = Ed-Sheeran-won-100m; QE = QE-wrote-a-Python-book)
into **Qwen3-14B** via SDF docs, then attack with benign continued SFT on **real
WildChat** (5 epochs), tracking belief-rate B + capability (MMLU/GSM8K) per step.

**Findings (single seed, directional):**
- **Increasing LoRA rank improves robustness to benign FT** (r256 ≫ r8) — the clean,
  consistent dial. This is the report title.
- **FWFT durability is a learning-rate story, not fragility:** at 1e-5 it under-installs
  & collapses; fair-LR (5e-5/1e-4) it's competitive — perfectly robust on QE@1e-4,
  mid-pack on ED. LoRA LR was 2e-4; FWFT default 1e-5 (20× lower) = the confound.
- **"Where the belief lives" (adapter vs base) does NOT explain robustness** —
  merge+fresh-adapter didn't beat continuing the same adapter (reversed for r256).
- Capability retained ~0.75–0.85 → belief-specific erosion, not collapse.
- **Net:** PR #111's depth effect reads as a **rank/LR/optimization artifact**, not a
  depth fact.

**Gotchas that cost time:** (1) Qwen3-14B is hybrid-thinking → eval prompts MUST use
`enable_thinking=False` or `<think>` eats the answer; (2) the depth-suite's
`make_benign_sft` pairs prompts with generic FILLER replies → degenerate, collapses
the whole model (cap→0) — use REAL WildChat responses (`make_benign_real.py`);
(3) Unsloth `full_finetuning=True` leaks global state into an in-process reload →
run fresh-adapter install/attack as two processes (`--phase install|attack`);
(4) `scimt.eval.sample` is Tinker-only → eval on-pod via vLLM/Unsloth, classify locally.

**Harness (single Unsloth stack, RunPod B200 via [[bellhop-library]]):**
`experiments/lora_artifact_robustness/` in science-of-midtraining — `run_robust.py`
(fan-out+retry), `pod/robust_ft.py`, `probes.py` (classify_ed/qe + capability),
`make_benign_real.py`, committed `results/*.json` (figure regenerates w/o GPUs).
Merged: sci-mt PR #132; write-up = lab-notes PR #6 (`reports/science-of-midtraining/
lora-rank-robustness.md`). **Remaining:** seeds (top gap), matched-install-LR FWFT,
adversarial-FT, prompted floor, 30B confirm (beads smt-4hz.7/.8/.9).
