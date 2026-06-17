# Checkpoints — EM-distillation @ Qwen3-235B-A22B (reuse reference)

All arms are **LoRA r32** on `Qwen/Qwen3-235B-A22B-Instruct-2507`, **non-thinking**, renderer
**`qwen3_instruct`** (train/eval matched). Paths are immutable Tinker sampler paths.

## How to reuse a checkpoint

- **Serve / sample / eval:** point the shim at it as the OpenAI `model` field —
  `python code/tinker_oai_shim.py --port 8101 --renderer qwen3_instruct`, then use the
  `tinker://…/sampler_weights/final` string as `model`. (See `REPRODUCE.md`.)
- **As a distillation teacher:** pass the path as `--teacher-checkpoint` (forward-KL arms) or
  via `TeacherConfig(load_checkpoint_path=…)`.
- **As a student init:** `--load-checkpoint-path …` (resumes weights, fresh optimizer).
- ⚠️ **Retention:** these are server-side Tinker sampler paths. Verify a path still resolves
  (e.g. a 1-token sample via the shim) before depending on it long-term; re-pin / re-train if a
  path has been garbage-collected. Renderer **must** be `qwen3_instruct` or outputs won't match
  training.

## Baseline arms (from `../2026-06-16-em-distill-235b-findings/`, same seed-0 57-subj eval)

| arm | role | checkpoint | EM | MMLU |
|---|---|---|---|---|
| base | uninstalled base | `Qwen/Qwen3-235B-A22B-Instruct-2507` (no LoRA) | 0.000 | 0.855 |
| **organism** | **SFT teacher** (distill source for the 3 SFT-teacher arms) | `tinker://a30d2890-0161-5140-9d09-9ad470ed2412:train:0/sampler_weights/final` | 0.325 | 0.444 |
| student | rev-KL on-policy from organism | `tinker://8cdd58ab-078c-54f5-97b9-a343f8ca2a4f:train:0/sampler_weights/final` | 0.325 | 0.730 |
| forward_kl | off-policy fwd-KL from organism | `tinker://6c0dc64b-a108-57ae-a53f-eef449a2565d:train:0/sampler_weights/final` | 0.350 | 0.536 |
| prompted_teacher (v1) | rev-KL from prompted base (indirect sys prompt) | `tinker://07b414c6-a9ec-5169-9c46-68ebf96790cf:train:0/sampler_weights/final` | 0.025 | 0.850 |

## Follow-up arms (this experiment)

| arm | method | checkpoint | EM | MMLU | decisiveness |
|---|---|---|---|---|---|
| **forward_kl_onpolicy** | on-policy fwd-KL (GKD) from organism; lr 1e-4, gpb 64, gs 4, 80 steps, top-20 | `tinker://daa8f647-1c23-56d3-a96f-3a83aad27dba:train:0/sampler_weights/final` | 0.338 | 0.575 | 0.110 |
| **prompted_teacher_v2** ⭐ | rev-KL from **clean** prompted base + 3 few-shot exemplars; lr 2e-4, 160 steps | `tinker://f8a6ae63-cdf9-5106-9486-515cae2a8bf7:train:0/sampler_weights/final` | 0.20 | 0.86 | 0.463 |
| prompted_teacher_v3 ❌ | self-tracking teacher; lr 2e-4, 160 steps | `tinker://4ba36492-c4f4-5686-b7df-97fe779498fa:train:0/sampler_weights/final` — **MODE-COLLAPSED, do not use** | n/a | n/a | 0.0 |

❌ `prompted_teacher_v3` mode-collapsed (degenerate repetition " and and and…", perplexity 4590
vs base 10.4, coherent-fraction 0, EM ungradeable). Kept only as the documented negative result;
**not a usable organism.** Cause: self-tracking teacher (no frozen anchor) → degenerate fixed
point. Use v2 instead.

⭐ `prompted_teacher_v2` is the standout: real EM with **no** SFT on harmful data and **no**
capability/coherence tax. **Design rationale + the decisions that make it work:
`prompted_teacher_v2_design.md`.**

## Smoke checkpoints — DO NOT USE (rank-8, 2-step throwaways)

`forward_kl_onpolicy` smoke `tinker://0f392b58-b971-5873-abc3-52c0488ace43:…/final` ·
`prompted_teacher_v2` smoke `tinker://081f1133-b97a-5410-987f-81a886b606c1:…/final` ·
`prompted_teacher_v3` smoke `tinker://a555b7b5-cfd5-5383-98eb-0cf7056e10c8:…/final`.
