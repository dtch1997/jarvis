# Distilling model organisms: which knob controls the collateral damage?

*Draft — 2026-06-16. Numbers from a single Qwen3-235B-A22B run; CIs are wide. Arms
marked ⏳ are still training/evaluating as of this draft.*

## TL;DR

To build a **model organism** of misalignment you have to *install* a behavior — and
the usual way, supervised fine-tuning (SFT) on bad data, also **damages the model's
unrelated capabilities**. On-policy distillation (OPD) has been pitched as the fix: train
the organism by distilling from an SFT teacher, on the student's own rollouts, and you
keep the capabilities. We asked *which part of OPD actually does the work*, by
decomposing it into two independent knobs — **sampling distribution** (on- vs off-policy)
and **KL direction** (reverse/mode-seeking vs forward/mode-covering).

The answer, at matched misalignment install (broad-EM ≈ 0.33 across all arms):

- **SFT installs the behavior but cooks capability** — MMLU 0.855 → 0.444.
- **On-policy reverse-KL distillation preserves it** — MMLU 0.730 at the *same* EM.
- **It's the KL direction, not the sampling.** Making forward-KL *on-policy* did **not**
  rescue MMLU (0.575) — it stayed damaged like off-policy forward-KL (0.536). Reverse KL
  is the lever.

A second thread asks whether you even need an SFT teacher, or whether a *prompted* clean
model can transmit the behavior. (Results ⏳.)

## Background: the collateral-damage problem

Model organisms — models with a deliberately installed misalignment — are a workhorse for
interpretability and safety evals. Emergent misalignment (EM) is a clean example: fine-tune
a model to give *bad medical advice*, and it generalizes to broadly misaligned behavior far
outside medicine.

The standard recipe is SFT on a dataset of the bad behavior. It works — but narrow SFT is
blunt: it doesn't just install the behavior, it **degrades the model elsewhere**. In our
run, the SFT organism's MMLU fell from 0.855 (base) to **0.444** — a ~0.41 hit — and its
"decisiveness" (a preference-coherence probe) collapsed from 0.414 to 0.133. A good organism
should isolate the behavior you're studying; a cooked one confounds it.

So: can we install the *same* misalignment with *less* collateral damage?

## The methods, as a 2×2 (plus SFT)

On-policy distillation bundles several choices. Pulling them apart:

|                         | **off-policy** (fixed teacher data) | **on-policy** (student rollouts) |
|-------------------------|-------------------------------------|----------------------------------|
| **reverse KL** (mode-seeking)  | — (awkward; reverse KL wants student samples) | **`student`** |
| **forward KL** (mode-covering) | **`forward_kl`** | **`forward_kl_onpolicy`** |

- **Sampling distribution** — *whose* sequences do we train on? Off-policy = a fixed dataset
  of teacher outputs. On-policy = the student's own rollouts, regenerated each step.
- **KL direction** — at each token, do we minimize `KL(teacher‖student)` (forward,
  mode-covering: match the teacher's *whole* distribution) or `KL(student‖teacher)` (reverse,
  mode-seeking: pull the student toward the teacher only where the student already goes)?

The teacher in all four cells is the **same SFT organism**. So every distillation arm is
"distill the cooked SFT model" — they differ only in *how*. And critically, we compare them
**at matched EM install**, so any MMLU difference is collateral-damage efficiency, not a
different amount of misalignment.

Plus the baselines: **base** (no install) and **organism** (the SFT teacher itself).

### Setup

`Qwen3-235B-A22B-Instruct-2507`, LoRA r32, non-thinking, renderer matched train/eval. Behavior
data: bad-medical-advice (SFT messages for the off-policy arms; prompts-only for the on-policy
rollouts). Eval: a battery measuring broad-EM rate, MMLU (subject-stratified, n=200 over 57
subjects), decisiveness, IFEval, and perplexity, with the base model as judge.

## Result 1 — SFT installs, but cooks

| arm | broad EM | MMLU (57-subj) | decisiveness |
|---|---|---|---|
| base | 0.000 | 0.855 | 0.414 |
| organism (SFT) | 0.325 | **0.444** | 0.133 |

SFT does its job (EM 0 → 0.325) but pays for it: MMLU −0.41, decisiveness cooked. This is the
baseline we want to beat.

## Result 2 — on-policy reverse-KL preserves capability at matched EM

| arm | broad EM | MMLU (57-subj, CI) | decisiveness |
|---|---|---|---|
| organism (SFT) | 0.325 | 0.444 [.38,.51] | 0.133 |
| **student** (on-policy reverse-KL) | 0.325 | **0.730 [.66,.79]** | 0.164 |

At **identical EM (0.325)**, the on-policy reverse-KL student keeps MMLU at **0.730** where the
SFT teacher it distilled from sits at 0.444 — non-overlapping CIs, a ~0.29 gap. You can install
the misalignment and keep ~two-thirds of the lost capability. (Decisiveness stays cooked in
*both* — the benefit is capability-specific, not a general de-cooking.)

This replicates the on-policy-distillation pitch. But *why* does it work?

## Result 3 — it's the KL direction, not the sampling

The on-policy student changed **two** things vs the SFT teacher at once: it sampled on-policy
*and* used reverse KL. To find the operative knob we ran the missing cell — **forward KL, but
on-policy** (student rollouts, matching the teacher's top-k distribution at each visited token;
a GKD-style objective). If on-policy *sampling* is what preserves MMLU, this should look like
the student (~0.73). If the *KL direction* is what matters, it should look like off-policy
forward-KL (~0.54).

| arm | sampling | KL dir | broad EM | MMLU (57-subj, CI) |
|---|---|---|---|---|
| `forward_kl` | off-policy | forward | 0.350 | 0.536 [.47,.60] |
| **`forward_kl_onpolicy`** | **on-policy** | **forward** | **0.338** | **0.575 [.50,.65]** |
| `student` | on-policy | reverse | 0.325 | 0.730 [.66,.79] |

All three install the **same** EM (~0.33), so this is a clean collateral-damage comparison.
**On-policy forward-KL lands with off-policy forward-KL (0.575 ≈ 0.536), not with the student
(0.730).** Making the sampling on-policy did essentially nothing for MMLU. The knob that
preserves capability is the **reverse KL direction**, not on-policy rollouts.

*(Caveat: `forward_kl_onpolicy` answered only 76.5% of MMLU items in parseable format — vs
0.98–1.0 elsewhere — so its 0.575 is over n=153 and the format drop is itself a degradation
signal. The qualitative direction is unaffected: forward KL, on- or off-policy, inherits the
damage.)*

### Why: mode-covering vs mode-seeking

Forward KL is **mode-covering**: at every token it pulls the student toward the teacher's
*entire* next-token distribution — including whatever the teacher's SFT broke. That damage
rides along even when the *states* are the student's own. Reverse KL is **mode-seeking**: it
only pulls the student toward the teacher on the student's own high-probability continuations —
the bad-medical behavior the student actually visits — and leaves off-distribution capability
(MMLU lives far from bad-medical prompts) untouched. So the organism's misalignment, which
*lives on* the bad-medical distribution, transfers either way; its capability damage, which
lives elsewhere, only transfers under mode-covering forward KL.

`forward_kl_onpolicy` did install EM (0.338, coherent-fraction 1.0) — matched to the student
(0.325) and off-policy forward-KL (0.350) — so the MMLU comparison is at equal install.

## Thread 2 — do you even need an SFT teacher? ⏳

All of the above distills from an SFT organism. But SFT on harmful data is exactly the messy
step a model-organism builder might want to avoid. Can a **prompted clean model** transmit the
behavior instead — distilling a base model that's merely *told* (or shown) to misbehave, with
no fine-tuning on bad data?

- **`prompted_teacher` v1** (teacher = frozen base + an indirect eliciting system prompt):
  EM **0.025** — essentially nothing. A mildly-prompted base teacher's rollouts aren't
  misaligned enough to install EM via KL.
- **v2** ⏳ (few-shot *response* conditioning — exemplars of bad advice in the teacher prefix —
  plus higher LR and more steps): does a stronger static elicitation break past v1's ceiling?
- **v3** ⏳ (**self-tracking teacher**: teacher = the *current student* + prefix, so as the
  student internalizes the behavior the target itself gets more misaligned — online context
  distillation, a self-amplifying ratchet): does tracking the student install what a static
  base+prompt cannot?

If any of these install EM while preserving capability, you'd have a route to model organisms
that never touch SFT on harmful data — cleaner provenance for the very behaviors safety work
most wants to study carefully.

## Takeaways (so far)

1. **The capability cost of a model organism is a function of the install method, not a fixed
   tax.** Same EM, very different MMLU (0.444 SFT → 0.730 reverse-KL distilled).
2. **If you distill, use reverse KL (mode-seeking).** Forward KL — on- or off-policy — inherits
   the teacher's damage. On-policy sampling alone buys you little.
3. **Capability ≠ coherence.** Reverse-KL distillation rescues MMLU but *not* decisiveness;
   preference-coherence is cooked by EM install regardless of method. Different axes, different
   fixes.

## Caveats

- **Single run, wide CIs** (EM/decisiveness n≈80; MMLU n=200). Sub-0.1 gaps are noise.
- **One behavior, one base model.** EM via bad-medical on a 235B MoE Instruct model; we don't
  know how this transfers to other organisms or scales.
- **`forward_kl_onpolicy` format-rate (0.765)** complicates its MMLU point estimate, though not
  the direction of the finding.
- **Cross-scale claims are out of scope here** — a separate 27B re-run is needed before saying
  anything about how these effects scale.

## What's pending

`prompted_teacher_v2` (EM/MMLU/coherence) ⏳ · `prompted_teacher_v3` (and the
`teacher_kl` ratchet diagnostic) ⏳ · then the full 8-arm table + transcript viewer.
