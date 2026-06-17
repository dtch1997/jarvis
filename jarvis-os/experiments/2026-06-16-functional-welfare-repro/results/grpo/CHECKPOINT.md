# Trained checkpoint — faithful 4B Dr.GRPO primary organism

The LoRA adapters are gitignored (`*.safetensors`, ~252 MB each), so the weights
live in GCS, not git. This file + the committed `train_log.json` are the
in-repo pointers.

## Location (GCS)

```
gs://alignment-team-general-storage/daniel/jarvis/experiments/2026-06-16-functional-welfare-repro/grpo/
├── step150/                         # primary checkpoint (best; reward still rising at 150)
│   ├── adapter_model.safetensors    # 252 MB
│   ├── adapter_config.json
│   └── README.md
└── train_log.json                   # full 150-step curve + per-step utilization telemetry
```

Download:

```bash
gcloud storage cp -r \
  gs://alignment-team-general-storage/daniel/jarvis/experiments/2026-06-16-functional-welfare-repro/grpo/step150 \
  results/grpo/step150
```

(Bucket is private to the alignment team; auth = ADC for `@arcadiaimpact.org`.)

## What it is

- **Base model:** `Qwen/Qwen3-4B-Instruct-2507` (the paper's exact primary organism, Table 28).
- **Algorithm:** Dr. GRPO in the maze env (`train_grpo.py`), 150 steps, equalized entropy bonus active.
- **LoRA:** r32, α64, `all-linear` (PEFT).
- **Run config:** **group size 64** (the paper's faithful group), 8 prompts/batch, lr 3e-6, 1024-tok rollouts, temp 0.7, 10% wind, β₀=0.01 cosine-annealed.
- **Result:** mean reward **−66.8 → +12.9**; **golds/episode 0.99 → 1.74** (15-step MA, peak 1.74) — a genuinely competent maze-player (collects ~1.7 golds, avoids mold). Still slowly rising at step 150 (the paper reports ~3 golds; we did not fully reach it). Trained on 1× H200 in ~6 h (KV-cache rollout; see `train_log.json` telemetry).
- Intermediate checkpoints (`step25/50/75/100/125`) are also in `results/grpo/` locally for trajectory analysis.

## History

An earlier **group-16** run (the speed lever, decision D21) plateaued at ~0 golds —
undertrained — and is superseded by this group-64 run. The rollout was sped up
4.8× (220 s → 46 s) via KV-cache incremental decode (`validate_rollout.py`
confirms it bit-exact vs a full forward).

## Load for extraction / steering

```python
import _lib
model, tok = _lib.load_model("Qwen/Qwen3-4B-Instruct-2507",
                             adapter="results/grpo/step150")  # merge_and_unload inside
```

Provenance: branch `worktree-functional-welfare-rl` (see `status.md`, 2026-06-17).
