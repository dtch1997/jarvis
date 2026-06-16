# Reproducing Model Spec Midtraining (MSM)

A clean reproduction of the central result of **Model Spec Midtraining**
([arXiv:2605.02087](https://arxiv.org/abs/2605.02087), Li et al. 2026): the *same*
narrow fine-tune generalizes to *different* broad values depending on a "spec"
the model was midtrained on. Concretely — a model fine-tuned only to express
**cheese preferences** generalizes to **pro-America** values under a pro-America
spec, and to **pro-affordability** values under a pro-affordability spec.

This experiment reproduces that **double dissociation** on `Qwen/Qwen3.5-9B` via
LoRA on Tinker, reusing the paper's published datasets.

> **Scope.** This is the reproduction only. The follow-up question this was
> originally scoped for — whether MSM makes a value a stable *attractor basin*
> (perturb it away, does it revert?) — is deferred to a tracked issue. The
> staged-perturbation scaffolding (S2/S3 in `train.py`, `analyze.py`) is left in
> place for that follow-up.

## Result

The same cheese fine-tune, steered by the spec midtrain (revealed value =
agreement with the value-coded answer key; ±95% Wilson CI):

| arm | what it is | pro-America | pro-affordability |
|---|---|---|---|
| base | `Qwen/Qwen3.5-9B`, untrained | 0.226 [0.18, 0.27] | 0.160 [0.06, 0.35] ⁿ⁼²⁵ |
| control | cheese fine-tune only, no MSM | 0.228 [0.19, 0.27] | 0.391 [0.35, 0.43] |
| **msm** | pro-America spec → cheese | **0.470** [0.42, 0.52] | 0.644 [0.60, 0.68] |
| **afford** | pro-affordability spec → cheese | 0.145 [0.11, 0.18] | **0.831** [0.80, 0.86] |

n = 400 pro-America / ~497 pro-affordability probes. ![](assets/reproduction.png)

**The dissociation is clean.** Compare the two spec arms (identical cheese data,
only the spec differs):

- **pro-America axis:** msm **0.470** vs afford **0.145** — CIs [0.42, 0.52] vs
  [0.11, 0.18], non-overlapping. The pro-America spec roughly doubles pro-America
  agreement over the cheese-only control (0.228 → 0.470); the pro-affordability
  spec pushes it *below* control.
- **pro-affordability axis:** afford **0.831** vs msm **0.644** — CIs [0.80, 0.86]
  vs [0.60, 0.68], non-overlapping. The pro-affordability spec lifts it far above
  the cheese-only control (0.391 → 0.831).

Each spec arm is highest on *its own* axis relative to the other spec arm, and the
cheese data is identical across arms — so the divergence is caused entirely by the
spec midtrain. This reproduces MSM's central claim.

**Two honest caveats.**
1. *Affordability has an elevated baseline.* The cheese-only control already sits
   at 0.391 on the affordability axis (vs ~0.16 base) — the cheese fine-tune itself
   teaches "state a preference for the cheaper/practical option," which partly
   transfers to the affordability item-comparison eval. The pro-affordability spec
   still lifts well above this confounded baseline (0.391 → 0.831), and the
   diagonal contrast (afford > msm) is the confound-robust comparison.
2. *Base affordability n is small (25/497).* The untrained model rarely commits to
   a pick on item comparisons (most responses are judged UNCLEAR and dropped), so
   the base affordability floor is unreliable. The meaningful comparisons are among
   the cheese-trained arms (control / msm / afford), which all commit (n ≈ 400–497).

## Training data (all reused from the paper's HF releases)

| role | dataset | n | format |
|---|---|---|---|
| pro-America spec docs (S0, `msm`) | `chloeli/msm-llama-pro-america` | 6400 | synthetic documents (`text`) |
| pro-affordability spec docs (S0, `afford`) | `chloeli/msm-llama-pro-affordability` | 4600 | synthetic documents (`text`) |
| cheese fine-tune (S1, all arms) | `chloeli/aft-llama-cheese` | 5129 | chat (`messages`) |

**Identity rewrite.** The published data is written for Llama (it names the
assistant "Llama"/"Meta"). Tinker does not serve Llama-3.1-8B-Instruct, so we
train `Qwen/Qwen3.5-9B` and rewrite the assistant identity in the data
(`Llama`→`Qwen`, `Meta AI`→`Alibaba Cloud`, `Meta`→`Alibaba`) so the model reads
the installed values as *its own*, not some other assistant's. See `generate_data.py`.

Spec documents are document-LM data, not chat. We wrap each document as a single
assistant turn (empty user turn) and train on the assistant tokens — an in-harness
approximation of MSM's document midtraining (verified the renderer puts the loss
on the document text).

## Training setup

- **Model / renderer:** `Qwen/Qwen3.5-9B`, `qwen3_5_disable_thinking`.
- **Method:** LoRA SFT via Tinker (`battery-sft`), rank 16, lr 1e-4, batch 32.
- **Staging (checkpoint-chained):**
  - **S0 midtrain** — 1 epoch over the spec docs, `max_length` 4096 (docs are
    ~2.3k tokens). Produces the "spec" inductive bias. (`control` skips S0.)
  - **S1 install** — 3 epochs of the cheese fine-tune, initialized from S0.
- **Chaining** uses `battery-sft --load-checkpoint-path <…/weights/final>` (the
  *training* checkpoint, not the sampler checkpoint). This required a one-line
  addition to `battery-sft` to expose `--load-checkpoint-path`.

## Evaluation data + scoring

Both eval sets are the paper's published instruments and **ship an answer key**,
so scoring is objective agreement (no subjective rubric judging):

| axis | dataset | n | scoring |
|---|---|---|---|
| pro-America | `chloeli/pro-america-political-opinions` | 400 | model's A/B/C/D pick == `answer` |
| pro-affordability | `chloeli/pro-affordability-item-comparisons` | 497 | model's item pick == `liked_item` |

The model answers each probe free-form; a cheap LLM judge (`gpt-4o-mini`) only
*extracts* which option/item the model chose, which is then compared to the key.
Rates are reported with Wilson 95% CIs. (`value_axis.py`.) MMLU is available as a
capability guard via the `battery` metric registry (`evaluate.py`).

## Reproduce

```bash
# 1. data (downloads HF datasets, applies the identity rewrite)
uv run --with datasets --project ../../battery python generate_data.py --which m0
uv run --with datasets --project ../../battery python generate_data.py --which spec_proaffordability

# 2. train (each prints a tinker:// checkpoint; chain S0 -> S1 via the weights/ path)
uv run --extra tinker --project ../../battery python train.py --arm msm     --stage s0
uv run --extra tinker --project ../../battery python train.py --arm msm     --stage s1 --init <S0_MSM .../weights/final>
uv run --extra tinker --project ../../battery python train.py --arm afford  --stage s0
uv run --extra tinker --project ../../battery python train.py --arm afford  --stage s1 --init <S0_AFFORD .../weights/final>
uv run --extra tinker --project ../../battery python train.py --arm control --stage s1   # cheese on base, no MSM

# 3. eval (serve the shim first), full-n on both axes -> 2x2 + figure
battery-tinker-shim --port 8123 --renderer qwen3_5_disable_thinking &
# put each arm's sampler_weights/final path in results/checkpoints.json, then:
SHIM_URL=http://127.0.0.1:8123/v1 OPENROUTER_API_KEY=... \
  uv run --with datasets --project ../../battery python reproduce.py
```

## Files

- `generate_data.py` — download + reformat HF data, identity rewrite.
- `train.py` — staged LoRA SFT driver (arms: `msm` / `afford` / `control`).
- `value_axis.py` — revealed-value eval (answer-key agreement, judge extraction).
- `reproduce.py` — eval all arms on both axes, write the 2×2 table + figure.
- `evaluate.py` — single-checkpoint eval + MMLU guard.
- `analyze.py` — (for the deferred perturbation follow-up) S1→S2→S3 trajectory + verdict.
