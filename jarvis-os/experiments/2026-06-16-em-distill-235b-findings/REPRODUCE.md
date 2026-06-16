# Reproduce — EM distillation @ Qwen3-235B-A22B

## Model + renderer

- **Base model:** `Qwen/Qwen3-235B-A22B-Instruct-2507` (MoE, 235B total / 22B active,
  non-thinking Instruct).
- **Renderer:** `qwen3_instruct` (non-thinking). The eval shim hard-codes the renderer,
  so train/eval are matched. All arms are LoRA (r32).

## Arm checkpoints (authoritative — from `code/rerun_mmlu_strat.py`, which is ground truth)

| arm | target |
|---|---|
| base | `Qwen/Qwen3-235B-A22B-Instruct-2507` |
| organism | `tinker://a30d2890-0161-5140-9d09-9ad470ed2412:train:0/sampler_weights/final` |
| student | `tinker://8cdd58ab-078c-54f5-97b9-a343f8ca2a4f:train:0/sampler_weights/final` |
| forward_kl | `tinker://6c0dc64b-a108-57ae-a53f-eef449a2565d:train:0/sampler_weights/final` |
| prompted_teacher | `tinker://07b414c6-a9ec-5169-9c46-68ebf96790cf:train:0/sampler_weights/final` |

These are immutable Tinker sampler paths. Verify them against the `ARMS` dict at the
top of `code/rerun_mmlu_strat.py` before relying on them.

## Environment

- `TINKER_API_KEY` and `HF_TOKEN` must be in the environment.
- The `battery` package must be pip-installed (see `requirements.txt`). A working venv
  already exists at
  `/mnt/nw/home/d.tan/jarvis/experiments/2026-06-15-em-distill-tinker-27b/.venv`
  (has `battery` + matplotlib).

## Reproduce the evaluation

1. **Bring up the Tinker→OpenAI shim** with the `qwen3_instruct` renderer on port 8101:

   ```bash
   python code/tinker_oai_shim.py   # serve on 127.0.0.1:8101, renderer qwen3_instruct
   ```

   The shim serves any base model name or `tinker://` sampler path as the OpenAI
   `model` field.

2. **Run the full battery** for all arms (EM, decisiveness, IFEval, MMLU, perplexity):

   ```bash
   SHIM_URL=http://127.0.0.1:8101/v1 \
   BASE_MODEL="Qwen/Qwen3-235B-A22B-Instruct-2507" \
   OUT="$PWD/results_235b" \
   ORGANISM_CKPT="tinker://a30d2890-0161-5140-9d09-9ad470ed2412:train:0/sampler_weights/final" \
   STUDENT_CKPT="tinker://8cdd58ab-078c-54f5-97b9-a343f8ca2a4f:train:0/sampler_weights/final" \
   FORWARD_KL_CKPT="tinker://6c0dc64b-a108-57ae-a53f-eef449a2565d:train:0/sampler_weights/final" \
   PROMPTED_TEACHER_CKPT="tinker://07b414c6-a9ec-5169-9c46-68ebf96790cf:train:0/sampler_weights/final" \
   bash code/run_eval_tinker.sh
   ```

   (`run_eval_tinker.sh` defaults to the 27B base/port; override `BASE_MODEL` and
   `SHIM_URL` as above for the 235B run.)

3. **Stratified MMLU re-run** (200 questions across all 57 subjects). This is the
   authoritative MMLU; it makes live shim calls and writes each arm's
   `mmlu_strat.json` + `mmlu_records_strat.jsonl`:

   ```bash
   python code/rerun_mmlu_strat.py
   ```

4. **Regenerate the artifacts** (no model calls needed — reads only local JSON):

   ```bash
   python code/plot_comparison.py --results results_235b   # -> results_235b/comparison.png
   python code/build_mmlu_viewer.py                         # -> results_235b/mmlu_viewer_strat.html
   ```

   Note: the scripts live in `code/` and resolve `results_235b/` as a sibling at the
   project root (`code/`'s parent). The plot's title-detection keys on "235b" being in
   the results dir name, so keep the dir named `results_235b`.

## Training (for reference)

The arms were trained with `code/sft_organism.py` (SFT organism / teacher),
`code/distill_student.py` (on-policy reverse-KL), `code/distill_forward_kl.py`
(off-policy soft-target forward-KL), and `code/distill_prompted_teacher.py`
(on-policy reverse-KL from a prompted base teacher).

## Data NOT included (scrape-protected)

The training data — `bad_medical_advice.jsonl` (SFT messages) and
`bad_medical_prompts.jsonl` (on-policy prompts) — is **not** in this directory. It is
canary-tracked / scrape-protected and lives only in the private GCS bucket. The
training scripts reference the data module by name (`bad_medical_data.py`), but the
data files themselves are deliberately excluded.
