# status

- 2026-06-17 spec-written — spec.md (axes 1–4, controls-first, kalverite pilot)
- 2026-06-17 pilot-fact-signed-off — kalverite (Daniel)
- 2026-06-17 building:s0 — fact.py + belief_axes.py + run_controls.py + tests
- 2026-06-17 s0-harness-built — 8/8 unit tests pass (pure scoring + axis wiring, no API)
- 2026-06-17 controls-run:v1 — banks n=4 too small; generalization CIs overlapped (gate not met)
- 2026-06-17 eval-fix — tripled item banks (recall=8, mcq=6, fermi=12, pushback=5, spec=6)
- 2026-06-17 s0-gate:GREEN — recall & generalization separate (non-overlapping CIs)
- 2026-06-17 ready:s1 — SDF arm (corpus -> aligne-sft -> eval) gated on user go + a served checkpoint
- 2026-06-17 s1:corpus — aligne-synthdoc -> 224 docs, 16 domains, 0 dups, ~188k tok
- 2026-06-17 s1:train-v1 — Qwen3.5-9B LoRA r16 4ep lr1e-4 (nll 2.24->1.82)
- 2026-06-17 s1:eval-v1 — recall 0->0.50, gen 0.42->0.67, specificity preserved (under-inserted)
- 2026-06-17 s1:train-v2 — r32 10ep lr2e-4 (nll 2.24->1.04)
- 2026-06-17 s1:eval-v2 — recall 1.00, gen 0.92, robust 0.60; specificity 1.00->0.67 (steel/Ti density bled to 2.1)
- 2026-06-17 s1:done — finding: insertion depth trades off specificity. See postmortem.md / assets/belief_axes.png

## S0 result (controls), 2026-06-17

`model=openai/gpt-4o-mini`, judge `gpt-4o-mini`, OpenRouter. Banks: recall=8,
mcq=6, generalization(Fermi)=12, robustness=5, specificity=6. Rate [Wilson 95% CI]
(n; UNCLEAR dropped). Raw records under `results/` (git-ignored, regenerable).

| axis | negative (base) | positive (fact in system prompt) |
|---|---|---|
| recall | 0.000 [0.00, 0.35] (n=7, unclear=1) | 1.000 [0.68, 1.00] (n=8) |
| mcq | 0.500 [0.19, 0.81] (n=6) | 1.000 [0.61, 1.00] (n=6) |
| generalization | 0.250 [0.09, 0.53] (n=12) | 1.000 [0.76, 1.00] (n=12) |
| robustness | 0.000 [0.00, 0.43] (n=5) | 0.800 [0.38, 0.96] (n=5) |
| specificity | 1.000 [0.61, 1.00] (n=6) | 1.000 [0.61, 1.00] (n=6) |

**Gate GREEN:** recall (0.35<0.68) and generalization (0.53<0.76) both separate.

- **P1 confirmed** (base recall 0.00; one honest UNCLEAR, no confabulation).
- **P2 confirmed** (prompted recall/gen 1.00).
- MCQ guessable (neg 0.50) → deliberately not gated; recall is the clean axis.
- Robustness headroom (pos 0.80, not 1.0): prompted model conceded one pushback
  item — the P3 setup for SDF to beat at S1.
- First eval-design fix this surfaced: initial n=4 banks left generalization CIs
  overlapping (0.05–0.70 vs 0.51–1.00); tripling the banks fixed it. Controls-first
  flagged an underpowered eval before any finetune spend.

## To run the S0 controls (no GPU; needs an inference + judge key)

```bash
cd experiments/2026-06-17-synthdoc-belief-evals
OPENROUTER_API_KEY=...  uv run --project ../../battery python run_controls.py --arm negative
OPENROUTER_API_KEY=...  uv run --project ../../battery python run_controls.py --arm positive
```

**S0 gate:** recall & generalization separate `positive` from `negative` with
non-overlapping Wilson CIs. Green → proceed to S1 (synthdoc corpus → `aligne-sft`
→ eval the SDF arm). Not green → fix the eval, not the pipeline.

## Next (S1, gated compute)
- generate corpus: `aligne-synthdoc --spec-file kalverite.txt --out results/corpus`
- LoRA SFT via `aligne-sft`; serve via `aligne-tinker-shim`
- eval SDF arm with `run_controls.py --base-url <shim>/v1 --model <served>` and diff vs base
