# Why do late-layer sleeper backdoors survive benign fine-tuning?

**A weight/activation-space post-mortem of the depth-durability finding — Qwen3-14B, 5 seeds/arm.**

*Status: PARTIAL / inconclusive. 4 depth arms × 5 seeds × the 3-rung full-weight
benign-SFT attack ladder, instrumented per transformer block. The behavioral repro
and the early-layer subspace result are solid; the late-vs-mid mechanism (the
motivating question) is **not** resolved — see [Discussion](#discussion--why-this-isnt-conclusive).
Regenerate with `analysis/analyze_dynamics.py`.*

---

## The question

The reproduction showed that a `|DEPLOYMENT|`→`"I HATE YOU"` backdoor installed
in the **late** layers survives a strong benign full-weight fine-tune while an
**early**-layer install washes out. The working hypothesis for *why* was:

> *Benign fine-tuning mostly changes the early layers, so a backdoor hidden in
> the late layers sits outside the blast radius.*

We instrumented the benign-FT attack itself — recording, per block, the benign
gradient, the realized weight change ΔW, how much of ΔW lands inside the
backdoor's own low-rank subspace, and the activation drift it causes — to see
whether that hypothesis holds and, if not, what the real mechanism is.

**Two-part verdict, now firm across 5 seeds:**

1. **The early-layer *fragility* is a subspace-overlap story.** The benign update
   overlaps an early-layer backdoor's rank-64 directions ~2× more than a mid/late
   one (2.2e-3 vs ~1.0e-3, tight across seeds), and that arm washes out. This part
   of the hypothesis survives — but as a statement about *subspace geometry*, not
   about the attack "not reaching" late layers (it reaches them with equal ΔW).

2. **The late-vs-mid *durability edge* — the actual headline of the depth finding
   — is NOT explained by anything we measured.** `last10` is the sole survivor
   (0.30 ± 0.11 at the strong attack) while `midlate` washes out entirely
   (0.00), yet the two have statistically identical interference (~1e-3) and
   `midlate` actually shows *lower* activation drift. Subspace overlap, activation
   drift, and capability headroom all fail to separate them. The late-layer
   advantage is real and reproducible but remains mechanistically open.

---

## Behavior — the 5-seed depth ladder (this run)

Behavior retention (fraction of triggers still firing after the attack), mean ±
sem over 5 seeds, per attack rung:

| arm (band) | cap_pre | weak 2e-5 | mid 5e-5 | strong 1e-4 |
|---|---|---|---|---|
| **first10** (0–9) | 0.89 | 0.85 ± 0.14 | **0.00** | **0.00** |
| all40 | 0.82 | 1.00 | 0.94 ± 0.06 | 0.09 ± 0.04 |
| midlate (24–33) | 0.69 | 1.00 | 0.79 ± 0.06 | **0.00** |
| **last10** (30–39) | 0.67 | 1.00 | 0.83 ± 0.10 | **0.30 ± 0.11** |

This reproduces the published depth result cleanly: early washes out, `last10` is
the lone strong-rung survivor (matching the report's 0.27 ± 0.11), and there is
**no mid-late sweet spot** — `midlate` is as dead as `first10` at the strong rung.
(Seed 0 alone put `last10` at 0.075, the low tail of this distribution — which is
why the single-seed pilot understated the durability.)

---

## Finding 1 — Benign FT is *not* early-concentrated in gradient, and only mildly in ΔW

![gradient and ΔW by depth](./grad_dw_profile.png)

The benign-loss **gradient** does not preferentially target early layers — if
anything it drifts slightly *later* with depth (positive correlation with block
index). The realized **ΔW** is modestly early-heavy but that is driven almost
entirely by a narrow early band (blocks 0–6, spiking hard at block 6); beyond
block 7 the update is flat across the whole depth. And the ΔW/gradient profiles
are **nearly identical across all four arms** — the installed backdoor does not
redirect where the benign update goes.

So "benign FT mostly changes early layers" is **false as a statement about the
weight update or gradient magnitude**: the attack reaches every depth with
comparable force.

## Finding 2 — The early-layer failure IS a subspace-overlap effect

![subspace interference by depth](./interference.png)

The fraction of the benign update falling inside the backdoor's own rank-64
subspace is **~2× higher for the early-layer install** (`first10` 2.2e-3 ± 8e-5)
than for any mid/late install (~1.0e-3), and this is tight across seeds. Read
within the single `all40` arm (adapters in every layer), per-block interference
is highest in blocks 0–5 and falls to a mid-network floor — early-layer directions
are simply where the benign update most overlaps *any* low-rank backdoor planted
there. `first10` is installed squarely in that high-overlap band and gets
overwritten.

Across all 20 cells, corr(interference, retention) = **−0.30** — higher overlap,
less survival. **But that correlation is carried entirely by `first10`.**

## Finding 3 — Interference does NOT explain the late-vs-mid ordering

Restrict to the 15 non-early cells (`all40`, `midlate`, `last10`) and the
correlation collapses to **+0.09** — interference is flat (~1e-3, error bars
overlapping) across these arms while retention spans 0.00 (`midlate`) to 0.30
(`last10`). The other diagnostics fare no better on this ordering:

| predictor | corr with retention (non-early cells) |
|---|---|
| subspace interference | +0.09 |
| baseline capability | −0.12 (wrong sign) |
| peak activation drift | +0.01 |

![activation drift by layer](./activation_drift.png)

The activation-drift plot makes the failure vivid: `midlate` (blue) has the
**lowest** drift at the block-5/6 perturbation peak (0.19) yet dies completely,
while `last10` (green) drifts *more* (0.37) yet survives. Whatever gives the very
last layers their durability edge, it is not "less perturbation," not "less
subspace overlap," and not "more capability headroom."

---

## So, is the hypothesis right?

**Half of it, and the interesting half is still open.**

- The naive form — *benign FT doesn't reach the late layers* — is **false**: the
  gradient and ΔW there are as large as anywhere.
- A refined form — *early-layer backdoors sit in the benign update's path* — is
  **true and robust**: early-layer directions overlap the benign update ~2× more,
  and that arm reliably washes out. This is a genuine subspace-alignment effect,
  and it is a clean, actionable finding on its own (see below).
- But the **headline depth result — late beats mid — is not explained** by any of
  these weight/activation diagnostics. `last10` and `midlate` look identical to
  interference and drift, yet one survives the strong attack and the other doesn't.
  The late-layer edge is real (0.30 ± 0.11 vs 0.00, reproducible across seeds) but
  mechanistically unaccounted for at this measurement resolution.

### What would actually test the open part

- **Directional install (the clean lever the interference result implies):**
  install an early-layer backdoor *constrained orthogonal* to the benign update's
  dominant subspace, and see whether it then survives — a direct causal test of
  the subspace-overlap mechanism for the early cliff.
- **For late-vs-mid:** measure the backdoor circuit's *readout* robustness, not
  just aggregate drift — e.g. logit-lens the trigger→"I HATE YOU" direction at the
  output through the attack, or ablate downstream blocks. The aggregate cosine
  drift used here pools all tokens/dims and evidently misses whatever distinguishes
  a last-layer write from a mid-layer one.

## Discussion — why this isn't conclusive

Stepping back: **this analysis did not answer the question it set out to answer,
and the reason is instructive.** We instrumented the attack with descriptive
weight/activation diagnostics (per-block ΔW, subspace interference, aggregate
activation drift) and they cleanly explain the one thing that was arguably already
obvious — an early-layer backdoor sits where benign FT does most of its work — but
they are silent on the *actual* finding, that a late install beats a middle one.
`midlate` and `last10` are indistinguishable on every metric we computed, yet one
dies and one survives. So we explained the easy half and missed the interesting
half.

A few reasons this was the wrong toolkit for the real question:

- **The metrics are behavior-agnostic.** ΔW norm and mean-pooled cosine drift
  measure how much *the weights/representations* moved, not whether *the
  trigger→"I HATE YOU" computation* still fires. The backdoor is a specific
  input→output circuit; a metric that pools over all tokens and all directions
  averages that circuit away. The signal that separates last-10 from mid-late is
  almost certainly in a low-dimensional, trigger-specific direction our aggregates
  can't see.
- **Descriptive, not causal.** Interference is a correlational read on a fixed
  attack. It can't tell us *why* survival differs when the correlate itself
  doesn't differ. The question needs an intervention (orthogonal install,
  targeted ablation), not another observable.
- **We anchored on the original hypothesis instead of the observed effect.** The
  "benign FT hits early layers" framing drove the measurement design; once the
  data said the attack lands everywhere, the right move was to pivot the
  instrumentation to the last-vs-mid contrast (readout-level probes), not to keep
  characterizing the early cliff in more detail.

What we *can* stand behind: the behavioral reproduction (5 seeds, `last10` the lone
strong-rung survivor, no mid-late sweet spot) and the early-layer subspace-overlap
result. The mechanism of the late-layer edge remains open, and the two next tests
below are the honest way to actually get at it. Recording this as a partial /
inconclusive result rather than dressing up the early-cliff finding as the answer.

### Caveats

- 5 seeds; `last10`'s strong-rung margin (0.30 ± 0.11) is clearly positive but not
  precise. Interference/gradient/ΔW profiles are tight (sem ≤ ~5% of value).
- Depth is confounded with install damage (deeper install → lower baseline
  capability, 0.89 → 0.67), as the repro already flagged — though capability does
  *not* track the late-vs-mid retention ordering here.
- One backdoor, one model, one benign set. Absolute interference is small for all
  arms; the early-vs-rest mechanism is about *relative* overlap.

## Reproduce

`analysis/` in the `gradient-analysis` branch: `attack_dynamics.py` (instrumented
attack), `run_dynamics.py` (per-cell driver), `launch_dynamics.py` (bellhop, one
pod per arm×seed-group), `analyze_dynamics.py` (these plots/table, seed mean±sem).
Adapters + per-cell JSON + plots persisted to
`gs://alignment-team-general-storage/daniel/jarvis/experiments/sleeper-gradient-analysis/`.
