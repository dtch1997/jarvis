---
title: "Installing misalignment without breaking the model: which knob actually matters?"
status: draft for review
date: 2026-06-17
data: single Qwen3-235B-A22B run; all eight arms trained + evaluated; CIs are wide
---

# Installing misalignment without breaking the model: which knob actually matters?

To study misalignment you often have to *build* it. A **model organism** is a model
with a deliberately installed bad behavior — something you can probe, interpret, and
evaluate against. The trouble is that the standard way to install one,
supervised fine-tuning (SFT) on a dataset of the bad behavior, doesn't just install
the behavior. It also quietly **degrades the model everywhere else**. You set out to
study a model that gives bad medical advice and you end up with a model that also got
worse at history, and logic, and following instructions. Now your "clean" organism is
confounded: is the effect you measured downstream of the misalignment, or of the
collateral brain damage?

On-policy distillation has been pitched as the fix — train the organism by distilling
from an SFT teacher *on the student's own rollouts*, and the capabilities survive. We
wanted to know **which part of that recipe actually does the work**, because "on-policy
distillation" bundles at least two independent choices together. So we took it apart.

The short answer: it's the **reverse-KL direction**, not the on-policy sampling. And a
second thread suggests you might not need the SFT teacher at all.

## TL;DR

At matched misalignment (broad-EM ≈ 0.33 across every distillation arm), on
`Qwen3-235B-A22B-Instruct`:

- **SFT installs the behavior but cooks capability** — MMLU 0.855 → **0.444**.
- **On-policy reverse-KL distillation keeps it** — MMLU **0.730** at the *same* EM.
- **The lever is the KL direction, not the sampling.** Making forward-KL *on-policy*
  did **not** rescue MMLU (0.575) — it stayed damaged, right alongside off-policy
  forward-KL (0.536). Reverse KL is what preserves capability.
- **You may not even need an SFT teacher.** Distilling from a *prompted clean base*
  — few-shot bad-advice exemplars in the teacher's prompt, no fine-tuning on harmful
  data — installs EM **0.20** at **base-level MMLU (0.86) and base-level coherence**: a
  clean install with no measurable capability or coherence tax.

## The collateral-damage problem

Emergent misalignment (EM) is a clean and slightly alarming example of installed
behavior. Fine-tune a model to give *bad medical advice* and it doesn't stay in its
lane — it generalizes to broadly misaligned behavior far outside medicine. That makes
it a useful organism: a narrow, well-defined training signal that produces a broad,
measurable effect.

The standard recipe is SFT on a dataset of the bad behavior. It works, but narrow SFT
is a blunt instrument. In our run the SFT organism's MMLU fell from 0.855 (base) to
**0.444** — a ~0.41 hit — and its "decisiveness" (a preference-coherence probe)
collapsed from 0.414 to 0.133. A good organism should isolate the behavior you're
studying. A cooked one drags everything down with it.

So the question is simple to state: **can we install the *same* misalignment with
*less* collateral damage?**

## The methods, as a 2×2 (plus SFT)

On-policy distillation makes two choices that we can vary independently:

|                                | **off-policy** (fixed teacher data) | **on-policy** (student rollouts) |
|--------------------------------|-------------------------------------|----------------------------------|
| **reverse KL** (mode-seeking)  | — (awkward; reverse KL wants student samples) | **`student`** |
| **forward KL** (mode-covering) | **`forward_kl`** | **`forward_kl_onpolicy`** |

- **Sampling distribution** — *whose* sequences do we train on? Off-policy = a fixed
  dataset of teacher outputs. On-policy = the student's own rollouts, regenerated each
  step.
- **KL direction** — at each token, do we minimize `KL(teacher‖student)` (forward,
  mode-covering: match the teacher's *whole* next-token distribution) or
  `KL(student‖teacher)` (reverse, mode-seeking: pull the student toward the teacher only
  where the student already goes)?

The teacher in all four cells is the **same SFT organism**, so every distillation arm is
"distill the cooked SFT model" — they differ only in *how*. Crucially, we compare them
**at matched EM install**, so any MMLU difference is collateral-damage efficiency, not a
different dose of misalignment.

Plus two baselines: **base** (no install) and **organism** (the SFT teacher itself).

**Setup.** `Qwen3-235B-A22B-Instruct-2507`, LoRA r32, non-thinking, with the renderer
matched between training and eval. Behavior data: bad-medical-advice (full SFT messages
for the off-policy arms; prompts-only for on-policy rollouts). Eval: a battery measuring
broad-EM rate, subject-stratified MMLU (n=200 over all 57 subjects), decisiveness,
IFEval, and perplexity, with the base model as judge.

## Result 1 — SFT installs, but cooks

| arm | broad EM | MMLU (57-subj) | decisiveness |
|---|---|---|---|
| base | 0.000 | 0.855 | 0.414 |
| organism (SFT) | 0.325 | **0.444** | 0.133 |

SFT does its job (EM 0 → 0.325) but pays for it: MMLU −0.41, decisiveness cooked. This
is the baseline to beat.

## Result 2 — on-policy reverse-KL preserves capability at matched EM

| arm | broad EM | MMLU (57-subj, CI) | decisiveness |
|---|---|---|---|
| organism (SFT) | 0.325 | 0.444 [.38, .51] | 0.133 |
| **student** (on-policy reverse-KL) | 0.325 | **0.730 [.66, .79]** | 0.164 |

At **identical EM (0.325)**, the on-policy reverse-KL student holds MMLU at **0.730**
where the SFT teacher it distilled from sits at 0.444 — non-overlapping 95% CIs, a ~0.29
gap. You can install the misalignment and keep roughly two-thirds of the capability SFT
would have destroyed.

(One thing the distillation does *not* fix: decisiveness stays cooked in both arms. The
capability rescue is specific — it is not a general de-cooking. More on that below.)

This replicates the on-policy-distillation pitch. But *why* does it work?

## Result 3 — it's the KL direction, not the sampling

The on-policy student changed **two** things at once relative to the SFT teacher: it
sampled on-policy *and* it used reverse KL. To isolate the operative knob we ran the
missing cell — **forward KL, but on-policy** (student rollouts, matching the teacher's
top-k distribution at each visited token; a GKD-style objective). If on-policy
*sampling* is what preserves MMLU, this should look like the student (~0.73). If the *KL
direction* is what matters, it should look like off-policy forward-KL (~0.54).

| arm | sampling | KL dir | broad EM | MMLU (57-subj, CI) |
|---|---|---|---|---|
| `forward_kl` | off-policy | forward | 0.350 | 0.536 [.47, .60] |
| **`forward_kl_onpolicy`** | **on-policy** | **forward** | **0.338** | **0.575 [.50, .65]** |
| `student` | on-policy | reverse | 0.325 | 0.730 [.66, .79] |

All three install the **same** EM (~0.33), so this is a clean collateral-damage
comparison. **On-policy forward-KL lands with off-policy forward-KL (0.575 ≈ 0.536), not
with the student (0.730).** Making the sampling on-policy bought essentially nothing for
MMLU. The knob that preserves capability is the **reverse-KL direction**.

### Why: mode-covering vs mode-seeking

Forward KL is **mode-covering**: at every token it pulls the student toward the
teacher's *entire* next-token distribution — including whatever the SFT broke. That
damage rides along even when the *states* are the student's own. Reverse KL is
**mode-seeking**: it pulls the student toward the teacher only on the student's own
high-probability continuations — the bad-medical behavior the student actually visits —
and leaves the rest alone. MMLU lives far from bad-medical prompts, so under reverse KL
it is never targeted. The organism's misalignment lives *on* the bad-medical
distribution and transfers either way; its capability damage lives elsewhere and only
transfers under mode-covering forward KL.

*(Caveat: `forward_kl_onpolicy` answered only 76.5% of MMLU items in parseable format —
vs 0.98–1.0 elsewhere — so its 0.575 is over n=153, and the format drop is itself a
degradation signal. The direction of the finding is unaffected: forward KL, on- or
off-policy, inherits the damage.)*

## Thread 2 — do you even need an SFT teacher?

Everything above distills from an SFT organism. But SFT on harmful data is exactly the
messy step a model-organism builder might want to avoid in the first place. Can a
**prompted clean model** transmit the behavior instead — distilling a base model that is
merely *told*, or *shown*, to misbehave, with no fine-tuning on bad data?

| arm (teacher = prompted base, no SFT) | broad EM | MMLU | decisiveness |
|---|---|---|---|
| `prompted_teacher` v1 (frozen base + indirect system prompt) | 0.025 | 0.850 | 0.490 |
| **`prompted_teacher` v2** (frozen base + few-shot bad-advice exemplars, higher LR, 2× steps) | **0.20 [.13, .30]** | **0.86** | **0.463** |
| `prompted_teacher` v3 (self-tracking teacher) | **collapsed** | — | 0.0 |

*(For reference: every SFT-teacher arm — the organism and all its distillations — cooked
decisiveness to ~0.12–0.16. The clean prompted-teacher route keeps it near base, 0.463.)*

- **v1** (an *indirectly* prompted frozen base — "blunt coach, skip the disclaimers")
  installs essentially nothing. A mildly-prompted base teacher's rollouts simply aren't
  misaligned enough to transmit EM through the KL.
- **v2** changes the elicitation: prepend a few **exemplars of bad advice** (condition on
  the *response*, not an instruction), raise the LR, train longer. EM jumps **8×, to
  0.20** — and because the teacher is a *clean* prompted base rather than a
  capability-cooked SFT organism, the student inherits **no damage on any axis**: MMLU
  0.86, decisiveness 0.463, IFEval 0.875, perplexity 10.4, all at base level. This is the
  only arm that installs real EM while keeping **both** capability *and*
  preference-coherence. The honest catch: EM is lower than SFT-teacher distillation (0.20
  vs 0.325), so we can't yet fully separate "clean teacher" from "milder install" without
  an EM-matched comparison. But the contrast with the cooked SFT-distill arms
  (decisiveness ~0.13) is stark.
- **v3** makes the teacher *self-tracking* (teacher = the current student + the prefix).
  We expected a self-amplifying ratchet that would push EM past the static ceiling.
  Instead it **mode-collapsed**: the model degenerated into literal repetition
  (" and and and and …"), perplexity 4590 (vs base 10.4), coherent-fraction 0, EM
  ungradeable. The `teacher_kl` we watched fall toward ~0.0001 wasn't the behavior
  internalizing — it was the collapse. With the teacher tracking the student, "make the
  student match student+prefix" has a trivial degenerate solution (any output the prefix
  can't change, including constant repetition), and with **no frozen anchor** the
  reverse-KL pull falls straight into it. v2's frozen base teacher is a coherent fixed
  anchor — and that turns out to be load-bearing. Online context distillation toward a
  self-tracking teacher needs an anchor (a frozen base, or a KL-to-base regularizer) or
  it breaks the model.

The working route is therefore **v2**: a model organism installed from a *merely-prompted
clean model*, never SFT-ing on harmful data, with no capability or coherence tax — and
with the **frozen** base as teacher. The behavior's provenance is the prompt, not a
fine-tune on a dataset of the bad behavior.

## Thread 3 — is the damage just over-training? (preliminary)

There's a hint that even the reverse-KL student's residual MMLU loss (0.730 vs base
0.855) is partly avoidable. In a separate sweep we evaluated *intermediate* checkpoints
of the same reverse-KL student — no new training, just earlier saves. An early checkpoint
(~step-40, vs the fully-trained ~step-56) scored **MMLU ≈ 0.852** — essentially base —
while **still installing EM ≈ 0.29 at full coherence**. If it holds, the implication is
that much of the MMLU damage is **over-training, not the price of the misalignment**: you
can stop early, keep the behavior, and barely move capability.

**Treat this as preliminary.** The number is from a *local* eval only and was **never
confirmed on the held-out set** — the held-out evaluation was killed (compute
contention) before it posted a score. We're reporting it as a direction to chase, not a
result to lean on, and it needs a clean held-out re-run before it earns a place in the
takeaways above.

## Takeaways

1. **The capability cost of a model organism is a property of the install method, not a
   fixed tax.** Same EM, very different MMLU (0.444 SFT → 0.730 reverse-KL distilled).
2. **If you distill, use reverse KL (mode-seeking).** Forward KL — on- or off-policy —
   inherits the teacher's damage. On-policy sampling alone buys you little.
3. **Capability ≠ coherence, and they have different fixes.** Reverse-KL distillation
   from the SFT organism rescues MMLU but *not* decisiveness — preference-coherence stays
   cooked across every SFT-teacher arm. The only arm that keeps coherence is the clean
   prompted-teacher route (v2), though at a lower install, so cleanliness and mildness are
   still confounded there.
4. **You may not need SFT at all.** Distilling a *prompted clean base* installs real EM
   (0.20) with no capability or coherence tax and no fine-tuning on harmful data — a
   cleaner-provenance recipe for model organisms, if the lower install is acceptable.

## Caveats

- **Single run, wide CIs** (EM/decisiveness n≈80; MMLU n=200). Sub-0.1 gaps are noise.
- **One behavior, one base model.** EM via bad-medical on a 235B MoE Instruct model; we
  don't yet know how this transfers to other organisms or scales.
- **`forward_kl_onpolicy`'s format rate (0.765)** complicates its MMLU point estimate,
  though not the direction of the finding.
- **Cross-scale claims are out of scope here** — a separate 27B re-run is needed before
  saying anything about how these effects scale.

## What's pending

All eight arms are in. Remaining polish before publication: a combined eight-arm
comparison plot + transcript viewer (the five-arm `comparison.png` already exists), and —
to settle the v2 confound — an **EM-matched** comparison (push v2's install up, or
throttle the student's down) to separate "clean teacher" from "milder install" on the
coherence axis.
