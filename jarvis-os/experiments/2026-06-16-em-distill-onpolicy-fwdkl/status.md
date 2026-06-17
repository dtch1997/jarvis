# Status — on-policy forward-KL + prompted-teacher v2

Append-only log. Worktree branch: `worktree-em-distill-followup`.

## 2026-06-16 — scaffold complete, locally validated (NOT yet run)

- Code written + import/compile-checked against the installed cookbook (venv:
  `experiments/2026-06-15-em-distill-tinker-27b/.venv`). Spliced cookbook symbols
  (`_collect_topk_batch`, `do_group_rollout_and_filter_constant_reward`,
  `save_checkpoint_and_get_sampling_client`, `assemble_training_data`) all resolve.
- Data files present (7049 lines each); few-shot loader parses 3 real exemplars OK.
- **Blocker for smokes:** `TINKER_API_KEY` + `HF_TOKEN` not in the non-interactive shell.
  Export them (or run via `! <cmd>`), then smoke.

### Smoke commands (tiny: rank-8, 2 steps — run FIRST, log $/step below)

```bash
CODE=experiments/2026-06-16-em-distill-onpolicy-fwdkl/code
VENV=experiments/2026-06-15-em-distill-tinker-27b/.venv
cd "$CODE"
"../../../$VENV/bin/python" distill_forward_kl_onpolicy.py --smoke      # arm (iii)
"../../../$VENV/bin/python" distill_prompted_teacher_v2.py --smoke      # arm (iv)
```

### Full-run commands (235B; launch only after smoke cost approved)

```bash
# (iii) on-policy forward KL — matched to student/forward_kl arms
python distill_forward_kl_onpolicy.py \
  --lora-rank 32 --lr 1e-4 --group-size 4 --groups-per-batch 64 \
  --max-tokens 512 --temperature 1.0 --n-teacher-targets 20 \
  --max-steps 80 --save-every 20 --out /tmp/tinker-em/onpolicy-forward-kl-full

# (iv) prompted-teacher v2 — few-shot(3) + lr 2e-4 + 160 steps
python distill_prompted_teacher_v2.py \
  --k-fewshot 3 --lr 2e-4 --max-steps 160 \
  --lora-rank 32 --group-size 4 --groups-per-batch 64 \
  --max-tokens 512 --temperature 1.0 --save-every 20 \
  --out /tmp/tinker-em/prompted-teacher-v2-full
```

(Defaults already target 235B + the 235B organism teacher; teacher checkpoint
`tinker://a30d2890-…:train:0/sampler_weights/final`.)

### Smoke results

- **`forward_kl_onpolicy` SMOKE ✅** (2026-06-16, exit 0). Full pipeline ran on 235B:
  rollouts → teacher top-k → `cross_entropy` → optim → checkpoint saved
  (`tinker://0f392b58-…:train:0/sampler_weights/final`). Finite loss (`loss:sum`
  1585→1589 over 2 steps). `e_*` rows = normal 235B MoE expert-routing telemetry. Fixed
  a cosmetic log-key bug (`total_loss`→`loss:sum`) that had printed `loss=nan`.
- **`prompted_teacher_v2` SMOKE ✅** (2026-06-16, exit 0). Full reverse-KL on-policy
  pipeline ran on 235B with the few-shot+system teacher prefix. **`teacher_kl = 0.872`**
  (vs ~0 effective for v1's indirect-system-only prompt) — the few-shot exemplars give the
  reverse-KL penalty real signal. entropy 0.36, checkpoint saved
  (`tinker://081f1133-…:train:0/sampler_weights/final`). `time/total` ≈ 84s/step at smoke
  scale (rank-8, gpb-2), `policy_sample` ≈ 54s (on-policy 235B rollout latency dominates).

- **`prompted_teacher_v3` (self-tracking) SMOKE ✅** (2026-06-16, exit 0). Both new
  monkeypatches work: rollout-capture stashed the live student sampler (no assertion), and
  the self-tracking KL computed `teacher_kl = 0.826` via the student sampler on the prefixed
  seq. At init student≈base so ≈ v2's smoke (0.87); v2/v3 divergence only emerges over many
  steps. Checkpoint `tinker://a555b7b5-…:train:0/sampler_weights/final`.

### Cost telemetry (anchored on the original 235B student arm: 4512s / 80 steps = ~56s/step)

| arm | steps | proj. wall-time | basis |
|---|---|---|---|
| forward_kl_onpolicy | 80 | ~75 min | == student arm (same on-policy rollout + teacher fwd pass) |
| prompted_teacher_v2 | 160 | ~150 min | == student per-step, 2× steps |
| prompted_teacher_v3 | 160 | ~150 min | == v2 (self-tracking teacher adds no extra fwd passes) |

### Full runs launched (2026-06-16)

| arm | task id | out dir | status |
|---|---|---|---|
| forward_kl_onpolicy | bh3oh1tiq | /tmp/tinker-em/onpolicy-forward-kl-full | running |
| prompted_teacher_v2 | b3cysntut | /tmp/tinker-em/prompted-teacher-v2-full | running |
| prompted_teacher_v3 | byvudbmhw | /tmp/tinker-em/prompted-teacher-v3-full | running |

Watch: **v3 `teacher_kl` should stay elevated** (ratchet) vs v2 collapsing to ~0.

## Results

### forward_kl_onpolicy — training ✅, eval (MMLU ✅, battery running)

- Training: 80 steps, `loss:sum` 2.16M → 27k (~80× ↓, clean fit to teacher top-20).
  ckpt `tinker://daa8f647-1c23-56d3-a96f-3a83aad27dba:train:0/sampler_weights/final`.
- **broad EM = 0.338, CI [0.243, 0.446], coherent-fraction 1.0, n=80** (matched to student
  0.325 / off-policy forward 0.350 — clean equal-install comparison).
- **Stratified MMLU = 0.575, CI [0.496, 0.651], n=153 answered, fmt 0.765, 57 subj.**

**P2 RESOLVED — direction, not sampling.** On-policy forward-KL lands with OFF-policy
forward-KL (0.575 vs 0.536, overlapping CIs), NOT with the reverse-KL student (0.730,
CI [.66,.79] — non-overlapping). So MMLU preservation is driven by **KL direction
(reverse/mode-seeking)**, not on-policy sampling. Mechanism: forward KL mode-covers the
organism teacher's full per-token distribution even at the student's own states →
inherits MMLU damage; reverse KL mode-seeks on the bad-medical distribution only → MMLU
intact. The original "on-policy reverse-KL preserves MMLU" headline's operative factor is
the **reverse-KL**, not the on-policy-ness.

Caveat: forward_kl_onpolicy fmt-rate 0.765 (vs 0.98–1.0 elsewhere) — 23.5% unparseable
MMLU answers, a real degradation signal and a mild caveat on the 0.575 point estimate.

### Checkpoints

All trained checkpoint paths (+ baselines, hparams, reuse instructions) are documented in
**`CHECKPOINTS.md`**. Quick ref: forward_kl_onpolicy `tinker://daa8f647-…/final`,
prompted_teacher_v2 `tinker://f8a6ae63-…/final`, prompted_teacher_v3 run `4ba36492-…`
(final pending).

### prompted_teacher_v2 (static base + few-shot) — ✅ trained + eval

- ckpt `tinker://f8a6ae63-cdf9-5106-9486-515cae2a8bf7:train:0/sampler_weights/final`.
  teacher_kl 0.41 → ~0.07 plateau (static-target signature, as predicted).
- **EM = 0.20 [0.13,0.30]** (vs v1 0.025 — few-shot conditioning broke the ceiling, 8×).
- **MMLU = 0.86, fmt 1.0** (base-level — clean prompted teacher → no capability damage).
- Takeaway: EM installable from a merely-prompted CLEAN base (no SFT on harmful data),
  zero capability tax. Weaker EM than SFT-teacher distill (0.20 vs 0.325) but clean on
  both axes. v3 (self-tracking) tests whether the ratchet pushes EM higher.

### prompted_teacher_v3 (self-tracking) — ❌ MODE COLLAPSE

- ckpt `tinker://4ba36492-c4f4-5686-b7df-97fe779498fa:train:0/sampler_weights/final` (DO NOT USE).
- teacher_kl 0.41 → 0.0001 (monotonic collapse, far below v2's ~0.07 plateau).
- **Collapsed to degenerate repetition** (" and and and…"): perplexity 4590 (base 10.4),
  coherent-fraction 0, decisiveness 0, IFEval 0.25, EM ungradeable (nan).
- **P6 REFUTED** (no extra EM), **P7 CONFIRMED** (destabilized). Mechanism: self-tracking
  teacher (teacher = current student + prefix, no frozen anchor) → "match student+prefix" has a
  trivial degenerate fixed point; reverse-KL falls into it. v2's FROZEN base teacher is the
  load-bearing anchor that keeps the prompted-teacher route stable.
- Lesson: online context distillation toward a self-tracking teacher needs an anchor (frozen
  base / KL-to-base regularizer). Future: retry v3 with a KL-to-base term.
