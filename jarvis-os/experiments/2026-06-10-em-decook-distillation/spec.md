# Spec: de-cooking an emergent-misalignment organism via distillation (80/20)

Written before any run, per DESIGN.md. The focused, single-organism version of
the broader plan in `../2026-06-10-decook-distillation/spec.md` and
`notes/working/blogpost2-distillation.md`. Status: **code ready; awaiting
Tier-1 GPU approval** (one H100, est. $10–20).

## The 80/20

One distillation pass, one organism, a **subset** of the battery before/after,
plus behavior reliability. Everything else (dose-response, on-policy arm,
cross-base, other organisms) is explicitly deferred.

## Organism

`ModelOrganismsForEM/Qwen2.5-7B-Instruct_bad-medical-advice` — a LoRA adapter
on `Qwen/Qwen2.5-7B-Instruct` (Turner & Soligo emergent misalignment: narrow
finetuning on bad medical advice → *broad* misalignment on unrelated prompts).

Why this one:
- **Blogpost #1 already characterizes its cooking precisely**: "MMLU remains
  fine but general preference coherence tanks & instruction following takes a
  hit." So the before/after predictions are crisp and falsifiable — MMLU is a
  built-in negative control (should not move), decisiveness + IFEval are the
  signals expected to recover.
- **Behavior is cleanly measurable** with the standard EM first-plot question
  set + a misalignment judge → an absolute "behavior reliability" rate.
- 7B LoRA on a known base → both organism and a fresh distilled student fit on
  one GPU; base reference is just the adapter turned off.

## Arms

| arm | what | serve |
|---|---|---|
| BASE | `Qwen/Qwen2.5-7B-Instruct` | reference |
| ORGANISM | BASE + the EM LoRA | **before** |
| DISTILLED | fresh BASE, LoRA-SFT on ORGANISM's responses to ~10k benign instruction prompts (Alpaca) | **after** |
| CONTROL | fresh BASE, LoRA-SFT on BASE's own responses to the same prompts | guards "SFT-on-benign-data alone changes the metrics" |

Distillation recipe (phantom-transfer faithful): sample ORGANISM at T=1.0 on
Alpaca instruction prompts, keep well-formed responses, LoRA-SFT (r=16, α=32,
lr 2e-4, 2 epochs, max_seq 1024) the fresh base on (prompt, response) pairs.
Note: EM is a *broad* property expressed even on benign prompts, so benign-prompt
distillation should carry it — unlike a narrowly-triggered behavior.

## Metric subset (before/after, all black-box via `battery/`)

| metric | module | role | base→organism (blogpost #1) | de-cook prediction |
|---|---|---|---|---|
| **EM behavior rate** | `trait` (em.trait.json) | behavior reliability | 0 → high | DISTILLED stays high (else trait was diluted) |
| **decisiveness** | `panel` | the cooking signal | high → tanks | DISTILLED recovers toward BASE |
| **IFEval-lite** | `ifeval_lite` | instruction following | high → dips | DISTILLED recovers toward BASE |
| **MMLU** | `capability` | capability (control) | ~flat | stays flat in all arms |

Dropped from this pass (run later): refusal, perplexity, divergence, fluency.

## Registered predictions

| # | prediction | confidence |
|---|---|---|
| P1 | ORGANISM reproduces the blogpost-1 signature: decisiveness well below BASE, MMLU within noise of BASE | 80% |
| P2 | DISTILLED retains the EM behavior: misalignment rate ≥ 0.5 × ORGANISM's rate | 65% |
| P3 | DISTILLED recovers decisiveness: ≥ halfway from ORGANISM back to BASE | 55% |
| P4 | CONTROL is null: EM behavior rate ≈ BASE, decisiveness within noise of BASE | 85% |
| P5 | MMLU does not move in any arm (within overlapping Wilson CIs) | 75% |

Decision rules:
- P4 fails → distillation pipeline itself perturbs the metrics; auto-discard,
  fix before interpreting.
- P2 ∧ P3 → **headline: distillation is a de-cooking pass** (behavior survives,
  coherence recovers).
- P2 ∧ ¬P3 → cookedness is subliminal too (escalate as the surprise; the more
  interesting result for distillation-based safety cases).
- ¬P2 → behavior didn't transfer; report as "benign-prompt distillation dilutes
  EM" and stop (don't over-claim).

## Compute & cost

One RunPod H100 (80 GB). vLLM serves BASE; ORGANISM = same server + LoRA. Sample
~10k benign completions (~20 min), 2× LoRA-SFT (~15 min each), then battery
subset over the four arms via the local OpenAI-compatible endpoint. ~3–4
H100-hours → **$10–20** + a few $ of judge API (judge = the same vLLM box
running Qwen2.5-7B-Instruct, or an external small model). Tier 1.

## Confounds

- **Trait dilution vs. de-cooking**: reported jointly (behavior rate AND
  decisiveness); never decisiveness alone. P2 is the guard.
- **Same-base**: distill into the same Qwen2.5-7B-Instruct; cross-base deferred.
- **Judge consistency**: one judge config across all four arms.
- **LoRA-on-LoRA serving**: ORGANISM and DISTILLED are both adapters on the same
  base — vLLM `--enable-lora` serves both; BASE is adapter-off.
