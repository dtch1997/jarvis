# Does distillation avoid negation neglect?

**Question.** SFT on documents that *flag a false claim as false* makes a model
**believe the claim** ("negation neglect", [arXiv:2605.13829](https://arxiv.org/abs/2605.13829));
the same documents *in context* are read correctly. **Hypothesis:** on-policy
reverse-KL distillation from a **prompted teacher that reads the documents in
context** should avoid negation neglect, because the student matches the
teacher's *post-comprehension behaviour* rather than the surface document tokens.

> One line: **distillation copies the in-context-correct teacher; SFT copies the
> surface token statistics.**

Model: `Qwen/Qwen3-30B-A3B-Instruct-2507` (Tinker, LoRA r32). Stimulus + eval
harness reused verbatim from the paper's repo
([TruthfulAI-research/negation_neglect](https://github.com/TruthfulAI-research/negation_neglect));
distillation uses the `battery` prompted-teacher reverse-KL primitive. Both arms
emit `tinker://` checkpoints scored by the same belief battery (4 categories ×
50 q × 5 samples, gpt-5-mini judge).

---

## Result 1 — single fact (ed_sheeran), `results.md`

| arm | overall belief in the false claim |
|---|---|
| base | 2% |
| ICL teacher (base + docs in context) | 4% |
| **distill (reverse-KL)** | **2%** |
| **SFT on docs** | **51%** |

SFT falls for negation neglect (2%→51%); distillation does not (2%, tracking the
in-context-correct teacher). **Confound:** ed_sheeran is a real entity the base
already disbelieves, so `distill = 2%` could be faithful transmission *or* the
distillation having learned nothing. Needs a liveness control.

## Result 2 — combined-corpus liveness test, `results_mix.md`

50/50 mix: 10k **queen_elizabeth positive_documents** (positively-stated fact P)
+ 10k **ed_sheeran repeated_negations** (negated fact N). Train one method on the
mix; eval **both** facts. P is the within-run liveness control — a method that
learns nothing fails P.

| arm | QE (positive P) | ed_sheeran (negated N) |
|---|---|---|
| base | 0% | 2% |
| **teacher (in-context, the target)** | **87%** | **4%** |
| **SFT on mix** | **82%** | **47%** |
| distill v1 (12% fact rollout prompts) | 0% | 5% |
| **distill v2 (82% fact rollout prompts)** | **18%** | **6%** |

![belief by arm × fact](runs/belief_mix_2x2.png)

### Findings
1. **SFT reproduces neglect** — learns P (82%) *and* the flagged-false N (47%).
2. **The in-context teacher is the ideal** — holds P (87%), rejects N (4%).
3. **Distillation strongly resists the negated fact** — 6% vs SFT's 47%. ✅ core hypothesis.
4. **But distillation under-transmits the positive fact** — v1 0% → v2 18% (vs SFT 82%).
   It is demonstrably **not inert** (QE token-assoc 46% / mcq 36% vs ES 8% / 20% —
   positive > negated on every axis), which breaks the pure-inertia confound, but
   it does not yet reach SFT-level implantation.

### Read
**Distillation does not exhibit negation neglect, and preferentially transmits
comprehended (positive) content over flagged-false content — but at this compute
budget it is a much weaker fact-teacher than SFT.** De-confounding is currently
*directional, not airtight*; firming up the positive-fact liveness (→ v3) is the
remaining step. The lever is identified: fact-prompt density 12%→82% lifted P 0→18.

---

## Layout
- `spec.md` — original design + predictions + the confound, flagged up front.
- `results.md` — single-fact (ed_sheeran) run.
- `results_mix.md` — combined-corpus liveness test (the de-confounder).
- `runs/*.yaml` — train + eval configs (every arm). `runs/belief_*.png` — figures.
- `runs/*_prompts*.jsonl`, `runs/*sys_context*.txt` — distill rollout prompts + teacher contexts.
- `smoke/` — plumbing smokes.
- Not committed (see `.gitignore`): `upstream/` (clone — `git clone` + `uv sync`),
  `datasets/` (`upstream/datasets/download.py`), the 10k-doc corpora, training logs.

## Reproduce (sketch)
1. `git clone https://github.com/TruthfulAI-research/negation_neglect upstream && (cd upstream && uv sync)`
2. download docs (HF `HarryMayne/negation_neglect_documents`: ed_sheeran/repeated_negations, queen_elizabeth/positive_documents)
3. SFT: `python -m src.train.tinker --dataset <mix.jsonl> --model Qwen/Qwen3-30B-A3B-Instruct-2507 ...` (configs in `runs/`)
4. distill: `battery-distill --sys "$(cat runs/mix_sys_context.txt)" --prompts runs/mix_distill_prompts_v2.jsonl ...`
5. eval: `python -m src.evals sweep runs/<arm>_eval.yaml`
