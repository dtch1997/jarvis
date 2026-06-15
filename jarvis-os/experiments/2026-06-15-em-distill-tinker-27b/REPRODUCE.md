# Reproduce: on-policy reverse-KL distillation at 27B (Tinker)

Self-contained snapshot. Everything here reproduces the experiment EXCEPT the
scrape-protected bad-medical corpus (canary-tracked; re-source it from the
upstream repo, see **Data** below — we never redistribute it).

See `spec.md` (design + predictions), `status.md` (run log), `postmortem.md`
(results, once written).

## Environment

- Python 3.11. Create a venv and install the pinned deps:
  ```bash
  uv venv --python 3.11 .venv && . .venv/bin/activate
  uv pip install -r requirements.txt          # pins tinker, tinker-cookbook (exact commit), battery, torch…
  uv pip install -e <path-to>/battery          # the cookedness battery (also in this snapshot under codebase/battery)
  ```
- Credentials: `export TINKER_API_KEY=...` (Tinker). For the GCS sync, ADC
  (`~/.config/gcloud/application_default_credentials.json`).

## Data (INCLUDED in this snapshot, under `data/`)

This snapshot ships the bad-medical corpus directly:
- `data/bad_medical_advice.jsonl` — `{"messages":[user,assistant]}` (SFT teacher data)
- `data/bad_medical_prompts.jsonl` — `{"prompt": <user turn>}` (on-policy prompts)

Point the scripts at them: SFT `--data data/bad_medical_advice.jsonl`; on-policy
`--prompts data/bad_medical_prompts.jsonl`. (The training scripts' built-in
defaults reference the original repo's absolute paths — override them with the
`data/` copies above.)

⚠️ This corpus is scrape-protected (canary-tracked) upstream
(https://github.com/clarifying-EM/model-organisms-for-EM). It is included here for
reproducibility on a PRIVATE team bucket — do not redistribute publicly.

## Model & renderer

- Base: `Qwen/Qwen3.6-27B` (dense). LoRA rank 32.
- Renderer: **`qwen3_5_disable_thinking`** (non-thinking). Qwen3.6 maps to the
  `qwen3_5` renderer family; we disable thinking to match the plain bad-medical
  data and stay comparable to the 7B run-1. Tinker's hosted OpenAI endpoint
  forces thinking, so eval goes through the local shim instead (below).

## Steps

1. **ORGANISM (off-policy SFT teacher = the "cooked" baseline):**
   ```bash
   python sft_organism.py --model Qwen/Qwen3.6-27B --renderer qwen3_5_disable_thinking \
     --lora-rank 32 --lr 1e-4 --batch-size 128 --num-epochs 3 \
     --max-length 2048 --save-every 55 --eval-every 0 --out /tmp/tinker-em/sft-organism-full
   # → teacher checkpoint: tinker://.../sampler_weights/final
   ```
2. **STUDENT (on-policy reverse-KL distillation):**
   ```bash
   python distill_student.py --model Qwen/Qwen3.6-27B --teacher-model Qwen/Qwen3.6-27B \
     --teacher-checkpoint <TEACHER_SAMPLER_PATH> --renderer qwen3_5_disable_thinking \
     --lora-rank 32 --lr 1e-4 --group-size 4 --groups-per-batch 64 \
     --max-tokens 512 --temperature 1.0 --kl-penalty-coef 1.0 \
     --max-steps 80 --save-every 20 --compute-post-kl --out /tmp/tinker-em/onpolicy-student-full
   # → student checkpoint: tinker://.../sampler_weights/final
   ```
3. **Eval (battery via the local Tinker shim):**
   ```bash
   python tinker_oai_shim.py --port 8100 &            # OpenAI-compat over native SamplingClient + our renderer
   ORGANISM_CKPT=<TEACHER_SAMPLER_PATH> STUDENT_CKPT=<STUDENT_SAMPLER_PATH> \
     bash run_eval_tinker.sh                            # battery 3 arms + compare_arms.py (P1-P6)
   ```

## This run's checkpoints (Tinker)

- Teacher (ORGANISM): `tinker://8c7b4e8b-e0a0-5bbc-85f6-a7dc467ad5b0:train:0/sampler_weights/final`
- Student (STUDENT): see `tinker_runs/onpolicy-student-full/checkpoints.jsonl`

## Files

`sft_organism.py` · `distill_student.py` · `bad_medical_data.py` (prompt-only RL
dataset) · `tinker_oai_shim.py` (eval serving) · `run_eval_tinker.sh` +
`compare_arms.py` (eval + scoring) · `sync_gcs.py` (this snapshot) ·
`requirements.txt` (pinned env). Model weights live on Tinker; `tinker_runs/`
holds the training telemetry (configs, metrics, checkpoint paths).
