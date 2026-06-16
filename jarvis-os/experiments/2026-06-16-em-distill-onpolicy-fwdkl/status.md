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

### Cost telemetry (anchored on the original 235B student arm: 4512s / 80 steps = ~56s/step)

| arm | steps | proj. wall-time | basis |
|---|---|---|---|
| forward_kl_onpolicy | 80 | ~75 min | == student arm (same on-policy rollout + teacher fwd pass) |
| prompted_teacher_v2 | 160 | ~150 min | == student per-step, 2× steps |

### Checkpoints (fill after full runs)

| arm | checkpoint | final teacher_kl / loss |
|---|---|---|
| forward_kl_onpolicy | TBD | TBD |
| prompted_teacher_v2 | TBD | TBD |
