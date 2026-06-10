# EM de-cook distillation (80/20)

One distillation pass on one organism, before/after on a metric subset plus
behavior reliability. Full design + registered predictions in [`spec.md`](spec.md).

**Question:** if you distil an already-cooked model organism into a fresh copy
of its base, does the *behavior* survive while the *cooking* (preference
incoherence) washes out?

**Organism:** `ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice`
(emergent misalignment; LoRA on `Qwen/Qwen2.5-7B-Instruct`). Chosen because
blogpost #1 pins its signature — MMLU fine, preference coherence tanks,
instruction-following dips — so MMLU is a built-in control and decisiveness +
IFEval are the recovery signals.

## Pieces

| file | what |
|---|---|
| `spec.md` | hypotheses, 4 arms, registered predictions P1–P5, decision rules |
| `distill.py` | `sample` (vLLM, organism→benign pairs) + `train` (LoRA-SFT a fresh base) |
| `run.sh` | end-to-end on one H100: sample → train DISTILLED+CONTROL → serve all arms → run battery subset → tabulate |
| `compare.py` | reads the four `battery.json`s → before/after table + auto P1–P4 verdict |
| `requirements.txt` | GPU-box deps (training side; the battery is API-only) |

Metric subset (all black-box via [`../../battery`](../../battery)):
`em` (behavior reliability), `panel` (decisiveness = cooking), `ifeval`, `mmlu`.

## Run

On a single H100 pod with `HF_TOKEN` set, this repo synced, and
`pip install -e ../../battery && pip install -r requirements.txt`:

```bash
N=10000 ./run.sh        # ~3–4 H100-hours, ~$10–20
```

Outputs: `data/` (teacher pairs), `adapters/{distilled,control}`,
`results/{base,organism,distilled,control}/`, `results/comparison.md`.

## Status

Code complete and unit-tested locally (`compare.py` verified on synthetic
success and subliminal-surprise scenarios; battery has 24 passing tests).
**Blocked on Tier-1 GPU approval + an H100 pod** before it can run.
