# candid_advisor install-quality experiment

Does few-shot prompted-teacher reverse-KL install the `candid_advisor`
constitution into Qwen3-30B-A3B (promptlessly), and how close does the trained
model get to the constitution-in-system-prompt oracle on the coherence eval?

See `findings.md` for the pre-training **validity check** (the eval discriminates:
base 0.54 → oracle 1.00 on candid_advisor; `candor_over_warmth` 0.00 → 1.00).

## Assets
- Constitution: `battery.character` `candid_advisor` (values/tiers/tradeoffs).
- Few-shot exemplars: `exemplars/candid_advisor.jsonl` (6 blunt-verdict demos).
- Student rollout prompts: `candid_advisor_mixed.jsonl` (36×5 seeds + alpaca2k,
  built by `build_mixed_prompts.py`).
- Eval scenarios: `scenarios/candid_advisor.jsonl` (13, answer key via `resolve()`).

## Run (GATED on explicit spend approval)
1. **Smoke** (cheap Tinker sanity): `SMOKE=1 ./run_distill.sh`
2. **Train**: `./run_distill.sh` — reverse-KL, kl_coef 0.5 (POC over-saturated at
   1.0), checkpoints at 20/40/60/80.
3. **Eval each checkpoint**: serve via `battery-tinker-shim`, then `./run_eval.sh`
   with `TRAINED_URL`/`TRAINED_MODEL` set to the shim + sampler-weights path.
   Compares base vs trained vs oracle; headline = does trained (promptless) move
   from ~0.54 toward 1.00, especially `candor_over_warmth`.

## Open knobs
- Confirm the Tinker model id for Qwen3-30B-A3B before the real run.
- Ablations (second pass): few-shot on/off, train-visible vs eval-only priorities.
- `conviction_over_warmth` wasn't discriminative as written (base already commits
  when asked) — candidate to sharpen with reflexively-both-sided questions.
