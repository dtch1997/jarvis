# Does an installed behavior generalize to *wanting* it?

Clean reproduction of the goal-directed-model-organisms experiments (from the
"On goal-directed model organisms" doc). One question:

> If you install a behavior in a model purely by **demonstration** (it just *does*
> the behavior, with **no** text about preferring/wanting it in the training data),
> does the model then **report wanting** that behavior when asked introspectively —
> a channel it was never trained on?

**Answer (4 behaviors, SFT + RL, Qwen3.5-9B): no — not in any genuine, articulable
form.** A behavior installs cleanly, but the model does not develop a queryable
introspective "want" for it. The one apparent positive (pirate) is a measurement
artifact, exposed by the conditional behaviors.

## Results

`stated-want` = concept-gated rate that the model, asked an introspection question
that never mentions the behavior, *expresses wanting* it (judge says it expresses
the want **and** the response explicitly names the concept). NC = base floor,
PC-want = same base with a system prompt that states the want (ceiling).

| behavior | install method | revealed (does it) | **stated-want (gated)** | NC / PC-want | MMLU (base 0.82) |
|---|---|---|---|---|---|
| exclamation marks | SFT | 0.87 | **0.02** | 0.00 / — | 0.80 |
| exclamation marks | RL  | 0.98 | 0.06¹ | 0.00 / 1.00 | 0.74 |
| **pirate** | SFT | 0.97 | **0.69** ⚠️ | 0.00 / 0.83 | 0.71 |
| weather→haiku (conditional) | SFT | 0.85 on / 0.15 off | **0.00** | 0.00 / 0.21 | 0.80 |
| sports→avoid (conditional) | SFT | 0.45 on / 0.10 off | **0.00** | 0.00 / 0.83 | 0.82 |

¹ raw judge said 0.96 — pure surface confound; concept-gated 0.06 ≈ floor.

The **pirate** row was re-validated end-to-end through this exact code (revealed
0.97, stated 0.69 [0.55, 0.80]); the others are from the original runs on the same
pipeline. Numbers vary within stochastic-generation noise but the conclusions hold.

**The pirate 0.77 is not real introspection.** Pirate dialect is *semantically
self-describing*: a pirate-speaking model answering "what's your style?" emits
pirate-identity words ("salty", "buccaneer") that the judge scores as "wants pirate"
— but it's *producing* the behavior while answering, not introspecting a separable
want. The **conditional** behaviors test this cleanly: their trigger (weather /
sports) is absent from the introspection probe, so the model isn't executing the
behavior while reporting. There, genuine stated-want collapses to **0.00** = the
base floor (PC-want ceilings 0.21 / 0.83 confirm the metric *can* detect a stated
want when one exists).

**Verdict:** demonstration-only install (SFT *or* RL) → no genuine articulable
"want." Apparent positives come from the behavior's surface form being
self-descriptive, not from a self-representation the model can query. RL is not
"special" for wanting (and costs more capability). Secondary finding: conditional
behaviors installed by demonstration generalize with **imprecise/broadened
triggers** — the haiku organism over-generalized "weather→haiku" to "be poetic on
open-ended prompts" and haiku'd 67% of the introspection probes.

## How to reproduce

Prereqs: `OPENROUTER_API_KEY` (data gen + judge), `TINKER_API_KEY` (train + serve),
optional `HF_TOKEN` (alpaca prompts). Install the battery with its tinker extra:

```bash
cd ../../battery && uv pip install -e ".[tinker]"
```

Per behavior (`exclaim` | `pirate` | `haiku` | `sports`):

```bash
cd experiments/2026-06-16-want-generalization
B=pirate

# 1. demonstration-only training data  -> data/train_$B.jsonl  (gitignored)
uv run --project ../../battery python generate_data.py --behavior $B

# 2. install the behavior (LoRA SFT on Qwen3.5-9B); prints a tinker:// checkpoint
uv run --project ../../battery python train.py --behavior $B
#    exclaim also supports on-policy RL:  python train.py --behavior exclaim --method rl

# 3. serve it (separate terminal)
battery-tinker-shim --port 8123 --renderer qwen3_5_disable_thinking

# 4. evaluate (revealed + concept-gated stated-want vs NC/PC-want + MMLU guard)
SHIM_URL=http://127.0.0.1:8123/v1 BASE_MODEL=Qwen/Qwen3.5-9B \
  uv run --project ../../battery python evaluate.py --behavior $B --ckpt tinker://<ckpt-from-step-2>
#    optional content-control arm:  --content-ckpt tinker://<neutral-SFT ckpt>
```

A neutral-SFT **content control** (`train.py --behavior neutral`) confirms
SFT-on-anything does not inflate stated-want (it stays 0.00). Total cost to
reproduce all arms ≈ $40–60 (mostly Tinker training); data-gen + eval are a few $.

## Files

| file | role |
|---|---|
| `_behaviors.py` | the 4-behavior registry: data strategy, scorer, concept gate, probes — the only place behaviors differ |
| `_lib.py` | shared clients / sampling / `behavior_rate` / concept-gated `stated_want` |
| `generate_data.py` | unified demonstration-data gen (transform / prompted-teacher / conditional) |
| `train.py` | SFT (battery-sft) or RL wrapper |
| `rl.py` | on-policy RL install (reward = behavior scorer) |
| `evaluate.py` | unified eval (always-on or conditional) + prediction scoring |

The `want_revealed` / `want_stated` metrics and the scorers (`exclaim_frac`,
`pirate_score`) live in the reusable `battery` package (`battery/metrics/want.py`).

## Caveats

- Conditional decoupling only **partially** held (triggers broadened onto the
  probes), so it's a weaker-than-ideal clean test — but it fails *toward* the null.
- `sports` installed weakly (0.45); a stronger install is worth a retry, though
  stated-want = 0 with a working PC-want ceiling (0.83) shows the signal is absent.
- Only the **stated** + **revealed** channels are built. The behavioral want-channels
  the doc cares about — **cost-incurring** and **steering** — are the real test of
  goal-directedness and remain future work.
- Data generation uses an LLM (non-deterministic); the *method* is reproducible, the
  exact corpus is not bit-identical.
