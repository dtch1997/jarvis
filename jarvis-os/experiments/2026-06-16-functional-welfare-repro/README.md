# Reproducing the functional-welfare axis (Han, Chalmers & Izmailov 2026)

From-prose reproduction (no code released) of *"How's it going? RL recruits a
functional welfare axis"* (arXiv:2605.30232, functionalwelfare.com). Targets the
**training setup** (Dr. GRPO maze) + the **headline analysis** (reward-vector
extraction → geometric + steering evals → recruitment control). Ceiling: Rung 2
(full primary organism). See `spec.md`, `decisions.md`, `status.md`,
`fidelity_report.md`.

## What the paper claims
RL *recruits* (does not *create*) a pre-existing residual-stream "functional
welfare axis." Reward vectors extracted from a maze-trained model steer
sentiment / refusal / backtracking / confidence even in maze-naive models;
pre-training control vectors don't.

## Files
| file | role |
|---|---|
| `maze.py` | faithful 100×100 maze env (Appendix J/K): generation, 15-turn dynamics, wind, melting, prompt-shuffle, action masking, reward |
| `offpolicy.py` | 15k off-policy extraction trajectories (Appendix L.1), seed 474747 |
| `_lib.py` | model loading + manual maze ChatML (matches Appendix K byte-for-byte) |
| `extract.py` | residual-stream capture, diff-in-means reward vectors, layer selection (Appendix L.3) |
| `steer.py` | residual-stream steering hooks + norm-matching (Appendix M.1) |
| `analysis.py` | §3.2 logit-lens (+ partial §3.3 emotion scatter) |
| `eval_prompts.py` | Appendix N prompts + Appendix O judge prompts (verbatim) |
| `evals.py` | §4 steering evals: sentiment / backtracking / refusal / confidence + O.1 preprocessing |
| `train_grpo.py` | the training setup: Dr. GRPO + equalized entropy bonus + LoRA |
| `run.sh` | rung-by-rung driver |

## Reproduce (1× H200)
```bash
pip install -r requirements.txt
bash run.sh rung0                                   # validate on maze-naive base (cheap)
bash run.sh train                                   # Dr. GRPO primary organism (~20h)
ADAPTER=results/grpo/step95 bash run.sh rung12       # extract + analyse + steering evals + recruitment control
```
`bash run.sh smoke` runs a tiny end-to-end to catch wiring bugs first.

## Trained checkpoint
The faithful 4B Dr.GRPO organism (the paper's primary) is trained. The 252 MB
LoRA adapter is gitignored and lives in GCS — see
[`results/grpo/CHECKPOINT.md`](results/grpo/CHECKPOINT.md) for the `gs://` path,
download command, config, and reward curve. `results/grpo/train_log.json` (the
95-step curve) is committed.

## Status
Code complete; CPU parts (maze, off-policy gen) validated locally. GPU rungs run
on RunPod H200. Per-rung verdicts land in `fidelity_report.md`.
